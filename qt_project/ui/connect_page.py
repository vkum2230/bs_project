#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接页面 —— 首屏（左右布局，匹配设计图）

左侧：蓝色渐变品牌区
右侧：WiFi/蓝牙 标签切换 + 连接内容
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QIcon


class ConnectPage(QWidget):
    """连接手机页面"""

    skip_clicked = pyqtSignal()
    ble_advertising_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        # 主布局：左右分栏
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== 左侧：深灰品牌区 ==========
        left_panel = QFrame()
        left_panel.setFixedWidth(420)
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #2E2E3A;
                border: none;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(28, 14, 28, 14)
        left_layout.setSpacing(0)
        left_layout.setAlignment(Qt.AlignCenter)

        left_layout.addStretch(1)

        # 图标区域（圆角暗色背景 + 骑行图标）
        icon_bg = QFrame()
        icon_bg.setFixedSize(150, 150)
        icon_bg.setStyleSheet("""
            QFrame {
                background-color: rgba(255,255,255,0.08);
                border-radius: 30px;
                border: none;
            }
        """)
        icon_bg_layout = QVBoxLayout(icon_bg)
        icon_bg_layout.setContentsMargins(0, 0, 0, 0)
        icon_bg_layout.setAlignment(Qt.AlignCenter)

        self.bike_icon_lbl = QLabel()
        self.bike_icon_lbl.setAlignment(Qt.AlignCenter)
        self._load_icon("riding-fill.png", self.bike_icon_lbl, 110, 110)
        icon_bg_layout.addWidget(self.bike_icon_lbl)
        left_layout.addWidget(icon_bg, alignment=Qt.AlignCenter)

        left_layout.addSpacing(12)

        # 大标题
        brand_title = QLabel("智能骑行")
        brand_title.setAlignment(Qt.AlignCenter)
        brand_title.setStyleSheet("color: #FFFFFF; background: transparent;")
        brand_title.setFont(QFont("Noto Sans CJK SC", 28, QFont.Bold))
        left_layout.addWidget(brand_title)

        left_layout.addSpacing(6)

        # 副标题
        brand_sub = QLabel("连接您的智能骑行设备，开启全新的骑行体验。\n实时监测数据，优化训练效果。")
        brand_sub.setAlignment(Qt.AlignCenter)
        brand_sub.setStyleSheet("color: #AAAAAA; background: transparent;")
        brand_sub.setFont(QFont("Noto Sans CJK SC", 11))
        brand_sub.setWordWrap(True)
        left_layout.addWidget(brand_sub)

        left_layout.addSpacing(18)

        # 三个功能卡片（用图标图片）
        self._add_feature_card_img(left_layout, "热点.png", "实时数据同步")
        left_layout.addSpacing(6)
        self._add_feature_card_img(left_layout, "wifi.png", "多种连接方式")
        left_layout.addSpacing(6)
        self._add_feature_card_img(left_layout, "二维码.png", "快速配对")

        left_layout.addStretch(1)

        main_layout.addWidget(left_panel)

        # ========== 右侧：深灰连接区 ==========
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #2C2C2C; border: none;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(32, 24, 32, 20)
        right_layout.setSpacing(0)

        # 标题
        header = QLabel("连接设备")
        header.setStyleSheet("color: #FFFFFF; background: transparent;")
        header.setFont(QFont("Noto Sans CJK SC", 20, QFont.Bold))
        right_layout.addWidget(header)

        right_layout.addSpacing(8)

        # 副标题
        sub_header = QLabel("选择一种方式连接您的智能骑行设备")
        sub_header.setStyleSheet("color: #AAAAAA; background: transparent;")
        sub_header.setFont(QFont("Noto Sans CJK SC", 12))
        right_layout.addWidget(sub_header)

        right_layout.addSpacing(18)

        # --- 标签切换栏 ---
        tab_bar = QHBoxLayout()
        tab_bar.setSpacing(10)

        self.tab_wifi = QPushButton("  WiFi (MQTT)")
        self.tab_wifi.setCheckable(True)
        self.tab_wifi.setChecked(True)
        self.tab_wifi.setFixedHeight(38)
        self.tab_wifi.setFont(QFont("Noto Sans CJK SC", 12))
        self.tab_wifi.setCursor(Qt.PointingHandCursor)
        self.tab_wifi.clicked.connect(lambda: self._switch_tab(0))
        self._set_btn_icon(self.tab_wifi, "wifi.png", 20)

        self.tab_ble = QPushButton("  蓝牙")
        self.tab_ble.setCheckable(True)
        self.tab_ble.setChecked(False)
        self.tab_ble.setFixedHeight(38)
        self.tab_ble.setFont(QFont("Noto Sans CJK SC", 12))
        self.tab_ble.setCursor(Qt.PointingHandCursor)
        self.tab_ble.clicked.connect(lambda: self._switch_tab(1))
        self._set_btn_icon(self.tab_ble, "蓝牙.png", 20)

        tab_bar.addWidget(self.tab_wifi)
        tab_bar.addWidget(self.tab_ble)
        right_layout.addLayout(tab_bar)

        self._update_tab_style()

        right_layout.addSpacing(20)

        # --- 内容切换区 ---
        self.content_stack = QStackedWidget()
        self.content_stack.setFixedHeight(330)

        # WiFi 页面
        self.wifi_page = self._build_wifi_page()
        self.content_stack.addWidget(self.wifi_page)

        # 蓝牙页面
        self.ble_page = self._build_ble_page()
        self.content_stack.addWidget(self.ble_page)

        right_layout.addWidget(self.content_stack)

        # 分割线（紧挨内容卡片，跳过连接上移）
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #3A3A3A;")
        right_layout.addWidget(line)

        right_layout.addSpacing(10)

        # 跳过连接
        self.skip_btn = QPushButton("暂时跳过连接")
        self.skip_btn.setFixedHeight(32)
        self.skip_btn.setFont(QFont("Noto Sans CJK SC", 12))
        self.skip_btn.setStyleSheet("""
            QPushButton {
                color: #888888;
                background: transparent;
                border: none;
            }
            QPushButton:hover { color: #AAAAAA; }
            QPushButton:pressed { color: #FFFFFF; }
        """)
        self.skip_btn.setCursor(Qt.PointingHandCursor)
        self.skip_btn.clicked.connect(self.skip_clicked.emit)
        right_layout.addWidget(self.skip_btn, alignment=Qt.AlignCenter)

        main_layout.addWidget(right_panel, 1)

    # ========== 构建子页面 ==========

    def _build_wifi_page(self):
        page = QFrame()
        page.setStyleSheet("background-color: #2A2A2A; border-radius: 12px; border: none;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        # 二维码（进一步放大，去掉边框）
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setFixedSize(180, 180)
        self.qr_label.setStyleSheet("background-color: #1A1A1A; border-radius: 8px; border: none;")
        self._load_qrcode()
        layout.addWidget(self.qr_label, alignment=Qt.AlignCenter)

        layout.addSpacing(18)

        # 提示文字（放大）
        tip = QLabel("使用App扫描二维码连接")
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet("color: #AAAAAA; background: transparent; border: none;")
        tip.setFont(QFont("Noto Sans CJK SC", 12))
        layout.addWidget(tip)

        layout.addSpacing(8)

        # MQTT 地址标签（纯文字，无背景框）
        self.mqtt_addr_label = QLabel("mqtt://broker.emqx.io:1883")
        self.mqtt_addr_label.setAlignment(Qt.AlignCenter)
        self.mqtt_addr_label.setStyleSheet("color: #888888; background: transparent; border: none;")
        self.mqtt_addr_label.setFont(QFont("Helvetica", 11))
        layout.addWidget(self.mqtt_addr_label, alignment=Qt.AlignCenter)

        layout.addSpacing(12)

        # 自动配置按钮（纯文字蓝色，无框）
        auto_btn = QPushButton("  扫描后自动配置连接")
        auto_btn.setFixedHeight(32)
        auto_btn.setFont(QFont("Noto Sans CJK SC", 11))
        auto_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #4DB8FF;
                border: none;
            }
            QPushButton:pressed { color: #3AA8F0; }
        """)
        auto_btn.setCursor(Qt.PointingHandCursor)
        self._set_btn_icon(auto_btn, "二维码.png", 16)
        layout.addWidget(auto_btn, alignment=Qt.AlignCenter)

        layout.addStretch(1)
        return page

    def _build_ble_page(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)
        page_layout.setAlignment(Qt.AlignTop)

        # 卡片
        card = QFrame()
        card.setStyleSheet("background-color: #2A2A2A; border-radius: 12px; border: none;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(0)
        card_layout.setAlignment(Qt.AlignCenter)

        # 蓝牙图标（用图片，放大）
        ble_icon_lbl = QLabel()
        ble_icon_lbl.setAlignment(Qt.AlignCenter)
        self._load_icon("蓝牙.png", ble_icon_lbl, 72, 72)
        card_layout.addWidget(ble_icon_lbl)

        card_layout.addSpacing(12)

        # 设备物理地址
        addr_title = QLabel("设备物理地址")
        addr_title.setAlignment(Qt.AlignCenter)
        addr_title.setStyleSheet("color: #AAAAAA; background: transparent; border: none;")
        addr_title.setFont(QFont("Noto Sans CJK SC", 11))
        card_layout.addWidget(addr_title)

        card_layout.addSpacing(12)

        # MAC 地址（去掉边框）
        mac_label = QLabel("2C:CF:67:F2:ED:B2")
        mac_label.setAlignment(Qt.AlignCenter)
        mac_label.setStyleSheet("""
            color: #FFFFFF;
            background-color: #1A1A1A;
            border-radius: 6px;
            border: none;
            padding: 5px 10px;
        """)
        mac_label.setFont(QFont("Helvetica", 12, QFont.Bold))
        card_layout.addWidget(mac_label, alignment=Qt.AlignCenter)

        card_layout.addSpacing(18)

        # 开始广播按钮（加长）
        self.ble_btn = QPushButton("开始广播")
        self.ble_btn.setFixedSize(280, 40)
        self.ble_btn.setFont(QFont("Noto Sans CJK SC", 12, QFont.Bold))
        self.ble_btn.setStyleSheet("""
            QPushButton {
                background-color: #4DB8FF;
                color: #111111;
                border-radius: 8px;
                border: none;
            }
            QPushButton:pressed { background-color: #3AA8F0; }
            QPushButton:disabled { background-color: #555555; color: #888888; }
        """)
        self.ble_btn.setCursor(Qt.PointingHandCursor)
        self.ble_btn.clicked.connect(self._on_ble_btn_clicked)
        card_layout.addWidget(self.ble_btn, alignment=Qt.AlignCenter)

        page_layout.addWidget(card)

        page_layout.addSpacing(14)

        # 提示文字（在卡片外，单行）
        self.ble_tip = QLabel("点击“开始广播”后，在您的手机或设备上搜索蓝牙设备并连接")
        self.ble_tip.setAlignment(Qt.AlignCenter)
        self.ble_tip.setStyleSheet("color: #888888; background: transparent; border: none;")
        self.ble_tip.setFont(QFont("Noto Sans CJK SC", 10))
        page_layout.addWidget(self.ble_tip)

        page_layout.addStretch(1)
        return page

    # ========== 辅助方法 ==========

    def _load_icon(self, filename, label, w, h):
        """加载 TuBiao 目录下的图标到 QLabel"""
        base_path = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_path, "..", "TuBiao", filename)
        img_path = os.path.abspath(img_path)
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(scaled)
            label.setStyleSheet("background: transparent; border: none;")
        else:
            label.setText("[图标缺失]")
            label.setStyleSheet("color: #e74c3c; background: transparent;")

    def _set_btn_icon(self, btn, filename, size):
        """给 QPushButton 设置图标"""
        base_path = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_path, "..", "TuBiao", filename)
        img_path = os.path.abspath(img_path)
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            btn.setIcon(QIcon(scaled))
            btn.setIconSize(scaled.size())

    def _add_feature_card_img(self, parent_layout, icon_file, text):
        """添加带图片图标的功能卡片"""
        card = QFrame()
        card.setFixedHeight(38)
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(255,255,255,0.06);
                border-radius: 10px;
                border: none;
            }
        """)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 0, 12, 0)
        card_layout.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        self._load_icon(icon_file, icon_lbl, 20, 20)
        card_layout.addWidget(icon_lbl)

        text_lbl = QLabel(text)
        text_lbl.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        text_lbl.setFont(QFont("Noto Sans CJK SC", 11))
        card_layout.addWidget(text_lbl)
        card_layout.addStretch(1)

        parent_layout.addWidget(card)

    def _switch_tab(self, index):
        self.content_stack.setCurrentIndex(index)
        self.tab_wifi.setChecked(index == 0)
        self.tab_ble.setChecked(index == 1)
        self._update_tab_style()

    def _update_tab_style(self):
        active = """
            QPushButton {
                background-color: #4DB8FF;
                color: #111111;
                border-radius: 8px;
                border: none;
            }
        """
        inactive = """
            QPushButton {
                background-color: #3A3A4A;
                color: #888888;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover { background-color: #4A4A5A; }
        """
        self.tab_wifi.setStyleSheet(active if self.tab_wifi.isChecked() else inactive)
        self.tab_ble.setStyleSheet(active if self.tab_ble.isChecked() else inactive)

    def _load_qrcode(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_path, "..", "TuBiao", "erweima.png")
        img_path = os.path.abspath(img_path)
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.qr_label.setPixmap(scaled)
        else:
            self.qr_label.setText("二维码缺失")
            self.qr_label.setStyleSheet("color: #e74c3c; background-color: #FFFFFF; border-radius: 8px;")

    def _on_ble_btn_clicked(self):
        self.ble_btn.setEnabled(False)
        self.ble_btn.setText("广播中...")
        self.ble_tip.setText("正在广播蓝牙信号，请在手机上搜索并连接...")
        self.ble_tip.setStyleSheet("color: #f39c12; background: transparent;")
        self.ble_advertising_requested.emit()

    # -------------- 外部调用接口 --------------

    def set_wifi_status(self, connected: bool):
        if connected:
            self.mqtt_addr_label.setText("已连接")
            self.mqtt_addr_label.setStyleSheet("""
                color: #2ecc71;
                background-color: #1a3a2a;
                border-radius: 6px;
                padding: 3px 8px;
            """)
        else:
            self.mqtt_addr_label.setText("mqtt://broker.emqx.io:1883")
            self.mqtt_addr_label.setStyleSheet("""
                color: #888888;
                background-color: #1A1A1A;
                border-radius: 6px;
                padding: 3px 8px;
            """)

    def set_ble_status(self, status: str, color: str = "#888888"):
        self.ble_tip.setText(status)
        self.ble_tip.setStyleSheet(f"color: {color}; background: transparent;")

    def on_ble_advertising_started(self):
        self.ble_btn.setText("广播中...")

    def on_ble_connected(self):
        self.ble_tip.setText("蓝牙已连接")
        self.ble_tip.setStyleSheet("color: #2ecc71; background: transparent;")

    def on_mqtt_connected(self):
        self.set_wifi_status(True)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    page = ConnectPage()
    page.setWindowTitle("ConnectPage Test")
    page.resize(1024, 600)
    page.show()
    sys.exit(app.exec_())
