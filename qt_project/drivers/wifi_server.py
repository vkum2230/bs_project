#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WiFi WebSocket 服务器（基于本地 asyncio + websockets）

设计说明：
- 树莓派作为 WebSocket Server，手机 App 作为 Client 连接
- 与 test_mqtt.py 的 MQTT 客户端不同，这里采用本地 Server 模式
- 支持：实时数据广播、App 命令接收、历史文件传输、断连补发推送

职责：
- 在指定端口（默认 8765）监听 WebSocket 连接
- 向所有已连接客户端广播 JSON 消息
- 接收并转发 App 命令到 CommService
"""

import asyncio
import json
import threading
import time
from typing import Set, Optional
from PyQt5.QtCore import QThread, pyqtSignal


class WifiServer(QThread):
    """WebSocket 服务器 - 在独立线程的 asyncio 事件循环中运行"""

    client_connected = pyqtSignal(str)      # 参数: 客户端地址
    client_disconnected = pyqtSignal(str)   # 参数: 客户端地址
    command_received = pyqtSignal(str)      # 收到 App 发来的 JSON 命令
    error_occurred = pyqtSignal(str)        # 错误信息

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        super().__init__()
        self.host = host
        self.port = port
        self._clients: Set = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server = None
        self._running = False
        self._lock = threading.Lock()

    def run(self):
        """在独立线程中启动 asyncio 事件循环"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._running = True

        async def _start():
            import websockets
            self._server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port,
            )
            print(f"[WifiServer] WebSocket 服务已启动: ws://{self.host}:{self.port}")
            return self._server

        try:
            self._loop.run_until_complete(_start())
            self._loop.run_forever()
        except Exception as e:
            err_msg = f"[WifiServer] 服务异常: {e}"
            print(err_msg)
            self.error_occurred.emit(err_msg)
        finally:
            self._cleanup()

    async def _handle_client(self, websocket, path):
        """处理单个 WebSocket 客户端连接"""
        addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        with self._lock:
            self._clients.add(websocket)
        print(f"[WifiServer] App 已连接: {addr}")
        self.client_connected.emit(addr)

        # 发送连接成功确认
        await self._send_to(websocket, json.dumps({
            "event": "connected",
            "msg": "SMART RIDE WiFi ready",
            "timestamp": time.time(),
        }, ensure_ascii=False))

        try:
            async for message in websocket:
                msg = message.strip() if isinstance(message, str) else message.decode("utf-8").strip()
                if msg:
                    print(f"[WifiServer] 收到命令: {msg}")
                    self.command_received.emit(msg)
        except Exception as e:
            print(f"[WifiServer] 客户端 {addr} 异常: {e}")
        finally:
            with self._lock:
                self._clients.discard(websocket)
            print(f"[WifiServer] App 已断开: {addr}")
            self.client_disconnected.emit(addr)

    async def _send_to(self, websocket, message: str):
        """向单个客户端发送消息"""
        try:
            await websocket.send(message)
        except Exception:
            pass

    def broadcast(self, message: str):
        """向所有已连接客户端广播消息（线程安全）"""
        if not (self._loop and self._loop.is_running() and self.isRunning()):
            return
        try:
            # 用 call_soon_threadsafe 把任务投递到事件循环线程，
            # 避免 asyncio.run_coroutine_threadsafe 在部分环境下抛 "no running event loop"
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._broadcast_async(message))
            )
        except RuntimeError as e:
            # 兜底：如果事件循环已停止或不可用，静默丢弃
            print(f"[WifiServer] broadcast 投递失败: {e}")
        except Exception as e:
            print(f"[WifiServer] broadcast 异常: {e}")

    def broadcast_binary(self, data: bytes):
        """向所有已连接客户端广播二进制消息（线程安全）"""
        if not (self._loop and self._loop.is_running() and self.isRunning()):
            return
        try:
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._broadcast_binary_async(data))
            )
        except Exception as e:
            print(f"[WifiServer] broadcast_binary 异常: {e}")

    async def _broadcast_async(self, message: str):
        """异步广播实现"""
        with self._lock:
            clients = list(self._clients)
        if not clients:
            return
        tasks = [self._send_to(ws, message) for ws in clients]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _broadcast_binary_async(self, data: bytes):
        """异步广播二进制实现"""
        with self._lock:
            clients = list(self._clients)
        if not clients:
            return
        tasks = [self._send_binary_to(ws, data) for ws in clients]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_binary_to(self, websocket, data: bytes):
        """向单个客户端发送二进制消息"""
        try:
            await websocket.send(data)
        except Exception:
            pass

    def has_connected_client(self) -> bool:
        """是否有 App 已连接"""
        with self._lock:
            return len(self._clients) > 0

    def stop(self):
        """停止服务"""
        self._running = False
        if self._loop:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
        self.wait(3000)

    def _cleanup(self):
        with self._lock:
            self._clients.clear()
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
        if self._loop:
            try:
                self._loop.close()
            except Exception:
                pass


if __name__ == "__main__":
    import sys
    from PyQt5.QtCore import QCoreApplication

    app = QCoreApplication(sys.argv)

    server = WifiServer()
    server.client_connected.connect(lambda addr: print(f"信号: 连接 {addr}"))
    server.client_disconnected.connect(lambda addr: print(f"信号: 断开 {addr}"))
    server.command_received.connect(lambda cmd: print(f"信号: 命令 {cmd}"))

    server.start()

    # 测试广播
    def test_broadcast():
        import time
        time.sleep(2)
        while server.isRunning():
            server.broadcast(json.dumps({"test": 1, "time": time.time()}))
            time.sleep(3)

    t = threading.Thread(target=test_broadcast, daemon=True)
    t.start()

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        server.stop()
