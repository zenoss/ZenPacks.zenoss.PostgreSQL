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

from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenModel.ManagedEntity import ManagedEntity
from Products.ZenModel.ZenossSecurity import ZEN_CHANGE_DEVICE
from Products.ZenRelations.RelSchema import ToManyCont, ToOne

from .util import CollectedOrModeledMixin

class Database(DeviceComponent, ManagedEntity, CollectedOrModeledMixin):
    meta_type = portal_type = 'PostgreSQLDatabase'

    dbName = None
    dbOid = None

    # We do more frequent collection of these values, but it's good to have an
    # immediate value to use as soon as the device is added.
    modeled_size = None

    _properties = ManagedEntity._properties + (
        {'id': 'dbName', 'type': 'string', 'mode': ''},
        {'id': 'dbOid', 'type': 'int', 'mode': ''},
        {'id': 'modeled_size', 'type': 'int', 'mode': ''},
    )

    _relations = ManagedEntity._relations + (
        ('server', ToOne(ToManyCont,
            'Products.ZenModel.Device.Device',
            'pgDatabases'
            )
        ),
        ('tables', ToManyCont(ToOne,
            'ZenPacks.zenoss.PostgreSQL.Table.Table',
            'database'
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
        return self.server()

