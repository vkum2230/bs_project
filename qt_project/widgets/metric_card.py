#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""带图标的数据卡片控件（适配新版UI）"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontInfo


def _hex_to_rgba(hex_color: str, alpha: float = 0.35) -> str:
    """将 #RRGGBB 转为 rgba(r, g, b, a)，解决浅色在深色背景上看不见的问题"""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    a = int(alpha * 255)
    return f"rgba({r}, {g}, {b}, {a})"


class MetricCard(QFrame):
    """
    图标数据卡片
    - 顶部彩色圆角图标
    - 中间大字号数值 + 右下角小单位
    - 底部标题
    """

    def __init__(self, title, icon_text, color="#888888", unit="", parent=None):
        super().__init__(parent)
        self.color = color
        self.unit = unit
        self.setFrameShape(QFrame.NoFrame)
        self.setFrameShadow(QFrame.Plain)
        self.setLineWidth(0)
        self.setMidLineWidth(0)
        self.setStyleSheet("""
            MetricCard {
                background-color: #2E2E3A;
                border-radius: 12px;
                border: none;
            }
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setAlignment(Qt.AlignCenter)

        # 图标背景
        icon_bg = QFrame()
        icon_bg.setFixedSize(54, 54)
        icon_bg.setFrameShape(QFrame.NoFrame)
        icon_bg.setFrameShadow(QFrame.Plain)
        icon_bg.setLineWidth(0)
        icon_bg.setMidLineWidth(0)
        icon_bg.setStyleSheet(f"""
            QFrame {{
                background-color: {_hex_to_rgba(color, 0.35)};
                border-radius: 12px;
                border: none;
            }}
        """)
        icon_layout = QVBoxLayout(icon_bg)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignCenter)

        # 图标文字
        self.icon_label = QLabel(icon_text)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        icon_font = QFont()
        icon_font.setPointSize(24)
        icon_font.setFamilies([
            "Noto Color Emoji",
            "Segoe UI Emoji",
            "Apple Color Emoji",
            "EmojiOne Color",
            "Twitter Color Emoji",
            "Noto Sans CJK SC",
            "WenQuanYi Micro Hei",
            "Helvetica"
        ])
        self.icon_label.setFont(icon_font)
        icon_layout.addWidget(self.icon_label)

        # 数值 + 单位 容器
        value_container = QWidget()
        value_container.setStyleSheet("background: transparent; border: none;")
        value_layout = QHBoxLayout(value_container)
        value_layout.setSpacing(4)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setAlignment(Qt.AlignCenter)

        self.value_label = QLabel("--")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        self.value_label.setFont(QFont("Arial", 24, QFont.Bold))

        self.unit_label = QLabel(unit)
        self.unit_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.unit_label.setStyleSheet("color: #AAAAAA; background: transparent; border: none;")
        self.unit_label.setFont(QFont("Helvetica", 10))

        value_layout.addWidget(self.value_label, alignment=Qt.AlignVCenter)
        value_layout.addWidget(self.unit_label, alignment=Qt.AlignLeft | Qt.AlignBottom)

        # 标题
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #888888; background: transparent; border: none;")
        self.title_label.setFont(QFont("Helvetica", 11))

        # 垂直居中排列
        layout.addStretch(1)
        layout.addWidget(icon_bg, alignment=Qt.AlignCenter)
        layout.addSpacing(14)
        layout.addWidget(value_container, alignment=Qt.AlignCenter)
        layout.addSpacing(10)
        layout.addWidget(self.title_label, alignment=Qt.AlignCenter)
        layout.addStretch(1)

    def update_value(self, value, color=None):
        self.value_label.setText(str(value))
        if color:
            self.value_label.setStyleSheet(f"color: {color}; background: transparent; border: none;")
