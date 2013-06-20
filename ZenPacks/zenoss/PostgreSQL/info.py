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

from zope.component import adapts
from zope.interface import implements

from Products.ZenUtils.Utils import convToUnits
from Products.Zuul.decorators import info
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo

from .interfaces import IDatabaseInfo, ITableInfo
from .util import CollectedOrModeledProperty

from .Database import Database
from .Table import Table


class DatabaseInfo(ComponentInfo):
    implements(IDatabaseInfo)
    adapts(Database)

    dbName = ProxyProperty('dbName')
    dbOid = ProxyProperty('dbOid')
    dbSize = CollectedOrModeledProperty('size')

    @property
    def dbSizeString(self):
        return convToUnits(
            self._object.getIntForValue('size'), 1024, 'B')

    @property
    def tableCount(self):
        return self._object.tables.countObjects()


class TableInfo(ComponentInfo):
    implements(ITableInfo)
    adapts(Table)

    tableName = ProxyProperty('tableName')
    tableOid = ProxyProperty('tableOid')
    tableSchema = ProxyProperty('tableSchema')
    tableSize = CollectedOrModeledProperty('size')
    totalTableSize = CollectedOrModeledProperty('totalSize')

    @property
    def totalTableSizeString(self):
        return convToUnits(
            self._object.getIntForValue('totalSize'), 1024, 'B')

    @property
    @info
    def database(self):
        return self._object.database()

    @property
    def tableSizeString(self):
        return convToUnits(
            self._object.getIntForValue('size'), 1024, 'B')
