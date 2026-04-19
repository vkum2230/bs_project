#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能安全告警服务 (AlertService)

职责：
- 实时分析传感器数据和骑行状态
- 触发安全告警：后方来车、心率异常、疲劳、姿态异常
- 统一冷却去重，防止语音/LED/App 重复鬼畜
- 联动 CommService 推送告警到 App
"""

import time
from typing import Optional, Dict

from PyQt5.QtCore import QObject, pyqtSignal

from core.protocol import SensorData, RideSessionState, RideSummary, AlertType, build_alert_payload
from persistence.config_manager import get_config


class AlertService(QObject):
    """安全告警服务"""

    # 信号：alert_type_value, message, level
    alert_triggered = pyqtSignal(str, str, str)

    def __init__(self, parent=None, comm_service=None, config=None):
        super().__init__(parent)
        self.comm_service = comm_service
        self.config = config or get_config()

        # 冷却时间戳记录：{alert_type_value: 下次可触发时间}
        self._cooldowns: Dict[str, float] = {}

        # 疲劳告警：记录已告警过的小时数
        self._fatigue_alerted_hours: int = 0

    def reset(self):
        """重置状态（骑行开始/结束时调用）"""
        self._cooldowns.clear()
        self._fatigue_alerted_hours = 0

    def on_sensor_data(self, sensor: SensorData, ride_state: RideSessionState):
        """每次收到 STM32 传感器数据时调用"""
        now = time.time()

        # 心率异常和跌倒：任何时候都检查（安全相关）
        self._check_heart_rate(sensor, now)
        self._check_fall(sensor, now)

        # 只有骑行中才检查其他告警
        if ride_state != RideSessionState.RIDING:
            return

        self._check_rear_vehicle(sensor, now)

    def on_stats_updated(self, summary: RideSummary):
        """每秒接收骑行统计更新，用于疲劳告警"""
        self._check_fatigue(summary)

    # --------------------------------------------------------------------------
    # 各告警子项
    # --------------------------------------------------------------------------

    def _check_rear_vehicle(self, sensor: SensorData, now: float):
        """后方来车告警"""
        if sensor.rear_dist <= 0 or sensor.speed <= 0:
            return

        threshold = self.config.get("rear_dist_alert_m", 5.0)
        if sensor.rear_dist >= threshold:
            return

        level = "critical" if sensor.rear_dist < 3.0 else "warning"
        cooldown = 5.0 if sensor.rear_dist < 3.0 else 10.0
        msg = f"注意后方来车，距离 {sensor.rear_dist:.1f} 米"
        self._trigger(AlertType.REAR_VEHICLE, msg, level, cooldown, now)

    def _check_heart_rate(self, sensor: SensorData, now: float):
        """心率异常告警"""
        if sensor.heart_rate <= 0:
            return

        hr_max = self.config.get("heart_rate_max", 180)
        hr_min = self.config.get("heart_rate_min", 50)

        if sensor.heart_rate > hr_max:
            msg = f"心率过高，当前 {sensor.heart_rate:.0f}，请减速休息"
            self._trigger(AlertType.HEART_RATE_HIGH, msg, "warning", 30.0, now)
        elif sensor.heart_rate < hr_min:
            msg = f"心率过低，当前 {sensor.heart_rate:.0f}"
            self._trigger(AlertType.HEART_RATE_LOW, msg, "info", 60.0, now)

    def _check_fatigue(self, summary: RideSummary):
        """疲劳告警：连续骑行超过 4 小时提醒"""
        moving_hours = int(summary.moving_time // 3600)
        if moving_hours < 4:
            return

        # 每个新的小时只提醒一次
        if moving_hours > self._fatigue_alerted_hours:
            self._fatigue_alerted_hours = moving_hours
            msg = f"您已连续骑行超过 {moving_hours} 小时，建议休息"
            self._trigger(AlertType.FATIGUE, msg, "warning", 3600.0, time.time())

    def _check_fall(self, sensor: SensorData, now: float):
        """姿态异常/摔车告警"""
        if sensor.zt_flag == 0:
            msg = "检测到跌倒，请确认人身安全"
            self._trigger(AlertType.FALL_DETECTED, msg, "critical", 60.0, now)

    # --------------------------------------------------------------------------
    # 触发与冷却
    # --------------------------------------------------------------------------

    def _trigger(self, alert_type: AlertType, message: str, level: str, cooldown_sec: float, now: float):
        type_key = alert_type.value

        # 检查全局开关（映射 AlertType -> config 中的开关名）
        alert_name_map = {
            "rear_vehicle": "rear_vehicle",
            "heart_rate_high": "heart_rate",
            "heart_rate_low": "heart_rate",
            "fatigue": "fatigue",
            "fall_detected": "fall",
            "off_route": "off_route",
        }
        alert_name = alert_name_map.get(type_key, type_key)
        if not self.config.get_alert(alert_name):
            return

        # 检查冷却
        next_allowed = self._cooldowns.get(type_key, 0)
        if now < next_allowed:
            return

        self._cooldowns[type_key] = now + cooldown_sec
        print(f"[AlertService] 触发告警 [{type_key}] {level}: {message}")

        # 发射信号（供 main.py 联动语音+LED+UI）
        self.alert_triggered.emit(type_key, message, level)

        # 同时推送到 App（CommService）
        if self.comm_service:
            try:
                payload = build_alert_payload(alert_type, message, level)
                # 复用 CommService 内部事件推送通道
                self._push_to_comm(payload)
            except Exception as e:
                print(f"[AlertService] 推送告警到 CommService 失败: {e}")

    def _push_to_comm(self, payload: dict):
        """调用 CommService 推送告警事件"""
        if self.comm_service is None:
            return
        try:
            # 优先调用公开的 send_alert 接口
            if hasattr(self.comm_service, "send_alert"):
                self.comm_service.send_alert(
                    payload.get("type", ""),
                    payload.get("message", ""),
                    payload.get("level", "warning"),
                )
            elif hasattr(self.comm_service, "event_pushed"):
                self.comm_service.event_pushed.emit("alert", payload)
        except Exception as e:
            print(f"[AlertService] 推送告警到 CommService 失败: {e}")


if __name__ == "__main__":
    from PyQt5.QtCore import QCoreApplication
    app = QCoreApplication([])

    svc = AlertService()
    svc.alert_triggered.connect(lambda t, m, l: print(f"[{l}] {t}: {m}"))

    sensor = SensorData(
        speed=20.0,
        heart_rate=190,
        rear_dist=2.5,
        posture=0,
    )
    svc.on_sensor_data(sensor, RideSessionState.RIDING)

    # 模拟疲劳
    summary = RideSummary(moving_time=4 * 3600 + 10)
    svc.on_stats_updated(summary)

    app.quit()
