#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成虚拟骑行记录 - 使用高德地图JS API获取详细路线

起点：湖南工程学院 (27.847943, 112.931723)
终点：华隆步步高 (27.833051, 112.918485)
"""

import os
import sys
import json
import time
import math
import urllib.request
import urllib.parse
import urllib.error

# 添加项目路径
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_dir = os.path.dirname(_script_dir)  # qt_project/
sys.path.insert(0, _project_dir)
os.chdir(_project_dir)

from core.protocol import RideSummary, TrackPoint, GPSPoint
from persistence.ride_repository import RideRepository


AMAP_KEY = "8b657a470f4b69e82bf81f72b3a2b3c0"  # Web服务 API Key


def interpolate_points(points: list, max_distance: float = 20.0) -> list:
    """
    在点之间进行线性插值，确保任意两点间距离不超过max_distance米

    Args:
        points: [(lat, lon), ...] 原始轨迹点
        max_distance: 最大间隔距离（米）

    Returns:
        插值后的轨迹点列表
    """
    if len(points) < 2:
        return points

    result = [points[0]]

    for i in range(1, len(points)):
        p1 = result[-1]
        p2 = points[i]

        # 计算距离
        dist = haversine(p1[0], p1[1], p2[0], p2[1])

        if dist > max_distance:
            # 需要插值
            num_interpolated = int(math.ceil(dist / max_distance))
            for j in range(1, num_interpolated + 1):
                ratio = j / num_interpolated
                new_lat = p1[0] + (p2[0] - p1[0]) * ratio
                new_lon = p1[1] + (p2[1] - p1[1]) * ratio
                result.append((new_lat, new_lon))
        else:
            result.append(p2)

    return result


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点间的球面距离（米）"""
    R = 6371000  # 地球半径（米）
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def get_amap_bicycling_route_v3(origin: str, destination: str) -> dict:
    """
    使用高德地图v3骑行路线API获取更详细的路线

    Args:
        origin: "lon,lat" 格式
        destination: "lon,lat" 格式

    Returns:
        路线数据字典
    """
    url = "https://restapi.amap.com/v3/direction/bicycling"
    params = {
        'key': AMAP_KEY,
        'origin': origin,
        'destination': destination,
        'extensions': 'all',  # 获取完整路线信息
    }

    try:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        print(f"[高德API] 请求骑行路线: {origin} -> {destination}")

        with urllib.request.urlopen(full_url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except Exception as e:
        print(f"[高德API] 请求失败: {e}")
        return {}


def extract_polyline_from_v3(data: dict) -> list:
    """从v3 API响应中提取轨迹点"""
    points = []

    if data.get('status') != '1':
        print(f"[高德API] 状态错误: {data.get('info', '未知')}")
        return points

    routes = data.get('data', {}).get('paths', [])
    if not routes:
        routes = data.get('routes', [])
        if isinstance(routes, dict):
            routes = [routes]
        elif isinstance(routes, list) and routes and isinstance(routes[0], dict):
            if 'paths' in routes[0]:
                routes = routes[0]['paths']
            else:
                routes = [routes[0]]

    for route in routes:
        # 尝试获取steps中的polyline
        steps = route.get('steps', [])
        if isinstance(steps, list):
            for step in steps:
                polyline = step.get('polyline', '')
                if polyline:
                    # polyline是"lon,lat;lon,lat;..."格式
                    for coord in polyline.split(';'):
                        parts = coord.split(',')
                        if len(parts) >= 2:
                            try:
                                lon = float(parts[0])
                                lat = float(parts[1])
                                points.append((lat, lon))  # 注意：高德polyline是lng,lat格式
                            except ValueError:
                                pass

    return points


def get_amap_bicycling_route_v5(origin: str, destination: str) -> dict:
    """
    使用高德地图v5骑行路线API获取更详细的路线

    Args:
        origin: "lon,lat" 格式
        destination: "lon,lat" 格式

    Returns:
        路线数据字典
    """
    url = "https://restapi.amap.com/v5/direction/bicycling"
    params = {
        'key': AMAP_KEY,
        'origin': origin,
        'destination': destination,
        'show_fields': 'polyline,cost,navi',
        'strategy': 0,  # 最优路线
        'output': 'json'
    }

    try:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        print(f"[高德API v5] 请求骑行路线: {origin} -> {destination}")

        with urllib.request.urlopen(full_url, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except Exception as e:
        print(f"[高德API v5] 请求失败: {e}")
        return {}


def extract_polyline_from_v5(data: dict) -> list:
    """从v5 API响应中提取轨迹点"""
    points = []

    if data.get('status') != '1':
        print(f"[高德API v5] 状态错误: {data.get('info', '未知')}")
        return points

    routes = data.get('route', {}).get('paths', [])
    if not routes:
        print(f"[高德API v5] 没有找到路线")
        return points

    route = routes[0]

    # 尝试获取steps中的polyline
    steps = route.get('steps', [])
    if not steps:
        # 尝试从navi字段获取
        navi_list = route.get('navi', [])
        for navi_item in navi_list:
            polyline = navi_item.get('polyline', '')
            if polyline:
                for coord in polyline.split(';'):
                    parts = coord.split(',')
                    if len(parts) >= 2:
                        try:
                            lon = float(parts[0])
                            lat = float(parts[1])
                            points.append((lat, lon))
                        except ValueError:
                            pass

    for step in steps:
        # v5的polyline格式可能是 ; 分隔的 lng,lat 对
        polyline = step.get('polyline', '')
        if not polyline:
            continue

        # 尝试不同的分隔符格式
        if ';' in polyline:
            coords = polyline.split(';')
        else:
            coords = [polyline]

        for coord in coords:
            parts = coord.split(',')
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    points.append((lat, lon))
                except ValueError:
                    pass

    return points


def generate_virtual_ride():
    """生成虚拟骑行记录"""

    # 起点和终点（高德API使用lon,lat格式）
    origin = "112.931723,27.847943"  # 湖南工程学院
    destination = "112.918485,27.833051"  # 华隆步步高

    print("=" * 60)
    print("生成虚拟骑行记录")
    print(f"起点: 湖南工程学院 ({origin})")
    print(f"终点: 华隆步步高 ({destination})")
    print("=" * 60)

    # 尝试v5 API
    raw_points = []
    data = get_amap_bicycling_route_v5(origin, destination)
    raw_points = extract_polyline_from_v5(data)

    if not raw_points:
        print("[提示] v5 API返回空，尝试v3 API...")
        data = get_amap_bicycling_route_v3(origin, destination)
        raw_points = extract_polyline_from_v3(data)

    if not raw_points:
        print("[错误] 无法获取路线，使用手动路线点")
        # 使用已知在道路上的路线点
        raw_points = get_manual_route_points()

    print(f"[路线] 获取到 {len(raw_points)} 个原始轨迹点")

    # 去重并按顺序排列
    unique_points = []
    for p in raw_points:
        if not unique_points or haversine(unique_points[-1][0], unique_points[-1][1], p[0], p[1]) > 1.0:
            unique_points.append(p)

    print(f"[路线] 去重后 {len(unique_points)} 个点")

    # 对点间隔过大的地方进行插值
    interpolated_points = interpolate_points(unique_points, max_distance=15.0)
    print(f"[路线] 插值后 {len(interpolated_points)} 个点")

    # 计算总距离
    total_distance = 0.0
    for i in range(1, len(interpolated_points)):
        total_distance += haversine(
            interpolated_points[i-1][0], interpolated_points[i-1][1],
            interpolated_points[i][0], interpolated_points[i][1]
        )

    print(f"[路线] 总距离: {total_distance/1000:.2f} 公里")

    # 生成TrackPoint列表
    start_time = time.time()
    track_points = []

    # 模拟骑行参数
    total_duration = 1105  # 秒（约18分钟）
    interval = total_duration / len(interpolated_points)

    for i, (lat, lon) in enumerate(interpolated_points):
        timestamp = start_time + i * interval

        # 模拟传感器数据
        progress = i / len(interpolated_points)

        # 坡度模拟（根据位置变化）
        if i > 0:
            lat_diff = lat - interpolated_points[i-1][0]
            lon_diff = lon - interpolated_points[i-1][1]
            slope = (lat_diff * 100) if abs(lat_diff) > 0.0001 else 0.0
        else:
            slope = 0.0

        # 速度和功率模拟
        speed = 15.0 + 5.0 * math.sin(progress * math.pi)  # 10-20 km/h
        power = 120 + 80 * math.sin(progress * math.pi)  # 40-200 W
        cadence = 75 + 15 * math.sin(progress * math.pi)  # 60-90 rpm
        heart_rate = 130 + 20 * math.sin(progress * math.pi)  # 110-150 bpm

        # 海拔模拟（基于纬度和简单变化）
        base_elevation = 46.0
        elevation = base_elevation - (lat - 27.847) * 1000 + 2 * math.sin(i / 20)

        gps = GPSPoint(
            lat=lat,
            lon=lon,
            altitude=elevation,
            timestamp=timestamp
        )

        track_points.append(TrackPoint(
            gps=gps,
            speed=speed,
            power=power,
            cadence=cadence,
            heart_rate=heart_rate,
            altitude=elevation
        ))

    # 创建骑行摘要
    summary = RideSummary(
        id="ride_virtual_hunan_to_bubugao",
        start_time=start_time,
        end_time=start_time + total_duration,
        total_distance=total_distance / 1000,  # 转为km
        total_time=total_duration,
        moving_time=int(total_duration * 0.95),  # 95%在运动
        avg_speed=total_distance / 1000 / (total_duration / 3600),  # km/h
        max_speed=25.0,
        avg_power=165.0,
        max_power=305.0,
        avg_hr=138.0,
        max_hr=158.0,
        total_elevation_gain=12.0,
        max_elevation_gain=48.0,
        calories=580.0,
        file_path=""
    )

    # 保存骑行记录
    repo = RideRepository("~/smartride/rides")
    ride_id = repo.save_ride(summary, track_points)

    print(f"\n✅ 虚拟骑行记录已生成: {ride_id}")
    print(f"   总距离: {summary.total_distance:.2f} km")
    print(f"   轨迹点数: {len(track_points)}")

    # 打印前几个和后几个点用于验证
    print("\n轨迹点验证（前5个）:")
    for i, p in enumerate(interpolated_points[:5]):
        print(f"  {i}: ({p[0]:.6f}, {p[1]:.6f})")

    print("\n轨迹点验证（后5个）:")
    for i, p in enumerate(interpolated_points[-5:]):
        print(f"  {len(interpolated_points)-5+i}: ({p[0]:.6f}, {p[1]:.6f})")

    return ride_id


def get_manual_route_points() -> list:
    """
    手动定义的沿道路路线点
    从湖南工程学院到华隆步步高，途经至善路、福星中路、宝塔北路、河东大道、建设南路
    """

    # 这些点是根据地图上实际道路位置定义的
    points = [
        # 起点：湖南工程学院门口
        (27.847943, 112.931723),
        (27.847943, 112.931650),

        # 沿至善路向西
        (27.847920, 112.931500),
        (27.847900, 112.931300),
        (27.847880, 112.931100),
        (27.847860, 112.930900),
        (27.847840, 112.930700),
        (27.847820, 112.930500),

        # 至善路与福星中路交叉口
        (27.847800, 112.930300),
        (27.847780, 112.930100),
        (27.847760, 112.929900),

        # 沿福星中路向南
        (27.847500, 112.929700),
        (27.847200, 112.929500),
        (27.846900, 112.929300),
        (27.846600, 112.929100),
        (27.846300, 112.928900),
        (27.846000, 112.928700),

        # 转入宝塔北路
        (27.845700, 112.928500),
        (27.845400, 112.928300),
        (27.845100, 112.928100),
        (27.844800, 112.927900),
        (27.844500, 112.927700),

        # 宝塔北路与河东大道交叉口
        (27.844200, 112.927500),
        (27.843900, 112.927300),
        (27.843600, 112.927100),

        # 沿河东大道向南
        (27.843300, 112.927000),
        (27.843000, 112.926900),
        (27.842700, 112.926800),
        (27.842400, 112.926700),
        (27.842100, 112.926600),

        # 转入建设南路
        (27.841800, 112.926500),
        (27.841500, 112.926300),
        (27.841200, 112.926100),
        (27.840900, 112.925900),
        (27.840600, 112.925700),
        (27.840300, 112.925500),

        # 建设南路与莲城商业步行街交叉口
        (27.840000, 112.925300),
        (27.839700, 112.925100),
        (27.839400, 112.924900),
        (27.839100, 112.924700),
        (27.838800, 112.924500),

        # 沿莲城商业步行街向西南
        (27.838500, 112.924300),
        (27.838200, 112.924000),
        (27.837900, 112.923700),
        (27.837600, 112.923400),

        # 转入华隆步步高附近
        (27.837300, 112.923100),
        (27.837000, 112.922800),
        (27.836700, 112.922500),
        (27.836400, 112.922200),

        # 接近步步高
        (27.836100, 112.922000),
        (27.835800, 112.921800),
        (27.835500, 112.921600),
        (27.835200, 112.921400),

        # 到达步步高
        (27.834900, 112.921200),
        (27.834600, 112.921000),
        (27.834300, 112.920800),
        (27.834000, 112.920600),
        (27.833700, 112.920400),
        (27.833400, 112.920200),
        (27.833100, 112.920000),
        (27.833051, 112.918485),  # 华隆步步高
    ]

    return points


if __name__ == "__main__":
    ride_id = generate_virtual_ride()
    print(f"\n骑行记录ID: {ride_id}")
