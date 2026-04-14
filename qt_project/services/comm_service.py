#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通信调度器（CommService）

职责：
- 统一调度 BLE、WiFi、MQTT 三条通信通道
- 接收 STM32 高频传感器数据，合并为 1Hz 低频 App 数据包
- 实时数据定时推（1秒1次）+ 事件数据立即推
- 断连期间缓存数据，重连后自动补发
- 将 App 命令转发给主程序

架构：
    [SensorData] ──▶ DataBuffer ──▶ 定时器 1Hz ──▶ BLE Notify + WiFi JSON + MQTT Pub
    [事件触发] ──────────────────────▶ 立即推送 ──▶ BLE + WiFi + MQTT 三发
    [断连状态] ──────────────────────▶ BufferQueue ──▶ 重连后 WiFi/MQTT 批量补发
"""

import json
import time
import uuid
from typing import List, Optional, Callable
from collections import deque
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from core.protocol import (
    SensorData,
    AppRealtimeData,
    AppCommand,
    RideSessionState,
    sensor_to_app_data,
    build_alert_payload,
)
from drivers.ble_server import BleServer
from drivers.wifi_server import WifiServer
from persistence.buffer_queue import BufferQueue


# ==============================================================================
# MQTT 桥接器（兼容 paho-mqtt 1.x / 2.x）
# ==============================================================================

class MqttBridge:
    """
    MQTT 调试桥接器
    - 发布实时数据到 smartride/realtime
    - 发布事件到 smartride/event
    - 订阅 smartride/command 接收调试命令
    """

    def __init__(
        self,
        broker: str = "broker.emqx.io",
        port: int = 1883,
        client_id: Optional[str] = None,
        on_command: Optional[Callable[[str, str], None]] = None,
        on_connected: Optional[Callable[[], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
    ):
        self.broker = broker
        self.port = port
        self.client_id = client_id or f"smartride-pi5-{uuid.uuid4().hex[:8]}"
        self.on_command = on_command
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self._client = None
        self._connected = False
        self._topics = {
            "realtime": "smartride/realtime",
            "event": "smartride/event",
            "buffer": "smartride/buffer",
            "command": "smartride/command",
        }

    def start(self):
        try:
            import paho.mqtt.client as mqtt

            # 兼容 paho-mqtt 2.0+ 的 CallbackAPIVersion 参数
            try:
                self._client = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                    client_id=self.client_id,
                )
            except (AttributeError, TypeError):
                self._client = mqtt.Client(client_id=self.client_id)

            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message

            # 自动重连：1~15 秒退避
            try:
                self._client.reconnect_delay_set(min_delay=1, max_delay=15)
            except Exception:
                pass

            self._client.connect(self.broker, self.port, 60)
            self._client.loop_start()
            print(f"[MqttBridge] MQTT 连接启动: {self.broker}:{self.port}")

        except ImportError:
            print("[MqttBridge] 警告: paho-mqtt 未安装，MQTT 调试通道不可用")
            print("           安装命令: pip3 install paho-mqtt")
        except Exception as e:
            print(f"[MqttBridge] 启动失败: {e}")

    def stop(self):
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
            self._connected = False

    def publish(self, topic_key: str, payload: str or dict or bytes, qos: int = 0):
        if not self._client or not self._connected:
            return
        topic = self._topics.get(topic_key, topic_key)
        if isinstance(payload, dict):
            payload = json.dumps(payload, ensure_ascii=False)
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        try:
            result = self._client.publish(topic, payload, qos=qos)
            # paho-mqtt 2.x result.rc 是 ReasonCodes 对象
            rc = getattr(result, "rc", None)
            rc_val = rc.value if hasattr(rc, "value") else rc
            if rc is not None and rc != 0:
                print(f"[MqttBridge] 发布队列异常 [{topic}] rc={rc_val}")
        except Exception as e:
            print(f"[MqttBridge] 发布失败 [{topic}]: {e}")

    def _on_connect(self, client, userdata, flags, rc, *args):
        # paho 2.x rc 是 ReasonCodes 对象，打印其值更直观
        rc_val = getattr(rc, "value", rc) if hasattr(rc, "value") else rc
        if rc == 0:
            self._connected = True
            print(f"[MqttBridge] MQTT 连接成功 (client_id={client._client_id}, rc={rc_val})")
            try:
                client.subscribe(self._topics["command"])
                print(f"[MqttBridge] 已订阅命令主题: {self._topics['command']}")
            except Exception as e:
                print(f"[MqttBridge] 订阅失败: {e}")
            if self.on_connected:
                try:
                    self.on_connected()
                except Exception:
                    pass
        else:
            print(f"[MqttBridge] MQTT 连接失败，返回码: {rc_val}")

    def _on_disconnect(self, client, userdata, disconnect_flags, rc, properties=None):
        self._connected = False
        rc_val = getattr(rc, "value", rc) if hasattr(rc, "value") else rc
        print(f"[MqttBridge] MQTT 已断开 (rc={rc_val}, flags={disconnect_flags})")
        if self.on_disconnected:
            try:
                self.on_disconnected()
            except Exception:
                pass

    def _on_message(self, client, userdata, msg):
        try:
            text = msg.payload.decode("utf-8", errors="ignore").strip()
            if text and self.on_command:
                self.on_command(text, channel="mqtt")
        except Exception as e:
            print(f"[MqttBridge] 消息处理失败: {e}")


# ==============================================================================
# 数据缓存
# ==============================================================================

class DataBuffer:
    """最近 1 秒内的传感器数据缓存，用于平滑/合并"""

    def __init__(self, window_seconds: float = 1.0):
        self.window = window_seconds
        self._buffer: deque[SensorData] = deque()

    def push(self, sensor: SensorData):
        self._buffer.append(sensor)
        cutoff = time.time() - self.window
        while self._buffer and self._buffer[0].received_at < cutoff:
            self._buffer.popleft()

    def get_merged(self, ride_state: RideSessionState) -> AppRealtimeData:
        """合并最近 1 秒的数据为一条 AppRealtimeData"""
        if not self._buffer:
            return AppRealtimeData(ride_state=ride_state.value)

        latest = self._buffer[-1]
        n = len(self._buffer)

        # 速度、功率、心率取平均值更平滑；踏频、距离取最新值
        avg_speed = sum(s.speed for s in self._buffer) / n
        avg_power = sum(s.power for s in self._buffer) / n
        avg_hr = sum(s.heart_rate for s in self._buffer) / n
        avg_temp = sum(s.temperature for s in self._buffer) / n
        avg_rear = sum(s.rear_dist for s in self._buffer) / n

        return AppRealtimeData(
            speed=round(avg_speed, 1),
            cadence=latest.cadence,
            power=round(avg_power, 0),
            distance=latest.distance,
            heart_rate=round(avg_hr, 0),
            slope=latest.slope,
            temperature=round(avg_temp, 1),
            rear_dist=round(avg_rear, 1),
            gps=latest.location,
            ride_state=ride_state.value,
            timestamp=latest.received_at,
        )

    def clear(self):
        self._buffer.clear()


# ==============================================================================
# 通信调度器主类
# ==============================================================================

class CommService(QObject):
    """通信调度器"""

    # 转发 App 命令给主程序
    command_received = pyqtSignal(AppCommand)

    # 通道连接状态变化
    ble_client_connected = pyqtSignal(str)
    ble_client_disconnected = pyqtSignal()
    wifi_client_connected = pyqtSignal(str)
    wifi_client_disconnected = pyqtSignal(str)
    mqtt_connected = pyqtSignal()
    mqtt_disconnected = pyqtSignal()

    # 内部状态变化（可选外部监听）
    data_pushed = pyqtSignal(AppRealtimeData)
    event_pushed = pyqtSignal(str, dict)  # event_type, payload

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ride_state = RideSessionState.IDLE

        # 数据缓存与断连队列
        self.data_buffer = DataBuffer(window_seconds=1.0)
        self.buffer_queue = BufferQueue(max_items=5000, max_age_seconds=1800)

        # BLE / WiFi 服务器
        self.ble_server = BleServer(host_address="2C:CF:67:F2:ED:B2", port=1)
        self.wifi_server = WifiServer(host="0.0.0.0", port=8765)

        # MQTT 调试桥接器
        self.mqtt_bridge = MqttBridge(
            broker="broker.emqx.io",
            port=1883,
            client_id=None,  # 不固定 client_id，避免公共 broker 冲突
            on_command=self._on_mqtt_command,
            on_connected=lambda: self.mqtt_connected.emit(),
            on_disconnected=lambda: self.mqtt_disconnected.emit(),
        )

        # 绑定信号
        self.ble_server.client_connected.connect(self._on_ble_connected)
        self.ble_server.client_disconnected.connect(self._on_ble_disconnected)
        self.ble_server.command_received.connect(self._on_ble_command)
        self.ble_server.error_occurred.connect(lambda e: print(f"[CommService] BLE错误: {e}"))

        self.wifi_server.client_connected.connect(self._on_wifi_connected)
        self.wifi_server.client_disconnected.connect(self._on_wifi_disconnected)
        self.wifi_server.command_received.connect(self._on_wifi_command)
        self.wifi_server.error_occurred.connect(lambda e: print(f"[CommService] WiFi错误: {e}"))

        # 定时器：1Hz 推送实时数据
        self.push_timer = QTimer(self)
        self.push_timer.timeout.connect(self._push_realtime_data)
        self.push_timer.start(1000)

        self._servers_started = False

    def start(self):
        """启动 BLE、WiFi、MQTT 服务"""
        if self._servers_started:
            return
        print("[CommService] 启动通信服务...")
        self.ble_server.start()
        self.wifi_server.start()
        self.mqtt_bridge.start()
        self._servers_started = True

    def stop(self):
        """停止所有通信服务"""
        print("[CommService] 停止通信服务...")
        self.push_timer.stop()
        self.ble_server.stop()
        self.wifi_server.stop()
        self.mqtt_bridge.stop()
        self._servers_started = False

    # --------------------------------------------------------------------------
    # 数据入口（由 main.py 的串口接收回调调用）
    # --------------------------------------------------------------------------

    def on_sensor_data(self, sensor: SensorData):
        """每收到一条 STM32 数据就调用"""
        self.data_buffer.push(sensor)

        # 实时检测并推送事件（不依赖定时器）
        self._check_and_emit_events(sensor)

    def set_ride_state(self, state: RideSessionState):
        """更新当前骑行状态"""
        old_state = self.ride_state
        self.ride_state = state
        if old_state != state:
            self._push_event("ride_state_changed", {
                "old": old_state.value,
                "new": state.value,
            })

    # --------------------------------------------------------------------------
    # 定时推送逻辑
    # --------------------------------------------------------------------------

    def _push_realtime_data(self):
        """每秒执行一次：合并数据并推送到可用通道"""
        app_data = self.data_buffer.get_merged(self.ride_state)
        self.data_pushed.emit(app_data)

        has_ble = self.ble_server.has_connected_client()
        has_wifi = self.wifi_server.has_connected_client()

        if has_ble:
            # 蓝牙优先：发送 JSON
            try:
                ble_payload = app_data.to_json()
                self.ble_server.notify(ble_payload)
            except Exception as e:
                print(f"[CommService] BLE推送失败: {e}")
            # 蓝牙恢复后补发缓存
            self._try_flush_buffer()
        else:
            # 蓝牙断开，走网络通道（MQTT + 可选 WiFi）
            self.mqtt_bridge.publish("realtime", app_data.to_dict())
            if has_wifi:
                try:
                    json_payload = app_data.to_json()
                    self.wifi_server.broadcast(json_payload)
                except Exception as e:
                    print(f"[CommService] WiFi推送失败: {e}")
            # 只要 MQTT 连着或有 WiFi 客户端，就尝试补发；否则缓存
            if self.mqtt_bridge._connected or has_wifi:
                self._try_flush_buffer()
            else:
                self.buffer_queue.push(app_data)

    def _check_and_emit_events(self, sensor: SensorData):
        """基于传感器数据检查是否需要立即推送事件"""
        # 后方来车告警
        if sensor.rear_dist > 0 and sensor.rear_dist < 5:
            payload = build_alert_payload(
                type(self)._get_alert_type("rear_vehicle"),
                f"后方有车辆接近，距离仅{sensor.rear_dist:.1f}米",
                level="critical" if sensor.rear_dist < 3 else "warning",
            )
            self._push_event("alert", payload)

        # 心率过高告警（默认阈值 180，后续从配置读取）
        if sensor.heart_rate > 180:
            payload = build_alert_payload(
                type(self)._get_alert_type("heart_rate_high"),
                f"心率过高：{sensor.heart_rate:.0f}次每分钟，请注意",
                level="warning",
            )
            self._push_event("alert", payload)

        # 姿态异常告警
        if sensor.posture != 0:
            payload = build_alert_payload(
                type(self)._get_alert_type("fall_detected"),
                "检测到骑行姿态异常，请注意安全",
                level="warning",
            )
            self._push_event("alert", payload)

    @staticmethod
    def _get_alert_type(name: str):
        """辅助：从字符串名转换为 AlertType（容错）"""
        from core.protocol import AlertType
        try:
            return AlertType(name)
        except ValueError:
            return AlertType.REAR_VEHICLE

    def _push_event(self, event_type: str, payload: dict):
        """立即推送事件到可用通道（蓝牙优先）"""
        self.event_pushed.emit(event_type, payload)
        event_json = json.dumps({"event": event_type, "data": payload}, ensure_ascii=False)

        has_ble = self.ble_server.has_connected_client()
        has_wifi = self.wifi_server.has_connected_client()

        if has_ble:
            self.ble_server.notify(event_json)
        else:
            # 蓝牙断开，走网络通道（MQTT + 可选 WiFi）
            self.mqtt_bridge.publish("event", {"event": event_type, "data": payload})
            if has_wifi:
                self.wifi_server.broadcast(event_json)

    def _try_flush_buffer(self):
        """尝试将断连缓存的数据补发给 WiFi / MQTT 客户端"""
        if self.buffer_queue.is_empty():
            return

        summary = self.buffer_queue.get_summary()
        print(f"[CommService] 补发缓存数据: {summary['count']} 条, "
              f"持续时间 {summary['duration']} 秒")

        items = self.buffer_queue.drain()
        # 分批次发送，避免一次性发送太多导致阻塞
        BATCH_SIZE = 50
        for i in range(0, len(items), BATCH_SIZE):
            batch = items[i:i + BATCH_SIZE]
            batch_payload = {"event": "buffer_sync", "data": batch}
            batch_json = json.dumps(batch_payload, ensure_ascii=False)
            # 缓冲补发：蓝牙优先，否则 MQTT/WiFi
            if self.ble_server.has_connected_client():
                self.ble_server.notify(batch_json)
            else:
                self.mqtt_bridge.publish("buffer", batch_payload)
                if self.wifi_server.has_connected_client():
                    self.wifi_server.broadcast(batch_json)

    # --------------------------------------------------------------------------
    # 命令接收与转发
    # --------------------------------------------------------------------------

    def _on_ble_command(self, text: str):
        self._handle_command(text, channel="ble")

    def _on_wifi_command(self, text: str):
        self._handle_command(text, channel="wifi")

    def _on_mqtt_command(self, text: str, channel: str = "mqtt"):
        self._handle_command(text, channel="mqtt")

    def _handle_command(self, text: str, channel: str):
        """解析并转发 App 命令"""
        try:
            cmd = AppCommand.from_json(text)
            print(f"[CommService] 收到 [{channel}] 命令: {cmd.cmd_type.value}")
            self.command_received.emit(cmd)
        except Exception as e:
            print(f"[CommService] 命令解析失败: {e}, 原文: {text}")

    # --------------------------------------------------------------------------
    # 连接状态回调
    # --------------------------------------------------------------------------

    def _on_ble_connected(self, addr: str):
        print(f"[CommService] BLE 客户端已连接: {addr}")
        self.ble_client_connected.emit(addr)

    def _on_ble_disconnected(self):
        print("[CommService] BLE 客户端已断开")
        self.ble_client_disconnected.emit()

    def _on_wifi_connected(self, addr: str):
        print(f"[CommService] WiFi 客户端已连接: {addr}")
        self.wifi_client_connected.emit(addr)

    def _on_wifi_disconnected(self, addr: str):
        print(f"[CommService] WiFi 客户端已断开: {addr}")
        self.wifi_client_disconnected.emit(addr)

    # --------------------------------------------------------------------------
    # 便捷查询接口
    # --------------------------------------------------------------------------

    def has_any_client(self) -> bool:
        """是否有任一 App 客户端连接（BLE / WiFi）"""
        return self.ble_server.has_connected_client() or self.wifi_server.has_connected_client()

    def get_channel_status(self) -> dict:
        """获取通道状态摘要"""
        return {
            "ble_connected": self.ble_server.has_connected_client(),
            "wifi_connected": self.wifi_server.has_connected_client(),
            "mqtt_connected": self.mqtt_bridge._connected,
            "buffer_count": self.buffer_queue.size(),
            "ride_state": self.ride_state.value,
        }
