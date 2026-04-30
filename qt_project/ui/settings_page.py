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
    QSpinBox, QDoubleSpinBox, QPushButton, QFrame,
    QCheckBox, QGridLayout, QMessageBox, QSlider
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
        self.spin_hr_max = QSpinBox()
        self.spin_hr_max.setRange(60, 250)
        self.spin_hr_max.setValue(self.config.get("heart_rate_max", 180))
        self.spin_hr_max.setStyleSheet(self._spin_style())
        card_layout.addWidget(lbl_hr_max, 0, 0)
        card_layout.addWidget(self.spin_hr_max, 0, 1)

        # 心率下限
        lbl_hr_min = QLabel("心率下限 (bpm)")
        lbl_hr_min.setStyleSheet("color: #AAAAAA; background: transparent;")
        lbl_hr_min.setFont(QFont("Helvetica", 11))
        self.spin_hr_min = QSpinBox()
        self.spin_hr_min.setRange(30, 120)
        self.spin_hr_min.setValue(self.config.get("heart_rate_min", 50))
        self.spin_hr_min.setStyleSheet(self._spin_style())
        card_layout.addWidget(lbl_hr_min, 1, 0)
        card_layout.addWidget(self.spin_hr_min, 1, 1)

        # 体重
        lbl_weight = QLabel("体重 (kg)")
        lbl_weight.setStyleSheet("color: #AAAAAA; background: transparent;")
        lbl_weight.setFont(QFont("Helvetica", 11))
        self.spin_weight = QDoubleSpinBox()
        self.spin_weight.setRange(20.0, 200.0)
        self.spin_weight.setDecimals(1)
        self.spin_weight.setValue(self.config.get("weight_kg", 70.0))
        self.spin_weight.setStyleSheet(self._spin_style())
        card_layout.addWidget(lbl_weight, 2, 0)
        card_layout.addWidget(self.spin_weight, 2, 1)

        # 后方来车距离阈值
        lbl_rear = QLabel("后方来车阈值 (m)")
        lbl_rear.setStyleSheet("color: #AAAAAA; background: transparent;")
        lbl_rear.setFont(QFont("Helvetica", 11))
        self.spin_rear = QDoubleSpinBox()
        self.spin_rear.setRange(1.0, 20.0)
        self.spin_rear.setDecimals(1)
        self.spin_rear.setValue(self.config.get("rear_dist_alert_m", 5.0))
        self.spin_rear.setStyleSheet(self._spin_style())
        card_layout.addWidget(lbl_rear, 3, 0)
        card_layout.addWidget(self.spin_rear, 3, 1)

        # 播报音量（移到系统设置卡片内）
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

        # 让最后一列占满剩余空间，保持对齐
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

    def _spin_style(self) -> str:
        return """
            QSpinBox, QDoubleSpinBox {
                background-color: #3A3A4A;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 4px;
                min-width: 80px;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                width: 0px;
                border: none;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                width: 0px;
                border: none;
            }
        """

    def reload_config(self):
        """从配置管理器重新加载所有设置到 UI 控件（供外部修改配置后刷新）"""
        self.spin_hr_max.setValue(self.config.get("heart_rate_max", 180))
        self.spin_hr_min.setValue(self.config.get("heart_rate_min", 50))
        self.spin_weight.setValue(self.config.get("weight_kg", 70.0))
        self.spin_rear.setValue(self.config.get("rear_dist_alert_m", 5.0))
        vol = self.config.get("voice_volume", 85)
        self.slider_volume.setValue(vol)
        self.lbl_volume_val.setText(f"{vol}%")
        alerts = self.config.get("alerts_enabled", {})
        self.chk_rear.setChecked(alerts.get("rear_vehicle", True))
        self.chk_hr.setChecked(alerts.get("heart_rate", True))
        self.chk_fatigue.setChecked(alerts.get("fatigue", True))
        self.chk_fall.setChecked(alerts.get("fall", True))

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
        """滑动结束时实时应用音量"""
        vol = self.slider_volume.value()
        print(f"[Settings] 滑块释放，应用音量 {vol}%")
        self._set_system_volume(vol)

    @staticmethod
    def _set_system_volume(volume: int) -> bool:
        """通过 amixer 设置系统音量（覆盖在线/离线所有语音）
        返回是否至少有一个控制项设置成功
        """
        import subprocess
        vol = max(0, min(100, volume))
        success = False

        # 先检测可用的声卡和控制项
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
        self.config.set("heart_rate_max", self.spin_hr_max.value())
        self.config.set("heart_rate_min", self.spin_hr_min.value())
        self.config.set("weight_kg", round(self.spin_weight.value(), 1))
        self.config.set("rear_dist_alert_m", round(self.spin_rear.value(), 1))

        alerts = {
            "rear_vehicle": self.chk_rear.isChecked(),
            "heart_rate": self.chk_hr.isChecked(),
            "fatigue": self.chk_fatigue.isChecked(),
            "fall": self.chk_fall.isChecked(),
        }
        self.config.set("alerts_enabled", alerts)

        # 保存并立即应用音量
        self.config.set("voice_volume", self.slider_volume.value())
        self._set_system_volume(self.slider_volume.value())

        self.config_saved.emit()
        QMessageBox.information(self, "保存成功", "设置已保存并生效")

    def _reset_defaults(self):
        reply = QMessageBox.question(
            self, "恢复默认", "确定要恢复默认设置吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.spin_hr_max.setValue(180)
            self.spin_hr_min.setValue(50)
            self.spin_weight.setValue(70.0)
            self.spin_rear.setValue(5.0)
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
