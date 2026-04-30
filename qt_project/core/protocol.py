#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMART RIDE 统一数据协议定义

用途：
1. 规范 STM32 → 树莓派 的数据格式
2. 规范 树莓派 ↔ App 的通信格式
3. 提供协议转换工具（BLE GATT / WiSocket / FIT / GPX）
"""

import json
import struct
import time
from dataclasses import dataclass, asdict, field
from enum import Enum, IntEnum
from typing import Optional, Dict, Any, List


# ==============================================================================
# 一、枚举定义
# ==============================================================================

class RideSessionState(Enum):
    """骑行会话状态"""
    IDLE = "idle"           # 未开始
    RIDING = "riding"       # 骑行中
    PAUSED = "paused"       # 暂停中
    FINISHED = "finished"   # 已结束


class AppCommandType(Enum):
    """App 发给树莓派的命令类型（xinjia.txt 协议）"""
    START_RIDE = "start_ride"
    PAUSE_RIDE = "pause_ride"
    RESUME_RIDE = "resume_ride"
    STOP_RIDE = "stop_ride"
    SET_TARGET = "set_target"
    LOAD_ROUTE = "load_route"
    REQUEST_HISTORY = "request_history"
    REQUEST_FIT = "request_fit"
    REQUEST_GPX = "request_gpx"
    UPDATE_CONFIG = "update_config"
    PING = "ping"
    # xinjia.txt 新增命令
    SET_THRESHOLD = "set_threshold"
    SET_ALERT_SWITCH = "set_alert_switch"
    SET_NAV_DESTINATION = "set_nav_destination"
    SET_RIDE_STATE = "set_ride_state"


class AlertType(Enum):
    """安全告警类型"""
    REAR_VEHICLE = "rear_vehicle"       # 后方来车
    HEART_RATE_HIGH = "heart_rate_high" # 心率过高
    HEART_RATE_LOW = "heart_rate_low"   # 心率过低
    FATIGUE = "fatigue"                 # 疲劳提醒
    FALL_DETECTED = "fall_detected"     # 摔车检测
    OFF_ROUTE = "off_route"             # 偏离路线


# ==============================================================================
# 二、基础数据结构
# ==============================================================================

@dataclass
class GPSPoint:
    """GPS 坐标点"""
    lat: float = 0.0      # 纬度
    lon: float = 0.0      # 经度
    altitude: float = 0.0 # 海拔（米）
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "altitude": self.altitude,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GPSPoint":
        return cls(
            lat=d.get("lat", 0.0),
            lon=d.get("lon", 0.0),
            altitude=d.get("altitude", 0.0),
            timestamp=d.get("timestamp", time.time()),
        )


@dataclass
class SensorData:
    """
    STM32 → 树莓派 的传感器数据包（当前 JSON 协议）

    对应 STM32 通过串口发来的 JSON 数据，字段必须向后兼容。
    """
    speed: float = 0.0           # 速度 km/h
    cadence: float = 0.0         # 踏频 rpm
    power: float = 0.0           # 功率 W
    distance: float = 0.0        # 距离 km
    ride_time: int = 0           # 骑行时间秒
    slope: float = 0.0           # 坡度 %
    zt_flag: int = 5             # 骑行状态标志（0跌倒 1右转弯 2左转弯 3上坡 4下坡 5正常骑行）
    yaw: float = 0.0             # IMU 航偏角，0°指北，顺时针增加
    temperature: float = 0.0     # 温度 °C
    heart_rate: float = 0.0      # 心率 bpm
    rear_dist: float = 0.0       # 后方距离 m
    err_code: int = 0            # 错误码（0=正常）
    location: Optional[GPSPoint] = None
    received_at: float = field(default_factory=time.time)

    @classmethod
    def from_stm32_json(cls, raw: Dict[str, Any]) -> "SensorData":
        """从 STM32 发来的原始 JSON 字典解析"""
        loc = raw.get("location")
        gps = GPSPoint.from_dict(loc) if isinstance(loc, dict) else None
        return cls(
            speed=float(raw.get("speed", 0.0)),
            cadence=float(raw.get("cadence", 0.0)),
            power=float(raw.get("power", 0.0)),
            distance=float(raw.get("distance", 0.0)),
            ride_time=int(raw.get("ride_time", 0)),
            slope=float(raw.get("slope", 0.0)),
            zt_flag=int(raw.get("zt_flag", 5)),
            yaw=float(raw.get("yaw", 0.0)),
            temperature=float(raw.get("temperature", 0.0)),
            heart_rate=float(raw.get("heart_rate", 0.0)),
            rear_dist=float(raw.get("rear_dist", 0.0)),
            err_code=int(raw.get("err_code", 0)),
            location=gps,
            received_at=time.time(),
        )

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "speed": self.speed,
            "cadence": self.cadence,
            "power": self.power,
            "distance": self.distance,
            "ride_time": self.ride_time,
            "slope": self.slope,
            "zt_flag": self.zt_flag,
            "yaw": self.yaw,
            "temperature": self.temperature,
            "heart_rate": self.heart_rate,
            "rear_dist": self.rear_dist,
            "err_code": self.err_code,
            "received_at": self.received_at,
        }
        if self.location:
            d["location"] = self.location.to_dict()
        return d


@dataclass
class RideSummary:
    """单次骑行的统计摘要"""
    id: str = ""                     # 骑行记录唯一 ID
    start_time: float = 0.0
    end_time: float = 0.0
    total_distance: float = 0.0      # km
    total_time: int = 0              # 秒（含暂停）
    moving_time: int = 0             # 秒（不含暂停）
    avg_speed: float = 0.0           # km/h
    max_speed: float = 0.0           # km/h
    avg_power: float = 0.0           # W
    max_power: float = 0.0           # W
    avg_hr: float = 0.0              # bpm
    max_hr: float = 0.0              # bpm
    total_elevation_gain: float = 0.0 # m（相对于初始海拔的当前爬升）
    max_elevation_gain: float = 0.0   # m（相对于初始海拔的最大爬升）
    calories: float = 0.0            # kcal
    file_path: str = ""              # 本地 FIT/GPX 文件路径

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# 三、App ↔ 树莓派 通信协议
# ==============================================================================

@dataclass
class AppCommand:
    """App 发送给树莓派的命令"""
    cmd_type: AppCommandType
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps({
            "cmd": self.cmd_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "AppCommand":
        d = json.loads(text)
        return cls(
            cmd_type=AppCommandType(d.get("cmd", "ping")),
            payload=d.get("payload", {}),
            timestamp=d.get("timestamp", time.time()),
        )


@dataclass
class AppRealtimeData:
    """
    树莓派实时推送给 App 的数据包
    用于 WiFi WebSocket 或 BLE Notify
    """
    speed: float = 0.0
    cadence: float = 0.0
    power: float = 0.0
    distance: float = 0.0
    heart_rate: float = 0.0
    slope: float = 0.0
    temperature: float = 0.0
    rear_dist: float = 0.0
    gps: Optional[GPSPoint] = None
    ride_state: str = RideSessionState.IDLE.value
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "speed": self.speed,
            "cadence": self.cadence,
            "power": self.power,
            "distance": self.distance,
            "heart_rate": self.heart_rate,
            "slope": self.slope,
            "temperature": self.temperature,
            "rear_dist": self.rear_dist,
            "ride_state": self.ride_state,
            "timestamp": self.timestamp,
        }
        if self.gps:
            d["gps"] = self.gps.to_dict()
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_ble_bytes(self) -> bytes:
        """
        压缩为 BLE 广播/Notify 字节流（小端模式，紧凑格式）
        格式：
          uint16  speed_x100      (km/h * 100)
          uint16  cadence
          uint16  power
          uint32  distance_x100   (km * 100)
          uint8   heart_rate
          int8    slope_x10       (坡度 * 10)
          int8    temperature
          uint8   ride_state      (0=idle, 1=riding, 2=paused)
          uint32  timestamp
        总长度：18 字节
        """
        state_map = {
            RideSessionState.IDLE.value: 0,
            RideSessionState.RIDING.value: 1,
            RideSessionState.PAUSED.value: 2,
            RideSessionState.FINISHED.value: 3,
        }
        return struct.pack(
            "<HHHIBbbBI",
            int(self.speed * 100),
            int(self.cadence),
            int(self.power),
            int(self.distance * 100),
            int(self.heart_rate),
            int(self.slope * 10),
            int(self.temperature),
            state_map.get(self.ride_state, 0),
            int(self.timestamp),
        )

    @classmethod
    def from_ble_bytes(cls, data: bytes) -> "AppRealtimeData":
        state_map = {0: "idle", 1: "riding", 2: "paused", 3: "finished"}
        unpacked = struct.unpack("<HHHIBbbBI", data)
        return cls(
            speed=unpacked[0] / 100.0,
            cadence=unpacked[1],
            power=unpacked[2],
            distance=unpacked[3] / 100.0,
            heart_rate=unpacked[4],
            slope=unpacked[5] / 10.0,
            temperature=unpacked[6],
            ride_state=state_map.get(unpacked[7], "idle"),
            timestamp=unpacked[8],
        )


@dataclass
class DeviceInfo:
    """设备信息（用于 BLE Read 或 App 握手）"""
    device_name: str = "SMART-RIDE"
    firmware_version: str = "1.0.0"
    hardware_version: str = "RPi5B"
    battery_percent: int = 100
    model_name: str = "SMART RIDE Pro"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# 四、标准 GATT 协议转换（让 App 像连普通传感器一样识别）
# ==============================================================================

class BleGattConverter:
    """
    将内部 SensorData 转换为标准蓝牙 GATT 协议字节流

    支持的协议：
    - Cycling Speed and Cadence (CSC) 0x1816
    - Cycling Power (CP) 0x1818
    - Heart Rate (HR) 0x180D
    """

    @staticmethod
    def to_csc_data(cadence: float, wheel_revs: int, last_wheel_event: int) -> bytes:
        """
        CSC Measurement (0x2A5B)
        flags + cumulative_wheel_revolutions + last_wheel_event_time +
        cumulative_crank_revolutions + last_crank_event_time
        """
        flags = 0x03  # 同时存在 Wheel & Crank 数据
        crank_revs = int(cadence)  # 简化为累计踏频数
        last_crank_event = last_wheel_event  # 简化
        return struct.pack(
            "<BIHHH",
            flags,
            wheel_revs,
            last_wheel_event,
            crank_revs,
            last_crank_event,
        )

    @staticmethod
    def to_power_data(power: float, cadence: float = 0) -> bytes:
        """
        Cycling Power Measurement (0x2A63)
        flags + instantaneous_power + accumulated_torque + ...
        这里做最小化实现，仅 flags + power
        """
        flags = 0x00  # 只有瞬时功率
        return struct.pack("<Hh", flags, int(power))

    @staticmethod
    def to_hr_data(heart_rate: float) -> bytes:
        """
        Heart Rate Measurement (0x2A37)
        flags(1字节) + heart_rate(1字节)
        """
        flags = 0x00  # 心率格式为 uint8，无传感器接触状态等
        return struct.pack("<BB", flags, int(heart_rate))


# ==============================================================================
# 五、FIT / GPX 轨迹点（用于持久化层）
# ==============================================================================

@dataclass
class TrackPoint:
    """单个轨迹点，用于写入 FIT/GPX"""
    gps: GPSPoint
    speed: float = 0.0       # km/h
    power: float = 0.0       # W
    cadence: float = 0.0     # rpm
    heart_rate: float = 0.0  # bpm
    altitude: float = 0.0    # m

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gps": self.gps.to_dict(),
            "speed": self.speed,
            "power": self.power,
            "cadence": self.cadence,
            "heart_rate": self.heart_rate,
            "altitude": self.altitude,
        }


# ==============================================================================
# 六、便捷工具函数
# ==============================================================================

def sensor_to_app_data(sensor: SensorData, ride_state: RideSessionState) -> AppRealtimeData:
    """将 STM32 传感器数据转换为对外实时数据"""
    return AppRealtimeData(
        speed=sensor.speed,
        cadence=sensor.cadence,
        power=sensor.power,
        distance=sensor.distance,
        heart_rate=sensor.heart_rate,
        slope=sensor.slope,
        temperature=sensor.temperature,
        rear_dist=sensor.rear_dist,
        gps=sensor.location,
        ride_state=ride_state.value,
        timestamp=sensor.received_at,
    )


def build_alert_payload(alert_type: AlertType, message: str, level: str = "warning") -> Dict[str, Any]:
    """构建安全告警 JSON 负载"""
    return {
        "type": alert_type.value,
        "message": message,
        "level": level,  # info / warning / critical
        "timestamp": time.time(),
    }


# ==============================================================================
# 七、协议版本常量
# ==============================================================================

PROTOCOL_VERSION = "1.0.0"
BLE_CUSTOM_SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"
BLE_CUSTOM_CHAR_NOTIFY = "0000ff01-0000-1000-8000-00805f9b34fb"
BLE_CUSTOM_CHAR_READ = "0000ff02-0000-1000-8000-00805f9b34fb"
BLE_CUSTOM_CHAR_WRITE = "0000ff03-0000-1000-8000-00805f9b34fb"


if __name__ == "__main__":
    # 简单测试
    sample_json = {
        "speed": 25.4,
        "cadence": 90,
        "power": 220,
        "distance": 15.25,
        "ride_time": 3600,
        "slope": 3.5,
        "posture": 0,
        "temperature": 26.5,
        "heart_rate": 145,
        "rear_dist": 12.5,
        "err_code": 0,
        "location": {"lat": 31.230416, "lon": 121.473701},
    }

    sensor = SensorData.from_stm32_json(sample_json)
    print("SensorData:", sensor.to_dict())

    app_data = sensor_to_app_data(sensor, RideSessionState.RIDING)
    print("AppRealtimeData JSON:", app_data.to_json())
    print("AppRealtimeData BLE bytes len:", len(app_data.to_ble_bytes()))

    cmd = AppCommand(AppCommandType.START_RIDE, payload={"target_power": 250})
    print("AppCommand JSON:", cmd.to_json())
