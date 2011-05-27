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

from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenModel.ManagedEntity import ManagedEntity
from Products.ZenModel.ZenossSecurity import ZEN_CHANGE_DEVICE
from Products.ZenRelations.RelSchema import ToManyCont, ToOne

from .util import CollectedOrModeledMixin

class Table(DeviceComponent, ManagedEntity, CollectedOrModeledMixin):
    meta_type = portal_type = 'PostgreSQLTable'

    tableName = None
    tableOid = None
    tableSchema = None

    # We do more frequent collection of these values, but it's good to have an
    # immediate value to use as soon as the device is added.
    modeled_tableSize = None
    modeled_totalTableSize = None

    _properties = ManagedEntity._properties + (
        {'id': 'tableName', 'type': 'string', 'mode': ''},
        {'id': 'tableOid', 'type': 'int', 'mode': ''},
        {'id': 'tableSchema', 'type': 'string', 'mode': ''},
        {'id': 'modeled_tableSize', 'type': 'int', 'mode': ''},
        {'id': 'modeled_totalTableSize', 'type': 'int', 'mode': ''},
    )

    _relations = ManagedEntity._relations + (
        ('database', ToOne(ToManyCont,
            'ZenPacks.zenoss.PostgreSQL.Database.Database',
            'tables'
            )
        ),
    )

    # Meta-data: Zope object views and actions
    factory_type_information = ({
        'actions': ({ 
            'id': 'perfConf', 
            'name': 'Template', 
            'action': 'objTemplates', 
            'permissions': (ZEN_CHANGE_DEVICE,), 
            },), 
        },)

    # Query for events by id instead of name.
    event_key = "ComponentId"

    def device(self):
        return self.database().device()

