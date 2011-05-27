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

import logging
log = logging.getLogger('zen.PostgreSQL')

from ....util import addLocalLibPath
addLocalLibPath()

from pg8000 import DBAPI

from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import ObjectMap, RelationshipMap
from Products.ZenUtils.Utils import prepId

SQL = {
    'DATABASES': (
        "SELECT d.datname, s.datid, pg_database_size(s.datid) AS size"
        "  FROM pg_database AS d"
        "  JOIN pg_stat_database AS s ON s.datname = d.datname"
        " WHERE NOT datistemplate AND datallowconn"
    ),

    'TABLES': (
        "SELECT relname, relname, schemaname,"
        "       pg_relation_size(relid) AS size,"
        "       pg_total_relation_size(relid) AS total_size"
        "  FROM pg_stat_user_tables"
    ),
}

class PostgreSQL(PythonPlugin):
    deviceProperties = PythonPlugin.deviceProperties + (
        'zPostgreSQLPort',
        'zPostgreSQLUsername',
        'zPostgreSQLPassword',
    )

    def collect(self, device, unused):
        results = dict(databases={})

        # TODO: Error handling.
        log.info("Connecting to database: postgres")
        conn = cursor = None
        try:
            conn = DBAPI.connect(
                host=device.manageIp,
                port=device.zPostgreSQLPort,
                database='postgres',
                user=device.zPostgreSQLUsername,
                password=device.zPostgreSQLPassword)

            cursor = conn.cursor()

            log.info("Querying for databases")
            cursor.execute(SQL['DATABASES'])
            for row in cursor.fetchall():
                datname, datid, size = row
                results['databases'][datname] = dict(
                    oid=datid,
                    size=size,
                )

            cursor.close()
            conn.close()

        except Exception, ex:
            log.warn("Error connecting to {0}: {1}".format(
                'postgres', ex))

            return None

        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

        for dbName in results['databases'].keys():
            if dbName == 'postgres':
                continue

            results['databases'][dbName]['tables'] = {}

            log.info("Connecting to database: {0}".format(dbName))
            try:
                conn = DBAPI.connect(
                    host=device.manageIp,
                    port=device.zPostgreSQLPort,
                    database=str(dbName),
                    user=device.zPostgreSQLUsername,
                    password=device.zPostgreSQLPassword)

                cursor = conn.cursor()

                log.info("Querying for tables in {0}".format(dbName))
                cursor.execute(SQL['TABLES'])
                for row in cursor.fetchall():
                    relname, relid, schemaname, size, total_size = row
                    results['databases'][dbName]['tables'][relname] = dict(
                        oid=relid,
                        schema=schemaname,
                        size=size,
                        totalSize=total_size,
                    )

            except Exception, ex:
                log.warn("Error connecting to {0}: {1}".format(
                    dbName, ex))

                continue

            finally:
                try:
                    cursor.close()
                    conn.close()
                except Exception:
                    pass

        return results

    def process(self, devices, results, unused):
        if results is None:
            return None

        maps = []

        databases = []
        for dbName, dbDetail in results['databases'].items():
            databases.append(ObjectMap(data=dict(
                id=prepId(dbName),
                title=dbName,
                dbName=dbName,
                dbOid=dbDetail['oid'],
                modeled_dbSize=dbDetail['size'],
            )))

        maps.append(RelationshipMap(
            relname='pgDatabases',
            modname='ZenPacks.zenoss.PostgreSQL.Database',
            objmaps=databases))

        for dbName, dbDetail in results['databases'].items():
            if 'tables' not in dbDetail:
                continue

            tables = []
            for tableName, tableDetail in dbDetail['tables'].items():
                tables.append(ObjectMap(data=dict(
                    id='{0}_{1}'.format(prepId(dbName), prepId(tableName)),
                    title=tableName,
                    tableName=tableName,
                    tableOid=tableDetail['oid'],
                    tableSchema=tableDetail['schema'],
                )))

            maps.append(RelationshipMap(
                compname='pgDatabases/{0}'.format(prepId(dbName)),
                relname='tables',
                modname='ZenPacks.zenoss.PostgreSQL.Table',
                objmaps=tables))

        return maps

