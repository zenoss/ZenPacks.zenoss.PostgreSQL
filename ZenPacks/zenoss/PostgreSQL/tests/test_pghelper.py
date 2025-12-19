##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013-2025, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Globals
import datetime
from mock import MagicMock, patch
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from ZenPacks.zenoss.PostgreSQL.util import (
    PgHelper,
    datetimeToEpoch,
    datetimeDurationInSeconds,
    exclude_patterns_list,
    is_suppressed,
)


class TestConnectionCaching(BaseTestCase):
    """Tests for connection caching functionality"""

    @patch('psycopg2.connect')
    def test_connection_caching(self, mock_connect):
        """Test that connections are cached properly to avoid redundant opens"""
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost', port=5432, username='pg', password='pw',
            ssl=False, default_db='pg'
        )

        # First call should create a new connection
        conn1 = helper.getConnection('testdb')
        self.assertEqual(mock_connect.call_count, 1)

        # Second call should return cached connection
        conn2 = helper.getConnection('testdb')
        self.assertEqual(mock_connect.call_count, 1)
        self.assertIs(conn1, conn2)

    @patch('psycopg2.connect')
    def test_multiple_database_connections(self, mock_connect):
        """Test that different databases have separate connections"""
        mock_connect.return_value = MagicMock()

        helper = PgHelper(
            host='localhost', port=5432, username='pg', password='pw',
            ssl=False, default_db='pg'
        )

        helper.getConnection('db1')
        helper.getConnection('db2')

        self.assertEqual(mock_connect.call_count, 2)
        self.assertIn('db1', helper._connections)
        self.assertIn('db2', helper._connections)


class TestLatencyMeasurement(BaseTestCase):
    """Tests for latency measurement functionality"""

    @patch('psycopg2.connect')
    @patch('ZenPacks.zenoss.PostgreSQL.util.time')
    def test_connection_latency_measurement(self, mock_time, mock_connect):
        """Test that connection and query latency are calculated correctly"""
        # Mock time to simulate latency:
        # [conn_start, conn_end, query_start, query_end]
        mock_time.time.side_effect = [1000.0, 1000.5, 1000.5, 1000.6]

        mock_connect.return_value = MagicMock()

        helper = PgHelper(
            host='localhost', port=5432, username='pg', password='pw',
            ssl=False, default_db='pg'
        )

        helper.getConnection('testdb')

        self.assertAlmostEqual(
            helper._connections['testdb']['connection_latency'], 0.5, places=2
        )
        self.assertAlmostEqual(
            helper._connections['testdb']['query_latency'], 0.1, places=2
        )


class TestDatabaseOperations(BaseTestCase):
    """Tests for parsing database query results into Python structures"""

    @patch('psycopg2.connect')
    def test_get_databases_structure(self, mock_connect):
        """Test getDatabases parses raw SQL tuples into correct dictionaries"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('postgres', 12345, 1048576),
            ('testdb', 12346, 2097152),
        ]

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost', port=5432, username='pg', password='pw',
            ssl=False, default_db='pg'
        )

        databases = helper.getDatabases()

        self.assertEqual(databases['postgres']['oid'], 12345)
        self.assertEqual(databases['testdb']['size'], 2097152)

    @patch('psycopg2.connect')
    def test_get_database_stats_calculations(self, mock_connect):
        """Test getDatabaseStats calculations (percentages, totals)"""
        # Data format: (datname, size, backends, xact_commit, xact_rollback, ...)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('testdb', 1048576, 5, 1000, 50, 10000, 50000, 20000, 15000, 100, 200, 10),
        ]

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        helper = PgHelper(
            host='localhost', port=5432, username='pg', password='pw',
            ssl=False, default_db='pg'
        )

        stats = helper.getDatabaseStats()['testdb']

        # Verify computed fields logic
        expected_total_xact = 1000 + 50
        expected_rollback_pct = (50.0 / expected_total_xact) * 100

        self.assertEqual(stats['xactTotal'], expected_total_xact)
        self.assertAlmostEqual(stats['xactRollbackPct'], expected_rollback_pct, places=2)


class TestHelperFunctions(BaseTestCase):
    """Tests for utility functions"""

    def test_datetime_conversions(self):
        """Test datetimeToEpoch and duration calculations"""
        dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
        self.assertIsInstance(datetimeToEpoch(dt), float)

        begin = datetime.datetime(2023, 1, 1, 12, 0, 0)
        end = datetime.datetime(2023, 1, 1, 12, 0, 5, 500000)
        self.assertAlmostEqual(datetimeDurationInSeconds(begin, end), 5.5, places=2)

    def test_exclude_patterns(self):
        """Test regex pattern compilation and filtering logic"""
        excludes = ['test_.*', '# Comment', '', '  ']
        patterns = exclude_patterns_list(excludes)

        # Should only compile the one valid regex
        self.assertEqual(len(patterns), 1)
        self.assertTrue(is_suppressed('test_table', patterns))
        self.assertFalse(is_suppressed('prod_table', patterns))


class TestConnectionCleanup(BaseTestCase):
    """Tests for resource cleanup"""

    @patch('psycopg2.connect')
    def test_close_connections(self, mock_connect):
        """Test that close() triggers closure on all cached connections"""
        mock_conn1 = MagicMock()
        mock_conn2 = MagicMock()
        mock_connect.side_effect = [mock_conn1, mock_conn2]

        helper = PgHelper(
            host='localhost', port=5432, username='pg', password='pw',
            ssl=False, default_db='pg'
        )

        helper.getConnection('db1')
        helper.getConnection('db2')
        helper.close()

        # Fix for older mock versions used in Zenoss (2.7) which lack assert_called_once()
        self.assertEqual(mock_conn1.close.call_count, 1)
        self.assertEqual(mock_conn2.close.call_count, 1)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestConnectionCaching))
    suite.addTest(makeSuite(TestLatencyMeasurement))
    suite.addTest(makeSuite(TestDatabaseOperations))
    suite.addTest(makeSuite(TestHelperFunctions))
    suite.addTest(makeSuite(TestConnectionCleanup))
    return suite