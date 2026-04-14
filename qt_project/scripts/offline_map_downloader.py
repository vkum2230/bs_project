#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线地图瓦片下载工具
用于下载 OpenStreetMap 瓦片到本地，支持按省份/区域下载

使用方法:
    python offline_map_downloader.py --province 广东省 --zoom 12-16
    python offline_map_downloader.py --bbox 113.2,22.5,114.5,23.5 --zoom 14-16
"""

import os
import sys
import math
import json
import time
import argparse
import hashlib
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse


class TileDownloader:
    """地图瓦片下载器"""
    
    # OpenStreetMap 瓦片服务器（多服务器轮询）
    OSM_SERVERS = ['a', 'b', 'c']
    
    # 中国各省份边界框 (min_lon, min_lat, max_lon, max_lat)
    PROVINCE_BBOX = {
        "北京市": (115.7, 39.4, 117.4, 41.6),
        "天津市": (116.7, 38.5, 118.4, 40.1),
        "河北省": (113.5, 36.0, 119.8, 42.6),
        "山西省": (110.2, 34.6, 114.5, 40.7),
        "内蒙古自治区": (97.2, 37.4, 126.1, 53.3),
        "辽宁省": (118.8, 38.7, 125.8, 43.4),
        "吉林省": (121.6, 40.8, 131.3, 46.3),
        "黑龙江省": (121.2, 43.4, 135.1, 53.5),
        "上海市": (120.8, 30.6, 122.2, 31.9),
        "江苏省": (116.4, 30.7, 121.9, 35.1),
        "浙江省": (118.0, 27.0, 123.0, 31.1),
        "安徽省": (114.9, 29.4, 119.6, 34.6),
        "福建省": (115.8, 23.5, 120.7, 28.3),
        "江西省": (113.5, 24.4, 118.4, 30.1),
        "山东省": (114.8, 34.3, 122.7, 38.4),
        "河南省": (110.4, 31.4, 116.6, 36.4),
        "湖北省": (108.4, 29.0, 116.1, 33.3),
        "湖南省": (108.8, 24.6, 114.3, 30.1),
        "广东省": (109.6, 20.2, 117.3, 25.3),
        "广西壮族自治区": (104.5, 20.9, 112.1, 26.4),
        "海南省": (108.6, 18.1, 111.0, 20.2),
        "重庆市": (105.3, 28.1, 110.2, 32.2),
        "四川省": (97.3, 26.0, 108.5, 34.3),
        "贵州省": (103.6, 24.6, 109.6, 29.2),
        "云南省": (97.5, 21.1, 106.2, 29.2),
        "西藏自治区": (78.4, 26.8, 99.1, 36.5),
        "陕西省": (105.5, 31.7, 111.2, 39.6),
        "甘肃省": (92.2, 32.6, 108.7, 42.8),
        "青海省": (89.4, 31.7, 103.1, 39.1),
        "宁夏回族自治区": (104.3, 35.2, 107.6, 39.4),
        "新疆维吾尔自治区": (73.5, 34.3, 96.4, 48.4),
        "台湾省": (119.3, 21.8, 122.0, 25.3),
        "香港特别行政区": (113.8, 22.1, 114.4, 22.6),
        "澳门特别行政区": (113.5, 22.1, 113.6, 22.2),
    }
    
    def __init__(self, output_dir="offline_maps", delay=0.2, max_workers=4):
        """
        初始化下载器
        
        Args:
            output_dir: 瓦片输出目录
            delay: 下载间隔（秒），避免请求过快
            max_workers: 并发下载线程数
        """
        self.output_dir = output_dir
        self.delay = delay
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.downloaded_count = 0
        self.failed_tiles = []
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
    def deg2num(self, lat_deg, lon_deg, zoom):
        """经纬度转换为瓦片坐标"""
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (xtile, ytile)
    
    def num2deg(self, xtile, ytile, zoom):
        """瓦片坐标转换为经纬度"""
        n = 2.0 ** zoom
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return (lat_deg, lon_deg)
    
    def get_tile_url(self, x, y, z):
        """获取瓦片 URL（轮询使用不同服务器）"""
        server = self.OSM_SERVERS[(x + y + z) % len(self.OSM_SERVERS)]
        return f"https://{server}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    
    def get_tile_path(self, x, y, z, province=None):
        """获取瓦片本地存储路径"""
        if province:
            # 按省份存储
            safe_name = hashlib.md5(province.encode('utf-8')).hexdigest()[:8]
            return os.path.join(self.output_dir, safe_name, str(z), str(x), f"{y}.png")
        else:
            # 通用存储
            return os.path.join(self.output_dir, str(z), str(x), f"{y}.png")
    
    def download_tile(self, x, y, z, province=None, retries=3):
        """
        下载单个瓦片
        
        Returns:
            (success: bool, path: str) 
        """
        tile_path = self.get_tile_path(x, y, z, province)
        
        # 如果已存在则跳过
        if os.path.exists(tile_path) and os.path.getsize(tile_path) > 100:
            return True, tile_path
        
        # 创建目录
        os.makedirs(os.path.dirname(tile_path), exist_ok=True)
        
        url = self.get_tile_url(x, y, z)
        
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    with open(tile_path, 'wb') as f:
                        f.write(response.content)
                    time.sleep(self.delay)  # 礼貌延迟
                    return True, tile_path
                elif response.status_code == 429:  # Too Many Requests
                    time.sleep(self.delay * (attempt + 2))
                else:
                    break
            except Exception as e:
                if attempt == retries - 1:
                    self.failed_tiles.append((x, y, z, str(e)))
                    return False, str(e)
                time.sleep(self.delay * (attempt + 1))
        
        return False, f"HTTP {response.status_code}"
    
    def get_tiles_in_bbox(self, min_lon, min_lat, max_lon, max_lat, zoom):
        """获取边界框内的所有瓦片坐标"""
        x_min, y_max = self.deg2num(max_lat, min_lon, zoom)  # 左上角
        x_max, y_min = self.deg2num(min_lat, max_lon, zoom)  # 右下角
        
        # 确保范围正确（y轴方向是从北到南，所以y_max > y_min）
        y_start = min(y_min, y_max)
        y_end = max(y_min, y_max)
        
        tiles = []
        for x in range(x_min, x_max + 1):
            for y in range(y_start, y_end + 1):
                tiles.append((x, y, zoom))
        return tiles
    
    def download_area(self, min_lon, min_lat, max_lon, max_lat, 
                      zoom_levels, province=None, progress_callback=None):
        """
        下载指定区域的多层级瓦片
        
        Args:
            min_lon, min_lat, max_lon, max_lat: 边界框
            zoom_levels: zoom 层级列表，如 [12, 13, 14, 15, 16]
            province: 省份名称（可选，用于组织存储）
            progress_callback: 进度回调函数 (downloaded, total, current_zoom)
        """
        # 收集所有需要下载的瓦片
        all_tiles = []
        for z in zoom_levels:
            tiles = self.get_tiles_in_bbox(min_lon, min_lat, max_lon, max_lat, z)
            all_tiles.extend([(x, y, z, province) for x, y, z in tiles])
        
        total = len(all_tiles)
        print(f"总共需要下载 {total} 个瓦片")
        
        # 并发下载
        downloaded = 0
        current_zoom = zoom_levels[0] if zoom_levels else 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_tile = {
                executor.submit(self.download_tile, x, y, z, prov): (x, y, z)
                for x, y, z, prov in all_tiles
            }
            
            for future in as_completed(future_to_tile):
                x, y, z = future_to_tile[future]
                try:
                    success, result = future.result()
                    if success:
                        downloaded += 1
                        self.downloaded_count += 1
                except Exception as e:
                    self.failed_tiles.append((x, y, z, str(e)))
                
                # 进度回调
                if z != current_zoom:
                    current_zoom = z
                    print(f"\n开始下载 zoom {z}...")
                
                if progress_callback and total > 0:
                    progress_callback(downloaded, total, current_zoom)
                
                # 控制台进度显示
                if downloaded % 50 == 0 or downloaded == total:
                    print(f"\r进度: {downloaded}/{total} ({downloaded*100//total}%)", end='', flush=True)
        
        print(f"\n\n下载完成！成功: {self.downloaded_count}, 失败: {len(self.failed_tiles)}")
        
        if self.failed_tiles:
            print(f"失败的瓦片数量: {len(self.failed_tiles)}")
            # 保存失败记录
            failed_file = os.path.join(self.output_dir, "failed_tiles.json")
            with open(failed_file, 'w') as f:
                json.dump(self.failed_tiles, f, indent=2)
            print(f"失败记录已保存到: {failed_file}")
        
        return self.downloaded_count, len(self.failed_tiles)
    
    def download_province(self, province_name, zoom_levels=None):
        """下载指定省份的瓦片"""
        if province_name not in self.PROVINCE_BBOX:
            print(f"错误: 未知的省份 '{province_name}'")
            print(f"可用省份: {', '.join(self.PROVINCE_BBOX.keys())}")
            return 0, 0
        
        if zoom_levels is None:
            # 骑行导航推荐层级
            zoom_levels = [12, 13, 14, 15, 16]
        
        bbox = self.PROVINCE_BBOX[province_name]
        print(f"开始下载 {province_name} 的地图瓦片")
        print(f"边界框: {bbox}")
        print(f"Zoom 层级: {zoom_levels}")
        print(f"输出目录: {self.output_dir}")
        print("-" * 50)
        
        return self.download_area(*bbox, zoom_levels, province_name)
    
    def get_storage_size(self):
        """获取已下载瓦片的总大小"""
        total_size = 0
        file_count = 0
        for dirpath, dirnames, filenames in os.walk(self.output_dir):
            for f in filenames:
                if f.endswith('.png'):
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
                    file_count += 1
        return file_count, total_size
    
    def generate_index(self):
        """生成索引文件，记录各省份瓦片信息"""
        index = {
            "provinces": {},
            "stats": {}
        }
        
        for province, bbox in self.PROVINCE_BBOX.items():
            safe_name = hashlib.md5(province.encode('utf-8')).hexdigest()[:8]
            province_dir = os.path.join(self.output_dir, safe_name)
            
            if os.path.exists(province_dir):
                # 统计该省份的瓦片
                tile_count = 0
                zoom_levels = set()
                
                for z_dir in os.listdir(province_dir):
                    z_path = os.path.join(province_dir, z_dir)
                    if os.path.isdir(z_path) and z_dir.isdigit():
                        zoom_levels.add(int(z_dir))
                        for x_dir in os.listdir(z_path):
                            x_path = os.path.join(z_path, x_dir)
                            if os.path.isdir(x_path):
                                tile_count += len([f for f in os.listdir(x_path) if f.endswith('.png')])
                
                index["provinces"][province] = {
                    "bbox": bbox,
                    "zoom_levels": sorted(list(zoom_levels)),
                    "tile_count": tile_count,
                    "directory": safe_name
                }
        
        # 添加统计信息
        file_count, total_size = self.get_storage_size()
        index["stats"] = {
            "total_tiles": file_count,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "output_dir": self.output_dir
        }
        
        # 保存索引
        index_file = os.path.join(self.output_dir, "index.json")
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        
        print(f"索引已生成: {index_file}")
        return index


def main():
    parser = argparse.ArgumentParser(description='离线地图瓦片下载工具')
    parser.add_argument('--province', type=str, help='省份名称，如"广东省"')
    parser.add_argument('--bbox', type=str, help='边界框，格式: min_lon,min_lat,max_lon,max_lat')
    parser.add_argument('--zoom', type=str, default='12-16', 
                        help='Zoom 层级范围，如 "12-16" 或 "14,15,16"')
    parser.add_argument('--output', type=str, default='offline_maps',
                        help='输出目录')
    parser.add_argument('--delay', type=float, default=0.2,
                        help='下载间隔（秒），默认0.2')
    parser.add_argument('--workers', type=int, default=4,
                        help='并发线程数，默认4')
    parser.add_argument('--list-provinces', action='store_true',
                        help='列出所有可用省份')
    parser.add_argument('--index', action='store_true',
                        help='生成索引文件')
    
    args = parser.parse_args()
    
    # 列出省份
    if args.list_provinces:
        print("可用省份列表:")
        for i, province in enumerate(TileDownloader.PROVINCE_BBOX.keys(), 1):
            print(f"  {i}. {province}")
        return
    
    # 生成索引
    if args.index:
        downloader = TileDownloader(args.output)
        index = downloader.generate_index()
        print(f"\n总瓦片数: {index['stats']['total_tiles']}")
        print(f"总大小: {index['stats']['total_size_mb']} MB")
        return
    
    # 解析 zoom 层级
    if '-' in args.zoom:
        z_min, z_max = map(int, args.zoom.split('-'))
        zoom_levels = list(range(z_min, z_max + 1))
    else:
        zoom_levels = [int(z) for z in args.zoom.split(',')]
    
    # 创建下载器
    downloader = TileDownloader(args.output, args.delay, args.workers)
    
    # 按省份下载
    if args.province:
        downloader.download_province(args.province, zoom_levels)
    
    # 按边界框下载
    elif args.bbox:
        coords = list(map(float, args.bbox.split(',')))
        if len(coords) != 4:
            print("错误: 边界框格式错误，应为 min_lon,min_lat,max_lon,max_lat")
            return
        min_lon, min_lat, max_lon, max_lat = coords
        print(f"下载区域: {min_lon},{min_lat} 到 {max_lon},{max_lat}")
        print(f"Zoom 层级: {zoom_levels}")
        downloader.download_area(min_lon, min_lat, max_lon, max_lat, zoom_levels)
    
    else:
        print("请指定 --province 或 --bbox 参数")
        print("使用 --help 查看帮助")
        return
    
    # 生成索引
    print("\n" + "=" * 50)
    downloader.generate_index()
    
    # 显示存储统计
    file_count, total_size = downloader.get_storage_size()
    print(f"\n总瓦片数: {file_count}")
    print(f"总大小: {total_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
