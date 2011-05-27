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

    def __init__(self, host, port, username, password):
        self._host = host
        self._port = port
        self._username = username
        self._password = password

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
            pg = PgHelper(
                self._host, self._port, self._username, self._password)

            self._data = dict(
                events=[],
                databaseStats = pg.getDatabaseStats(),
            )

            for dbName in self._data['databaseStats'].keys():
                self._data['databaseStats'][dbName]['tableStats'] = \
                    pg.getTableStatsForDatabase(dbName)

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
                    severity=5,
                    summary='postgres failure: {0}'.format(ex),
                    eventKey='postgresFailure',
                    eventClassKey='postgresFailure',
                )]
            )

        print json.dumps(data)

if __name__ == '__main__':
    host = port = username = password = None
    try:
        host, port, username, password = sys.argv[1:4]
    except ValueError:
        print >> sys.stderr,"Usage: {0} <host> <port> <username> <password>" \
            .format(sys.argv[0])

        sys.exit(1)

    poller = PostgresPoller(host, port, username, password)
    poller.printJSON()

