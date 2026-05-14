"""
=============================================================================
File: main.py
Author: Curtis Thetford
Date: May 14, 2026

Description:
Main PyQt6 graphical user interface for Sinking Funds Manager.
Handles overall application flow, the main spreadsheet logic, history reports,
and settings dialogs.

Change Log:
- 2.0 (05/14/2026): Rewritten in Python/PyQt6. Added FastInputTable, custom UI 
                    dialogs for settings, SVG branding, and history reporting.
- 1.0 : Original C# Version.
=============================================================================
"""
#  pip install PyQt6
import sys
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget, 
                             QTableWidgetItem, QPushButton, QDateEdit, QHeaderView, QMenuBar, QDialog, QTabWidget, QListWidget, QLineEdit, QMessageBox, QAbstractItemView, QMenu)
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtCore import QDate, Qt
from database import SavingsDatabase
from models import Account, CategoryType, Category, Transaction, TransactionList, AppSetting

class FastInputTable(QTableWidget):
    """
    Subclasses QTableWidget to intercept tab key presses (cursor navigation).
    Will automatically skip disabled columns (e.g. Total columns) ensuring very fast
    data entry using the keyboard.
    """
    def moveCursor(self, cursorAction, modifiers):
        idx = super().moveCursor(cursorAction, modifiers)
        if cursorAction in (QAbstractItemView.CursorAction.MoveNext, QAbstractItemView.CursorAction.MovePrevious):
            while idx.isValid() and idx.column() not in (3, 5):
                # Temporarily set current cell to the intermediate index to simulate stepping through
                old_idx = self.currentIndex()
                self.setCurrentIndex(idx)
                idx = super().moveCursor(cursorAction, modifiers)
                self.setCurrentIndex(old_idx)
                
                # Failsafe to prevent endless loop if we hit the end
                if not idx.isValid() or idx == old_idx:
                    break
        return idx

class AccountsDialog(QDialog):
    """
    Dialog for adding and soft-deleting accounts.
    Allows users to see a distinct list of active accounts and add new ones to the db.
    """
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Manage Accounts")
        self.resize(400, 300)
        layout = QVBoxLayout(self)
        self.acct_list = QListWidget()
        self.refresh_accounts()
        layout.addWidget(self.acct_list)
        btn_layout = QHBoxLayout()
        self.new_acct_input = QLineEdit()
        self.new_acct_input.setPlaceholderText("New Account...")
        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self.add_account)
        btn_del = QPushButton("Delete")
        btn_del.clicked.connect(self.del_account)
        btn_layout.addWidget(self.new_acct_input); btn_layout.addWidget(btn_add); btn_layout.addWidget(btn_del)
        layout.addLayout(btn_layout)

    def refresh_accounts(self): self.acct_list.clear(); self.acct_list.addItems(Account.read_all_from_db(self.db))
    def add_account(self): 
        if self.new_acct_input.text(): Account.add(self.db, self.new_acct_input.text()); self.new_acct_input.clear(); self.refresh_accounts()
    def del_account(self): 
        if self.acct_list.currentItem(): Account.delete(self.db, self.acct_list.currentItem().text()); self.refresh_accounts()

class TypesDialog(QDialog):
    """
    Dialog for managing Category Types and their associated colors.
    Note that this completely deletes types, so be cautious about constraints.
    """
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Manage Category Types")
        self.resize(400, 300)
        layout = QVBoxLayout(self)
        self.type_list = QListWidget()
        self.refresh_types()
        layout.addWidget(self.type_list)
        input_layout = QHBoxLayout()
        self.new_type_input = QLineEdit()
        self.new_type_input.setPlaceholderText("Type Name...")
        self.new_color_input = QComboBox()
        self.new_color_input.setEditable(True)
        self.new_color_input.addItems(["Red", "Green", "Blue", "Yellow", "Orange", "Purple", "LightGray", "DarkGray", "Cyan"])
        self.new_color_input.setCurrentIndex(-1)
        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self.add_type)
        btn_del = QPushButton("Delete")
        btn_del.clicked.connect(self.del_type)
        input_layout.addWidget(self.new_type_input); input_layout.addWidget(self.new_color_input); input_layout.addWidget(btn_add); input_layout.addWidget(btn_del)
        layout.addLayout(input_layout)

    def refresh_types(self): 
        self.type_list.clear()
        for t in CategoryType.read_all_from_db(self.db): self.type_list.addItem(f"{t['name']} ({t['color']})")
    def add_type(self): 
        if self.new_type_input.text(): CategoryType.add(self.db, self.new_type_input.text(), self.new_color_input.currentText()); self.new_type_input.clear(); self.refresh_types()
    def del_type(self):
        if self.type_list.currentItem(): CategoryType.delete(self.db, self.type_list.currentItem().text().split(" (")[0]); self.refresh_types()

