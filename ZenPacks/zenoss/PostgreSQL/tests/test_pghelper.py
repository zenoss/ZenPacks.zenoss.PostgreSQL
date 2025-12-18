##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Globals

import datetime
import time
from mock import MagicMock, patch, Mock
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from ZenPacks.zenoss.PostgreSQL.util import (
    PgHelper,
    datetimeToEpoch,
    datetimeDurationInSeconds,
    exclude_patterns_list,
    is_suppressed,
)


class TestPgHelperInitialization(BaseTestCase):
    """Tests for PgHelper initialization"""

    def test_init_with_ssl_enabled(self):
        """Test PgHelper initialization with SSL enabled"""
        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=True,
            default_db='postgres'
        )

        self.assertEqual(helper._host, 'localhost')
        self.assertEqual(helper._port, 5432)
        self.assertEqual(helper._username, 'postgres')
        self.assertEqual(helper._password, 'secret')
        self.assertEqual(helper._ssl, True)
        self.assertEqual(helper._default_db, 'postgres')
        self.assertEqual(helper._connections, {})
        self.assertIsNone(helper._pool)

    def test_init_with_ssl_disabled(self):
        """Test PgHelper initialization with SSL disabled"""
        helper = PgHelper(
            host='192.168.1.100',
            port=5433,
            username='dbuser',
            password='dbpass',
            ssl=False,
            default_db='mydb'
        )

        self.assertEqual(helper._host, '192.168.1.100')
        self.assertEqual(helper._port, 5433)
        self.assertEqual(helper._username, 'dbuser')
        self.assertEqual(helper._password, 'dbpass')
        self.assertEqual(helper._ssl, False)
        self.assertEqual(helper._default_db, 'mydb')


