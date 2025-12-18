##############################################################################
#
# Copyright (C) Zenoss, Inc. 2025, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Globals

from mock import MagicMock, patch, Mock
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from ZenPacks.zenoss.PostgreSQL.util import PgHelper


class TestPgHelperAsync(BaseTestCase):
    """Tests for PgHelper async methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_config = {
            'host': 'localhost',
            'port': 5432,
            'username': 'postgres',
            'password': 'postgres',
            'ssl': False,
            'default_db': 'postgres'
        }
    
    @patch('ZenPacks.zenoss.PostgreSQL.util.adbapi.ConnectionPool')
    def test_get_connection_pool_creates_pool(self, mock_pool):
        """Test that _getConnectionPool creates a pool"""
        pg = PgHelper(
            self.test_config['host'],
            self.test_config['port'],
            self.test_config['username'],
            self.test_config['password'],
            self.test_config['ssl'],
            self.test_config['default_db']
        )
        
        pool = pg._getConnectionPool()
        
        # Pool should be created
        self.assertTrue(mock_pool.called)
        # Verify psycopg2 driver is used
        args, kwargs = mock_pool.call_args
        self.assertEqual(args[0], 'psycopg2')
        
    @patch('ZenPacks.zenoss.PostgreSQL.util.adbapi.ConnectionPool')
    def test_get_connection_pool_with_ssl(self, mock_pool):
        """Test that _getConnectionPool handles SSL correctly"""
        pg = PgHelper(
            self.test_config['host'],
            self.test_config['port'],
            self.test_config['username'],
            self.test_config['password'],
            ssl=True,  # SSL enabled
            default_db=self.test_config['default_db']
        )
        
        pool = pg._getConnectionPool()
        
        # Verify SSL mode is set
        args, kwargs = mock_pool.call_args
        self.assertEqual(kwargs.get('sslmode'), 'require')
    
    @patch('ZenPacks.zenoss.PostgreSQL.util.adbapi.ConnectionPool')
    def test_get_connection_pool_without_ssl(self, mock_pool):
        """Test that _getConnectionPool handles no SSL correctly"""
        pg = PgHelper(
            self.test_config['host'],
            self.test_config['port'],
            self.test_config['username'],
            self.test_config['password'],
            ssl=False,  # SSL disabled
            default_db=self.test_config['default_db']
        )
        
        pool = pg._getConnectionPool()
        
        # Verify SSL mode is disabled
        args, kwargs = mock_pool.call_args
        self.assertEqual(kwargs.get('sslmode'), 'disable')


def test_suite():
    """Test suite for async tests"""
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPgHelperAsync))
    return suite

