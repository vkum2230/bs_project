# map_service.py
import os
import json
import hashlib
import requests
import math
import time
from io import BytesIO
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from PIL import Image, ImageDraw, ImageFont


class MapDownloader(QThread):
    """后台地图下载线程"""
    download_progress = pyqtSignal(int)
    download_complete = pyqtSignal(str, bool, str)
    
    def __init__(self, province_name, lat, lon, zoom, save_path, tianditu_key):
        super().__init__()
        self.province_name = province_name
        self.lat = lat
        self.lon = lon
        self.zoom = zoom
        self.save_path = save_path
        self.tianditu_key = tianditu_key
        
    def run(self):
        try:
            result = self._download_tianditu_map()
            if result:
                self.download_complete.emit(self.province_name, True, self.save_path)
            else:
                self.download_complete.emit(self.province_name, False, "")
        except Exception as e:
            print(f"下载地图失败 {self.province_name}: {e}")
            self.download_complete.emit(self.province_name, False, "")
    
    def _deg2num(self, lat_deg, lon_deg, zoom):
        """经纬度转瓦片坐标"""
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (xtile, ytile)
    
    def _download_tile(self, url, retries=3):
        """下载单张瓦片"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        }
        for i in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    return Image.open(BytesIO(response.content))
                elif response.status_code == 429:
                    time.sleep(0.5 * (i + 1))
            except Exception as e:
                if i == retries - 1:
                    raise e
                time.sleep(0.5)
        return None
    
    def _download_tianditu_map(self):
        """下载天地图瓦片并拼接"""
        center_x, center_y = self._deg2num(self.lat, self.lon, self.zoom)
        
        tile_size = 256
        grid_size = 3
        canvas = Image.new('RGB', (tile_size * grid_size, tile_size * grid_size), '#2A2A2A')
        
        tiles_downloaded = 0
        total_tiles = grid_size * grid_size
        servers = ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7']
        
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                x = center_x + dx
                y = center_y + dy
                
                max_tile = 2 ** self.zoom
                if x < 0 or x >= max_tile or y < 0 or y >= max_tile:
                    continue
                
                server = servers[(x + y) % 8]
                
                # 矢量底图
                base_url = f"http://{server}.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={self.zoom}&TILEROW={y}&TILECOL={x}&tk={self.tianditu_key}"
                
                # 标注层
                label_url = f"http://{server}.tianditu.gov.cn/cva_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cva&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={self.zoom}&TILEROW={y}&TILECOL={x}&tk={self.tianditu_key}"
                
                try:
                    base_tile = self._download_tile(base_url)
                    if base_tile:
                        # 尝试下载标注层
                        try:
                            label_tile = self._download_tile(label_url)
                            if label_tile:
                                # 确保RGBA模式
                                base_rgba = base_tile.convert('RGBA')
                                label_rgba = label_tile.convert('RGBA')
                                base_tile = Image.alpha_composite(base_rgba, label_rgba).convert('RGB')
                            else:
                                base_tile = base_tile.convert('RGB')
                        except:
                            base_tile = base_tile.convert('RGB')
                        
                        paste_x = (dx + 1) * tile_size
                        paste_y = (dy + 1) * tile_size
                        canvas.paste(base_tile, (paste_x, paste_y))
                        tiles_downloaded += 1
                        
                        progress = int(tiles_downloaded * 100 / total_tiles)
                        self.download_progress.emit(progress)
                        
                        time.sleep(0.1)  # 礼貌延迟
                        
                except Exception as e:
                    print(f"瓦片下载失败 ({x},{y}): {e}")
                    continue
        
        # 标记当前位置
        self._mark_position(canvas, tile_size, grid_size)
        
        if tiles_downloaded > 0:
            canvas.save(self.save_path, 'PNG')
            print(f"地图保存成功: {self.save_path}")
            return True
        return False
    
    def _mark_position(self, canvas, tile_size, grid_size):
        """在中心标记位置"""
        draw = ImageDraw.Draw(canvas)
        center_x = tile_size * grid_size // 2
        center_y = tile_size * grid_size // 2
        
        # 红色定位圆点
        marker_size = 10
        draw.ellipse(
            [center_x - marker_size, center_y - marker_size,
             center_x + marker_size, center_y + marker_size],
            fill='#e74c3c', outline='#FFFFFF', width=3
        )
        
        # 十字线
        line_len = 25
        draw.line([center_x - line_len, center_y, center_x + line_len, center_y], 
                 fill='#e74c3c', width=2)
        draw.line([center_x, center_y - line_len, center_x, center_y + line_len], 
                 fill='#e74c3c', width=2)


class MapService(QObject):
    def __init__(self, cache_dir="maps", tianditu_key=""):
        super().__init__()
        self.cache_dir = cache_dir
        self.tianditu_key = tianditu_key
        os.makedirs(cache_dir, exist_ok=True)
        
        self.index_path = os.path.join(cache_dir, "index.json")
        self.index_data = self._load_index()
        
    def _load_index(self):
        try:
            with open(self.index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_index(self):
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(self.index_data, f, ensure_ascii=False, indent=2)
    
    def _get_safe_name(self, province_name):
        return hashlib.md5(province_name.encode('utf-8')).hexdigest()[:8]
    
    def has_local_map(self, province_name, map_type="overview"):
        safe_name = self._get_safe_name(province_name)
        map_path = os.path.join(self.cache_dir, f"{safe_name}_{map_type}.png")
        exists = os.path.exists(map_path) and os.path.getsize(map_path) > 1024
        return exists, map_path
    
    def download_map(self, province_name, lat, lon, zoom=11,
                     progress_callback=None, complete_callback=None):
        """启动地图下载"""
        exists, path = self.has_local_map(province_name, "overview")
        if exists:
            if complete_callback:
                complete_callback(province_name, True, path)
            return None
        
        if not self.tianditu_key:
            print("警告：未配置天地图Key")
            path = self._generate_placeholder(province_name, lat, lon)
            if complete_callback:
                complete_callback(province_name, True, path)
            return None
        
        safe_name = self._get_safe_name(province_name)
        save_path = os.path.join(self.cache_dir, f"{safe_name}_overview.png")
        
        self.index_data[safe_name] = {
            "province": province_name,
            "lat": lat,
            "lon": lon,
            "zoom": zoom
        }
        self._save_index()
        
        downloader = MapDownloader(province_name, lat, lon, zoom, save_path, self.tianditu_key)
        
        if progress_callback:
            downloader.download_progress.connect(progress_callback)
        if complete_callback:
            downloader.download_complete.connect(complete_callback)
            
        downloader.start()
        return downloader
    
    def _generate_placeholder(self, province_name, lat, lon):
        """生成占位图"""
        safe_name = self._get_safe_name(province_name)
        save_path = os.path.join(self.cache_dir, f"{safe_name}_overview.png")
        
        img = Image.new('RGB', (400, 300), color='#2A2A2A')
        draw = ImageDraw.Draw(img)
        
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            font_large = ImageFont.load_default()
            font_small = font_large
        
        y = 80
        draw.text((200, y), f"📍 {province_name}", fill='#4DB8FF', font=font_large, anchor="mm")
        y += 50
        draw.text((200, y), "未配置地图Key", fill='#e74c3c', font=font_small, anchor="mm")
        y += 40
        draw.text((200, y), f"{lat:.4f}°N, {lon:.4f}°E", fill='#FFFFFF', font=font_small, anchor="mm")
        
        img.save(save_path)
        return save_path
    
    def get_cached_provinces(self):
        return [info["province"] for info in self.index_data.values()]