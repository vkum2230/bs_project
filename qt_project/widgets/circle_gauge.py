#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""圆形仪表盘控件"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QFontMetrics


class CircleGauge(QWidget):
    def __init__(self, title, unit, max_value, color1="#4DB8FF", parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.max_value = max_value
        self.color1 = QColor(color1)
        self.value = 0.0
        self.setMinimumSize(170, 170)
        self.setMaximumSize(190, 190)

    def set_value(self, value):
        self.value = float(value)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        size = min(width, height) - 8
        rect = QRect((width - size) // 2, (height - size) // 2, size, size)

        # 背景圆环
        pen_bg = QPen(QColor("#3A3A3A"))
        pen_bg.setWidth(10)
        painter.setPen(pen_bg)
        painter.drawEllipse(rect)

        # 进度圆弧
        angle = int(270 * min(self.value / self.max_value, 1.0))
        pen_arc = QPen(self.color1)
        pen_arc.setWidth(10)
        pen_arc.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_arc)
        painter.drawArc(rect, 225 * 16, -angle * 16)

        # 中心数值
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Arial", 32, QFont.Bold)
        painter.setFont(font)
        value_text = f"{self.value:.1f}" if self.value < 100 else f"{int(self.value)}"
        fm = QFontMetrics(font)
        text_rect = fm.boundingRect(value_text)
        painter.drawText((width - text_rect.width()) // 2, height // 2 - 8, value_text)

        # 单位
        painter.setPen(QColor("#888888"))
        font_unit = QFont("Helvetica", 11)
        painter.setFont(font_unit)
        fm_unit = QFontMetrics(font_unit)
        unit_rect = fm_unit.boundingRect(self.unit)
        painter.drawText((width - unit_rect.width()) // 2, height // 2 + 20, self.unit)

        # 标题
        painter.setPen(self.color1)
        font_title = QFont("Helvetica", 13, QFont.Bold)
        painter.setFont(font_title)
        fm_title = QFontMetrics(font_title)
        title_rect = fm_title.boundingRect(self.title)
        painter.drawText((width - title_rect.width()) // 2, height - 12, self.title)

        painter.end()
