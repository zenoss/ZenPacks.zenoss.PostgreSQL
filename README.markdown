# ZenPacks.zenoss.PostgreSQL

## About
This project is [Zenoss][] extension (ZenPack) that makes it possible to
monitor the performance of a PostgreSQL database server, the individual
databases and the tables within those databases.

## Installation
You must first have, or install, Zenoss 3.1.0 or later. Core and Enterprise
versions are supported. You can download the free Core version of Zenoss from
<http://community.zenoss.org/community/download>.

### Normal Installation (packaged egg)
Download the [latest PostgreSQL ZenPack][]. Copy this file to your Zenoss
server and run the following commands as the zenoss user.

    zenpack --install ZenPacks.zenoss.PostgreSQL-1.0.0-py2.6.egg
    zenoss restart

### Developer Installation (link mode)
If you wish to further develop and possibly contribute back to the PostgreSQL
ZenPack you should clone the [git repository][], then install the ZenPack in
developer mode using the following commands.

    git clone git://github.com/zenoss/ZenPacks.zenoss.PostgreSQL.git
    zenpack --link --install ZenPacks.zenoss.PostgreSQL
    zenoss restart

## Usage
Once the PostgreSQL ZenPack is installed you will have the following new
zProperties which should be set either for device classes or individual
devices.

 * zPostgreSQLPort - Port where PostgreSQL is listening. Default: 5432
 * zPostgreSQLUseSSL - Whether to use SSL or not. Default: False
 * zPostgreSQLUsername - Must be a superuser. Default: postgres
 * zPostgreSQLPassword - Password for user. No default.

In addition to setting these properties you must add the zenoss.PostgreSQL
modeler plugin to a device class or individual device. This modeler plugin
will discover all databases and tables using the connectivity information
provided through the above settings. Each database and table will
automatically be monitored.

The following elements are discovered:

 * Databases
  * Tables

The following performance metrics are collected.

 * Server
  * Summaries of all databases and tables.
 * Databases
  * Latencies
   * Connection
   * SELECT 1
  * Connections
   * Total
   * Active
   * Idle
  * Durations
   * Active Transactions (min/avg/max)
   * Idle Transactions (min/avg/max)
   * Queries (min/avg/max)
  * Size
  * Backends
  * Efficiencies
   * Transaction Rollback Percentage
   * Tuple Fetch Percentage
  * Transaction Rates
   * Commits/sec
   * Rollbacks/sec
  * Tuple Rates
   * Returned/sec
   * Fetched/sec
   * Inserted/sec
   * Updated/sec
   * Deleted/sec
  * Locks
   * Total
   * Granted
   * Waiting
   * Exclusive
   * AccessExclusive
  * Summaries of all tables.
 * Tables
  * Scan Rates
   * Sequential/sec
   * Indexed/sec
  * Tuple Rates
   * Sequentially Read/sec
   * Index Fetched/sec
   * Inserted/sec
   * Updated/sec
   * Hot Updated/sec
   * Deleted/sec
  * Tuples
   * Live
   * Dead

## PostgreSQL Server Impact
Zenoss will run the following queries every five (5) minutes. These queries
are intended to be lightweight so as to not adversely affect the server's
performance.

    # Database statistics - Run once.
    SELECT d.datname,
           pg_database_size(s.datid) AS size,
           numbackends,
           xact_commit, xact_rollback,
           blks_read, blks_hit,
           tup_returned, tup_fetched, tup_inserted,
           tup_updated, tup_deleted
      FROM pg_database AS d
      JOIN pg_stat_database AS s ON s.datname = d.datname
     WHERE NOT datistemplate AND datallowconn

    # Connection statistics - Run once.
    SELECT datname, xact_start, query_start, backend_start,
           now() AS now
      FROM pg_stat_activity

    # Lock statistics - Run once.
    SELECT d.datname, l.mode, l.granted
      FROM pg_database AS d
      LEFT JOIN pg_locks AS l ON l.database = d.oid
     WHERE NOT d.datistemplate AND d.datallowconn

    # Table statistics - Run once per database.
    SELECT relname,
           pg_relation_size(relid),
           pg_total_relation_size(relid),
           seq_scan, seq_tup_read,
           idx_scan, idx_tup_fetch,
           n_tup_ins, n_tup_upd, n_tup_del,
           n_tup_hot_upd, n_live_tup, n_dead_tup,
           last_vacuum, last_autovacuum,
           last_analyze, last_autoanalyze
      FROM pg_stat_user_tables

The following queries will be run whenever the PostgreSQL server device is
remodeled. This will once every 12 hours.

    # Database list - Run once.
    SELECT d.datname, s.datid, pg_database_size(s.datid) AS size
      FROM pg_database AS d
      JOIN pg_stat_database AS s ON s.datname = d.datname
     WHERE NOT datistemplate AND datallowconn

    # Table list - Run once per database.
    SELECT relname, relid, schemaname,
           pg_relation_size(relid) AS size,
           pg_total_relation_size(relid) AS total_size
      FROM pg_stat_user_tables


[Zenoss]: <http://www.zenoss.com/>
[latest PostgreSQL ZenPack]: <https://github.com/downloads/zenoss/ZenPacks.zenoss.PostgreSQL/ZenPacks.zenoss.PostgreSQL-1.0.0-py2.6.egg>
[git repository]: <https://github.com/zenoss/ZenPacks.zenoss.PostgreSQL>
