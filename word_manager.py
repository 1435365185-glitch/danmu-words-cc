# -*- coding: utf-8 -*-
"""
词库管理工具
- 表格显示所有单词
- 双击单元格直接编辑
- 添加 / 删除单词
- 自动保存到 words.json
"""
import sys
import json
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QMessageBox,
    QInputDialog, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "words.json")


class WordManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("词库管理")
        self.resize(1000, 650)
        self.words = []
        self._load()
        self._init_ui()
        self._fill_table()

    def _load(self):
        if os.path.exists(JSON_PATH):
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.words = data.get("words", [])
        else:
            self.words = []

    def _save(self):
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump({"words": self.words}, f, ensure_ascii=False, indent=2)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 按钮栏
        btn_bar = QHBoxLayout()
        btn_add = QPushButton("添加单词")
        btn_del = QPushButton("删除选中")
        btn_reset = QPushButton("重置已掌握")
        btn_save = QPushButton("保存")
        btn_add.clicked.connect(self.add_word)
        btn_del.clicked.connect(self.del_word)
        btn_reset.clicked.connect(self.reset_known)
        btn_save.clicked.connect(self._save_and_notify)
        btn_bar.addWidget(btn_add)
        btn_bar.addWidget(btn_del)
        btn_bar.addWidget(btn_reset)
        btn_bar.addStretch()
        btn_bar.addWidget(btn_save)
        layout.addLayout(btn_bar)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["单词", "词性", "中文释义", "英文例句", "例句翻译", "已掌握"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.table.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.table)

        self.setStyleSheet("""
            QPushButton { padding: 6px 16px; border-radius: 6px;
                         background: #7B4FAE; color: white; border: none; }
            QPushButton:hover { background: #6A3E9D; }
            QTableWidget { gridline-color: #ddd; font-size: 13px; }
            QHeaderView::section { background: #f0f0f0; padding: 6px; }
        """)

    def _fill_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.words))
        for row, w in enumerate(self.words):
            self.table.setItem(row, 0, QTableWidgetItem(w.get("word", "")))
            self.table.setItem(row, 1, QTableWidgetItem(w.get("pos", "")))
            self.table.setItem(row, 2, QTableWidgetItem(w.get("meaning", "")))
            self.table.setItem(row, 3, QTableWidgetItem(w.get("example", "")))
            self.table.setItem(row, 4, QTableWidgetItem(w.get("example_cn", "")))
            known_item = QTableWidgetItem("是" if w.get("known") else "否")
            known_item.setTextAlignment(Qt.AlignCenter)
            if w.get("known"):
                known_item.setForeground(QColor("#999"))
            self.table.setItem(row, 5, known_item)
        self.table.blockSignals(False)

    def on_item_changed(self, item):
        row = item.row()
        col = item.column()
        if row >= len(self.words):
            return
        key_map = {0: "word", 1: "pos", 2: "meaning",
                   3: "example", 4: "example_cn", 5: "known"}
        key = key_map[col]
        val = item.text()
        if col == 5:
            self.words[row][key] = (val == "是")
        else:
            self.words[row][key] = val
        self._save()

    def add_word(self):
        word, ok = QInputDialog.getText(self, "添加单词", "英文单词：")
        if not ok or not word.strip():
            return
        self.words.append({
            "word": word.strip(),
            "pos": "",
            "meaning": "",
            "example": "",
            "example_cn": "",
            "known": False
        })
        self._fill_table()
        self._save()
        # 跳到新行
        self.table.selectRow(len(self.words) - 1)

    def del_word(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()), reverse=True)
        if not rows:
            QMessageBox.information(self, "提示", "请先选中要删除的行")
            return
        for r in rows:
            self.words.pop(r)
        self._fill_table()
        self._save()

    def reset_known(self):
        for w in self.words:
            w["known"] = False
        self._fill_table()
        self._save()

    def _save_and_notify(self):
        self._save()
        QMessageBox.information(self, "提示", f"已保存，共 {len(self.words)} 个单词")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    win = WordManager()
    win.show()
    sys.exit(app.exec())
