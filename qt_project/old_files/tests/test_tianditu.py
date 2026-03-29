#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试天地图API是否能正常访问"""

import requests
import math
from PIL import Image
from io import BytesIO

# 你的天地图Key
TIANDITU_KEY = "a1eaef5f544e687811ac200552b9a3c2"

# 测试坐标：上海（东方明珠）
lat = 31.230416
lon = 121.473701
zoom = 14

def deg2num(lat_deg, lon_deg, zoom):
    """经纬度转瓦片坐标"""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

# 计算瓦片坐标
x, y = deg2num(lat, lon, zoom)
print(f"坐标: {lat}, {lon}")
print(f"Zoom: {zoom}")
print(f"瓦片坐标: x={x}, y={y}")
print()

# 测试下载矢量底图
server = "t0"
base_url = f"http://{server}.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={zoom}&TILEROW={y}&TILECOL={x}&tk={TIANDITU_KEY}"

print(f"测试URL: {base_url}")
print()

try:
    print("正在下载矢量底图...")
    response = requests.get(base_url, timeout=10)
    print(f"HTTP状态码: {response.status_code}")
    print(f"响应大小: {len(response.content)} bytes")

    if response.status_code == 200:
        # 尝试打开图片
        img = Image.open(BytesIO(response.content))
        print(f"图片尺寸: {img.size}")
        print(f"图片格式: {img.format}")

        # 保存测试图片
        img.save("test_tile.png")
        print("✅ 下载成功！图片已保存为 test_tile.png")
    else:
        print(f"❌ 下载失败！状态码: {response.status_code}")
        print(f"响应内容: {response.text[:200]}")

except Exception as e:
    print(f"❌ 错误: {e}")
