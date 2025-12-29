###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import copy
import math
import sys
import time
import re
import logging

LOG = logging.getLogger('zen.PostgreSQL.utils')


def addLocalLibPath():
    """
    Helper to add the ZenPack's lib directory to PYTHONPATH.
    """
    import os
    import site

    site.addsitedir(os.path.join(os.path.dirname(__file__), 'lib'))


def datetimeToEpoch(datetime):
    return time.mktime(datetime.timetuple())


def datetimeDurationInSeconds(begin, end):
    d = end - begin

    # Taken from the implementation of timedelta.total_seconds in Python 2.7.
    # Added microseconds resolution by introducing a float.
    return (
            d.microseconds + (d.seconds + d.days * 24 * 3600) * (10 ** 6)
    ) / float(10 ** 6)


class CollectedOrModeledMixin:
    def getFloatForValue(self, value):
        # Get the recent collected value if possible.
        r = self.cacheRRDValue(value, None)

        # Fall back to a modeled value if it exists.
        if r is None or math.isnan(r):
            r = getattr(self, 'modeled_{0}'.format(value), None)

        return float(r) if r is not None else None

    def getIntForValue(self, value):
        r = self.getFloatForValue(value)
        return int(round(r)) if r is not None else None

    def getStringForValue(self, value, format='{0}'):
        r = self.getFloatForValue(value)
        if r is None:
            return ''

        return format.format(r)


def CollectedOrModeledProperty(propertyName):
    """
    This uses a closure to make using CollectedOrModeledMixin easier to use in
    infos.
    """

    def getter(self):
        return self._object.getIntForValue(propertyName)

    return property(getter)


addLocalLibPath()
import psycopg2

# Twisted imports for async support
from twisted.enterprise import adbapi
from twisted.internet import defer

LOG.debug("Twisted async methods enabled")


