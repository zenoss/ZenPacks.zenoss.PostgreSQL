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

from twisted.internet import defer


class PostgreSQL(PythonPlugin):
    deviceProperties = PythonPlugin.deviceProperties + (
        'zPostgreSQLPort',
        'zPostgreSQLUsername',
        'zPostgreSQLPassword',
        'zPostgreSQLUseSSL',
        'zPostgreSQLDefaultDB',
        'zPostgreSQLTableRegex',
    )

    @defer.inlineCallbacks
    def collect(self, device, unused):
        """Async collect using Twisted Deferred for better performance."""
        pg = PgHelper(
            device.manageIp,
            device.zPostgreSQLPort,
            device.zPostgreSQLUsername,
            device.zPostgreSQLPassword,
            device.zPostgreSQLUseSSL,
            device.zPostgreSQLDefaultDB)

        results = {}
        exclude_patterns = exclude_patterns_list(getattr(device, 'zPostgreSQLTableRegex', []))

        log.info("Getting database list (async)")
        try:
            databases = yield pg.getDatabasesAsync()
            log.info("Found {0} databases".format(len(databases)))
            results['databases'] = databases
        except Exception, ex:
            log.error("Error getting database list: {0}".format(ex))
            import traceback
            log.error("Traceback: {0}".format(traceback.format_exc()))
            defer.returnValue(None)
            return

        # Collect tables from all databases in parallel
        table_deferreds = []
        db_names = []

        for dbName in results['databases'].keys():
            if dbName == device.zPostgreSQLDefaultDB:
                continue

            results['databases'][dbName]['tables'] = {}
            db_names.append(dbName)
            table_deferreds.append(pg.getTablesInDatabaseAsync(dbName))

        if table_deferreds:
            log.info("Getting tables list for {0} databases in parallel".format(len(db_names)))
            # Get all tables in parallel using DeferredList
            all_tables = yield defer.DeferredList(table_deferreds, consumeErrors=True)

            for i, (success, result) in enumerate(all_tables):
                dbName = db_names[i]

                if not success:
                    log.warn("Error getting tables list for {0}: {1}".format(
                        dbName, result.getErrorMessage() if hasattr(result, 'getErrorMessage') else result))
                    continue

                tables = result
                if exclude_patterns:
                    for key in tables.keys():
                        if is_suppressed(key, exclude_patterns):
                            del tables[key]

                results['databases'][dbName]['tables'] = tables

        # Close pool after collection
        try:
            pg.close()
        except Exception:
            pass

        defer.returnValue(results)

    def process(self, devices, results, unused):
        if results is None:
            return None

        maps = [self.objectMap(dict(setPostgreSQL=True))]

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

