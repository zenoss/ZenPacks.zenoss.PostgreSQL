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

from Products.Zuul.form import schema
from Products.Zuul.interfaces.component import IComponentInfo
from Products.Zuul.utils import ZuulMessageFactory as _t


class IDatabaseInfo(IComponentInfo):
    dbName = schema.Text(title=_t(u"Database Name"))
    dbOid = schema.Int(title=_t(u"Database OID"))
    dbSizeString = schema.Int(title=_t(u"Database Size"))
    tableCount = schema.Int(title=_t(u"Table Count"))


class ITableInfo(IComponentInfo):
    tableName = schema.Text(title=_t(u"Table Name"))
    tableOid = schema.Int(title=_t(u"Table OID"))
    tableSchema = schema.Text(title=_t(u"Table Schema"))
    tableSizeString = schema.Int(title=_t(u"Table Size"))
    totalTableSizeString = schema.Int(title=_t(u"Total Table Size"))
    database = schema.Entity(title=_t(u"Database"))
