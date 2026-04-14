#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""右侧数据格子控件"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor


class SmallDataBox(QFrame):
    def __init__(self, title, unit, icon_text="●", color="#888888", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.color = QColor(color)
        self.setStyleSheet(f"""
            SmallDataBox {{
                background-color: #353535;
                border-radius: 8px;
                border: 1px solid #4A4A4A;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(6, 4, 6, 4)

        # 顶部：图标+标题
        header = QHBoxLayout()
        header.setSpacing(4)
        header.setAlignment(Qt.AlignCenter)

        icon = QLabel(icon_text)
        icon.setStyleSheet(f"color: {color}; background: transparent;")
        icon.setFont(QFont("Helvetica", 11))
        header.addWidget(icon)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; background: transparent;")
        title_label.setFont(QFont("Helvetica", 10))
        header.addWidget(title_label)
        layout.addLayout(header)

        # 数值
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        self.value_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)

        # 单位
        unit_label = QLabel(unit)
        unit_label.setStyleSheet("color: #666666; background: transparent;")
        unit_label.setFont(QFont("Helvetica", 9))
        unit_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(unit_label)

    def update_value(self, value, color=None):
        self.value_label.setText(str(value))
        if color:
            self.value_label.setStyleSheet(f"color: {color}; background: transparent;")
