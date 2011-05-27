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

def addLocalLibPath():
    """
    Helper to add the ZenPack's lib directory to PYTHONPATH.
    """
    import os
    import site

    site.addsitedir(os.path.join(os.path.dirname(__file__), 'lib'))

class CollectedOrModeledMixin:
    def getFloatForValue(self, value):
        # Get the recent collected value if possible.
        r = self.cacheRRDValue(value, None)

        # Fall back to a modeled value if it exists.
        if r is None:
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
from pg8000 import DBAPI

class PgHelper(object):
    _host = None
    _port = None
    _username = None
    _password = None
    _connections = None

    def __init__(self, host, port, username, password):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._connections = {}

    def __del__(self):
        for conn in self._connections.values():
            try:
                conn.close()
            except Exception:
                pass

    def getConnection(self, db):
        if db in self._connections and self._connections[db]:
            return self._connections[db]

        self._connections[db] = DBAPI.connect(
            host=self._host,
            port=self._port,
            database=db,
            user=self._username,
            password=self._password)

        return self._connections[db]

    def getDatabases(self):
        cursor = self.getConnection('postgres').cursor()

        databases = {}

        try:
            cursor.execute(
                "SELECT d.datname, s.datid, pg_database_size(s.datid) AS size"
                "  FROM pg_database AS d"
                "  JOIN pg_stat_database AS s ON s.datname = d.datname"
                " WHERE NOT datistemplate AND datallowconn"
            )

            for row in cursor.fetchall():
                databases[row[0]] = dict(
                    oid=row[1],
                    size=row[2]
                )
        finally:
            cursor.close()

        return databases

    def getTablesInDatabase(self, db):
        cursor = self.getConnection(str(db)).cursor()

        tables = {}

        try:
            cursor.execute(
                "SELECT relname, relid, schemaname,"
                "       pg_relation_size(relid) AS size,"
                "       pg_total_relation_size(relid) AS total_size"
                "  FROM pg_stat_user_tables"
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