class CategoriesDialog(QDialog):
    """
    Dialog for adding and soft-deleting categories inside a specific account.
    Categories are joined with Types via picklists contextually holding category colors.
    """
    def __init__(self, db, account_name, parent=None):
        super().__init__(parent)
        self.db = db
        self.account_name = account_name
        self.setWindowTitle(f"Manage Categories: {account_name}")
        self.resize(400, 300)
        layout = QVBoxLayout(self)
        self.cat_list = QListWidget()
        layout.addWidget(self.cat_list)
        
        self.new_cat_input = QLineEdit()
        self.new_cat_input.setPlaceholderText("Category...")
        self.cat_type_combo = QComboBox()
        self.cat_type_combo.addItems([t['name'] for t in CategoryType.read_all_from_db(self.db)])
        
        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self.add_category)
        btn_del = QPushButton("Delete")
        btn_del.clicked.connect(self.del_category)
        
        row1 = QHBoxLayout()
        row1.addWidget(self.new_cat_input); row1.addWidget(self.cat_type_combo)
        layout.addLayout(row1)
        row2 = QHBoxLayout()
        row2.addWidget(btn_add); row2.addWidget(btn_del)
        layout.addLayout(row2)
        self.refresh_categories()

    def refresh_categories(self):
        self.cat_list.clear()
        for name, c in Category.read_from_db(self.db, self.account_name).items(): 
            self.cat_list.addItem(f"{name} [{c.type}]")

    def add_category(self):
        if self.new_cat_input.text(): 
            Category.add(self.db, self.account_name, self.new_cat_input.text(), self.cat_type_combo.currentText())
            self.new_cat_input.clear()
            self.refresh_categories()

    def del_category(self):
        if self.cat_list.currentItem(): 
            Category.delete(self.db, self.account_name, self.cat_list.currentItem().text().split(" [")[0])
            self.refresh_categories()

class ManageVisibilityDialog(QDialog):
    """
    Shows soft-deleted (Hidden) accounts and categories.
    Provides a right-click context menu to toggle the visibility (Unhide/Hide)
    or confirm a state without permanently dropping transactional histories.
    """
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Manage Account & Category Visibility")
        self.resize(500, 400)
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.setup_accounts_tab()
        self.setup_categories_tab()
        
    def setup_accounts_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        self.acct_list = QListWidget()
        self.acct_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.acct_list.customContextMenuRequested.connect(self.acct_context_menu)
        l.addWidget(self.acct_list)
        self.tabs.addTab(tab, "Accounts")
        self.load_accounts()
        
    def setup_categories_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        self.cat_list = QListWidget()
        self.cat_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cat_list.customContextMenuRequested.connect(self.cat_context_menu)
        l.addWidget(self.cat_list)
        self.tabs.addTab(tab, "Categories")
        self.load_categories()

    def load_accounts(self):
        self.acct_list.clear()
        for row in self.db.execute_reader("SELECT name, hidden FROM d_Accounts ORDER BY name"):
            status = "[Hidden] " if row['hidden'] == 'Y' else ""
            self.acct_list.addItem(f"{status}{row['name']}")

    def load_categories(self):
        self.cat_list.clear()
        for row in self.db.execute_reader("SELECT account, name, hidden FROM d_Categories ORDER BY account, name"):
            status = "[Hidden] " if row['hidden'] == 'Y' else ""
            self.cat_list.addItem(f"{status}{row['account']} -> {row['name']}")

    def acct_context_menu(self, pos):
        if item := self.acct_list.itemAt(pos):
            self.show_menu(item, is_account=True, global_pos=self.acct_list.viewport().mapToGlobal(pos))

    def cat_context_menu(self, pos):
        if item := self.cat_list.itemAt(pos):
            self.show_menu(item, is_account=False, global_pos=self.cat_list.viewport().mapToGlobal(pos))
            
    def show_menu(self, item, is_account, global_pos):
        text = item.text()
        is_hidden = text.startswith("[Hidden] ")
        pure_text = text[9:] if is_hidden else text
        
        menu = QMenu()
        action_toggle = menu.addAction("Unhide" if is_hidden else "Hide")
        
        if menu.exec(global_pos) == action_toggle:
            if is_account:
                if is_hidden: Account.unhide(self.db, pure_text)
                else: Account.delete(self.db, pure_text)
                self.load_accounts()
            else:
                acc, name = pure_text.split(" -> ")
                if is_hidden: Category.unhide(self.db, acc, name)
                else: Category.delete(self.db, acc, name)
                self.load_categories()