class TestConnectionParameters(BaseTestCase):
    """Tests for connection parameters (basic attribute checks)"""

    def test_connection_attributes_with_ssl_enabled(self):
        """Test PgHelper attributes with SSL enabled"""
        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=True,
            default_db='postgres'
        )

        self.assertEqual(helper._host, 'localhost')
        self.assertEqual(helper._port, 5432)
        self.assertEqual(helper._username, 'postgres')
        self.assertEqual(helper._password, 'secret')
        self.assertEqual(helper._ssl, True)

    def test_connection_attributes_with_ssl_disabled(self):
        """Test PgHelper attributes with SSL disabled"""
        helper = PgHelper(
            host='192.168.1.100',
            port=5433,
            username='dbuser',
            password='dbpass',
            ssl=False,
            default_db='postgres'
        )

        self.assertEqual(helper._host, '192.168.1.100')
        self.assertEqual(helper._port, 5433)
        self.assertEqual(helper._username, 'dbuser')
        self.assertEqual(helper._password, 'dbpass')
        self.assertEqual(helper._ssl, False)

    def test_connection_port_as_string(self):
        """Test that port can be provided as string"""
        helper = PgHelper(
            host='localhost',
            port='5432',  # String port
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        # Port is stored as provided (string or int)
        self.assertEqual(helper._port, '5432')


class TestConnectionCaching(BaseTestCase):
    """Tests for connection caching functionality"""

    @patch('psycopg2.connect')
    def test_connection_caching(self, mock_connect):
        """Test that connections are cached properly"""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        # First call should create a new connection
        conn1 = helper.getConnection('testdb')
        self.assertEqual(mock_connect.call_count, 1)
        self.assertIn('testdb', helper._connections)

        # Second call should return cached connection
        conn2 = helper.getConnection('testdb')
        self.assertEqual(mock_connect.call_count, 1)  # Still 1
        self.assertIs(conn1, conn2)

    @patch('psycopg2.connect')
    def test_multiple_database_connections(self, mock_connect):
        """Test that different databases have separate connections"""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        # Connect to first database
        helper.getConnection('db1')
        self.assertEqual(mock_connect.call_count, 1)

        # Connect to second database
        helper.getConnection('db2')
        self.assertEqual(mock_connect.call_count, 2)

        # Both should be cached
        self.assertIn('db1', helper._connections)
        self.assertIn('db2', helper._connections)


class TestLatencyMeasurement(BaseTestCase):
    """Tests for latency measurement functionality"""

    @patch('psycopg2.connect')
    @patch('ZenPacks.zenoss.PostgreSQL.util.time')
    def test_connection_latency_measurement(self, mock_time, mock_connect):
        """Test that connection latency is measured correctly"""
        # Mock time to simulate latency
        mock_time.time.side_effect = [
            1000.0,  # connection_begin
            1000.5,  # after connection (0.5s latency)
            1000.5,  # query_begin
            1000.6,  # after query (0.1s latency)
        ]

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        helper.getConnection('testdb')

        self.assertAlmostEqual(
            helper._connections['testdb']['connection_latency'], 0.5, places=2
        )
        self.assertAlmostEqual(
            helper._connections['testdb']['query_latency'], 0.1, places=2
        )

    @patch('psycopg2.connect')
    def test_get_connection_latency_for_database(self, mock_connect):
        """Test getConnectionLatencyForDatabase method"""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        helper.getConnection('testdb')
        latency = helper.getConnectionLatencyForDatabase('testdb')

        self.assertIsInstance(latency, float)
        self.assertGreaterEqual(latency, 0)

    @patch('psycopg2.connect')
    def test_get_query_latency_for_database(self, mock_connect):
        """Test getQueryLatencyForDatabase method"""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        helper.getConnection('testdb')
        latency = helper.getQueryLatencyForDatabase('testdb')

        self.assertIsInstance(latency, float)
        self.assertGreaterEqual(latency, 0)


class TestDatabaseOperations(BaseTestCase):
    """Tests for database query operations and JSON structure"""

    @patch('psycopg2.connect')
    def test_get_databases_structure(self, mock_connect):
        """Test getDatabases returns correct JSON structure"""
        # Mock cursor with sample data
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('postgres', 12345, 1048576),
            ('testdb', 12346, 2097152),
        ]

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        databases = helper.getDatabases()

        # Check structure
        self.assertIn('postgres', databases)
        self.assertIn('testdb', databases)

        # Check postgres database structure
        self.assertIn('oid', databases['postgres'])
        self.assertIn('size', databases['postgres'])
        self.assertEqual(databases['postgres']['oid'], 12345)
        self.assertEqual(databases['postgres']['size'], 1048576)

        # Check testdb database structure
        self.assertEqual(databases['testdb']['oid'], 12346)
        self.assertEqual(databases['testdb']['size'], 2097152)

    @patch('psycopg2.connect')
    def test_get_database_stats_structure(self, mock_connect):
        """Test getDatabaseStats returns correct JSON structure"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('testdb', 1048576, 5, 1000, 50, 10000, 50000, 20000, 15000, 100, 200, 10),
        ]

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        stats = helper.getDatabaseStats()

        # Check structure
        self.assertIn('testdb', stats)
        db_stats = stats['testdb']

        # Check all required fields
        required_fields = [
            'size', 'numBackends', 'xactCommit', 'xactRollback',
            'xactTotal', 'xactRollbackPct', 'blksRead', 'blksHit',
            'tupReturned', 'tupFetched', 'tupTotal', 'tupFetchedPct',
            'tupInserted', 'tupUpdated', 'tupDeleted'
        ]

        for field in required_fields:
            self.assertIn(field, db_stats)

        # Check calculated values
        self.assertEqual(db_stats['xactTotal'], 1050)  # 1000 + 50
        self.assertAlmostEqual(db_stats['xactRollbackPct'], (50.0 / 1050) * 100, places=2)
        self.assertEqual(db_stats['tupTotal'], 35000)  # 20000 + 15000
        self.assertAlmostEqual(db_stats['tupFetchedPct'], (15000.0 / 35000) * 100, places=2)

    @patch('psycopg2.connect')
    def test_get_connection_stats_structure(self, mock_connect):
        """Test getConnectionStats returns correct JSON structure"""
        now = datetime.datetime.now()

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('testdb', now, now, now, now),
            ('testdb', None, None, now, now),
        ]

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        stats = helper.getConnectionStats()

        # Check top-level structure
        self.assertIn('databases', stats)
        self.assertIn('totalConnections', stats)
        self.assertIn('activeConnections', stats)
        self.assertIn('idleConnections', stats)

        # Check counts
        self.assertEqual(stats['totalConnections'], 2)
        self.assertEqual(stats['activeConnections'], 1)
        self.assertEqual(stats['idleConnections'], 1)

        # Check database-specific stats
        self.assertIn('testdb', stats['databases'])
        db_stats = stats['databases']['testdb']
        self.assertIn('totalConnections', db_stats)
        self.assertIn('activeConnections', db_stats)
        self.assertIn('idleConnections', db_stats)

    @patch('psycopg2.connect')
    def test_get_locks_structure(self, mock_connect):
        """Test getLocks returns correct JSON structure"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('testdb', 'AccessShareLock', True),
            ('testdb', 'RowExclusiveLock', False),
        ]

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        locks = helper.getLocks()

        # Check top-level structure
        self.assertIn('databases', locks)
        self.assertIn('locksTotal', locks)
        self.assertIn('locksTotalGranted', locks)
        self.assertIn('locksTotalWaiting', locks)

        # Check counts
        self.assertEqual(locks['locksTotal'], 2)
        self.assertEqual(locks['locksTotalGranted'], 1)
        self.assertEqual(locks['locksTotalWaiting'], 1)

        # Check lock mode keys exist
        self.assertIn('locksAccessShare', locks)
        self.assertIn('locksRowExclusive', locks)

    @patch('psycopg2.connect')
    def test_get_tables_in_database(self, mock_connect):
        """Test getTablesInDatabase returns correct structure"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('users', 12345, 'public', 8192, 16384),
            ('orders', 12346, 'public', 16384, 32768),
        ]

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        tables = helper.getTablesInDatabase('testdb')

        # Check structure
        self.assertIn('users', tables)
        self.assertIn('orders', tables)

        # Check users table
        self.assertEqual(tables['users']['oid'], 12345)
        self.assertEqual(tables['users']['schema'], 'public')
        self.assertEqual(tables['users']['size'], 8192)
        self.assertEqual(tables['users']['totalSize'], 16384)

    @patch('psycopg2.connect')
    def test_get_table_stats_for_database(self, mock_connect):
        """Test getTableStatsForDatabase returns correct structure"""
        now = datetime.datetime.now()

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('users', 8192, 16384, 100, 1000, 200, 2000, 50, 30, 10, 20, 500, 50,
             now, now, now, now),
        ]

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        stats = helper.getTableStatsForDatabase('testdb')

        # Check structure
        self.assertIn('users', stats)
        table_stats = stats['users']

        # Check all required fields
        required_fields = [
            'size', 'totalSize', 'seqScan', 'seqTupRead', 'idxScan',
            'idxTupFetch', 'nTupIns', 'nTupUpd', 'nTupDel', 'nTupHotUpd',
            'nLiveTup', 'nDeadTup', 'lastVacuum', 'lastAutoVacuum',
            'lastAnalyze', 'lastAutoAnalyze'
        ]

        for field in required_fields:
            self.assertIn(field, table_stats)


class TestHelperFunctions(BaseTestCase):
    """Tests for helper utility functions"""

    def test_datetime_to_epoch(self):
        """Test datetimeToEpoch converts datetime to epoch correctly"""
        dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
        epoch = datetimeToEpoch(dt)

        self.assertIsInstance(epoch, float)
        self.assertGreater(epoch, 0)

    def test_datetime_duration_in_seconds(self):
        """Test datetimeDurationInSeconds calculates duration correctly"""
        begin = datetime.datetime(2023, 1, 1, 12, 0, 0)
        end = datetime.datetime(2023, 1, 1, 12, 0, 5, 500000)  # 5.5 seconds later

        duration = datetimeDurationInSeconds(begin, end)

        self.assertAlmostEqual(duration, 5.5, places=2)

    def test_datetime_duration_microseconds(self):
        """Test that microseconds are included in duration calculation"""
        begin = datetime.datetime(2023, 1, 1, 12, 0, 0, 0)
        end = datetime.datetime(2023, 1, 1, 12, 0, 0, 123456)

        duration = datetimeDurationInSeconds(begin, end)

        self.assertAlmostEqual(duration, 0.123456, places=6)

    def test_exclude_patterns_list_valid(self):
        """Test exclude_patterns_list with valid patterns"""
        excludes = [
            'test_.*',
            '^pg_.*',
            '.*_temp$',
        ]

        patterns = exclude_patterns_list(excludes)

        self.assertEqual(len(patterns), 3)
        for pattern in patterns:
            self.assertTrue(hasattr(pattern, 'search'))

    def test_exclude_patterns_list_with_comments(self):
        """Test exclude_patterns_list ignores comments"""
        excludes = [
            'test_.*',
            '# This is a comment',
            '^pg_.*',
            '',  # Empty line
            '  ',  # Whitespace only
        ]

        patterns = exclude_patterns_list(excludes)

        # Should only have 2 valid patterns (comments and empty lines ignored)
        self.assertEqual(len(patterns), 2)

    def test_exclude_patterns_list_invalid_regex(self):
        """Test exclude_patterns_list handles invalid regex gracefully"""
        excludes = [
            'valid_.*',
            '[invalid(',  # Invalid regex
            'another_valid',
        ]

        # Should not raise exception
        patterns = exclude_patterns_list(excludes)

        # Should have 2 valid patterns (invalid one skipped)
        self.assertEqual(len(patterns), 2)

    def test_is_suppressed_matches(self):
        """Test is_suppressed returns True for matching patterns"""
        import re
        patterns = [
            re.compile('test_.*'),
            re.compile('^pg_.*'),
        ]

        self.assertTrue(is_suppressed('test_table', patterns))
        self.assertTrue(is_suppressed('pg_catalog', patterns))

    def test_is_suppressed_no_match(self):
        """Test is_suppressed returns False for non-matching patterns"""
        import re
        patterns = [
            re.compile('test_.*'),
            re.compile('^pg_.*'),
        ]

        self.assertFalse(is_suppressed('users', patterns))
        self.assertFalse(is_suppressed('orders', patterns))

    def test_is_suppressed_empty_patterns(self):
        """Test is_suppressed with empty pattern list"""
        patterns = []

        self.assertFalse(is_suppressed('any_table', patterns))


class TestConnectionCleanup(BaseTestCase):
    """Tests for connection cleanup"""

    @patch('psycopg2.connect')
    def test_close_connections(self, mock_connect):
        """Test that close() properly closes all connections"""
        mock_connection1 = MagicMock()
        mock_connection2 = MagicMock()
        mock_cursor = MagicMock()

        mock_connection1.cursor.return_value = mock_cursor
        mock_connection2.cursor.return_value = mock_cursor

        # Return different connections for different calls
        mock_connect.side_effect = [mock_connection1, mock_connection2]

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        # Create connections
        helper.getConnection('db1')
        helper.getConnection('db2')

        # Close all
        helper.close()

        # Check that both connections were closed
        self.assertEqual(mock_connection1.close.call_count, 1)
        self.assertEqual(mock_connection2.close.call_count, 1)

    @patch('psycopg2.connect')
    def test_close_handles_exceptions(self, mock_connect):
        """Test that close() handles exceptions gracefully"""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.close.side_effect = Exception("Connection already closed")
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost',
            port=5432,
            username='postgres',
            password='secret',
            ssl=False,
            default_db='postgres'
        )

        helper.getConnection('testdb')

        # Should not raise exception
        helper.close()


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPgHelperInitialization))
    suite.addTest(makeSuite(TestConnectionParameters))
    suite.addTest(makeSuite(TestConnectionCaching))
    suite.addTest(makeSuite(TestLatencyMeasurement))
    suite.addTest(makeSuite(TestDatabaseOperations))
    suite.addTest(makeSuite(TestHelperFunctions))
    suite.addTest(makeSuite(TestConnectionCleanup))
    return suite
