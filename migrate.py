"""
=============================================================================
File: migrate.py
Author: Curtis Thetford
Date: May 14, 2026

Description:
Standalone migration script to convert Version 1.0 setup elements (.txt files)
and legacy transactions into the new Version 2.0 SQLite architecture.

Change Log:
- 2.0 (05/14/2026): Created script to transition text-based metadata to the 
                    centralized SQLite tracking standard.
=============================================================================
"""
import sqlite3
import os
from database import SavingsDatabase
from models import Account, CategoryType, Category

def migrate():
    """
    Executes the one-time migration workflow.
    
    Workflow steps:
    1. Initializes an empty V2 database instance using SavingsDatabase scaffolding.
    2. Parses legacy `Accounts.txt`, `Types.txt`, and `Categories.txt` flat files
       into normalized SQL table entries via Model classes.
    3. Copies over legacy table data (`Transactions`) unchanged into the new schema.
    """
    old_db_file = "SavingsDatabase.sqlite"
    new_db_file = "SavingsDatabase_V2.sqlite"

    if os.path.exists(new_db_file):
        print(f"Error: {new_db_file} already exists. Please delete or rename it before running migration.")
        return

    # 1. Initialize the NEW database (this creates the new tables/views)
    print("Creating new database schema...")
    new_db = SavingsDatabase(db_file=new_db_file)

    # 2. Import Setup Data from Text Files
    print("Importing setup from .txt files...")
    
    if os.path.exists("Accounts.txt"):
        with open("Accounts.txt", "r") as f:
            for line in f:
                name = line.strip()
                if name and not name.startswith("#"):
                    Account.add(new_db, name)

    if os.path.exists("Types.txt"):
        with open("Types.txt", "r") as f:
            for line in f:
                if line.strip() and not line.strip().startswith("#"):
                    tokens = [t.strip() for t in line.split(',')]
                    if len(tokens) >= 2:
                        CategoryType.add(new_db, tokens[0], tokens[1])

    if os.path.exists("Categories.txt"):
        with open("Categories.txt", "r") as f:
            for line in f:
                if line.strip() and not line.strip().startswith("#"):
                    tokens = [t.strip() for t in line.split(',')]
                    if len(tokens) >= 4:
                        # account, name, hidden, type
                        Category.add(new_db, tokens[0], tokens[1], tokens[3])

    # 3. Import Transactions from OLD Database
    if os.path.exists(old_db_file):
        print(f"Migrating transactions from {old_db_file}...")
        try:
            old_conn = sqlite3.connect(old_db_file)
            old_conn.row_factory = sqlite3.Row
            cursor = old_conn.cursor()
            
            transactions = cursor.execute("SELECT * FROM Transactions").fetchall()
            
            for t in transactions:
                sql = """
                    INSERT INTO Transactions 
                    (account, id, create_ts, category, net_change, comment) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                new_db.execute(sql, (
                    t['account'], t['id'], t['create_ts'], 
                    t['category'], t['net_change'], t['comment']
                ))
            
            old_conn.close()
            print(f"Successfully migrated {len(transactions)} transactions.")
        except Exception as e:
            print(f"Warning: Could not migrate transactions. Error: {e}")
    else:
        print("Old database file not found. Skipping transaction migration.")

    new_db.close()
    print("\nMigration Complete!")
    print(f"New file created: {new_db_file}")
    print("To use this, rename it to 'SavingsDatabase.sqlite' or update your main.py.")

if __name__ == "__main__":
    migrate()