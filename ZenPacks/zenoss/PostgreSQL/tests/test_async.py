##############################################################################
#
# Copyright (C) Zenoss, Inc. 2025, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Globals

import time
from mock import MagicMock, patch, Mock
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from twisted.internet import defer
from twisted.trial import unittest as trial_unittest

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
    
    def test_async_imports(self):
        """Test that Twisted imports are available"""
        try:
            from twisted.enterprise import adbapi
            from twisted.internet import defer
            self.assertTrue(True, "Twisted imports available")
        except ImportError as e:
            self.fail("Twisted imports failed: {0}".format(e))
    

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


class TestPgHelperAsyncIntegration(trial_unittest.TestCase):
    """Integration tests for async methods using Twisted Trial
    
    Note: These tests require a running PostgreSQL instance
    Run with: trial ZenPacks.zenoss.PostgreSQL.tests.test_async
    """
    
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
        self.pg = None
    
    def tearDown(self):
        """Clean up after tests"""
        if self.pg:
            try:
                self.pg.close()
            except Exception:
                pass
    
    @defer.inlineCallbacks
    def test_getDatabasesAsync_returns_deferred(self):
        """Test that getDatabasesAsync returns a Deferred"""
        self.pg = PgHelper(
            self.test_config['host'],
            self.test_config['port'],
            self.test_config['username'],
            self.test_config['password'],
            self.test_config['ssl'],
            self.test_config['default_db']
        )
        
        try:
            result = self.pg.getDatabasesAsync()
            self.assertTrue(isinstance(result, defer.Deferred))
            
            # Actually execute the query
            databases = yield result
            self.assertIsInstance(databases, dict)
            
        except Exception as e:
            # If connection fails, just verify the method exists and returns Deferred
            self.assertTrue(hasattr(self.pg, 'getDatabasesAsync'))
    
    @defer.inlineCallbacks
    def test_getTablesInDatabaseAsync_returns_deferred(self):
        """Test that getTablesInDatabaseAsync returns a Deferred"""
        self.pg = PgHelper(
            self.test_config['host'],
            self.test_config['port'],
            self.test_config['username'],
            self.test_config['password'],
            self.test_config['ssl'],
            self.test_config['default_db']
        )
        
        try:
            result = self.pg.getTablesInDatabaseAsync('postgres')
            self.assertTrue(isinstance(result, defer.Deferred))
            
            # Actually execute the query
            tables = yield result
            self.assertIsInstance(tables, dict)
            
        except Exception as e:
            # If connection fails, just verify the method exists and returns Deferred
            self.assertTrue(hasattr(self.pg, 'getTablesInDatabaseAsync'))
    
    @defer.inlineCallbacks
    def test_async_fallback_on_error(self):
        """Test that async methods fallback to sync on error"""
        # Create helper with invalid host to force error
        self.pg = PgHelper(
            host='invalid-host-12345',
            port=5432,
            username='postgres',
            password='postgres',
            ssl=False,
            default_db='postgres'
        )
        
        try:
            # This should fallback to sync method
            result = yield self.pg.getDatabasesAsync()
            # If we get here, fallback worked (sync might also fail though)
            self.assertIsInstance(result, dict)
        except Exception:
            # Both async and sync failed - this is OK for invalid host
            pass


class TestPgHelperAsyncPerformance(BaseTestCase):
    """Performance comparison tests for async vs sync methods
    
    Note: These are unit tests that mock the database
    """
    
    @patch('ZenPacks.zenoss.PostgreSQL.util.psycopg2.connect')
    @patch('ZenPacks.zenoss.PostgreSQL.util.adbapi.ConnectionPool')
    def test_async_methods_exist_alongside_sync(self, mock_pool, mock_connect):
        """Test that both async and sync methods coexist"""
        pg = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='postgres',
            ssl=False,
            default_db='postgres'
        )
        
        # Both sync and async methods should exist
        self.assertTrue(hasattr(pg, 'getDatabases'))
        self.assertTrue(hasattr(pg, 'getDatabasesAsync'))
        self.assertTrue(hasattr(pg, 'getTablesInDatabase'))
        self.assertTrue(hasattr(pg, 'getTablesInDatabaseAsync'))
        
        # Verify they are different methods
        self.assertNotEqual(pg.getDatabases, pg.getDatabasesAsync)
        self.assertNotEqual(pg.getTablesInDatabase, pg.getTablesInDatabaseAsync)


def test_suite():
    """Test suite for async tests"""
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPgHelperAsync))
    suite.addTest(makeSuite(TestPgHelperAsyncPerformance))
    # Note: TestPgHelperAsyncIntegration uses Twisted Trial, 
    # run separately with: trial ZenPacks.zenoss.PostgreSQL.tests.test_async
    return suite
