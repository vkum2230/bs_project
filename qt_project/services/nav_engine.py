#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线导航引擎 (NavEngine)

职责：
- 调用本地 Valhalla 服务进行离线路线规划
- 解析导航指令（maneuvers）并转为中文语音播报文本
- 计算当前位置在路线上的最近点及剩余距离
- 提供 turn-by-turn 导航状态跟踪
"""

import json
import math
import os
import subprocess
import time
import urllib.request
from typing import List, Tuple, Optional, Dict, Any

from PyQt5.QtCore import QObject, pyqtSignal


# Valhalla maneuver type -> 中文指令映射
MANEUVER_TYPE_MAP = {
    0: "继续",
    1: "出发",
    2: "出发后右转",
    3: "出发后左转",
    4: "出发后直行",
    5: "出发后靠右",
    6: "出发后靠左",
    7: "短暂行驶后右转",
    8: "短暂行驶后左转",
    9: "短暂行驶后直行",
    10: "右转",
    11: "左转",
    12: "直行",
    13: "靠右",
    14: "靠左",
    15: "到达目的地",
    16: "到达目的地下方",
    17: "合并",
    18: "从右侧匝道进入",
    19: "从左侧匝道进入",
    20: "从右侧出口驶出",
    21: "从左侧出口驶出",
    22: "在右侧路口右转",
    23: "在左侧路口左转",
    24: "在右侧环岛第一个出口驶出",
    25: "在右侧环岛第二个出口驶出",
    26: "在右侧环岛第三个出口驶出",
    27: "在右侧环岛第四个出口驶出",
    28: "在右侧环岛第五个出口驶出",
    29: "在右侧环岛第六个出口驶出",
    30: "在右侧环岛第七个出口驶出",
    31: "在右侧环岛第八个出口驶出",
    32: "在左侧环岛第一个出口驶出",
    33: "在左侧环岛第二个出口驶出",
    34: "在左侧环岛第三个出口驶出",
    35: "在左侧环岛第四个出口驶出",
    36: "在左侧环岛第五个出口驶出",
    37: "在左侧环岛第六个出口驶出",
    38: "在左侧环岛第七个出口驶出",
    39: "在左侧环岛第八个出口驶出",
    40: "在右侧掉头",
    41: "在左侧掉头",
    42: "在右侧绕环岛",
    43: "在左侧绕环岛",
    44: "在右侧高架上右转",
    45: "在左侧高架上左转",
    46: "在右侧高架上直行",
    47: "在左侧高架上直行",
    48: "在右侧驶出高架上右转",
    49: "在左侧驶出高架上右转",
    50: "在右侧驶出高架上左转",
    51: "在左侧驶出高架上左转",
    52: "在右侧驶出高架上直行",
    53: "在左侧驶出高架上直行",
    54: "在右侧高架上合并",
    55: "在左侧高架上合并",
    56: "在右侧高架匝道进入",
    57: "在左侧高架匝道进入",
}


def _decode_polyline6(encoded: str) -> List[Tuple[float, float]]:
    """解码 Valhalla polyline6 编码为 [(lat, lon), ...]"""
    coords = []
    index = 0
    lat = 0
    lon = 0

    while index < len(encoded):
        # decode latitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lat_change = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += lat_change

        # decode longitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lon_change = ~(result >> 1) if (result & 1) else (result >> 1)
        lon += lon_change

        coords.append((lat * 1e-6, lon * 1e-6))

    return coords


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点间距离（米）"""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算从 (lat1,lon1) 到 (lat2,lon2) 的航向角（0°指北，顺时针）"""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def _relative_direction(yaw: float, target_bearing: float) -> str:
    """
    计算目标点相对于当前朝向的方向。
    yaw: 当前朝向（0°指北，顺时针）——箭头指的方向就是"前"
    target_bearing: 从当前位置看向目标点的方位角（0°指北，顺时针）
    返回: 正前、右前、左前、后方、右后、左后
    """
    diff = (target_bearing - yaw + 360) % 360
    if diff > 180:
        diff -= 360

    ad = abs(diff)
    if ad <= 30:
        result = "正前方"
    elif 30 < ad <= 90:
        result = "右前方" if diff > 0 else "左前方"
    elif 90 < ad <= 150:
        result = "右后方" if diff > 0 else "左后方"
    else:
        result = "后方"

    print(f"[_relative_direction] yaw={yaw:.1f}, target={target_bearing:.1f}, diff={diff:.1f}, ad={ad:.1f}, result={result}")
    return result


def _point_to_segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> Tuple[float, float, float]:
    """点(px,py)到线段(ab)的最短距离，返回 (距离, 最近点x, 最近点y)"""
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    ab2 = abx * abx + aby * aby
    if ab2 == 0:
        return _haversine(px, py, ax, ay), ax, ay
    t = max(0, min(1, (apx * abx + apy * aby) / ab2))
    cx = ax + t * abx
    cy = ay + t * aby
    dist = _haversine(px, py, cx, cy)
    return dist, cx, cy


class NavEngine(QObject):
    """离线导航引擎"""

    # 信号
    route_planned = pyqtSignal(object)      # 路线规划完成，带回 Route 对象
    route_failed = pyqtSignal(str)          # 路线规划失败
    nav_updated = pyqtSignal(object)        # 导航状态更新

    # 自动启动配置
    _VALHALLA_SERVICE_PATH = "/home/hedya/Desktop/bs_project/qt_project/valhalla/build/valhalla_service"
    _VALHALLA_CONFIG_PATH = "/home/hedya/Desktop/bs_project/qt_project/maps/valhalla_data/valhalla.json"

    def __init__(self, base_url: str = "http://localhost:8002", parent=None):
        super().__init__(parent)
        self.base_url = base_url.rstrip("/")
        self._route = None          # 当前路线数据
        self._shape = []            # 解码后的坐标列表 [(lat, lon), ...]
        self._maneuvers = []        # 导航指令列表
        self._current_step = 0      # 当前执行到第几个 maneuver
        self._deviation_count = 0   # 偏离路线计数
        self._current_yaw = None    # 当前朝向（0°指北，顺时针）
        self._service_process = None  # 自动启动的服务进程

    # ------------------------------------------------------------------
    # 服务健康检查与自动启动
    # ------------------------------------------------------------------
    def _is_service_healthy(self, timeout: int = 2) -> bool:
        """检测 Valhalla HTTP 服务是否可用（POST /route 有效坐标）"""
        try:
            payload = json.dumps({
                "locations": [
                    {"lon": 112.93, "lat": 27.83},
                    {"lon": 112.95, "lat": 27.85},
                ],
                "costing": "bicycle",
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/route",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except urllib.error.HTTPError as e:
            # 400 表示服务活着但坐标有问题，也算健康
            return e.code in (200, 400)
        except Exception:
            return False

    def _start_valhalla_service(self) -> bool:
        """尝试自动启动 valhalla_service，返回是否成功"""
        # 1. 检查二进制是否存在
        if not os.path.isfile(self._VALHALLA_SERVICE_PATH):
            print(f"[NavEngine] valhalla_service 不存在: {self._VALHALLA_SERVICE_PATH}")
            return False
        if not os.access(self._VALHALLA_SERVICE_PATH, os.X_OK):
            print(f"[NavEngine] valhalla_service 无执行权限")
            return False

        # 2. 检查配置文件是否存在
        if not os.path.isfile(self._VALHALLA_CONFIG_PATH):
            print(f"[NavEngine] 配置文件不存在: {self._VALHALLA_CONFIG_PATH}")
            return False

        # 3. 杀掉可能残留的进程
        try:
            subprocess.run(
                ["pkill", "-f", "valhalla_service"],
                capture_output=True, timeout=5,
            )
            time.sleep(1)
        except Exception:
            pass

        # 4. 启动服务
        print(f"[NavEngine] 正在启动 Valhalla 服务...")
        try:
            log_path = "/home/hedya/Desktop/bs_project/qt_project/maps/valhalla_data/valhalla_auto.log"
            log_file = open(log_path, "a")
            self._service_process = subprocess.Popen(
                [self._VALHALLA_SERVICE_PATH, self._VALHALLA_CONFIG_PATH],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=os.path.dirname(self._VALHALLA_SERVICE_PATH),
            )
            # Popen 会持有文件描述符，不需要在这里关闭
        except Exception as e:
            print(f"[NavEngine] 启动失败: {e}")
            return False

        # 5. 等待服务就绪（最多 10 秒）
        for i in range(20):
            time.sleep(0.5)
            if self._is_service_healthy(timeout=1):
                print(f"[NavEngine] Valhalla 服务已就绪")
                return True

        print(f"[NavEngine] 服务未在预期时间内就绪")
        return False

    # ------------------------------------------------------------------
    # 路线规划
    # ------------------------------------------------------------------
    def plan_route(
        self,
        start_lon: float,
        start_lat: float,
        end_lon: float,
        end_lat: float,
        costing: str = "bicycle",
    ) -> Optional[Dict[str, Any]]:
        """
        规划路线，返回解析后的路线字典。
        如果服务未启动，自动尝试启动。
        失败时 emit route_failed 并返回 None。
        """
        # 0. 确保服务可用
        if not self._is_service_healthy():
            if not self._start_valhalla_service():
                self.route_failed.emit(
                    "Valhalla 服务未启动，且自动启动失败。"
                    f"请检查 {self._VALHALLA_SERVICE_PATH} 是否存在。"
                )
                return None

        url = f"{self.base_url}/route"
        payload = {
            "locations": [
                {"lon": start_lon, "lat": start_lat},
                {"lon": end_lon, "lat": end_lat},
            ],
            "costing": costing,
            "directions_options": {"units": "kilometers", "language": "zh-CN"},
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            self.route_failed.emit(f"请求失败: {e}")
            return None

        if "trip" not in data:
            err = data.get("error", "未知错误")
            self.route_failed.emit(str(err))
            return None

        trip = data["trip"]
        leg = trip["legs"][0]
        shape_encoded = leg.get("shape", "")
        self._shape = _decode_polyline6(shape_encoded)
        self._maneuvers = leg.get("maneuvers", [])
        self._current_step = 0

        total_dist = trip.get("summary", {}).get("length", 0)
        total_time = trip.get("summary", {}).get("time", 0)

        # 为每个 maneuver 附加 begin/end 坐标（方便前端绘制）
        for m in self._maneuvers:
            bi = m.get("begin_shape_index", 0)
            ei = m.get("end_shape_index", len(self._shape) - 1)
            m["_begin_coord"] = self._shape[bi] if bi < len(self._shape) else self._shape[-1]
            m["_end_coord"] = self._shape[ei] if ei < len(self._shape) else self._shape[-1]

        route = {
            "start": (start_lat, start_lon),
            "end": (end_lat, end_lon),
            "shape": self._shape,
            "maneuvers": self._maneuvers,
            "total_distance_km": total_dist,
            "total_time_sec": total_time,
            "raw": data,
        }
        self._route = route
        self.route_planned.emit(route)
        return route

    # ------------------------------------------------------------------
    # 导航跟踪
    # ------------------------------------------------------------------
    def update_yaw(self, yaw: float):
        """更新当前朝向（0°指北，顺时针增加）"""
        self._current_yaw = yaw % 360.0

    def update_position(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """
        根据当前 GPS 位置更新导航状态。
        返回当前导航状态字典，包含：
        - current_instruction: 当前应执行的中文指令
        - distance_to_next_maneuver: 到下一个 maneuver 的距离（米）
        - remaining_distance_km: 剩余总距离（公里）
        - remaining_time_sec: 剩余总时间（秒）
        - off_route: 是否偏离路线
        - arrived: 是否已到达
        - relative_direction: 路线相对朝向（如"左前方"）
        """
        if not self._route or not self._shape:
            return None

        # 1. 找到路线上最近的点
        min_dist = float("inf")
        nearest_idx = 0
        for i in range(len(self._shape) - 1):
            a_lat, a_lon = self._shape[i]
            b_lat, b_lon = self._shape[i + 1]
            d, _, _ = _point_to_segment_distance(lat, lon, a_lat, a_lon, b_lat, b_lon)
            if d < min_dist:
                min_dist = d
                nearest_idx = i

        # 2. 判断是否偏离路线（>50米认为偏离）
        off_route = min_dist > 50
        if off_route:
            self._deviation_count += 1
        else:
            self._deviation_count = 0

        # 3. 推进 maneuver 索引
        # 当当前点已超过某个 maneuver 的 end_shape_index 时，步进到下一个
        while (
            self._current_step < len(self._maneuvers) - 1
            and nearest_idx >= self._maneuvers[self._current_step].get("end_shape_index", 0)
        ):
            self._current_step += 1

        maneuver = self._maneuvers[self._current_step] if self._current_step < len(self._maneuvers) else None

        # 4. 计算到下一个 maneuver 的距离
        dist_to_next = 0.0
        if maneuver:
            end_idx = maneuver.get("end_shape_index", len(self._shape) - 1)
            if nearest_idx < end_idx:
                # 累加从当前最近点到 maneuver 结束点的路径距离
                for i in range(nearest_idx, min(end_idx, len(self._shape) - 1)):
                    a_lat, a_lon = self._shape[i]
                    b_lat, b_lon = self._shape[i + 1]
                    dist_to_next += _haversine(a_lat, a_lon, b_lat, b_lon)
            else:
                dist_to_next = 0.0

        # 5. 计算剩余总距离
        remaining_dist = 0.0
        for i in range(nearest_idx, len(self._shape) - 1):
            a_lat, a_lon = self._shape[i]
            b_lat, b_lon = self._shape[i + 1]
            remaining_dist += _haversine(a_lat, a_lon, b_lat, b_lon)

        # 6. 构建状态
        instruction = ""
        if maneuver:
            mtype = maneuver.get("type", 0)
            instruction = MANEUVER_TYPE_MAP.get(mtype, maneuver.get("instruction", "继续"))

        arrived = self._current_step >= len(self._maneuvers) - 1 and dist_to_next < 30

        # 7. 计算路线相对方向（需要 yaw）
        # 用从用户当前位置到路线上最近点的方位角，计算"路线在你的哪个方向"
        # 更符合用户看图时的空间直觉
        rel_dir = ""
        if self._current_yaw is not None and nearest_idx < len(self._shape):
            nearest_lat, nearest_lon = self._shape[nearest_idx]
            route_bearing = _bearing(lat, lon, nearest_lat, nearest_lon)
            rel_dir = _relative_direction(self._current_yaw, route_bearing)
            print(f"[NavUpdate] user=({lat:.5f},{lon:.5f}) nearest=({nearest_lat:.5f},{nearest_lon:.5f}) bearing={route_bearing:.1f}, rel_dir={rel_dir}")

        state = {
            "current_instruction": instruction,
            "distance_to_next_maneuver": round(dist_to_next, 1),
            "remaining_distance_km": round(remaining_dist / 1000, 2),
            "remaining_time_sec": None,  # 简单处理，不估算动态时间
            "off_route": off_route,
            "deviation_count": self._deviation_count,
            "arrived": arrived,
            "current_step": self._current_step,
            "total_steps": len(self._maneuvers),
            "nearest_shape_index": nearest_idx,
            "relative_direction": rel_dir,
        }
        self.nav_updated.emit(state)
        return state

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    def get_route_geojson(self) -> Optional[Dict]:
        """返回路线的 GeoJSON LineString，供 Leaflet 绘制"""
        if not self._shape:
            return None
        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[lon, lat] for lat, lon in self._shape],
            },
            "properties": {},
        }

    def clear(self):
        """清除当前路线"""
        self._route = None
        self._shape = []
        self._maneuvers = []
        self._current_step = 0
        self._deviation_count = 0
        self._current_yaw = None

    def is_active(self) -> bool:
        return self._route is not None
