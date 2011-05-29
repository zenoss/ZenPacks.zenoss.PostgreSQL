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
import md5
import os
import sys
import tempfile
import time

from util import PgHelper

class PostgresPoller(object):
    _host = None
    _port = None
    _username = None
    _password = None
    _data = None

    def __init__(self, host, port, username, password, ssl):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._ssl = ssl

    def _getTempFilename(self):
        target_hash = md5.md5('{0}+{1}+{2}'.format(
            self._host, self._port, self._username)).hexdigest()

        return os.path.join(
            tempfile.gettempdir(),
            '.zenoss_postgres_{0}'.format(target_hash))

    def _cacheData(self):
        tmpfile = self._getTempFilename()
        tmp = open(tmpfile, 'w')
        json.dump(self._data, tmp)
        tmp.close()

    def _loadData(self):
        if self._data:
            return

        tmpfile = self._getTempFilename()
        if not os.path.isfile(tmpfile):
            return None

        # Make sure temporary data isn't too stale.
        if os.stat(tmpfile).st_mtime < (time.time() - 50):
            os.unlink(tmpfile)
            return None

        tmp = open(tmpfile, 'r')
        self._data = json.load(tmp)
        tmp.close()

        self._cacheData()

    def getData(self):
        self._loadData()

        if not self._data:
            self._data = dict(events=[])

            pg = PgHelper(
                self._host,
                self._port,
                self._username,
                self._password,
                self._ssl)

            self._data['connectionLatency'] = \
                pg.getConnectionLatencyForDatabase('postgres')

            self._data['queryLatency'] = \
                pg.getQueryLatencyForDatabase('postgres')

            # Calculated server-level stats.
            databaseSummaries = dict(
                size=0,
                numBackends=0,
                xactCommit=0,
                xactRollback=0,
                blksRead=0,
                blksHit=0,
                tupReturned=0,
                tupFetched=0,
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

            databases = pg.getDatabaseStats()
            for dbName, dbStats in databases.items():
                databases[dbName]['connectionLatency'] = \
                    pg.getConnectionLatencyForDatabase(dbName)

                databases[dbName]['queryLatency'] = \
                    pg.getQueryLatencyForDatabase(dbName)

                local_dbTableSummaries = copy.copy(dbTableSummaries)

                for statName in databaseSummaries.keys():
                    if statName in dbStats and dbStats[statName] is not None:
                        databaseSummaries[statName] += dbStats[statName]

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

            self._data.update(databaseSummaries)
            self._data.update(tableSummaries)
            self._data['databases'] = databases

        self._cacheData()
        return self._data

    def printJSON(self):
        data = None
        try:
            data = self.getData()
            data['events'].append(dict(
                severity=0,
                summary='postgres connectivity restored',
                eventKey='postgresFailure',
                eventClassKey='postgresRestored',
            ))
        except Exception, ex:
            data = dict(
                events=[dict(
                    severity=4,
                    summary='postgres failure: {0}'.format(ex),
                    eventKey='postgresFailure',
                    eventClassKey='postgresFailure',
                )]
            )

        print json.dumps(data)

if __name__ == '__main__':
    usage = "Usage: {0} <host> <port> <username> <password <ssl>"

    host = port = username = password = ssl = None
    try:
        host, port, username, password, ssl = sys.argv[1:6]
    except ValueError:
        print >> sys.stderr, usage.format(sys.argv[0])
        sys.exit(1)

    if ssl == 'False':
        ssl = False

    poller = PostgresPoller(host, port, username, password, ssl)
    poller.printJSON()