from PyQt6.QtWidgets import QSpinBox

class GeneralSettingsDialog(QDialog):
    """
    Settings interface to configure app-wide properties, like the retention
    days dynamically passed into the database's auto-backup pruning engine.
    """
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("General Settings")
        self.resize(300, 150)
        layout = QVBoxLayout(self)
        
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("Backup retention (days):"))
        self.retention_spin = QSpinBox()
        self.retention_spin.setRange(1, 365)
        
        # Load current setting
        current_retention = int(AppSetting.get(self.db, 'backup_retention_days', 7))
        self.retention_spin.setValue(current_retention)
        form_layout.addWidget(self.retention_spin)
        layout.addLayout(form_layout)
        
        layout.addStretch()
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)

    def save(self):
        AppSetting.set(self.db, 'backup_retention_days', self.retention_spin.value())
        self.accept()

class SinkingFundsManager(QMainWindow):
    """
    The Core application window routing context menus, primary spreadsheet
    views, and application lifecycle events (save-warnings and initializations).
    """
    def __init__(self):
        super().__init__()
        self.db = SavingsDatabase()
        self.setWindowTitle("Sinking Funds Manager")
        self.setWindowIcon(QIcon("icon.svg"))
        self.resize(1000, 600)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.setup_menu()
        self.setup_top_bar()
        self.setup_table()
        self.setup_bottom_bar()
        self.load_accounts()

    def setup_menu(self):
        menubar = self.menuBar()
        tools = menubar.addMenu("Tools")
        tools.addAction("Manage Accounts").triggered.connect(lambda: AccountsDialog(self.db, self).exec() or self.load_accounts())
        tools.addAction("Manage Category Types").triggered.connect(lambda: TypesDialog(self.db, self).exec() or self.on_account_changed(self.current_account))
        tools.addAction("Manage Categories").triggered.connect(lambda: CategoriesDialog(self.db, self.current_account, self).exec() or self.on_account_changed(self.current_account))
        tools.addSeparator()
        tools.addAction("Manage Visibility (Hide/Unhide)").triggered.connect(self.open_manage_visibility)
        tools.addSeparator()
        tools.addAction("General Settings").triggered.connect(self.open_general_settings)

        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About").triggered.connect(self.show_about)

    def show_about(self):
        about_text = (
            "<h2>Sinkin Funds Manager</h2>"
            "<p><b>Version:</b> 2.0<br/>"
            "<b>Created by:</b> Curtis Thetford<br/>"
            "<b>Date:</b> May 14, 2026</p>"
            "<p>This program is free software: you can redistribute it and/or modify "
            "it under the terms of the GNU General Public License as published by "
            "the Free Software Foundation, either version 3 of the License, or "
            "(at your option) any later version.</p>"
            "<p>This program is distributed in the hope that it will be useful, "
            "but WITHOUT ANY WARRANTY; without even the implied warranty of "
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the "
            "GNU General Public License for more details.</p>"
        )
        QMessageBox.about(self, "About Sinkin Funds Manager", about_text)

    def open_manage_visibility(self): ManageVisibilityDialog(self.db, self).exec(); self.load_accounts()
    def open_general_settings(self): GeneralSettingsDialog(self.db, self).exec()

    def setup_top_bar(self):
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Account:"))
        self.account_combo = QComboBox()
        self.account_combo.currentTextChanged.connect(self.on_account_changed)
        layout.addWidget(self.account_combo); layout.addStretch()
        self.main_layout.addLayout(layout)

    def setup_table(self):
        self.table = FastInputTable()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Category", "Type", "Balance", "Change", "New Balance", "Comments"])
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.cellChanged.connect(self.on_cell_changed)
        self.main_layout.addWidget(self.table)

    def setup_bottom_bar(self):
        layout = QHBoxLayout()
        self.lbl_total = QLabel("Total: $0.00")
        layout.addWidget(self.lbl_total); layout.addStretch()
        self.date_edit = QDateEdit(calendarPopup=True)
        self.date_edit.setDate(QDate.currentDate())
        layout.addWidget(QLabel("Date:")); layout.addWidget(self.date_edit)
        self.lbl_old = QLabel("Old: $0.00"); self.lbl_new = QLabel("New: $0.00")
        layout.addWidget(self.lbl_old); layout.addWidget(self.lbl_new)
        
        self.btn_clear = QPushButton("Clear Transaction")
        self.btn_clear.clicked.connect(self.clear_transaction)
        layout.addWidget(self.btn_clear)
        
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.on_save)
        layout.addWidget(self.btn_save)
        self.main_layout.addLayout(layout)

    def load_accounts(self):
        self.account_combo.blockSignals(True)
        self.account_combo.clear()
        
        accounts = Account.read_all_from_db(self.db)
        self.account_combo.addItems(accounts)
        
        last_account = AppSetting.get(self.db, "last_account", "")
        if last_account in accounts:
            self.account_combo.setCurrentText(last_account)
            
        self.account_combo.blockSignals(False)
        self.on_account_changed(self.account_combo.currentText())

    def on_account_changed(self, account_name):
        if not account_name: return
        self.current_account = account_name
        AppSetting.set(self.db, "last_account", account_name)
        
        self.trans_list = TransactionList(self.db, account_name)
        categories = Category.read_from_db(self.db, account_name)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(categories))
        self.table.blockSignals(True)
        total_old = 0.0
        for row, (name, cat) in enumerate(categories.items()):
            bal = self.trans_list.get_category_sum(name)
            total_old += bal
            self.table.setItem(row, 0, self._ro_item(name))
            self.table.setItem(row, 1, self._ro_item(cat.type))
            self.table.setItem(row, 2, self._ro_item(f"{bal:,.2f}", True))
            self.table.setItem(row, 3, QTableWidgetItem("0.00"))
            self.table.setItem(row, 4, self._ro_item(f"{bal:,.2f}", True))
            self.table.setItem(row, 5, QTableWidgetItem(""))
            if cat.color:
                color = QColor(cat.color)
                if self.table.item(row, 0):
                    self.table.item(row, 0).setForeground(color)
        self.table.blockSignals(False)
        self.table.setSortingEnabled(True)
        self.lbl_old.setText(f"Old: ${total_old:,.2f}")
        self.update_totals()

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        row = item.row()
        cat_name = self.table.item(row, 0).text()
        
        menu = QMenu()
        action_monthly = menu.addAction("View Monthly History (12 months)")
        action_weekly = menu.addAction("View Weekly History (12 weeks)")
        menu.addSeparator()
        action_last10 = menu.addAction("View Last 10 Transactions")
        
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == action_monthly:
            self.show_history_report(cat_name, 'monthly')
        elif action == action_weekly:
            self.show_history_report(cat_name, 'weekly')
        elif action == action_last10:
            self.show_history_report(cat_name, 'last10')

    def show_history_report(self, cat_name, report_type):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Report: {cat_name}")
        dialog.resize(550, 400)
        layout = QVBoxLayout(dialog)
        table = QTableWidget()
        layout.addWidget(table)
        
        if report_type == 'monthly':
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Period", "Change", "Ending Balance"])
            sql = "SELECT period, month_change, ending_balance FROM v_PeriodTotals WHERE account = ? AND category = ? ORDER BY period DESC LIMIT 12"
            rows = self.db.execute_reader(sql, (self.current_account, cat_name))
        elif report_type == 'weekly':
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Week Ending", "Change", "Ending Balance"])
            sql = "SELECT period, week_change, ending_balance FROM v_WeeklyTotals WHERE account = ? AND category = ? ORDER BY period DESC LIMIT 12"
            rows = self.db.execute_reader(sql, (self.current_account, cat_name))
        elif report_type == 'last10':
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Date", "Amount", "Comment"])
            sql = "SELECT create_ts, net_change, comment FROM Transactions WHERE account = ? AND category = ? ORDER BY create_ts DESC LIMIT 10"
            rows = self.db.execute_reader(sql, (self.current_account, cat_name))
            
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            if report_type == 'last10':
                table.setItem(r, 0, self._ro_item(str(row["create_ts"])))
                table.setItem(r, 1, self._ro_item(f"{row['net_change']:,.2f}", align_right=True))
                table.setItem(r, 2, self._ro_item(str(row["comment"] or "")))
            else:
                period_str = str(row["period"])
                if report_type == 'weekly':
                    try:
                        # Convert "YYYY-WW" to the Saturday of that week
                        sat_date = datetime.strptime(f"{period_str}-6", "%Y-%W-%w")
                        period_str = sat_date.strftime("%Y-%m-%d")
                    except ValueError: pass
                    
                table.setItem(r, 0, self._ro_item(period_str))
                chg = row["month_change"] if report_type == 'monthly' else row["week_change"]
                bal = row["ending_balance"]
                table.setItem(r, 1, self._ro_item(f"{chg:,.2f}", align_right=True))
                table.setItem(r, 2, self._ro_item(f"{bal:,.2f}", align_right=True))
                
        table.horizontalHeader().setStretchLastSection(True)
        table.resizeColumnsToContents()
        dialog.exec()

    def _ro_item(self, text, align_right=False):
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled) # Prevent selection & focus completely
        if align_right: item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return item

    def on_cell_changed(self, row, col):
        if col == 3:
            try:
                self.table.blockSignals(True)
                curr = float(self.table.item(row, 2).text().replace(',', ''))
                change = float(self.table.item(row, 3).text() or 0)
                self.table.item(row, 4).setText(f"{curr + change:,.2f}")
                self.table.blockSignals(False)
                self.update_totals()
            except: self.table.item(row, 3).setText("0.00"); self.table.blockSignals(False)

    def has_unsaved_changes(self):
        for r in range(self.table.rowCount()):
            if self.table.item(r, 3) and self.table.item(r, 3).text() and float(self.table.item(r, 3).text().replace(',', '')) != 0:
                return True
        return False

    def closeEvent(self, event):
        if self.has_unsaved_changes():
            reply = QMessageBox.question(self, 'Unsaved Changes', 
                "You have unsaved changes. Are you sure you want to exit without saving?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def clear_transaction(self):
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            if self.table.item(r, 3): self.table.item(r, 3).setText("0.00")
            if self.table.item(r, 5): self.table.item(r, 5).setText("")
            
            # Reset new balance to old balance automatically
            curr = float(self.table.item(r, 2).text().replace(',', ''))
            self.table.item(r, 4).setText(f"{curr:,.2f}")
            
        self.table.blockSignals(False)
        self.update_totals()

    def update_totals(self):
        change_total, new_total = 0.0, 0.0
        for r in range(self.table.rowCount()):
            try:
                change_total += float(self.table.item(r, 3).text().replace(',', ''))
                new_total += float(self.table.item(r, 4).text().replace(',', ''))
            except: pass
        self.lbl_total.setText(f"Total: ${change_total:,.2f}")
        self.lbl_new.setText(f"New: ${new_total:,.2f}")

    def on_save(self):
        t_date = self.date_edit.date().toPyDate()
        for r in range(self.table.rowCount()):
            amt = float(self.table.item(r, 3).text().replace(',', ''))
            if amt != 0:
                self.trans_list.add_transaction(Transaction(t_date, self.table.item(r, 0).text(), amt, self.table.item(r, 5).text()))
        self.trans_list.write()
        self.db.backup()
        self.on_account_changed(self.account_combo.currentText())
        QMessageBox.information(self, "Success", "Transactions saved!")

if __name__ == '__main__':
    # Tell Windows this is a separate app from the generic Python executable
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('sinkingfunds.manager.app.1')
        
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.svg")) # Also set at application level for the taskbar
    window = SinkingFundsManager()
    window.show()
    sys.exit(app.exec())