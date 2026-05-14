"""
=============================================================================
File: database.py
Author: Curtis Thetford
Date: May 14, 2026

Description:
Handles SQLite database connectivity, schema creation, version upgrades,
and automatic backups for the Sinkin Funds Manager application.

Change Log:
- 2.0 (05/14/2026): Rewritten in Python/PyQt6. Added schema version tracking, 
                    settings table, and dynamic backup retention.
- 1.0 : Original C# Version.
=============================================================================
"""
import sqlite3
import os
import shutil
from datetime import datetime, timedelta

class SavingsDatabase:
    """
    Coordinates connection and schema management for the underlying SQLite database.
    Performs automatic migrations, tracks database versions, and runs auto-backups.
    """
    def __init__(self, db_file="SavingsDatabase.sqlite"):
        """
        Initializes the database connection. Creates the database file if it 
        doesn't exist, establishes a connection, and runs any necessary upgrades.
        """
        self.db_file = db_file
        self.changed = False
        self.connection = None

        is_new = not os.path.exists(self.db_file)
        self.connect()
        if is_new:
            self.create_new()
            
        self.check_and_upgrade()

    def check_and_upgrade(self):
        """
        Verifies the database schema version based on the `db_version` table.
        Applies incremental schema updates (e.g. adding new Views or Settings tables)
        if the database is running an older schema version.
        """
        try:
            # Try to get the current version
            rows = self.execute_reader("SELECT version FROM db_version")
            current_version = rows[0]["version"]
        except sqlite3.OperationalError:
            # In older databases, the 'db_version' table won't exist.
            self.execute("CREATE TABLE db_version (version INTEGER)")
            self.execute("INSERT INTO db_version (version) VALUES (1)")
            current_version = 1
            
        if current_version < 2:
            try:
                self.execute("CREATE VIEW v_TotalsByWeek as select account, category, strftime('%Y',create_ts) as Y, strftime('%W',create_ts) as M, max(create_ts) as maxdate, sum(net_change) as amt from Transactions group by account, category, Y, M")
                self.execute("CREATE VIEW v_WeeklyTotals as select a.account, a.category, a.maxdate, strftime('%Y-%W', a.maxdate) as period, max(a.amt) as week_change, sum(b.amt) as ending_balance from v_TotalsByWeek a left join v_TotalsByWeek b on a.account = b.account and a.category = b.category and b.maxdate <= a.maxdate group by 1,2,3,4")
            except sqlite3.OperationalError: pass
            
            self.execute("UPDATE db_version SET version = 2")
            current_version = 2
            
        if current_version < 3:
            try:
                self.execute("CREATE TABLE d_Settings (key varchar(50) PRIMARY KEY, value varchar(256))")
            except sqlite3.OperationalError: pass
            
            self.execute("UPDATE db_version SET version = 3")
            current_version = 3

    def connect(self):
        """Establishes a connection to the SQLite database file and sets the row_factory to sqlite3.Row."""
        self.connection = sqlite3.connect(self.db_file)
        self.connection.row_factory = sqlite3.Row

    def close(self):
        """Safely closes the active database connection if one exists."""
        if self.connection:
            self.connection.close()

    def execute(self, sql, params=()):
        """
        Executes a write-operation SQL command (INSERT, UPDATE, DELETE) and commits changes.
        Flags the database instance as `changed` to trigger backup evaluations on close.
        """
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        self.connection.commit()
        self.changed = True

    def execute_reader(self, sql, params=()):
        """
        Executes a read-only SQL query (SELECT) and returns the fetched results.
        Returns: 
            list: A list of sqlite3.Row objects representing the result set.
        """
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()

    def create_new(self):
        """
        Scaffolds a completely new SQLite database instance. Builds base tables 
        (Accounts, Types, Categories, Transactions, Settings, Version) and summary Views.
        """
        cursor = self.connection.cursor()
        
        # Setup Database Version Tracking
        cursor.execute("CREATE TABLE db_version (version INTEGER)")
        cursor.execute("INSERT INTO db_version (version) VALUES (1)")
        
        # Setup Settings Table
        cursor.execute("CREATE TABLE d_Settings (key varchar(50) PRIMARY KEY, value varchar(256))")
        
        # Setup Tables with Hidden flags and Primary Keys
        cursor.execute("CREATE TABLE d_Accounts (name varchar(50) PRIMARY KEY, hidden character(1) DEFAULT 'N')")
        cursor.execute("CREATE TABLE d_Types (name varchar(50) PRIMARY KEY, color varchar(20))")
        cursor.execute("CREATE TABLE d_Categories (account varchar(50), name varchar(50), hidden character(1) DEFAULT 'N', type varchar(20), PRIMARY KEY(account, name))")
        cursor.execute("CREATE TABLE Transactions (account varchar(50), id integer, create_ts datetime, category varchar(50), net_change decimal(10,2), comment varchar (256))")
        
        # Create Views
        cursor.execute("CREATE VIEW v_TotalsByMonth as select account, category, strftime('%Y', create_ts) as Y, strftime('%m', create_ts) as M, max(create_ts) as maxdate, sum(net_change) as amt from Transactions group by account, category, Y, M")
        cursor.execute("CREATE VIEW v_PeriodTotals as select a.account, a.category, a.maxdate, strftime('%Y-%m', a.maxdate) as period, max(a.amt) as month_change, sum(b.amt) as ending_balance from v_TotalsByMonth a left join v_TotalsByMonth b on a.account = b.account and a.category = b.category and b.maxdate <= a.maxdate group by 1,2,3,4")
        
        cursor.execute("CREATE VIEW v_TotalsByWeek as select account, category, strftime('%Y',create_ts) as Y, strftime('%W',create_ts) as M, max(create_ts) as maxdate, sum(net_change) as amt from Transactions group by account, category, Y, M")
        cursor.execute("CREATE VIEW v_WeeklyTotals as select a.account, a.category, a.maxdate, strftime('%Y-%W', a.maxdate) as period, max(a.amt) as week_change, sum(b.amt) as ending_balance from v_TotalsByWeek a left join v_TotalsByWeek b on a.account = b.account and a.category = b.category and b.maxdate <= a.maxdate group by 1,2,3,4")

        self.connection.commit()

    def backup(self):
        """
        Creates a time-stamped backup of the `.sqlite` file in the Backup directory.
        Only runs if changes were made during the session. Automatically prunes 
        old backups based on the user's `backup_retention_days` setting.
        """
        if not self.changed: return
        
        try:
            retention_days = int(self.execute_reader("SELECT value FROM d_Settings WHERE key = 'backup_retention_days'")[0]["value"])
        except (sqlite3.OperationalError, IndexError, ValueError):
            retention_days = 7
            
        backup_dir = "Backup"
        if not os.path.exists(backup_dir): os.makedirs(backup_dir)
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        for filename in os.listdir(backup_dir):
            filepath = os.path.join(backup_dir, filename)
            if os.path.isfile(filepath) and datetime.fromtimestamp(os.path.getmtime(filepath)) < cutoff_date:
                os.remove(filepath)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(self.db_file, os.path.join(backup_dir, f"{os.path.basename(self.db_file)}.{timestamp}"))