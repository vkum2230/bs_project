#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地 HTTP 瓦片服务器
为离线地图提供本地瓦片文件服务
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote


class TileRequestHandler(BaseHTTPRequestHandler):
    """处理瓦片请求"""

    # 类变量：瓦片根目录
    tiles_root = "maps/xiangtan_tiles"

    def log_message(self, format, *args):
        """抑制默认日志输出，减少控制台噪音"""
        pass

    def do_GET(self):
        """处理 GET 请求"""
        path = unquote(self.path)

        # 瓦片路径格式: /{z}/{x}/{y}.png
        if path.endswith('.png'):
            parts = path.strip('/').split('/')
            if len(parts) == 3:
                z, x, y = parts
                tile_path = os.path.join(self.tiles_root, z, x, y)

                if os.path.exists(tile_path):
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    with open(tile_path, 'rb') as f:
                        self.wfile.write(f.read())
                    return

        #  favicon.ico 或其他请求返回 404
        self.send_response(404)
        self.end_headers()


class TileServer:
    """本地瓦片服务器"""

    def __init__(self, tiles_root="maps/xiangtan_tiles", port=8766):
        """
        初始化瓦片服务器

        Args:
            tiles_root: 瓦片文件根目录
            port: 服务端口，默认 8766
        """
        self.tiles_root = tiles_root
        self.port = port
        self.server = None
        self.thread = None
        self._running = False

    def start(self):
        """启动服务器（后台线程）"""
        if self._running:
            print(f"[TileServer] 服务器已在运行 (端口 {self.port})")
            return

        # 解析为绝对路径
        abs_root = os.path.abspath(self.tiles_root)
        if not os.path.exists(abs_root):
            print(f"[TileServer] 警告: 瓦片目录不存在: {abs_root}")

        TileRequestHandler.tiles_root = abs_root

        try:
            self.server = HTTPServer(("0.0.0.0", self.port), TileRequestHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self._running = True
            print(f"[TileServer] 瓦片服务器已启动: http://localhost:{self.port}")
            print(f"[TileServer] 瓦片根目录: {abs_root}")
        except Exception as e:
            print(f"[TileServer] 启动失败: {e}")

    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            self.server = None
        self._running = False
        print("[TileServer] 瓦片服务器已停止")

    @property
    def is_running(self):
        return self._running

    @property
    def url(self):
        """获取瓦片服务 URL 模板"""
        return f"http://localhost:{self.port}/{{z}}/{{x}}/{{y}}.png"


# 全局单例
_tile_server_instance = None


def get_tile_server(tiles_root="maps/xiangtan_tiles", port=8766) -> TileServer:
    """获取全局瓦片服务器实例（懒加载）"""
    global _tile_server_instance
    if _tile_server_instance is None:
        _tile_server_instance = TileServer(tiles_root, port)
    return _tile_server_instance


if __name__ == "__main__":
    server = TileServer()
    server.start()
    print("按 Ctrl+C 停止...")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
