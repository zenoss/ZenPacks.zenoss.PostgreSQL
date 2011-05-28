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

import json

from Products.ZenRRD.CommandParser import CommandParser

class table(CommandParser):
    def processResults(self, cmd, result):
        data = json.loads(cmd.result.output)

        for point in cmd.points:
            component = cmd.points[0].component

            table = None
            for dbName, dbStats in data['databases'].items():
                if table is not None:
                    break

                for tableName, tableStats in dbStats['tables'].items():
                    component_id = '{0}_{1}'.format(dbName, tableName)
                    if component_id == component:
                        table = tableStats
                        break

            if table is None:
                # No matching table found.
                continue

            if point.id in table:
                result.values.append((point, table[point.id]))

        return result

