#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置页面 (SettingsPage)

职责：
- 展示和修改用户配置项
- 心率上限、心率下限、体重、后方来车阈值、告警开关
"""

from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QCheckBox, QGridLayout, QMessageBox, QSlider
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from persistence.config_manager import get_config, ConfigManager


class SettingsPage(QWidget):
    """系统设置页"""

    config_saved = pyqtSignal()

    def __init__(self, config: Optional[ConfigManager] = None, parent=None):
        super().__init__(parent)
        self.config = config or get_config()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # 标题
        title = QLabel("⚙️ 系统设置")
        title.setStyleSheet("color: #FFFFFF; background: transparent;")
        title.setFont(QFont("Helvetica", 16, QFont.Bold))
        layout.addWidget(title)

        # 设置卡片
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border-radius: 12px;
                border: 1px solid #3A3A4A;
            }
        """)
        card_layout = QGridLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(12, 10, 12, 10)

        # 心率上限
        lbl_hr_max = QLabel("心率上限 (bpm)")
        lbl_hr_max.setStyleSheet("color: #AAAAAA; background: transparent;")
        lbl_hr_max.setFont(QFont("Helvetica", 11))
        self.hr_max_value = 180
        self.hr_max_label = QLabel(str(self.hr_max_value))
        self.hr_max_label.setStyleSheet("""
            QLabel {
                background-color: #3A3A4A;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 50px;
            }
        """)
        self.hr_max_label.setAlignment(Qt.AlignCenter)
        hr_max_layout = QHBoxLayout()
        hr_max_layout.setSpacing(2)
        hr_max_layout.addWidget(self.hr_max_label)
        self.btn_hr_max_minus = QPushButton("−")
        self.btn_hr_max_minus.setFixedSize(32, 36)
        self.btn_hr_max_minus.setStyleSheet(self._arrow_btn_style())
        self.btn_hr_max_minus.clicked.connect(lambda: self._adjust_value("hr_max", -1))
        self.btn_hr_max_plus = QPushButton("+")
        self.btn_hr_max_plus.setFixedSize(32, 36)
        self.btn_hr_max_plus.setStyleSheet(self._arrow_btn_style())
        self.btn_hr_max_plus.clicked.connect(lambda: self._adjust_value("hr_max", 1))
        hr_max_layout.addWidget(self.btn_hr_max_minus)
        hr_max_layout.addWidget(self.btn_hr_max_plus)
        card_layout.addWidget(lbl_hr_max, 0, 0)
        card_layout.addLayout(hr_max_layout, 0, 1)

        # 心率下限
        lbl_hr_min = QLabel("心率下限 (bpm)")
        lbl_hr_min.setStyleSheet("color: #AAAAAA; background: transparent;")
        lbl_hr_min.setFont(QFont("Helvetica", 11))
        self.hr_min_value = 50
        self.hr_min_label = QLabel(str(self.hr_min_value))
        self.hr_min_label.setStyleSheet("""
            QLabel {
                background-color: #3A3A4A;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 50px;
            }
        """)
        self.hr_min_label.setAlignment(Qt.AlignCenter)
        hr_min_layout = QHBoxLayout()
        hr_min_layout.setSpacing(2)
        hr_min_layout.addWidget(self.hr_min_label)
        self.btn_hr_min_minus = QPushButton("−")
        self.btn_hr_min_minus.setFixedSize(32, 36)
        self.btn_hr_min_minus.setStyleSheet(self._arrow_btn_style())
        self.btn_hr_min_minus.clicked.connect(lambda: self._adjust_value("hr_min", -1))
        self.btn_hr_min_plus = QPushButton("+")
        self.btn_hr_min_plus.setFixedSize(32, 36)
        self.btn_hr_min_plus.setStyleSheet(self._arrow_btn_style())
        self.btn_hr_min_plus.clicked.connect(lambda: self._adjust_value("hr_min", 1))
        hr_min_layout.addWidget(self.btn_hr_min_minus)
        hr_min_layout.addWidget(self.btn_hr_min_plus)
        card_layout.addWidget(lbl_hr_min, 1, 0)
        card_layout.addLayout(hr_min_layout, 1, 1)

        # 体重
        lbl_weight = QLabel("体重 (kg)")
        lbl_weight.setStyleSheet("color: #AAAAAA; background: transparent;")
        lbl_weight.setFont(QFont("Helvetica", 11))
        self.weight_value = 70.0
        self.weight_label = QLabel(f"{self.weight_value:.1f}")
        self.weight_label.setStyleSheet("""
            QLabel {
                background-color: #3A3A4A;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 50px;
            }
        """)
        self.weight_label.setAlignment(Qt.AlignCenter)
        weight_layout = QHBoxLayout()
        weight_layout.setSpacing(2)
        weight_layout.addWidget(self.weight_label)
        self.btn_weight_minus = QPushButton("−")
        self.btn_weight_minus.setFixedSize(32, 36)
        self.btn_weight_minus.setStyleSheet(self._arrow_btn_style())
        self.btn_weight_minus.clicked.connect(lambda: self._adjust_value("weight", -0.1))
        self.btn_weight_plus = QPushButton("+")
        self.btn_weight_plus.setFixedSize(32, 36)
        self.btn_weight_plus.setStyleSheet(self._arrow_btn_style())
        self.btn_weight_plus.clicked.connect(lambda: self._adjust_value("weight", 0.1))
        weight_layout.addWidget(self.btn_weight_minus)
        weight_layout.addWidget(self.btn_weight_plus)
        card_layout.addWidget(lbl_weight, 2, 0)
        card_layout.addLayout(weight_layout, 2, 1)

        # 后方来车距离阈值
        lbl_rear = QLabel("后方来车阈值 (m)")
        lbl_rear.setStyleSheet("color: #AAAAAA; background: transparent;")
        lbl_rear.setFont(QFont("Helvetica", 11))
        self.rear_value = 5.0
        self.rear_label = QLabel(f"{self.rear_value:.1f}")
        self.rear_label.setStyleSheet("""
            QLabel {
                background-color: #3A3A4A;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 50px;
            }
        """)
        self.rear_label.setAlignment(Qt.AlignCenter)
        rear_layout = QHBoxLayout()
        rear_layout.setSpacing(2)
        rear_layout.addWidget(self.rear_label)
        self.btn_rear_minus = QPushButton("−")
        self.btn_rear_minus.setFixedSize(32, 36)
        self.btn_rear_minus.setStyleSheet(self._arrow_btn_style())
        self.btn_rear_minus.clicked.connect(lambda: self._adjust_value("rear", -0.1))
        self.btn_rear_plus = QPushButton("+")
        self.btn_rear_plus.setFixedSize(32, 36)
        self.btn_rear_plus.setStyleSheet(self._arrow_btn_style())
        self.btn_rear_plus.clicked.connect(lambda: self._adjust_value("rear", 0.1))
        rear_layout.addWidget(self.btn_rear_minus)
        rear_layout.addWidget(self.btn_rear_plus)
        card_layout.addWidget(lbl_rear, 3, 0)
        card_layout.addLayout(rear_layout, 3, 1)

        # 播报音量
        lbl_volume = QLabel("播报音量")
        lbl_volume.setStyleSheet("color: #AAAAAA; background: transparent;")
        lbl_volume.setFont(QFont("Helvetica", 11))

        vol_widget = QWidget()
        vol_widget.setStyleSheet("background: transparent;")
        vol_layout = QHBoxLayout(vol_widget)
        vol_layout.setContentsMargins(0, 0, 0, 0)
        vol_layout.setSpacing(8)

        self.slider_volume = QSlider(Qt.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(self.config.get("voice_volume", 85))
        self.slider_volume.setSingleStep(5)
        self.slider_volume.setPageStep(10)
        self.slider_volume.setStyleSheet(self._slider_style())
        self.slider_volume.valueChanged.connect(self._on_volume_changed)
        self.slider_volume.sliderReleased.connect(self._on_volume_released)
        vol_layout.addWidget(self.slider_volume, 1)

        self.lbl_volume_val = QLabel(f"{self.slider_volume.value()}%")
        self.lbl_volume_val.setStyleSheet("color: #FFFFFF; background: transparent;")
        self.lbl_volume_val.setFont(QFont("Helvetica", 12, QFont.Bold))
        self.lbl_volume_val.setFixedWidth(45)
        vol_layout.addWidget(self.lbl_volume_val)

        card_layout.addWidget(lbl_volume, 4, 0)
        card_layout.addWidget(vol_widget, 4, 1)

        layout.addWidget(card)

        # 告警开关卡片
        alert_card = QFrame()
        alert_card.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border-radius: 12px;
                border: 1px solid #3A3A4A;
            }
        """)
        alert_layout = QVBoxLayout(alert_card)
        alert_layout.setSpacing(10)
        alert_layout.setContentsMargins(12, 10, 12, 10)

        alert_title = QLabel("🔔 告警开关")
        alert_title.setStyleSheet("color: #FFFFFF; background: transparent;")
        alert_title.setFont(QFont("Helvetica", 13, QFont.Bold))
        alert_layout.addWidget(alert_title)

        alerts = self.config.get("alerts_enabled", {})

        checkbox_grid = QGridLayout()
        checkbox_grid.setSpacing(10)
        checkbox_grid.setHorizontalSpacing(28)
        checkbox_grid.setVerticalSpacing(10)

        self.chk_rear = QCheckBox("后方来车告警")
        self.chk_rear.setChecked(alerts.get("rear_vehicle", True))
        self.chk_rear.setStyleSheet(self._checkbox_style())
        checkbox_grid.addWidget(self.chk_rear, 0, 0)

        self.chk_hr = QCheckBox("心率异常告警")
        self.chk_hr.setChecked(alerts.get("heart_rate", True))
        self.chk_hr.setStyleSheet(self._checkbox_style())
        checkbox_grid.addWidget(self.chk_hr, 0, 1)

        self.chk_fatigue = QCheckBox("疲劳提醒")
        self.chk_fatigue.setChecked(alerts.get("fatigue", True))
        self.chk_fatigue.setStyleSheet(self._checkbox_style())
        checkbox_grid.addWidget(self.chk_fatigue, 0, 2)

        self.chk_fall = QCheckBox("姿态异常/摔车检测")
        self.chk_fall.setChecked(alerts.get("fall", True))
        self.chk_fall.setStyleSheet(self._checkbox_style())
        checkbox_grid.addWidget(self.chk_fall, 0, 3)

        checkbox_grid.setColumnStretch(4, 1)

        alert_layout.addLayout(checkbox_grid)

        layout.addWidget(alert_card)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)
        btn_layout.addStretch(1)

        self.btn_reset = QPushButton("恢复默认")
        self.btn_reset.setFixedSize(100, 36)
        self.btn_reset.setStyleSheet(
            "QPushButton { background-color: #888888; color: #FFFFFF; border-radius: 6px; font-size: 12px; }"
            "QPushButton:pressed { background-color: #666666; }"
        )
        self.btn_reset.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(self.btn_reset)

        self.btn_save = QPushButton("保存设置")
        self.btn_save.setFixedSize(100, 36)
        self.btn_save.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: #FFFFFF; border-radius: 6px; font-size: 12px; }"
            "QPushButton:pressed { background-color: #27ae60; }"
        )
        self.btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.btn_save)

        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)
        layout.addStretch(1)

        # 初始化值
        self._load_values()

    def _arrow_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #4A4A5A;
                color: #FFFFFF;
                border-radius: 6px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A5A6A;
            }
            QPushButton:pressed {
                background-color: #4DB8FF;
            }
        """

    def _load_values(self):
        """加载配置值"""
        self.hr_max_value = self.config.get("heart_rate_max", 180)
        self.hr_min_value = self.config.get("heart_rate_min", 50)
        self.weight_value = self.config.get("weight_kg", 70.0)
        self.rear_value = self.config.get("rear_dist_alert_m", 5.0)

        self.hr_max_label.setText(str(self.hr_max_value))
        self.hr_min_label.setText(str(self.hr_min_value))
        self.weight_label.setText(f"{self.weight_value:.1f}")
        self.rear_label.setText(f"{self.rear_value:.1f}")

    def reload_config(self):
        """从配置管理器重新加载所有设置到 UI 控件"""
        self._load_values()
        vol = self.config.get("voice_volume", 85)
        self.slider_volume.setValue(vol)
        self.lbl_volume_val.setText(f"{vol}%")
        alerts = self.config.get("alerts_enabled", {})
        self.chk_rear.setChecked(alerts.get("rear_vehicle", True))
        self.chk_hr.setChecked(alerts.get("heart_rate", True))
        self.chk_fatigue.setChecked(alerts.get("fatigue", True))
        self.chk_fall.setChecked(alerts.get("fall", True))

    def _adjust_value(self, name: str, delta: float):
        """调整数值"""
        if name == "hr_max":
            self.hr_max_value = max(60, min(250, self.hr_max_value + delta))
            self.hr_max_label.setText(str(int(self.hr_max_value)))
        elif name == "hr_min":
            self.hr_min_value = max(30, min(120, self.hr_min_value + delta))
            self.hr_min_label.setText(str(int(self.hr_min_value)))
        elif name == "weight":
            self.weight_value = max(20.0, min(200.0, self.weight_value + delta))
            self.weight_label.setText(f"{self.weight_value:.1f}")
        elif name == "rear":
            self.rear_value = max(1.0, min(20.0, self.rear_value + delta))
            self.rear_label.setText(f"{self.rear_value:.1f}")

    def _checkbox_style(self) -> str:
        return """
            QCheckBox {
                color: #FFFFFF;
                background: transparent;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #888888;
                background-color: #2E2E3A;
            }
            QCheckBox::indicator:checked {
                background-color: #2ecc71;
                border: 1px solid #2ecc71;
            }
        """

    def _slider_style(self) -> str:
        return """
            QSlider::groove:horizontal {
                height: 8px;
                background: #555555;
                border-radius: 4px;
            }
            QSlider::sub-page:horizontal {
                background: #2ecc71;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 28px;
                height: 28px;
                margin: -10px 0;
                background: #FFFFFF;
                border-radius: 14px;
            }
            QSlider::handle:horizontal:pressed {
                background: #DDDDDD;
            }
        """

    def _on_volume_changed(self, value: int):
        self.lbl_volume_val.setText(f"{value}%")

    def _on_volume_released(self):
        vol = self.slider_volume.value()
        print(f"[Settings] 滑块释放，应用音量 {vol}%")
        self._set_system_volume(vol)

    @staticmethod
    def _set_system_volume(volume: int) -> bool:
        import subprocess
        vol = max(0, min(100, volume))
        success = False

        candidates = [
            ("amixer", "-c", "2", "set", "PCM", f"{vol}%", "unmute"),
            ("amixer", "-c", "2", "set", "Headphone", f"{vol}%", "unmute"),
            ("amixer", "-c", "2", "set", "Speaker", f"{vol}%", "unmute"),
            ("amixer", "-c", "2", "set", "Digital", f"{vol}%", "unmute"),
            ("amixer", "set", "Master", f"{vol}%", "unmute"),
            ("amixer", "set", "PCM", f"{vol}%", "unmute"),
            ("amixer", "set", "Headphone", f"{vol}%", "unmute"),
        ]

        for cmd in candidates:
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=3)
                if result.returncode == 0:
                    print(f"[Volume] ✓ {' '.join(cmd)}")
                    success = True
                else:
                    err = result.stderr.decode().strip()[:60] if result.stderr else ""
                    print(f"[Volume] ✗ {' '.join(cmd)} — {err}")
            except Exception as e:
                print(f"[Volume] ✗ {' '.join(cmd)} — {e}")

        if success:
            print(f"[Volume] 系统音量已设置为 {vol}%")
        else:
            print(f"[Volume] 警告：所有 amixer 命令均失败，音量可能未生效")
        return success

    def _save_settings(self):
        self.config.set("heart_rate_max", int(self.hr_max_value))
        self.config.set("heart_rate_min", int(self.hr_min_value))
        self.config.set("weight_kg", round(self.weight_value, 1))
        self.config.set("rear_dist_alert_m", round(self.rear_value, 1))

        alerts = {
            "rear_vehicle": self.chk_rear.isChecked(),
            "heart_rate": self.chk_hr.isChecked(),
            "fatigue": self.chk_fatigue.isChecked(),
            "fall": self.chk_fall.isChecked(),
        }
        self.config.set("alerts_enabled", alerts)

        self.config.set("voice_volume", self.slider_volume.value())
        self._set_system_volume(self.slider_volume.value())

        self.config_saved.emit()

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("保存成功")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2A2A2A;
            }
            QMessageBox QLabel {
                color: #FFFFFF;
            }
        """)
        ok_btn = msg_box.addButton(QMessageBox.Ok)
        ok_btn.setStyleSheet("""
            QPushButton {
                color: #000000;
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 6px 20px;
                font-size: 13px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
            QPushButton:pressed {
                background-color: #D0D0D0;
            }
        """)
        msg_box.exec_()

    def _reset_defaults(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("恢复默认")
        msg_box.setText("确定要恢复默认设置吗？")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2A2A2A;
            }
            QMessageBox QLabel {
                color: #FFFFFF;
            }
        """)
        yes_btn = msg_box.addButton("是", QMessageBox.YesRole)
        no_btn = msg_box.addButton("否", QMessageBox.NoRole)
        btn_style = """
            QPushButton {
                color: #000000;
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 6px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
            QPushButton:pressed {
                background-color: #D0D0D0;
            }
        """
        yes_btn.setStyleSheet(btn_style)
        no_btn.setStyleSheet(btn_style)
        msg_box.setDefaultButton(no_btn)
        msg_box.exec_()

        if msg_box.clickedButton() == yes_btn:
            self.hr_max_value = 180
            self.hr_min_value = 50
            self.weight_value = 70.0
            self.rear_value = 5.0
            self.hr_max_label.setText(str(self.hr_max_value))
            self.hr_min_label.setText(str(self.hr_min_value))
            self.weight_label.setText(f"{self.weight_value:.1f}")
            self.rear_label.setText(f"{self.rear_value:.1f}")
            self.chk_rear.setChecked(True)
            self.chk_hr.setChecked(True)
            self.chk_fatigue.setChecked(True)
            self.chk_fall.setChecked(True)
            self.slider_volume.setValue(85)
            self._save_settings()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    page = SettingsPage()
    page.setWindowTitle("SettingsPage Test")
    page.resize(480, 600)
    page.show()
    sys.exit(app.exec_())