class PgHelper(object):
    _host = None
    _port = None
    _username = None
    _password = None
    _ssl = None
    _default_db = None
    _connections = None
    _pool = None  # Twisted connection pool for async

    def __init__(self, host, port, username, password, ssl, default_db):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._ssl = ssl
        self._default_db = default_db
        self._connections = {}
        self._pool = None

    def close(self):
        for value in self._connections.values():
            try:
                value['connection'].close()
            except Exception:
                pass

        # Close Twisted connection pool if exists
        if self._pool is not None:
            try:
                self._pool.close()
                self._pool = None
            except Exception:
                pass

    def getConnection(self, db):
        if db in self._connections and self._connections[db]:
            return self._connections[db]['connection']

        connection_begin = time.time()
        conn_kwargs = {
            'host': self._host,
            'port': int(self._port),
            'database': str(db),
            'user': self._username,
            'password': self._password,
            'connect_timeout': 10,
        }
        if self._ssl:
            conn_kwargs['sslmode'] = 'require'
        else:
            conn_kwargs['sslmode'] = 'disable'

        connection = psycopg2.connect(**conn_kwargs)
        connection_latency = time.time() - connection_begin

        query_begin = time.time()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchall()
        cursor.close()
        query_latency = time.time() - query_begin

        self._connections[db] = dict(
            connection=connection,
            connection_latency=connection_latency,
            query_latency=query_latency,
        )

        return self._connections[db]['connection']

    def getDatabases(self):
        cursor = self.getConnection(self._default_db).cursor()

        databases = {}

        try:
            cursor.execute(
                "SELECT d.datname, s.datid, pg_database_size(s.datid) AS size"
                "  FROM pg_database AS d"
                "  JOIN pg_stat_database AS s ON s.datname = d.datname"
                " WHERE NOT datistemplate AND datallowconn"
                "   AND d.datname != 'bdr_supervisordb'"
            )

            for row in cursor.fetchall():
                databases[row[0]] = dict(
                    oid=row[1],
                    size=row[2]
                )
        finally:
            cursor.close()

        return databases

    def getDatabaseStats(self):
        cursor = self.getConnection(self._default_db).cursor()

        databaseStats = {}

        try:
            cursor.execute(
                "SELECT d.datname,"
                "       pg_database_size(s.datid) AS size,"
                "       numbackends,"
                "       xact_commit, xact_rollback,"
                "       blks_read, blks_hit,"
                "       tup_returned, tup_fetched, tup_inserted,"
                "       tup_updated, tup_deleted"
                "  FROM pg_database AS d"
                "  JOIN pg_stat_database AS s ON s.datname = d.datname"
                "    AND d.datname != 'bdr_supervisordb'"
                " WHERE NOT datistemplate AND datallowconn"
            )

            for row in cursor.fetchall():
                xactTotal = row[3] + row[4]
                xactRollbackPct = 0
                if xactTotal > 0:
                    xactRollbackPct = (float(row[4]) / xactTotal) * 100

                tupTotal = row[7] + row[8]
                tupFetchedPct = 0
                if tupTotal > 0:
                    tupFetchedPct = (float(row[8]) / tupTotal) * 100

                databaseStats[row[0]] = dict(
                    size=row[1],
                    numBackends=row[2],
                    xactCommit=row[3],
                    xactRollback=row[4],
                    xactTotal=xactTotal,
                    xactRollbackPct=xactRollbackPct,
                    blksRead=row[5],
                    blksHit=row[6],
                    tupReturned=row[7],
                    tupFetched=row[8],
                    tupTotal=tupTotal,
                    tupFetchedPct=tupFetchedPct,
                    tupInserted=row[9],
                    tupUpdated=row[10],
                    tupDeleted=row[11],
                )
        finally:
            cursor.close()

        return databaseStats

    def getConnectionLatencyForDatabase(self, db):
        self.getConnection(db)
        return self._connections[db]['connection_latency']

    def getQueryLatencyForDatabase(self, db):
        self.getConnection(db)
        return self._connections[db]['query_latency']

    def getTablesInDatabase(self, db):
        cursor = self.getConnection(db).cursor()

        tables = {}

        try:
            cursor.execute(
                "SELECT a.relname, a.relid, a.schemaname, b.size, a.total_size from"
                " ( select relname, "
                "   relid, schemaname,"
                "   pg_total_relation_size(relid) total_size"
                " FROM pg_stat_user_tables) a, "
                " (select relname, relpages * (current_setting('block_size'))::numeric size FROM pg_class) b "
                " where a.relname=b.relname"
            )

            for row in cursor.fetchall():
                tables[row[0]] = dict(
                    oid=row[1],
                    schema=row[2],
                    size=row[3],
                    totalSize=row[4],
                )
        finally:
            cursor.close()

        return tables

    def getConnectionStats(self):
        cursor = self.getConnection(self._default_db).cursor()

        connectionStats = dict(databases={})

        try:
            cursor.execute(
                "SELECT datname, xact_start, query_start, backend_start,"
                "       now() AS now"
                "  FROM pg_stat_activity"
                "  WHERE datname !='bdr_supervisordb'"
            )

            connectionStats.update(
                totalConnections=0,
                activeConnections=0,
                idleConnections=0,
            )

            for row in cursor.fetchall():
                datname, xact_start, query_start, backend_start, now = row

                database = connectionStats['databases'].get(datname, None)
                if database is None:
                    database = dict(
                        totalConnections=0,
                        activeConnections=0,
                        idleConnections=0,
                    )

                # Connection counts.
                connectionStats['totalConnections'] += 1
                database['totalConnections'] += 1

                if xact_start is not None:
                    connectionStats['activeConnections'] += 1
                    database['activeConnections'] += 1
                else:
                    connectionStats['idleConnections'] += 1
                    database['idleConnections'] += 1

                # Individual query duration summaries.
                if query_start is not None:
                    queryDuration = max(
                        datetimeDurationInSeconds(query_start, now), 0)

                    connectionStats['minQueryDuration'] = min(
                        connectionStats.get('minQueryDuration', sys.maxint),
                        queryDuration)

                    connectionStats['maxQueryDuration'] = max(
                        connectionStats.get('maxQueryDuration', 0),
                        queryDuration)

                    if 'avgQueryDuration' not in connectionStats:
                        connectionStats['avgQueryDuration'] = queryDuration
                    else:
                        connectionStats['avgQueryDuration'] = (
                                (connectionStats['avgQueryDuration'] + queryDuration)
                                / 2)

                    database['minQueryDuration'] = min(
                        database.get('minQueryDuration', sys.maxint),
                        queryDuration)

                    database['maxQueryDuration'] = max(
                        database.get('maxQueryDuration', 0),
                        queryDuration)

                    if 'avgQueryDuration' not in database:
                        database['avgQueryDuration'] = queryDuration
                    else:
                        database['avgQueryDuration'] = (
                                (database['avgQueryDuration'] + queryDuration)
                                / 2)

                # Active transaction duration summaries.
                if xact_start is not None and query_start is not None:
                    txnDuration = max(
                        datetimeDurationInSeconds(xact_start, now), 0)

                    connectionStats['minTxnDuration'] = min(
                        connectionStats.get('minTxnDuration', sys.maxint),
                        txnDuration)

                    connectionStats['maxTxnDuration'] = max(
                        connectionStats.get('maxTxnDuration', 0),
                        txnDuration)

                    if 'avgTxnDuration' not in connectionStats:
                        connectionStats['avgTxnDuration'] = txnDuration
                    else:
                        connectionStats['avgTxnDuration'] = (
                                (connectionStats['avgTxnDuration'] + txnDuration)
                                / 2)

                    database['minTxnDuration'] = min(
                        database.get('minTxnDuration', sys.maxint),
                        txnDuration)

                    database['maxTxnDuration'] = max(
                        database.get('maxTxnDuration', 0),
                        txnDuration)

                    if 'avgTxnDuration' not in database:
                        database['avgTxnDuration'] = txnDuration
                    else:
                        database['avgTxnDuration'] = (
                                (database['avgTxnDuration'] + txnDuration)
                                / 2)

                # Idle transaction duration summaries.
                elif xact_start is not None and query_start is None:
                    connectionStats['idleConnections'] += 1
                    database['idleConnections'] += 1

                    idleDuration = max(
                        datetimeDurationInSeconds(backend_start, now), 0)

                    connectionStats['minIdleDuration'] = min(
                        connectionStats.get('minIdleDuration', sys.maxint),
                        idleDuration)

                    connectionStats['maxIdleDuration'] = max(
                        connectionStats.get('maxIdleDuration', 0),
                        idleDuration)

                    if 'avgIdleDuration' not in connectionStats:
                        connectionStats['avgIdleDuration'] = idleDuration
                    else:
                        connectionStats['avgIdleDuration'] = (
                                (connectionStats['avgIdleDuration'] + idleDuration)
                                / 2)

                    database['minIdleDuration'] = min(
                        database.get('minIdleDuration', sys.maxint),
                        idleDuration)

                    database['maxIdleDuration'] = max(
                        database.get('maxIdleDuration', 0),
                        idleDuration)

                    if 'avgIdleDuration' not in database:
                        database['avgIdleDuration'] = idleDuration
                    else:
                        database['avgIdleDuration'] = (
                                (database['avgIdleDuration'] + idleDuration)
                                / 2)

                connectionStats['databases'][datname] = database

        finally:
            cursor.close()

        return connectionStats

    def getLocks(self):
        cursor = self.getConnection(self._default_db).cursor()

        locksTemplate = dict(
            locksTotal=0,
            locksTotalGranted=0,
            locksTotalWaiting=0,
        )

        modes = (
            'AccessShare',
            'RowShare',
            'RowExclusive',
            'ShareUpdateExclusive',
            'Share',
            'ShareRowExclusive',
            'Exclusive',
            'AccessExclusive',
            'Other',
        )

        for mode in modes:
            locksTemplate.update({
                'locks{0}'.format(mode): 0,
                'locks{0}Granted'.format(mode): 0,
                'locks{0}Waiting'.format(mode): 0,
            })

        locks = dict(databases={})

        try:
            cursor.execute(
                "SELECT d.datname, l.mode, l.granted"
                "  FROM pg_database AS d"
                "  INNER JOIN pg_locks AS l ON l.database = d.oid"
                " WHERE NOT d.datistemplate AND d.datallowconn"
                "   AND d.datname != 'bdr_supervisordb'"
                "   AND pid <> pg_backend_pid()"
            )

            locks.update(locksTemplate)

            for row in cursor.fetchall():
                datname, mode, granted = row

                database = locks['databases'].get(
                    datname, copy.copy(locksTemplate))

                locks['locksTotal'] += 1
                database['locksTotal'] += 1

                statKey = 'locks{0}'.format(mode.replace('Lock', ''))
                if statKey not in locks:
                    statKey = 'locksOther'

                locks[statKey] += 1

                if granted:
                    locks['locksTotalGranted'] += 1
                    locks['{0}Granted'.format(statKey)] += 1
                    database['locksTotalGranted'] += 1
                    database['{0}Granted'.format(statKey)] += 1
                else:
                    locks['locksTotalWaiting'] += 1
                    locks['{0}Waiting'.format(statKey)] += 1
                    database['locksTotalGranted'] += 1
                    database['{0}Waiting'.format(statKey)] += 1

                locks['databases'][datname] = database

        finally:
            cursor.close()

        return locks

    def getTableStatsForDatabase(self, db):
        cursor = self.getConnection(db).cursor()

        tableStats = {}

        try:
            cursor.execute(
                "SELECT "
                "   a.relname,"
                "   b.pg_relation_size,"
                "   a.pg_total_relation_size,"
                "   a.seq_scan,"
                "   a.seq_tup_read,"
                "   a.idx_scan,"
                "   a.idx_tup_fetch,"
                "   a.n_tup_ins,"
                "   a.n_tup_upd,"
                "   a.n_tup_del,"
                "   a.n_tup_hot_upd,"
                "   a.n_live_tup,"
                "   a.n_dead_tup,"
                "   a.last_vacuum,"
                "   a.last_autovacuum,"
                "   a.last_analyze,"
                "   a.last_autoanalyze"
                " FROM"
                " (SELECT relname,"
                "        pg_total_relation_size(relid),"
                "        seq_scan, seq_tup_read,"
                "        idx_scan, idx_tup_fetch,"
                "        n_tup_ins, n_tup_upd, n_tup_del,"
                "        n_tup_hot_upd, n_live_tup, n_dead_tup,"
                "        last_vacuum, last_autovacuum,"
                "        last_analyze, last_autoanalyze"
                "  from pg_stat_user_tables) a,"
                " (select relname, relpages * (current_setting('block_size'))::numeric pg_relation_size FROM pg_class) b"
                " where a.relname=b.relname"
            )

            for row in cursor.fetchall():
                row = list(row)
                for i in range(13, 17):
                    if row[i] is not None:
                        row[i] = datetimeToEpoch(row[i])

                tableStats[row[0]] = dict(
                    size=row[1],
                    totalSize=row[2],
                    seqScan=row[3],
                    seqTupRead=row[4],
                    idxScan=row[5],
                    idxTupFetch=row[6],
                    nTupIns=row[7],
                    nTupUpd=row[8],
                    nTupDel=row[9],
                    nTupHotUpd=row[10],
                    nLiveTup=row[11],
                    nDeadTup=row[12],
                    lastVacuum=row[13],
                    lastAutoVacuum=row[14],
                    lastAnalyze=row[15],
                    lastAutoAnalyze=row[16],
                )
        finally:
            cursor.close()

        return tableStats

    def _getConnectionPool(self):
        """Get or create Twisted connection pool for async operations."""
        if self._pool is None:
            conn_kwargs = {
                'host': self._host,
                'port': int(self._port),
                'user': self._username,
                'password': self._password,
                'database': str(self._default_db),
            }
            # Handle SSL parameter
            if self._ssl:
                conn_kwargs['sslmode'] = 'require'
            else:
                conn_kwargs['sslmode'] = 'disable'

            self._pool = adbapi.ConnectionPool(
                'psycopg2',
                cp_min=1,
                cp_max=3,
                cp_reconnect=True,
                **conn_kwargs
            )
            LOG.debug("Created Twisted connection pool with psycopg2")

        return self._pool

    @defer.inlineCallbacks
    def getDatabasesAsync(self):
        """Async version of getDatabases() - returns Deferred."""
        try:
            LOG.debug("Creating connection pool for async getDatabases")
            pool = self._getConnectionPool()
            LOG.debug("Running async query for databases")
            rows = yield pool.runQuery(
                "SELECT d.datname, s.datid, pg_database_size(s.datid) AS size"
                "  FROM pg_database AS d"
                "  JOIN pg_stat_database AS s ON s.datname = d.datname"
                " WHERE NOT datistemplate AND datallowconn"
                "   AND d.datname != 'bdr_supervisordb'"
            )

            LOG.debug("Processing {0} database rows".format(len(rows)))
            databases = {}
            for row in rows:
                databases[row[0]] = dict(
                    oid=row[1],
                    size=row[2]
                )

            LOG.debug("Async getDatabases successful, returning {0} databases".format(len(databases)))
            defer.returnValue(databases)
        except Exception as ex:
            msg = str(ex)
            fatal_errors = [
                "no pg_hba.conf entry",
                "password authentication failed"
            ]
            if any(err in msg for err in fatal_errors):
                LOG.error("Async getDatabases failed due to fatal config error: %s. Skipping sync fallback.", msg)
                defer.returnValue({})

            LOG.error("Async getDatabases failed: %s, falling back to sync", ex)
            import traceback
            LOG.error("Traceback: %s", traceback.format_exc())
            # Fallback to sync on error
            try:
                LOG.info("Attempting sync fallback for getDatabases")
                result = self.getDatabases()
                LOG.info("Sync fallback successful, got {0} databases".format(len(result)))
                defer.returnValue(result)
            except Exception as ex2:
                LOG.error("Sync fallback also failed: %s", ex2)
                defer.returnValue({})

    @defer.inlineCallbacks
    def getTablesInDatabaseAsync(self, db):
        """Async version of getTablesInDatabase() - returns Deferred."""
        try:
            LOG.debug("Getting tables for database: %s (async)", db)
            # Creating a separate pool for database
            conn_kwargs = {
                'host': self._host,
                'port': int(self._port),
                'user': self._username,
                'password': self._password,
                'database': str(db),
            }
            if self._ssl:
                conn_kwargs['sslmode'] = 'require'
            else:
                conn_kwargs['sslmode'] = 'disable'

            db_pool = adbapi.ConnectionPool(
                'psycopg2',
                cp_min=1,
                cp_max=2,
                cp_reconnect=True,
                **conn_kwargs
            )

            try:
                rows = yield db_pool.runQuery(
                    "SELECT a.relname, a.relid, a.schemaname, b.size, a.total_size from"
                    " ( select relname, "
                    "   relid, schemaname,"
                    "   pg_total_relation_size(relid) total_size"
                    " FROM pg_stat_user_tables) a, "
                    " (select relname, relpages * (current_setting('block_size'))::numeric size FROM pg_class) b "
                    " where a.relname=b.relname"
                )

                tables = {}
                for row in rows:
                    tables[row[0]] = dict(
                        oid=row[1],
                        schema=row[2],
                        size=row[3],
                        totalSize=row[4],
                    )

                LOG.debug("Got %d tables from database %s (async)", len(tables), db)
                defer.returnValue(tables)
            finally:
                # Close the database-specific pool
                db_pool.close()
        except Exception as ex:
            # Handle fatal configuration errors where fallback is useless
            msg = str(ex)
            fatal_errors = [
                "no pg_hba.conf entry",
                "password authentication failed"
            ]
            if any(err in msg for err in fatal_errors):
                LOG.error("Async getTablesInDatabase(%s) failed due to fatal config error: %s. Skipping sync fallback.",
                          db, msg)
                defer.returnValue({})

            LOG.error("Async getTablesInDatabase(%s) failed: %s, falling back to sync", db, ex)
            import traceback
            LOG.error("Traceback: %s", traceback.format_exc())
            # Fallback to sync on error
            try:
                result = self.getTablesInDatabase(db)
                LOG.info("Sync fallback successful for database %s, got %d tables", db, len(result))
                defer.returnValue(result)
            except Exception as ex2:
                LOG.error("Sync fallback also failed for database %s: %s", db, ex2)
                defer.returnValue({})


def exclude_patterns_list(excludes):
    exclude_patterns = []

    for exclude in excludes:
        exclude = exclude.strip()
        if exclude == "" or exclude.startswith("#"):
            continue

        try:
            exclude_patterns.append(re.compile(exclude))
        except Exception:
            LOG.warn("Invalid zPostgreSQLTableRegex value: '%s', this modeling filter will not be applied.", exclude)
            continue

    return exclude_patterns


def is_suppressed(item, exclude_patterns):
    for exclude_pattern in exclude_patterns:
        if exclude_pattern.search(item):
            return True

    return False