#!/usr/bin/env python
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
import json
import sys
import decimal

from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from util import PgHelper


def clean_dict_data(d):
    fixed = {}
    for k,v in d.iteritems():
        if isinstance(v, decimal.Decimal):
            # convert decimal to string
            fixed.update({k: str(v)})
        elif isinstance(v, dict):
            # recurse
            fixed.update({k: clean_dict_data(v)})
        # If Null data exists, just skip it, rather than bias datapoints.
        elif v is None:
            continue
        else:
            # no conversion needed, replace
            fixed.update({k: v})
    return fixed

class PostgresPoller(object):
    _host = None
    _port = None
    _username = None
    _password = None
    _default_db = None

    def __init__(self, host, port, username, password, ssl, default_db):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._ssl = ssl
        self._default_db = default_db

    def getData(self, pg):
        data = dict(events=[])

        data.update(
            connectionLatency=pg.getConnectionLatencyForDatabase(self._default_db),
            queryLatency=pg.getQueryLatencyForDatabase(self._default_db),
            )

        # Calculated server-level stats.
        databaseSummaries = dict(
            size=0,
            numBackends=0,
            xactCommit=0,
            xactRollback=0,
            xactTotal=0,
            blksRead=0,
            blksHit=0,
            tupReturned=0,
            tupFetched=0,
            tupTotal=0,
            tupInserted=0,
            tupUpdated=0,
            tupDeleted=0,
        )

        tableSummaries = dict(
            seqScan=0,
            seqTupRead=0,
            idxScan=0,
            idxTupFetch=0,
            nTupIns=0,
            nTupUpd=0,
            nTupDel=0,
            nTupHotUpd=0,
            nLiveTup=0,
            nDeadTup=0,
        )

        dbTableSummaries = copy.copy(tableSummaries)

        # Catch exception in DB query to close open pg connection
        databases = pg.getDatabaseStats()

        for dbName, dbStats in databases.items():
            databases[dbName].update(
                connectionLatency=pg.getConnectionLatencyForDatabase(dbName),
                queryLatency=pg.getQueryLatencyForDatabase(dbName),
                )

            local_dbTableSummaries = copy.copy(dbTableSummaries)

            for statName in databaseSummaries.keys():
                if statName in dbStats and dbStats[statName] is not None:
                    databaseSummaries[statName] += dbStats[statName]

            # Average percentage summaries.
            for statName in ('xactRollbackPct', 'tupFetchedPct'):
                if statName in dbStats and dbStats[statName] is not None:
                    if statName in databaseSummaries:
                        databaseSummaries[statName] = (
                            (databaseSummaries[statName] +
                            dbStats[statName]) / 2.0)
                    else:
                        databaseSummaries[statName] = \
                            dbStats[statName]

            # Catch exception in table query to close open pg connection
            tables = pg.getTableStatsForDatabase(dbName)

            for tableName, tableStats in tables.items():
                for statName in tableSummaries.keys():
                    if statName in tableStats \
                            and tableStats[statName] is not None:
                        tableSummaries[statName] += tableStats[statName]
                        local_dbTableSummaries[statName] += \
                            tableStats[statName]

            databases[dbName].update(local_dbTableSummaries)
            databases[dbName]['tables'] = tables

        data.update(databaseSummaries)
        data.update(tableSummaries)
        data['databases'] = databases

        # Connection stats.
        for k, v in pg.getConnectionStats().items():
            if k == 'databases':
                for dbName, stats in v.items():
                    data['databases'][dbName].update(stats)
            else:
                data[k] = v

        # Lock stats.
        for k, v in pg.getLocks().items():
            if k == 'databases':
                for dbName, stats in v.items():
                    data['databases'][dbName].update(stats)
            else:
                data[k] = v

        return data

    def printJSON(self):
        pg = None
        data = None

        try:
            pg = PgHelper(
                self._host,
                self._port,
                self._username,
                self._password,
                self._ssl,
                self._default_db
                )

            data = self.getData(pg)
            data['events'].append(dict(
                severity=0,
                summary='postgres connectivity restored',
                eventKey='postgresFailure',
                eventClassKey='postgresRestored',
            ))
        except Exception, ex:
            severity = 4

            # Lower some transient failures that will recover quickly to debug
            # severity.

            # https://github.com/zenoss/ZenPacks.zenoss.PostgreSQL/issues/2
            if 'Unterminated string' in str(ex):
                severity = 1

            data = dict(
                events=[dict(
                    severity=severity,
                    summary='postgres failure: {0}'.format(ex),
                    eventKey='postgresFailure',
                    eventClassKey='postgresFailure',
                )]
            )
        finally:
            if pg:
                pg.close()

        print json.dumps(clean_dict_data(data))

if __name__ == '__main__':
    usage = "Usage: {0} <host> <port> <username> <password <ssl> <defaultDB>"

    host = port = username = password = ssl = default_db = None
    try:
        host, port, username, password, ssl, default_db = sys.argv[1:7]
    except ValueError:
        print >> sys.stderr, usage.format(sys.argv[0])
        sys.exit(1)

    if ssl == 'False':
        ssl = False

    poller = PostgresPoller(host, port, username, password, ssl, default_db)
    poller.printJSON()
