###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, 2013, Zenoss Inc.
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

from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import ObjectMap, RelationshipMap
from Products.ZenUtils.Utils import prepId

from ZenPacks.zenoss.PostgreSQL.util import PgHelper, exclude_patterns_list, is_suppressed

class PostgreSQL(PythonPlugin):
    deviceProperties = PythonPlugin.deviceProperties + (
        'zPostgreSQLPort',
        'zPostgreSQLUsername',
        'zPostgreSQLPassword',
        'zPostgreSQLUseSSL',
        'zPostgreSQLDefaultDB',
    )

    def collect(self, device, unused):
        pg = PgHelper(
            device.manageIp,
            device.zPostgreSQLPort,
            device.zPostgreSQLUsername,
            device.zPostgreSQLPassword,
            device.zPostgreSQLUseSSL,
            device.zPostgreSQLDefaultDB)

        results = {}
        exclude_patterns = exclude_patterns_list(getattr(device, 'zPostgreSQLTableRegex', []))

        log.info("Getting database list")
        try:
            results['databases'] = pg.getDatabases()
        except Exception, ex:
            log.warn("Error getting database list: {0}".format(ex))
            return None

        for dbName in results['databases'].keys():
            if dbName == device.zPostgreSQLDefaultDB:
                continue

            results['databases'][dbName]['tables'] = {}

            log.info("Getting tables list for {0}".format(dbName))
            try:
                results['databases'][dbName]['tables'] = pg.getTablesInDatabase(dbName)
                
                tables = pg.getTablesInDatabase(dbName)
                if pattern.pattern:
                    for key in tables.keys():
                        if is_suppressed(key, exclude_patterns):
                            del tables[key]
                
                results['databases'][dbName]['tables'] = tables    

            except Exception, ex:
                log.warn("Error getting tables list for {0}: {1}".format(
                    dbName, ex))

                continue

        return results

    def process(self, devices, results, unused):
        if results is None:
            return None

        maps = [ self.objectMap(dict(setPostgreSQL=True)) ]

        databases = []
        for dbName, dbDetail in results['databases'].items():
            databases.append(ObjectMap(data=dict(
                id=prepId(dbName),
                title=dbName,
                dbName=dbName,
                dbOid=dbDetail['oid'],
                modeled_size=dbDetail['size'],
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
                    modeled_size=tableDetail['size'],
                    modeled_totalSize=tableDetail['totalSize'],
                )))

            maps.append(RelationshipMap(
                compname='pgDatabases/{0}'.format(prepId(dbName)),
                relname='tables',
                modname='ZenPacks.zenoss.PostgreSQL.Table',
                objmaps=tables))

        return maps

