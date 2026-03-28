import json
import os
from shapely.geometry import shape, Point
from rtree import index

class LocationService:
    def __init__(self, geojson_path=None):
        self.idx = index.Index()
        self.provinces = []
        
        # 如果没有提供路径，使用内嵌的简化数据
        if geojson_path and os.path.exists(geojson_path):
            self._load_data(geojson_path)
        else:
            self._load_embedded_data()
        
    def _load_data(self, path):
        """加载GeoJSON并构建空间索引"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for i, feature in enumerate(data['features']):
            province_name = feature['properties']['name']
            geometry = shape(feature['geometry'])
            self.provinces.append({
                'name': province_name,
                'geometry': geometry,
                'bounds': geometry.bounds
            })
            self.idx.insert(i, geometry.bounds)
            
        print(f"已加载 {len(self.provinces)} 个省级行政区")

    def _load_embedded_data(self):
        """加载内嵌的简化省份边界数据"""
        # 简化的中国省份边界框数据（经纬度范围）
        # 实际使用时建议替换为完整GeoJSON文件
        province_boxes = {
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
        
        # 构建简单索引
        for i, (name, (min_lon, min_lat, max_lon, max_lat)) in enumerate(province_boxes.items()):
            self.provinces.append({
                'name': name,
                'bounds': (min_lon, min_lat, max_lon, max_lat),
                'is_box': True  # 标记为边界框模式
            })
            self.idx.insert(i, (min_lon, min_lat, max_lon, max_lat))
            
        print(f"已加载 {len(self.provinces)} 个省级行政区（边界框模式）")
    
    def get_province(self, lon, lat):
        """
        根据经纬度查询所在省份
        返回: 省份名称 或 None
        """
        point = (lon, lat)
        
        # 快速筛选候选区域
        candidates = list(self.idx.intersection((lon, lat, lon, lat)))
        
        for cid in candidates:
            province = self.provinces[cid]
            bounds = province['bounds']
            
            # 边界框判断
            if bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3]:
                return province['name']
                
        return None
    
    def get_location_info(self, lon, lat):
        """获取完整位置信息"""
        province = self.get_province(lon, lat)
        if province:
            return {
                'province': province,
                'lat': lat,
                'lon': lon,
                'display': f"{province} · {lat:.4f}°N {lon:.4f}°E"
            }
        return {
            'province': None,
            'lat': lat,
            'lon': lon,
            'display': f"未知区域 · {lat:.4f}°N {lon:.4f}°E"
        }