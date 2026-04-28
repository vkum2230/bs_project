#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蓝牙服务器（基于经典蓝牙 RFCOMM）— xinjia.txt 协议

设计说明：
- 采用按钮触发广播模式：用户点击"开始广播"后才启动蓝牙监听
- 其它设备可以连接到树莓派进行串口通信
- 树莓派物理地址: 2C:CF:67:F2:ED:B2
- 连接成功后发送握手帧: {"isConnect":"OK"}
"""

import socket
import json
import queue
import subprocess
import threading
import time
from typing import Optional
from PyQt5.QtCore import QThread, pyqtSignal


class BleServer(QThread):
    """蓝牙 RFCOMM 服务器 — 按钮触发广播模式"""

    client_connected = pyqtSignal(str)      # 参数: 客户端 MAC 地址
    client_disconnected = pyqtSignal()      # 客户端断开
    command_received = pyqtSignal(str)      # 收到 App 发来的 JSON 命令
    error_occurred = pyqtSignal(str)        # 错误信息
    advertising_started = pyqtSignal()      # 广播已启动
    advertising_stopped = pyqtSignal()      # 广播已停止

    def __init__(self, host_address: str = "2C:CF:67:F2:ED:B2", port: int = 1):
        super().__init__()
        self.host_address = host_address
        self.port = port
        self.server_sock: Optional[socket.socket] = None
        self.client_sock: Optional[socket.socket] = None
        self.client_addr: Optional[str] = None
        self._running = False
        self._advertising = False
        self._send_queue = queue.Queue()
        self._lock = threading.Lock()
        self.connected_at: float = 0.0

    @staticmethod
    def _setup_bluetooth(port: int = 1):
        """自动注册 SDP 服务并设置蓝牙可被发现/可连接"""
        for cmd_prefix in ([], ["sudo"]):
            cmd = cmd_prefix + ["sdptool", "add", f"--channel={port}", "SP"]
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=5, check=False
                )
                if result.returncode == 0:
                    print(f"[BleServer] SDP 服务注册成功")
                    break
            except FileNotFoundError:
                break
            except Exception:
                pass
        else:
            try:
                subprocess.run(
                    ["sudo", "btmgmt", "add-uuid", "1101", "/rfcomm0"],
                    capture_output=True, text=True, timeout=5, check=False
                )
            except FileNotFoundError:
                pass
            except Exception:
                pass

        for cmd_prefix in ([], ["sudo"]):
            cmd = cmd_prefix + ["hciconfig", "hci0", "piscan"]
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=5, check=False
                )
                if result.returncode == 0:
                    print(f"[BleServer] 蓝牙已设置为可发现/可连接")
                    break
                else:
                    up_cmd = cmd_prefix + ["hciconfig", "hci0", "up"]
                    subprocess.run(up_cmd, capture_output=True, timeout=5, check=False)
                    result2 = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
                    if result2.returncode == 0:
                        print(f"[BleServer] 蓝牙已唤醒并设置为可发现/可连接")
                        break
            except FileNotFoundError:
                break
            except Exception:
                pass

    def start_advertising(self):
        """开始蓝牙广播（由按钮触发）"""
        if self._advertising or self._running:
            return
        self._advertising = True
        self._running = True
        self.start()
        self.advertising_started.emit()
        print("[BleServer] 蓝牙广播已启动")

    def stop_advertising(self):
        """停止蓝牙广播"""
        self._advertising = False
        self._running = False
        self._cleanup()
        self.advertising_stopped.emit()
        print("[BleServer] 蓝牙广播已停止")

    def run(self):
        """主线程：监听连接 + 接收数据 + 发送数据"""
        self._setup_bluetooth(self.port)
        try:
            self.server_sock = socket.socket(
                socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM
            )
            self.server_sock.bind((self.host_address, self.port))
            self.server_sock.listen(1)
            print(f"[BleServer] 蓝牙服务已启动，等待连接...")

            while self._running:
                try:
                    self.server_sock.settimeout(1.0)
                    client_sock, client_info = self.server_sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                with self._lock:
                    self.client_sock = client_sock
                    self.client_addr = client_info[0]

                self.connected_at = time.time()
                print(f"[BleServer] App 已连接: {self.client_addr}")
                self.client_connected.emit(self.client_addr)

                # xinjia.txt 握手帧
                self._send_raw(b'{"isConnect":"OK"}\r\n')

                self._handle_client(client_sock)

                with self._lock:
                    self.client_sock = None
                    self.client_addr = None

                self.client_disconnected.emit()
                print("[BleServer] App 已断开，等待下一次连接...")

        except Exception as e:
            err_msg = f"[BleServer] 服务异常: {e}"
            print(err_msg)
            self.error_occurred.emit(err_msg)
        finally:
            self._cleanup()

    def _handle_client(self, sock: socket.socket):
        """处理单个客户端的连接生命周期"""
        sock.settimeout(0.05)
        buffer = b""

        while self._running:
            try:
                data = sock.recv(1024)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    msg = line.decode("utf-8", errors="ignore").strip()
                    if msg:
                        print(f"[BleServer] 收到命令: {msg}")
                        self.command_received.emit(msg)
            except socket.timeout:
                pass
            except Exception as e:
                print(f"[BleServer] 接收异常: {e}")
                break

            try:
                payload = self._send_queue.get_nowait()
                if isinstance(payload, str):
                    payload = payload.encode("utf-8")
                if payload.startswith(b"{") and not payload.endswith(b"\r\n"):
                    payload += b"\r\n"
                sock.sendall(payload)
            except queue.Empty:
                pass
            except Exception as e:
                print(f"[BleServer] 发送异常: {e}")
                break

        try:
            sock.close()
        except Exception:
            pass

    def _send_raw(self, payload: bytes):
        """直接发送字节（不经过队列，仅内部使用）"""
        if self.client_sock:
            try:
                self.client_sock.sendall(payload)
            except Exception:
                pass

    def notify(self, payload: bytes or str):
        """向已连接的 App 推送数据（放入发送队列）"""
        if self.has_connected_client():
            self._send_queue.put(payload)

    def has_connected_client(self) -> bool:
        """是否有 App 已连接"""
        with self._lock:
            return self.client_sock is not None

    def stop(self):
        """停止服务"""
        self._running = False
        self._advertising = False
        self._cleanup()
        self.wait(2000)

    def _cleanup(self):
        with self._lock:
            if self.client_sock:
                try:
                    self.client_sock.close()
                except Exception:
                    pass
                self.client_sock = None
            if self.server_sock:
                try:
                    self.server_sock.close()
                except Exception:
                    pass
                self.server_sock = None


if __name__ == "__main__":
    import sys
    from PyQt5.QtCore import QCoreApplication

    app = QCoreApplication(sys.argv)
    server = BleServer()
    server.client_connected.connect(lambda addr: print(f"信号: 连接 {addr}"))
    server.client_disconnected.connect(lambda: print("信号: 断开"))
    server.command_received.connect(lambda cmd: print(f"信号: 命令 {cmd}"))
    server.start_advertising()
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        server.stop()
