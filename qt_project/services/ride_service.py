#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
骑行会话管理服务 (RideService)

职责：
- 管理骑行生命周期：开始 / 暂停 / 恢复 / 结束
- 实时计算骑行统计：时间、距离、速度、功率、心率、爬升、卡路里
- 与 RideRepository 联动写入轨迹点（由外部注入）
- 与 CommService 同步骑行状态
"""

import time
from typing import Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from core.protocol import SensorData, RideSessionState, RideSummary, TrackPoint, GPSPoint
from persistence.config_manager import get_config
from persistence.ride_repository import RideRepository


class RideService(QObject):
    """骑行会话管理器"""

    # 骑行生命周期事件
    ride_started = pyqtSignal(RideSummary)   # 开始新骑行，带回初始摘要
    ride_paused = pyqtSignal()               # 暂停
    ride_resumed = pyqtSignal()              # 恢复
    ride_stopped = pyqtSignal(RideSummary)   # 结束，带回最终摘要

    # 状态与统计更新
    state_changed = pyqtSignal(str)          # 状态字符串变化
    stats_updated = pyqtSignal(RideSummary)  # 每秒更新当前统计

    def __init__(self, parent=None, ride_repo: RideRepository = None):
        super().__init__(parent)
        self.config = get_config()
        self.ride_repo = ride_repo

        self.state = RideSessionState.IDLE
        self.summary = RideSummary()

        # 骑行会话内部计时与基准
        self._start_time: float = 0.0           # 本次骑行开始时间戳
        self._pause_start_time: float = 0.0     # 进入暂停的时间戳
        self._total_pause_time: float = 0.0     # 累计暂停时长（秒）
        self._last_tick_time: float = 0.0       # 上次 timer tick 时间
        self._last_sensor_time: float = 0.0     # 上次收到传感器数据的时间（0 表示尚未收到）
        self._initial_altitude: Optional[float] = None  # 初始海拔基准值
        self._current_speed: float = 0.0            # 当前速度，用于 tick 中累加距离
        self._last_lat: Optional[float] = None      # 上次纬度
        self._last_lon: Optional[float] = None      # 上次经度
        self._location_moved: bool = False          # 本周期内位置是否发生变化

        # 用于计算平均值的数据累加器
        self._speed_sum: float = 0.0            # 速度总和
        self._speed_count: int = 0              # 速度数据点数
        self._power_sum: float = 0.0            # 功率总和
        self._power_count: int = 0              # 功率数据点数
        self._hr_sum: float = 0.0               # 心率总和
        self._hr_count: int = 0                 # 心率数据点数

        # 轨迹点缓存（用于生成 FIT/GPX）
        self._track_points: List[TrackPoint] = []

        # 定时器：每秒刷新统计并发射 stats_updated
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(1000)

    # --------------------------------------------------------------------------
    # 公开控制接口
    # --------------------------------------------------------------------------

    def start_ride(self) -> bool:
        """开始骑行"""
        if self.state in (RideSessionState.RIDING, RideSessionState.PAUSED):
            return False  # 已经在骑行中

        now = time.time()
        self.state = RideSessionState.RIDING
        self._start_time = now
        self._pause_start_time = 0.0
        self._total_pause_time = 0.0
        self._last_tick_time = now
        self._last_sensor_time = now
        self._initial_altitude = None
        self._speed_sum = 0.0
        self._speed_count = 0
        self._power_sum = 0.0
        self._power_count = 0
        self._hr_sum = 0.0
        self._hr_count = 0
        self._current_speed = 0.0
        self._last_lat = None
        self._last_lon = None
        self._location_moved = False
        self._track_points = []

        self.summary = RideSummary(
            start_time=now,
            end_time=0.0,
            total_distance=0.0,
            total_time=0,
            moving_time=0,
            avg_speed=0.0,
            max_speed=0.0,
            avg_power=0.0,
            max_power=0.0,
            avg_hr=0.0,
            max_hr=0.0,
            total_elevation_gain=0.0,
            max_elevation_gain=0.0,
            calories=0.0,
            file_path="",
        )

        self.state_changed.emit(self.state.value)
        self.stats_updated.emit(self.summary)
        self.ride_started.emit(self.summary)
        return True

    def pause_ride(self) -> bool:
        """暂停骑行"""
        if self.state != RideSessionState.RIDING:
            return False

        self.state = RideSessionState.PAUSED
        self._pause_start_time = time.time()
        self.state_changed.emit(self.state.value)
        self.ride_paused.emit()
        return True

    def resume_ride(self) -> bool:
        """恢复骑行"""
        if self.state != RideSessionState.PAUSED:
            return False

        self._total_pause_time += time.time() - self._pause_start_time
        self._pause_start_time = 0.0
        self.state = RideSessionState.RIDING
        now = time.time()
        self._last_tick_time = now
        self._last_sensor_time = now
        self.state_changed.emit(self.state.value)
        self.ride_resumed.emit()
        return True

    def stop_ride(self) -> bool:
        """结束骑行"""
        if self.state == RideSessionState.IDLE:
            return False

        # 若当前在暂停中，先把暂停时间算进去
        if self.state == RideSessionState.PAUSED and self._pause_start_time > 0:
            self._total_pause_time += time.time() - self._pause_start_time
            self._pause_start_time = 0.0

        now = time.time()
        self.summary.end_time = now
        self.summary.total_time = int(now - self._start_time)
        self.summary.moving_time = int(self.summary.moving_time)  # 取整

        # 结束前的最终统计计算
        if self._speed_count > 0:
            self.summary.avg_speed = round(self._speed_sum / self._speed_count, 1)
        if self._power_count > 0:
            self.summary.avg_power = round(self._power_sum / self._power_count, 0)
        if self._hr_count > 0:
            self.summary.avg_hr = round(self._hr_sum / self._hr_count, 0)
        weight = self.config.get("weight_kg", 70)
        self.summary.calories = round(weight * self.summary.total_distance * 1.036, 0)

        # 保存骑行记录（FIT + GPX）
        ride_id = ""
        if self.ride_repo:
            try:
                ride_id = self.ride_repo.save_ride(self.summary, self._track_points)
                self.summary.id = ride_id
                print(f"[RideService] 骑行记录已保存: {ride_id}, 轨迹点数: {len(self._track_points)}")
            except Exception as e:
                print(f"[RideService] 保存骑行记录失败: {e}")
                import traceback
                traceback.print_exc()

        self.state = RideSessionState.FINISHED
        self.state_changed.emit(self.state.value)
        self.ride_stopped.emit(self.summary)
        return True

    # --------------------------------------------------------------------------
    # 数据入口
    # --------------------------------------------------------------------------

    def on_sensor_data(self, sensor: SensorData):
        """接收 STM32 传感器数据，更新统计（距离基于速度积分）"""
        now = time.time()

        if self.state not in (RideSessionState.RIDING, RideSessionState.PAUSED):
            # IDLE / FINISHED 状态下只更新时间戳，不积分
            self._last_sensor_time = now
            return

        # 即使 PAUSED，也同步 end_time 和 total_time（用于 UI 显示总时长）
        self.summary.end_time = now
        self.summary.total_time = int(now - self._start_time)

        # 只有 RIDING 状态才积分和更新动态统计
        if self.state != RideSessionState.RIDING:
            self._last_sensor_time = now
            return

        # 更新当前速度（用于每秒 tick 累加距离）
        self._current_speed = sensor.speed
        self._last_sensor_time = now

        # 位置变化检测（有 GPS 且坐标有效时）
        if sensor.location and sensor.location.lat and sensor.location.lon:
            if self._last_lat is not None:
                if (abs(sensor.location.lat - self._last_lat) > 1e-6 or
                        abs(sensor.location.lon - self._last_lon) > 1e-6):
                    self._location_moved = True
            else:
                self._location_moved = True
            self._last_lat = sensor.location.lat
            self._last_lon = sensor.location.lon

        # 最大速度 / 功率 / 心率
        if sensor.speed > self.summary.max_speed:
            self.summary.max_speed = sensor.speed
        if sensor.power > self.summary.max_power:
            self.summary.max_power = sensor.power
        if sensor.heart_rate > self.summary.max_hr:
            self.summary.max_hr = sensor.heart_rate

        # 平均功率 / 心率累加
        self._power_sum += sensor.power
        self._power_count += 1
        self._hr_sum += sensor.heart_rate
        self._hr_count += 1

        # 平均速度 = 速度采样算术平均（只有收到新数据时才变化）
        self._speed_sum += sensor.speed
        self._speed_count += 1
        if self._speed_count > 0:
            self.summary.avg_speed = round(self._speed_sum / self._speed_count, 1)

        # 海拔爬升（基于初始海拔基准）
        if sensor.location and sensor.location.altitude:
            altitude = sensor.location.altitude
            if self._initial_altitude is None:
                self._initial_altitude = altitude
            gain = altitude - self._initial_altitude
            if gain > 0:
                self.summary.total_elevation_gain = round(gain, 1)
                if gain > self.summary.max_elevation_gain:
                    self.summary.max_elevation_gain = round(gain, 1)

        # 轨迹点采样（有 GPS 且坐标有效时记录）
        if sensor.location and sensor.location.lat and sensor.location.lon:
            tp = TrackPoint(
                gps=GPSPoint(
                    lat=sensor.location.lat,
                    lon=sensor.location.lon,
                    altitude=sensor.location.altitude or 0.0,
                    timestamp=now
                ),
                speed=sensor.speed,
                power=sensor.power,
                cadence=sensor.cadence,
                heart_rate=sensor.heart_rate,
                altitude=sensor.location.altitude or 0.0
            )
            self._track_points.append(tp)

        # 收到传感器数据后实时刷新 UI（避免等下一秒 tick）
        self.stats_updated.emit(self.summary)

    # --------------------------------------------------------------------------
    # 定时 tick：刷新时间、均速、卡路里
    # --------------------------------------------------------------------------

    def _on_tick(self):
        if self.state != RideSessionState.RIDING:
            return

        now = time.time()
        delta = now - self._last_tick_time
        self._last_tick_time = now

        # 移动时间：只要状态是 RIDING 就累加
        self.summary.moving_time += delta

        # 骑行距离：当前速度 × 时间间隔（仅当位置发生变化时才累加）
        if self._location_moved:
            self.summary.total_distance += self._current_speed * delta / 3600.0
            self._location_moved = False

        # 实时平均功率 / 心率
        if self._power_count > 0:
            self.summary.avg_power = round(self._power_sum / self._power_count, 0)
        if self._hr_count > 0:
            self.summary.avg_hr = round(self._hr_sum / self._hr_count, 0)
        # 平均速度在 on_sensor_data 中基于采样算术平均计算，无新数据时保持不变

        # 卡路里（简单公式：kcal = weight(kg) * distance(km) * 1.036）
        weight = self.config.get("weight_kg", 70)
        self.summary.calories = round(weight * self.summary.total_distance * 1.036, 0)

        self.stats_updated.emit(self.summary)

    # --------------------------------------------------------------------------
    # 查询接口
    # --------------------------------------------------------------------------

    def get_state(self) -> RideSessionState:
        return self.state

    def get_summary(self) -> RideSummary:
        return self.summary

    def is_riding(self) -> bool:
        return self.state == RideSessionState.RIDING

    def format_moving_time(self) -> str:
        """返回 hh:mm:ss 格式的移动时间"""
        t = int(self.summary.moving_time)
        h = t // 3600
        m = (t % 3600) // 60
        s = t % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
