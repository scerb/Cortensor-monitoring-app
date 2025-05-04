from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import QTableWidgetItem
import re


class TableRenderer:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.sort_column = -1
        self.sort_order = Qt.AscendingOrder

    def render_table(self, table, stats_dict):
        headers = [
            "Miner ID", "Ping", "Precommit (P/C)", "Commit (P/C)",
            "Prepare (P/C)", "Create (P/C)", "Last Active", "ETH Balance",
            "Staked", "Staked Time Ago"
        ]

        headers_with_arrows = headers[:]
        if self.sort_column != -1:
            arrow = "↓" if self.sort_order == Qt.DescendingOrder else "↑"
            headers_with_arrows[self.sort_column] += f" {arrow}"

        stats_list = self._dict_to_list(stats_dict)

        if self.sort_column != -1:
            stats_list = self._sort_stats(stats_list, headers)

        table.setRowCount(len(stats_list))
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers_with_arrows)

        thresholds = self.config_manager.get_balance_thresholds()

        for row, data in enumerate(stats_list):
            table.setRowHeight(row, int(table.rowHeight(row) * 0.8))
            self._render_row(table, row, data, thresholds)

        self._set_column_widths(table)

    def _dict_to_list(self, stats_dict):
        return [
            {**data, "miner_id": miner_id}
            for miner_id, data in stats_dict.items()
            if not miner_id.startswith("__")
        ]

    def _sort_stats(self, stats_list, headers):
        column_name = headers[self.sort_column]

        def get_sort_value(x):
            if column_name == "Miner ID":
                return x["miner_id"]
            elif column_name == "Ping":
                return x.get("ping", 0)
            elif column_name == "ETH Balance":
                return float(x.get("eth_balance", 0.0))
            elif column_name == "Staked":
                return float(x.get("staked", 0.0))
            elif column_name == "Last Active":
                text = x.get("last_active", "")
                if not isinstance(text, str):
                    return float('inf')
                time_match = re.search(r"(?:(\d+)\s*hr)?\s*(?:(\d+)\s*min)?\s*(?:(\d+)\s*sec)?", text)
                if time_match:
                    hrs = int(time_match.group(1) or 0)
                    mins = int(time_match.group(2) or 0)
                    secs = int(time_match.group(3) or 0)
                    return hrs * 3600 + mins * 60 + secs
                return float('inf')
            else:
                metric_map = {
                    "Precommit": "precommit",
                    "Commit": "commit",
                    "Prepare": "prepare",
                    "Create": "create"
                }
                metric = next((v for k, v in metric_map.items() if k in column_name), None)
                if not metric:
                    return 0
                m = x.get(metric, {})
                counter = m.get("counter", 1)
                return (m.get("point", 0) / counter) if counter else 0

        return sorted(stats_list, key=get_sort_value,
                      reverse=self.sort_order == Qt.DescendingOrder)

    def _render_row(self, table, row, data, thresholds):
        truncated_id = data["miner_id"][:5] + "..." + data["miner_id"][-5:] if len(data["miner_id"]) > 10 else data["miner_id"]
        item = QTableWidgetItem(truncated_id)
        item.setToolTip(data["miner_id"])
        table.setItem(row, 0, item)

        table.setItem(row, 1, QTableWidgetItem(str(data.get("ping", 0))))

        def format_pc(metric):
            m = data.get(metric, {})
            point = m.get("point", 0)
            counter = m.get("counter", 1)
            percent = (point / counter * 100) if counter else 0
            return f"{point}/{counter} ({percent:.2f}%)"

        table.setItem(row, 2, QTableWidgetItem(format_pc("precommit")))
        table.setItem(row, 3, QTableWidgetItem(format_pc("commit")))
        table.setItem(row, 4, QTableWidgetItem(format_pc("prepare")))
        table.setItem(row, 5, QTableWidgetItem(format_pc("create")))

        table.setItem(row, 6, QTableWidgetItem(str(data.get("last_active", ""))))

        def make_balance_item(key):
            val = data.get(key, "N/A")
            item = QTableWidgetItem(str(val))
            item.setTextAlignment(Qt.AlignRight)
            try:
                val_float = float(val)
                if key == "eth_balance":
                    if val_float < thresholds["eth_low"]:
                        item.setBackground(QBrush(QColor("#ffcccc")))
                    elif val_float < thresholds["eth_mid"]:
                        item.setBackground(QBrush(QColor("#fff2cc")))
                    else:
                        item.setBackground(QBrush(QColor("#ccffcc")))
            except:
                pass
            return item

        table.setItem(row, 7, make_balance_item("eth_balance"))
        table.setItem(row, 8, make_balance_item("staked"))
        table.setItem(row, 9, QTableWidgetItem(data.get("staked_time_ago", "N/A")))

        if data.get("is_offline", False):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    item.setBackground(QBrush(QColor("#ff9999")))

    def _set_column_widths(self, table):
        default_widths = [120, 60, 140, 140, 140, 140, 120, 100, 100, 120]
        column_widths = self.config_manager.get_column_widths()
        for i, default in enumerate(default_widths):
            table.setColumnWidth(i, int(column_widths.get(str(i), default)))

    def handle_header_click(self, index, table):
        column_widths = {}
        for i in range(table.columnCount()):
            column_widths[str(i)] = table.columnWidth(i)
        self.config_manager.save_column_widths(column_widths)

        self.sort_column = index if self.sort_column != index else self.sort_column
        self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
