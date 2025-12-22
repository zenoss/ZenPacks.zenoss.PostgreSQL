##############################################################################
#
# Copyright (C) Zenoss, Inc. 2025, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Globals
from mock import patch
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from ZenPacks.zenoss.PostgreSQL.util import PgHelper


class TestPgHelperInitialization(BaseTestCase):
    """
    Tests for Async Connection Pool configuration logic.
    Focuses on how PgHelper prepares arguments for adbapi.ConnectionPool.
    """

    def setUp(self):
        self.base_config = {
            'host': 'localhost',
            'port': 5432,
            'username': 'postgres',
            'password': 'secret',
            'default_db': 'postgres'
        }

    @patch('ZenPacks.zenoss.PostgreSQL.util.adbapi.ConnectionPool')
    def test_pool_creation_parameters(self, mock_pool):
        """
        Verify that _getConnectionPool correctly translates configuration
        parameters into arguments for adbapi.ConnectionPool.
        This covers both SSL transformation logic and basic driver selection.
        """
        # Case 1: SSL Enabled -> sslmode='require'
        helper_ssl = PgHelper(ssl=True, **self.base_config)
        helper_ssl._getConnectionPool()

        args, kwargs = mock_pool.call_args
        self.assertEqual(args[0], 'psycopg2')
        self.assertEqual(kwargs.get('sslmode'), 'require',
                         "SSL=True should map to sslmode='require'")

        # Reset mock for next assertion
        mock_pool.reset_mock()

        # Case 2: SSL Disabled -> sslmode='disable'
        helper_no_ssl = PgHelper(ssl=False, **self.base_config)
        helper_no_ssl._getConnectionPool()

        _, kwargs = mock_pool.call_args
        self.assertEqual(kwargs.get('sslmode'), 'disable',
                         "SSL=False should map to sslmode='disable'")


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPgHelperInitialization))
    return suite
