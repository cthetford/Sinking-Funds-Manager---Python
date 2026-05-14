import sys
from PyQt6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt

app = QApplication(sys.argv)
table = QTableWidget(2, 6)

def _ro_item(text, align_right=False):
    item = QTableWidgetItem(text)
    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
    if align_right: item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return item

for row in range(2):
    table.setItem(row, 0, _ro_item(f"Cat {row}"))
    table.setItem(row, 1, _ro_item(f"Type {row}"))
    table.setItem(row, 2, _ro_item(f"{row*100:,.2f}", True))
    table.setItem(row, 3, QTableWidgetItem("0.00"))
    table.setItem(row, 4, _ro_item(f"{row*100:,.2f}", True))
    table.setItem(row, 5, QTableWidgetItem(""))

def on_cell_changed(row, col):
    print(f"cellChanged: {row}, {col}")
    if col == 3:
        try:
            table.blockSignals(True)
            curr = float(table.item(row, 2).text().replace(',', ''))
            change = float(table.item(row, 3).text() or 0)
            table.item(row, 4).setText(f"{curr + change:,.2f}")
            table.blockSignals(False)
        except Exception as e:
            print("Error", e)
            table.item(row, 3).setText("0.00")
            table.blockSignals(False)

table.cellChanged.connect(on_cell_changed)
table.setSortingEnabled(True)
table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
print("Sorted successfully.")
