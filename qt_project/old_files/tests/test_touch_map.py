#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试地图触摸事件
"""

import sys
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings

class TouchTestWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("地图触摸测试")
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        self.web_view = QWebEngineView()
        self.web_view.setAttribute(Qt.WA_AcceptTouchEvents, True)
        
        # 启用触摸相关设置
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.TouchIconsEnabled, True)
        
        # 加载测试HTML
        with open('test_touch.html', 'r', encoding='utf-8') as f:
            html = f.read()
        
        self.web_view.setHtml(html)
        layout.addWidget(self.web_view)
        
        print("触摸测试窗口已打开")
        print("请在屏幕上尝试：")
        print("1. 单指拖动")
        print("2. 双指缩放")
        print("3. 双指旋转")
        print("\n观察窗口左上角的调试信息")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TouchTestWidget()
    window.show()
    sys.exit(app.exec_())
