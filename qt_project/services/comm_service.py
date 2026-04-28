#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通信调度器（CommService）— xinjia.txt 协议集成版

职责：
- 统一调度 BLE、MQTT 两条通信通道（WebSocket 已删除）
- 接收 STM32 高频传感器数据，合并为 1Hz 低频 App 数据包
- 实时数据定时推（1秒1次）+ 事件数据立即推
- 断连期间缓存数据，重连后自动补发
- 将 App 命令转发给主程序

MQTT 主题（xinjia.txt）：
- deviceData_1   : 实时数据推送（每秒）
- delayData_1    : 非实时数据/事件推送
- deviceHeart_1  : 设备心跳（每5秒）+ 连接握手
- appHeart_1     : 接收 App 心跳/连接请求
- appData_1      : 接收 App 命令

BLE：
- JSON 透传，协议格式与 MQTT 一致
- 连接成功后发送 {"isConnect":"OK"}
- 心跳每5秒 {"type":"heartbeat","timestamp":"...","device":"SMART-RIDE","channel":"ble"}
"""

import json
import os
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
from persistence.buffer_queue import BufferQueue
from persistence.ride_repository import RideRepository


# ==============================================================================
# MQTT 桥接器（xinjia.txt 协议）
# ==============================================================================

class MqttBridge:
    """
    MQTT 通信桥接器
    - 发布实时数据到 deviceData_1
    - 发布事件/非实时数据到 delayData_1
    - 发布心跳到 deviceHeart_1
    - 订阅 appHeart_1 接收 App 连接请求
    - 订阅 appData_1 接收 App 命令
    """

    def __init__(
        self,
        broker: str = "broker.emqx.io",
        port: int = 1883,
        client_id: Optional[str] = None,
        on_command: Optional[Callable[[str, str], None]] = None,
        on_connected: Optional[Callable[[], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
        on_app_connect: Optional[Callable[[], None]] = None,
    ):
        self.broker = broker
        self.port = port
        self.client_id = client_id or f"smartride-pi5-{uuid.uuid4().hex[:8]}"
        self.on_command = on_command
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self.on_app_connect = on_app_connect  # App 通过 appHeart_1 发来连接请求
        self._client = None
        self._connected = False
        self._app_connected = False  # App 是否已握手连接

        # xinjia.txt 协议主题
        self._topics = {
            "deviceData": "deviceData_1",
            "delayData": "delayData_1",
            "deviceHeart": "deviceHeart_1",
            "appHeart": "appHeart_1",
            "appData": "appData_1",
        }

    def start(self):
        try:
            import paho.mqtt.client as mqtt

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

            try:
                self._client.reconnect_delay_set(min_delay=1, max_delay=15)
            except Exception:
                pass

            self._client.connect(self.broker, self.port, 60)
            self._client.loop_start()
            print(f"[MqttBridge] MQTT 连接启动: {self.broker}:{self.port}")

        except ImportError:
            print("[MqttBridge] 警告: paho-mqtt 未安装，MQTT 通道不可用")
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
            self._app_connected = False

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
            rc = getattr(result, "rc", None)
            rc_val = rc.value if hasattr(rc, "value") else rc
            if rc is not None and rc != 0:
                print(f"[MqttBridge] 发布队列异常 [{topic}] rc={rc_val}")
        except Exception as e:
            print(f"[MqttBridge] 发布失败 [{topic}]: {e}")

    def _on_connect(self, client, userdata, flags, rc, *args):
        rc_val = getattr(rc, "value", rc) if hasattr(rc, "value") else rc
        if rc == 0:
            self._connected = True
            print(f"[MqttBridge] MQTT 连接成功 (client_id={client._client_id})")
            try:
                client.subscribe(self._topics["appHeart"])
                client.subscribe(self._topics["appData"])
                print(f"[MqttBridge] 已订阅: {self._topics['appHeart']}, {self._topics['appData']}")
            except Exception as e:
                print(f"[MqttBridge] 订阅失败: {e}")
            # 注意：心跳由 CommService 管理，不在此处启动
            if self.on_connected:
                try:
                    self.on_connected()
                except Exception:
                    pass
        else:
            print(f"[MqttBridge] MQTT 连接失败，返回码: {rc_val}")

    def _on_disconnect(self, client, userdata, disconnect_flags, rc, properties=None):
        self._connected = False
        self._app_connected = False
        rc_val = getattr(rc, "value", rc) if hasattr(rc, "value") else rc
        print(f"[MqttBridge] MQTT 已断开 (rc={rc_val})")
        if self.on_disconnected:
            try:
                self.on_disconnected()
            except Exception:
                pass

    def _on_message(self, client, userdata, msg):
        try:
            text = msg.payload.decode("utf-8", errors="ignore").strip()
            if not text:
                return
            topic = msg.topic
            print(f"[MqttBridge] 收到 [{topic}]: {text}")

            # App 心跳/连接请求
            if topic == self._topics["appHeart"]:
                try:
                    data = json.loads(text)
                    if data.get("isConnect") == "OK":
                        # App 请求连接，回复确认
                        self._app_connected = True
                        self.publish("deviceHeart", {"isConnect": "OK"})
                        print("[MqttBridge] App 已连接（握手成功）")
                        # 心跳由 CommService 通过 app_connected 信号管理
                        if self.on_app_connect:
                            self.on_app_connect()
                except Exception as e:
                    print(f"[MqttBridge] appHeart 解析失败: {e}")
                return

            # App 命令
            if topic == self._topics["appData"] and self.on_command:
                self.on_command(text, channel="mqtt")

        except Exception as e:
            print(f"[MqttBridge] 消息处理失败: {e}")

    def is_app_connected(self) -> bool:
        """App 是否已通过握手连接"""
        return self._app_connected

    def disconnect_app(self):
        """主动断开 App 连接（心跳由 CommService 停止）"""
        self._app_connected = False
        self.publish("deviceHeart", {"isConnect": "OK"})
        print("[MqttBridge] 已发送断开通知")


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
        if not self._buffer:
            return AppRealtimeData(ride_state=ride_state.value)
        latest = self._buffer[-1]
        n = len(self._buffer)
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
    mqtt_connected = pyqtSignal()
    mqtt_disconnected = pyqtSignal()
    app_connected = pyqtSignal(str)      # 参数: "mqtt" 或 "ble"
    app_disconnected = pyqtSignal(str)   # 参数: "mqtt" 或 "ble"

    # 内部状态变化
    data_pushed = pyqtSignal(AppRealtimeData)
    event_pushed = pyqtSignal(str, dict)

    def __init__(self, parent=None, ride_repo: Optional[RideRepository] = None):
        super().__init__(parent)
        self.ride_state = RideSessionState.IDLE
        self.ride_repo = ride_repo

        self.data_buffer = DataBuffer(window_seconds=1.0)
        self.buffer_queue = BufferQueue(max_items=5000, max_age_seconds=1800)

        self.ble_last_push_time = 0.0
        self.mqtt_last_push_time = 0.0

        # BLE 服务器（默认不启动，等用户点击"开始广播"）
        self.ble_server = BleServer(host_address="2C:CF:67:F2:ED:B2", port=1)

        # MQTT 桥接器
        self.mqtt_bridge = MqttBridge(
            broker="broker.emqx.io",
            port=1883,
            client_id=None,
            on_command=self._on_mqtt_command,
            on_connected=lambda: self.mqtt_connected.emit(),
            on_disconnected=lambda: (self.mqtt_disconnected.emit(), self.app_disconnected.emit("mqtt")),
            on_app_connect=lambda: self._on_app_connect("mqtt"),
        )

        # BLE 信号绑定
        self.ble_server.client_connected.connect(self._on_ble_connected)
        self.ble_server.client_disconnected.connect(self._on_ble_disconnected)
        self.ble_server.command_received.connect(self._on_ble_command)
        self.ble_server.error_occurred.connect(lambda e: print(f"[CommService] BLE错误: {e}"))

        # BLE 心跳定时器
        self._ble_heartbeat_timer = QTimer(self)
        self._ble_heartbeat_timer.timeout.connect(self._send_ble_heartbeat)

        # MQTT 心跳定时器（放在 CommService 中确保在主线程创建）
        self._mqtt_heartbeat_timer = QTimer(self)
        self._mqtt_heartbeat_timer.timeout.connect(self._send_mqtt_heartbeat)

        # app_connected 信号在主线程触发，安全启动心跳
        self.app_connected.connect(self._on_app_connected_for_heartbeat)
        self.app_disconnected.connect(self._on_app_disconnected_for_heartbeat)

        self._servers_started = False
        self._ble_started = False

    def start(self):
        """启动 MQTT 服务（BLE 等用户点击按钮后再启动）"""
        if self._servers_started:
            return
        print("[CommService] 启动通信服务...")
        self.mqtt_bridge.start()
        self._servers_started = True

    def start_ble(self):
        """启动 BLE 广播（由连接页面的'开始广播'按钮触发）"""
        if self._ble_started:
            return
        print("[CommService] 启动 BLE 广播...")
        self.ble_server.start_advertising()
        self._ble_started = True

    def stop(self):
        """停止所有通信服务"""
        print("[CommService] 停止通信服务...")
        self._ble_heartbeat_timer.stop()
        self._mqtt_heartbeat_timer.stop()
        self.ble_server.stop()
        self.mqtt_bridge.stop()
        self._servers_started = False
        self._ble_started = False

    # --------------------------------------------------------------------------
    # 数据入口
    # --------------------------------------------------------------------------

    def on_sensor_data(self, sensor: SensorData):
        """收到串口数据立即推送（不再定时发，避免空数据）"""
        if self._is_empty_data(sensor):
            return
        payload = self._build_realtime_payload_from_sensor(sensor)
        self._send_realtime_payload(payload)

    @staticmethod
    def _is_empty_data(sensor: SensorData) -> bool:
        """判断是否为全0空数据"""
        return (
            sensor.speed == 0.0
            and sensor.cadence == 0.0
            and sensor.power == 0.0
            and sensor.heart_rate == 0.0
            and sensor.slope == 0.0
            and sensor.temperature == 0.0
            and sensor.rear_dist == 0.0
        )

    def set_ride_state(self, state: RideSessionState):
        old_state = self.ride_state
        self.ride_state = state
        if old_state != state:
            self._push_event("ride_state_changed", {
                "old": old_state.value,
                "new": state.value,
            })

    # --------------------------------------------------------------------------
    # 实时数据推送（收到即发）
    # --------------------------------------------------------------------------

    def _send_realtime_payload(self, payload: dict):
        """推送实时数据到所有可用通道"""
        now = time.time()
        pushed_count = 0

        # BLE
        if self.ble_server.has_connected_client():
            try:
                self.ble_server.notify(json.dumps(payload, ensure_ascii=False))
                self.ble_last_push_time = now
                pushed_count += 1
            except Exception as e:
                print(f"[CommService] BLE推送失败: {e}")

        # MQTT
        if self.mqtt_bridge.is_app_connected():
            try:
                self.mqtt_bridge.publish("deviceData", payload)
                self.mqtt_last_push_time = now
                pushed_count += 1
            except Exception as e:
                print(f"[CommService] MQTT推送失败: {e}")

        if pushed_count == 0:
            print("[CommService] 所有通道断开，数据已缓存")

    def _build_realtime_payload_from_sensor(self, sensor: SensorData) -> dict:
        """从 SensorData 直接构建 xinjia.txt 实时数据消息体"""
        t = time.strftime("%H:%M:%S", time.localtime())
        return {
            "type": "realtime",
            "timestamp": t,
            "data": {
                "speed": sensor.speed,
                "cadence": sensor.cadence,
                "power": sensor.power,
                "heart_rate": sensor.heart_rate,
                "slope": sensor.slope,
                "temperature": sensor.temperature,
                "rear_dist": sensor.rear_dist,
                "gps": sensor.location.to_dict() if sensor.location else {"lat": 0.0, "lon": 0.0},
            }
        }

    @staticmethod
    def _get_alert_type(name: str):
        from core.protocol import AlertType
        try:
            return AlertType(name)
        except ValueError:
            return AlertType.REAR_VEHICLE

    def send_alert(self, alert_type, message: str, level: str = "warning"):
        """推送告警事件（alert_type 可以是 AlertType 枚举或字符串）"""
        if isinstance(alert_type, str):
            payload = {
                "type": alert_type,
                "message": message,
                "level": level,
                "timestamp": time.time(),
            }
        else:
            from core.protocol import build_alert_payload
            payload = build_alert_payload(alert_type, message, level)
        self._push_event("alert", payload)

    def _push_event(self, event_type: str, payload: dict):
        self.event_pushed.emit(event_type, payload)
        t = time.strftime("%H:%M:%S", time.localtime())

        # BLE
        if self.ble_server.has_connected_client():
            try:
                event_payload = {
                    "type": "event",
                    "timestamp": t,
                    "event": event_type,
                    "data": payload,
                }
                self.ble_server.notify(json.dumps(event_payload, ensure_ascii=False))
            except Exception as e:
                print(f"[CommService] BLE事件推送失败: {e}")

        # MQTT
        if self.mqtt_bridge.is_app_connected():
            try:
                event_payload = {
                    "type": "event",
                    "timestamp": t,
                    "event": event_type,
                    "data": payload,
                }
                self.mqtt_bridge.publish("delayData", event_payload)
            except Exception as e:
                print(f"[CommService] MQTT事件推送失败: {e}")

    def _flush_buffer_for_channel(self, channel: str):
        if self.buffer_queue.is_empty():
            return
        time_map = {
            "ble": self.ble_last_push_time,
            "mqtt": self.mqtt_last_push_time,
        }
        cutoff = time_map.get(channel, 0)
        if cutoff <= 0:
            return
        items = self.buffer_queue.get_since(cutoff)
        if not items:
            return
        print(f"[CommService] [{channel}] 补发缓存数据: {len(items)} 条")
        BATCH_SIZE = 50
        for i in range(0, len(items), BATCH_SIZE):
            batch = items[i:i + BATCH_SIZE]
            batch_payload = {"type": "buffer_sync", "timestamp": time.strftime("%H:%M:%S"), "data": batch}
            batch_json = json.dumps(batch_payload, ensure_ascii=False)
            try:
                if channel == "ble" and self.ble_server.has_connected_client():
                    self.ble_server.notify(batch_json)
                elif channel == "mqtt" and self.mqtt_bridge.is_app_connected():
                    self.mqtt_bridge.publish("delayData", batch_payload)
            except Exception as e:
                print(f"[CommService] [{channel}] 补发失败: {e}")
                return
        if items:
            latest_ts = items[-1].get("timestamp", time.time())
            if channel == "ble":
                self.ble_last_push_time = latest_ts
            elif channel == "mqtt":
                self.mqtt_last_push_time = latest_ts

    # --------------------------------------------------------------------------
    # 命令接收与转发
    # --------------------------------------------------------------------------

    def _on_ble_command(self, text: str):
        self._handle_command(text, channel="ble")

    def _on_mqtt_command(self, text: str, channel: str = "mqtt"):
        self._handle_command(text, channel="mqtt")

    def _handle_command(self, text: str, channel: str):
        try:
            cmd = AppCommand.from_json(text)
            print(f"[CommService] 收到 [{channel}] 命令: {cmd.cmd_type.value}")

            if cmd.cmd_type.value == "request_history":
                self._handle_request_history()
                return
            if cmd.cmd_type.value == "request_fit":
                self._handle_request_file(cmd.payload, "fit")
                return
            if cmd.cmd_type.value == "request_gpx":
                self._handle_request_file(cmd.payload, "gpx")
                return

            self.command_received.emit(cmd)
        except Exception as e:
            print(f"[CommService] 命令解析失败: {e}, 原文: {text}")

    def _handle_request_history(self):
        if not self.ride_repo:
            self._reply_json({"type": "history", "timestamp": time.strftime("%H:%M:%S"), "data": [], "error": "repo not ready"})
            return
        rides = self.ride_repo.list_rides(limit=50)
        self._reply_json({"type": "history", "timestamp": time.strftime("%H:%M:%S"), "data": rides})

    def _handle_request_file(self, payload: dict, ext: str):
        ride_id = payload.get("ride_id", "")
        if not ride_id or not self.ride_repo:
            self._reply_json({"type": "file_response", "timestamp": time.strftime("%H:%M:%S"), "error": "missing ride_id or repo"})
            return
        meta = self.ride_repo.get_ride(ride_id)
        if not meta:
            self._reply_json({"type": "file_response", "timestamp": time.strftime("%H:%M:%S"), "error": "ride not found"})
            return
        path_key = f"{ext}_path"
        file_path = meta.get(path_key, "")
        if not file_path or not os.path.exists(file_path):
            self._reply_json({"type": "file_response", "timestamp": time.strftime("%H:%M:%S"), "error": f"{ext} file not found"})
            return
        try:
            import base64
            with open(file_path, "rb") as f:
                data = f.read()
            encoded = base64.b64encode(data).decode("utf-8")
            self._reply_json({
                "type": "file_response",
                "timestamp": time.strftime("%H:%M:%S"),
                "file_type": ext,
                "ride_id": ride_id,
                "filename": os.path.basename(file_path),
                "size": len(data),
                "data": encoded,
            })
            print(f"[CommService] 已发送 {ext.upper()} 文件: {os.path.basename(file_path)} ({len(data)} bytes)")
        except Exception as e:
            self._reply_json({"type": "file_response", "timestamp": time.strftime("%H:%M:%S"), "error": str(e)})

    def _reply_json(self, payload: dict):
        if self.ble_server.has_connected_client():
            self.ble_server.notify(json.dumps(payload, ensure_ascii=False))
        if self.mqtt_bridge.is_app_connected():
            self.mqtt_bridge.publish("delayData", payload)

    # --------------------------------------------------------------------------
    # 连接状态回调
    # --------------------------------------------------------------------------

    def _on_ble_connected(self, addr: str):
        print(f"[CommService] BLE 客户端已连接: {addr}")
        # 发送握手帧
        try:
            self.ble_server.notify('{"isConnect":"OK"}')
        except Exception as e:
            print(f"[CommService] BLE握手发送失败: {e}")
        self._on_app_connect("ble")
        self.ble_client_connected.emit(addr)
        self._flush_buffer_for_channel("ble")
        # 启动 BLE 心跳
        self._ble_heartbeat_timer.start(5000)
        self._send_ble_heartbeat()

    def _on_ble_disconnected(self):
        print("[CommService] BLE 客户端已断开")
        self._ble_heartbeat_timer.stop()
        self.app_disconnected.emit("ble")
        self.ble_client_disconnected.emit()

    def _on_app_connect(self, channel: str):
        """App 已通过任一通道连接"""
        print(f"[CommService] App 已通过 [{channel}] 连接")
        self.app_connected.emit(channel)

    def _send_ble_heartbeat(self):
        """发送 BLE 心跳"""
        if not self.ble_server.has_connected_client():
            return
        payload = {
            "type": "heartbeat",
            "timestamp": time.strftime("%H:%M:%S"),
            "device": "SMART-RIDE",
            "channel": "ble",
        }
        try:
            self.ble_server.notify(json.dumps(payload, ensure_ascii=False))
        except Exception as e:
            print(f"[CommService] BLE心跳发送失败: {e}")

    # --------------------------------------------------------------------------
    # 便捷查询接口
    # --------------------------------------------------------------------------

    def has_any_client(self) -> bool:
        return self.ble_server.has_connected_client() or self.mqtt_bridge.is_app_connected()

    def get_channel_status(self) -> dict:
        return {
            "ble_connected": self.ble_server.has_connected_client(),
            "mqtt_connected": self.mqtt_bridge._connected,
            "app_mqtt_connected": self.mqtt_bridge.is_app_connected(),
            "buffer_count": self.buffer_queue.size(),
            "ride_state": self.ride_state.value,
        }

    def disconnect_app(self):
        """主动断开 App 连接"""
        if self.mqtt_bridge.is_app_connected():
            self.mqtt_bridge.disconnect_app()
            self.app_disconnected.emit("mqtt")
        if self.ble_server.has_connected_client():
            try:
                self.ble_server.notify('{"isConnect":"OK"}')
            except Exception:
                pass
            self.app_disconnected.emit("ble")

    def _on_app_connected_for_heartbeat(self, channel: str):
        """App 连接成功后启动对应通道的心跳（在主线程执行）"""
        if channel == "mqtt" and not self._mqtt_heartbeat_timer.isActive():
            self._mqtt_heartbeat_timer.start(5000)
            self._send_mqtt_heartbeat()
            print("[CommService] MQTT 心跳已启动")

    def _on_app_disconnected_for_heartbeat(self, channel: str):
        """App 断开后停止对应通道的心跳"""
        if channel == "mqtt" and self._mqtt_heartbeat_timer.isActive():
            self._mqtt_heartbeat_timer.stop()
            print("[CommService] MQTT 心跳已停止")

    def _send_mqtt_heartbeat(self):
        """发送 MQTT 心跳（每5秒由定时器触发）"""
        if self.mqtt_bridge.is_app_connected():
            self.mqtt_bridge.publish("deviceHeart", {"isConnect": "continue"})
            print("[CommService] MQTT 心跳已发送")
        else:
            self._mqtt_heartbeat_timer.stop()
            print("[CommService] MQTT App 已断开，停止心跳")
