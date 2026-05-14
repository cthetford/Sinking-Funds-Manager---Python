"""
=============================================================================
File: models.py
Author: Curtis Thetford
Date: May 14, 2026

Description:
Data models and core database interaction methods for Accounts, 
Category Types, Categories, Transactions, and AppSettings.

Change Log:
- 2.0 (05/14/2026): Rewritten in Python/PyQt6. Added AppSetting model, soft 
                    delete (hide/unhide) logic for accounts and categories.
- 1.0 : Original C# Version.
=============================================================================
"""
from datetime import datetime

class Account:
    """
    Manages Account entries in the database.
    Accounts represent high-level containers for categories and transactions.
    """
    @staticmethod
    def read_all_from_db(db, include_hidden=False):
        """
        Retrieves a list of all account names from the database.
        
        Args:
            db (Database): The active database connection object.
            include_hidden (bool): If True, hidden (soft-deleted) accounts are included.
            
        Returns:
            list: A list of account name strings.
        """
        sql = "SELECT * FROM d_Accounts" + ("" if include_hidden else " WHERE hidden != 'Y'") + " ORDER BY name"
        return [row["name"] for row in db.execute_reader(sql)]

    @staticmethod
    def add(db, name):
        """Adds a new account or replaces an existing one, marking it as active."""
        db.execute("INSERT OR REPLACE INTO d_Accounts (name, hidden) VALUES (?, 'N')", (name,))

    @staticmethod
    def delete(db, name):
        """Soft-deletes an account by setting its hidden flag to 'Y'."""
        db.execute("UPDATE d_Accounts SET hidden = 'Y' WHERE name = ?", (name,))

    @staticmethod
    def unhide(db, name):
        """Restores a soft-deleted account by setting its hidden flag back to 'N'."""
        db.execute("UPDATE d_Accounts SET hidden = 'N' WHERE name = ?", (name,))

class CategoryType:
    """
    Manages Category Types in the database.
    Used for grouping categories by type (e.g., Savings, Expenses) and assigning colors.
    """
    @staticmethod
    def read_all_from_db(db):
        """Retrieves all category types and their associated colors."""
        return [{"name": row["name"], "color": row["color"]} for row in db.execute_reader("SELECT * FROM d_Types ORDER BY name")]

    @staticmethod
    def add(db, name, color):
        """Adds a new category type or updates an existing one with a new color."""
        db.execute("INSERT OR REPLACE INTO d_Types (name, color) VALUES (?, ?)", (name, color))

    @staticmethod
    def delete(db, name):
        """Hard-deletes a category type from the database."""
        db.execute("DELETE FROM d_Types WHERE name = ?", (name,))

class Category:
    """
    Represents a sinking fund category linking directly to a parent Account.
    Tracks state including the visual color type and current fund total.
    """
    def __init__(self):
        self.name, self.type, self.hidden, self.color, self.total = "", "", "N", "", 0.0

    @staticmethod
    def add(db, account, name, type_name):
        db.execute("INSERT OR REPLACE INTO d_Categories (account, name, hidden, type) VALUES (?, ?, 'N', ?)", (account, name, type_name))

    @staticmethod
    def delete(db, account, name):
        db.execute("UPDATE d_Categories SET hidden = 'Y' WHERE account = ? AND name = ?", (account, name))

    @staticmethod
    def unhide(db, account, name):
        db.execute("UPDATE d_Categories SET hidden = 'N' WHERE account = ? AND name = ?", (account, name))

    @staticmethod
    def read_from_db(db, account, include_hidden=False):
        sql = "SELECT d_Categories.*, d_Types.color FROM d_Categories LEFT JOIN d_Types ON d_Categories.type = d_Types.name WHERE account = ?"
        if not include_hidden: sql += " AND d_Categories.hidden != 'Y'"
        results = {}
        for row in db.execute_reader(sql + " ORDER BY name", (account,)):
            c = Category()
            c.name, c.type, c.hidden, c.color = row["name"], row["type"], row["hidden"], (row["color"].strip() if row["color"] else "")
            results[c.name] = c
        return results

class Transaction:
    def __init__(self, t_date=None, category="", amount=0.0, comment=""):
        self.id = -1
        self.transaction_date = t_date or datetime.now()
        self.category, self.amount, self.comment, self.new_transaction, self.total = category, float(amount), comment, False, 0.0

class TransactionList:
    def __init__(self, db, account):
        self.account, self.my_db, self.transactions, self.category_totals = account, db, [], {}
        self.load()

    def load(self):
        self.category_totals = {row["category"]: float(row["total"]) for row in self.my_db.execute_reader("SELECT category, sum(net_change) as total FROM Transactions WHERE account = ? GROUP BY category", (self.account,))}
        row = self.my_db.execute_reader("SELECT max(id) FROM Transactions WHERE account = ?", (self.account,))
        self.latest_id = int(row[0][0]) if row and row[0][0] is not None else 0

    def get_category_sum(self, category): return self.category_totals.get(category, 0.0)

    def add_transaction(self, t):
        if t.amount == 0 and not t.comment: return
        t.new_transaction = True
        self.transactions.append(t)
        self.category_totals[t.category] = self.category_totals.get(t.category, 0.0) + t.amount

    def write(self):
        for t in self.transactions:
            if not t.new_transaction: continue
            self.latest_id += 1
            self.my_db.execute("INSERT INTO Transactions (account, id, create_ts, category, net_change, comment) VALUES (?, ?, ?, ?, ?, ?)", 
                               (self.account, self.latest_id, t.transaction_date.strftime("%Y-%m-%d %H:%M:%S"), t.category, t.amount, t.comment))
        self.transactions.clear()

class AppSetting:
    @staticmethod
    def get(db, key, default=""):
        try:
            rows = db.execute_reader("SELECT value FROM d_Settings WHERE key = ?", (key,))
            if rows: return rows[0]["value"]
        except: pass
        return default

    @staticmethod
    def set(db, key, value):
        db.execute("INSERT OR REPLACE INTO d_Settings (key, value) VALUES (?, ?)", (key, str(value)))