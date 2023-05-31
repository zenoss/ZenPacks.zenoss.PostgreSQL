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

import os

from Products.ZenEvents.EventManagerBase import EventManagerBase
from Products.ZenModel.Device import Device
from Products.ZenModel.ZenPack import ZenPack as ZenPackBase
from Products.ZenRelations.RelSchema import ToManyCont, ToOne
from Products.ZenUtils.Utils import monkeypatch, zenPath

class ZenPack(ZenPackBase):
    packZProperties = [
        ('zPostgreSQLPort', 5432, 'int'),
        ('zPostgreSQLUsername', 'postgres', 'string'),
        ('zPostgreSQLPassword', '', 'password'),
        ('zPostgreSQLUseSSL', False, 'boolean'),
        ('zPostgreSQLDefaultDB', 'postgres', 'string'),
        ('zPostgreSQLTableRegex', '', 'string'),
    ]

    packZProperties_data = {
        'zPostgreSQLTableRegex': {
            'description': "Filter tables from all databases if name matches regex provided",
            'label': "Regex Table Filter",
            'type': "string" },
    }

    def install(self, app):
        super(ZenPack, self).install(app)
        self.patchPostgreSQLDriver()
        self.updateExistingRelations(app.zport.dmd)

    def remove(self, app, leaveObjects=False):
        if not leaveObjects:
            # Remove our custom relations addition.
            Device._relations = tuple(
                [ x for x in Device._relations if x[0] != 'pgDatabases' ])

            self.updateExistingRelations(app.zport.dmd)
        
        # Revert all pg8000 library patches
        self.patchPostgreSQLDriver(revert=True)

        super(ZenPack, self).remove(app, leaveObjects=leaveObjects)

    def updateExistingRelations(self, dmd):
        log.info('Adding pgDatabases relationship to existing devices')
        for device in dmd.Devices.getSubDevicesGen():
            device.buildRelations()

    def patchPostgreSQLDriver(self, revert=False):
        log.info('Patching pg8000 core library')
        patch_dir = self.path('lib')
        
        # Getting a list of all patches which will be applied
        patches_list = [file for file in os.listdir(patch_dir) if file.endswith('.patch')]
        
        cmd = "patch -p0 -d %s -i %s" if not revert else "patch -p0 -R -d %s -i %s"  
        for patch in patches_list:
            os.system(cmd % (
                os.path.join(patch_dir, 'pg8000'),
                os.path.join(patch_dir, patch)
            ))

# Allow PostgreSQL databases to be related to any device.
Device._relations += (
    ('pgDatabases', ToManyCont(ToOne,
        'ZenPacks.zenoss.PostgreSQL.Database.Database', 'server')),
)

# We need to filter components by id instead of name.
EventManagerBase.ComponentIdWhere = (
    "\"(device = '%s' and component = '%s')\""
    " % (me.device().getDmdKey(), me.id)")

@monkeypatch('Products.ZenModel.Device.Device')
def setPostgreSQL(self, active=True):
    if not active:
        return

    device = self.primaryAq()

    # Automatically bind the device-level template.
    templates = list(device.zDeviceTemplates)
    if 'PostgreSQLServer' not in templates:
        templates.append('PostgreSQLServer')
        device.setZenProperty('zDeviceTemplates', templates)

    # Increase the COMMAND timeout to support big or slow database servers.
    if device.zCommandCommandTimeout < 180:
        device.setZenProperty('zCommandCommandTimeout', 180)

@monkeypatch('Products.ZenModel.Device.Device')
def getPostgreSQL(self):
    device = self.primaryAq()
    if 'PostgreSQLServer' in device.zDeviceTemplates \
       and device.zCommandCommandTimeout >= 180:
        return True

    return False

