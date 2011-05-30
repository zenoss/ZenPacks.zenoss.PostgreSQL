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

class database(CommandParser):
    def processResults(self, cmd, result):
        data = None
        try:
            data = json.loads(cmd.result.output)
        except ValueError:
            return

        if 'databases' not in data:
            return result

        for point in cmd.points:
            component = cmd.points[0].component

            database = None
            for dbName, dbStats in data['databases'].items():
                if dbName == component:
                    database = dbStats
                    break
            else:
                # No matching database found.
                continue

            if point.id in database:
                result.values.append((point, database[point.id]))

        return result

