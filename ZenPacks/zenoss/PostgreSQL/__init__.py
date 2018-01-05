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
    ]

    def install(self, app):
        super(ZenPack, self).install(app)
        self.symlinkPlugin()
        self.updateExistingRelations(app.zport.dmd)

    def remove(self, app, leaveObjects=False):
        if not leaveObjects:
            # Remove our custom relations addition.
            Device._relations = tuple(
                [ x for x in Device._relations if x[0] != 'pgDatabases' ])

            self.updateExistingRelations(app.zport.dmd)
            self.removePluginSymlink()

        super(ZenPack, self).remove(app, leaveObjects=leaveObjects)

    def symlinkPlugin(self):
        log.info('Linking poll_postgres.py plugin into $ZENHOME/libexec/')
        plugin_path = self.path('poll_postgres.py')

        os.system('chmod 0755 {0}'.format(plugin_path))
        os.system('ln -sf {0} {1}'.format(
            plugin_path,
            zenPath('libexec', 'poll_postgres.py')))

    def removePluginSymlink(self):
        log.info('Removing poll_postgres.py link from $ZENHOME/libexec/')
        os.system('rm -f {0}'.format(zenPath('libexec', 'poll_postgres.py')))

    def updateExistingRelations(self, dmd):
        log.info('Adding pgDatabases relationship to existing devices')
        for device in dmd.Devices.getSubDevicesGen():
            device.buildRelations()

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

