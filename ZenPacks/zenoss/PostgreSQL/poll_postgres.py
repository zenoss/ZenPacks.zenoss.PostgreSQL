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
import sys

from util import addLocalLibPath
addLocalLibPath()

from pg8000 import DBAPI

class PostgresPoller(object):
    _host = None
    _port = None
    _username = None
    _password = None

    def __init__(self, host, port, username, password):
        self._host = host
        self._port = port
        self._username = username
        self._password = password

    def getData(self):
        conn = DBAPI.connect(
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password)

        data = {}
        data['events'] = []

        # TODO: Error handling.
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        rows = cursor.fetchall()
        for row in rows:
            # TODO: Implementation.
            data['dpName'] = row[0]

        return data

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

