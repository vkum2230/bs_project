#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蓝牙服务器（基于经典蓝牙 RFCOMM）

设计说明：
- 本模块参考 test_ble.py 的经典蓝牙 Socket 实现
- 为了快速稳定地实现双向通信，采用 RFCOMM 串口透传模式
- 如需对接标准骑行 App（Zwift/Wahoo），未来可替换为 BLE GATT 实现

职责：
- 作为蓝牙服务端等待手机 App 连接
- 接收 App 发来的命令（JSON 字符串）
- 通过队列向 App 推送实时数据/事件
"""

import socket
import json
import queue
import subprocess
import threading
import time
from typing import Optional, Callable
from PyQt5.QtCore import QThread, pyqtSignal


class BleServer(QThread):
    """蓝牙 RFCOMM 服务器 - 在独立线程中运行"""

    client_connected = pyqtSignal(str)      # 参数: 客户端 MAC 地址
    client_disconnected = pyqtSignal()      # 客户端断开
    command_received = pyqtSignal(str)      # 收到 App 发来的 JSON 命令
    error_occurred = pyqtSignal(str)        # 错误信息

    def __init__(self, host_address: str = "2C:CF:67:F2:ED:B2", port: int = 1):
        super().__init__()
        self.host_address = host_address
        self.port = port
        self.server_sock: Optional[socket.socket] = None
        self.client_sock: Optional[socket.socket] = None
        self.client_addr: Optional[str] = None
        self._running = False
        self._send_queue = queue.Queue()
        self._lock = threading.Lock()

    @staticmethod
    def _setup_bluetooth(port: int = 1):
        """自动注册 SDP 服务并设置蓝牙可被发现/可连接"""
        # 1. 尝试注册 RFCOMM 串口服务 (SPP)
        # 先尝试不加 sudo，失败再加 sudo
        for cmd_prefix in ([], ["sudo"]):
            cmd = cmd_prefix + ["sdptool", "add", f"--channel={port}", "SP"]
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=5, check=False
                )
                if result.returncode == 0:
                    print(f"[BleServer] SDP 服务注册成功: {' '.join(cmd)}")
                    break
            except FileNotFoundError:
                # sdptool 不存在，跳到 btmgmt fallback
                break
            except Exception as e:
                print(f"[BleServer] SDP 注册尝试失败 ({' '.join(cmd)}): {e}")
        else:
            # 两个都失败了，尝试 btmgmt (新系统 fallback)
            try:
                subprocess.run(
                    ["sudo", "btmgmt", "add-uuid", "1101", "/rfcomm0"],
                    capture_output=True, text=True, timeout=5, check=False
                )
                print("[BleServer] 尝试通过 btmgmt 注册 UUID")
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"[BleServer] btmgmt 注册失败: {e}")

        # 2. 设置蓝牙可被发现、可连接
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
                    # 可能是 hci0 down，尝试先 up
                    up_cmd = cmd_prefix + ["hciconfig", "hci0", "up"]
                    subprocess.run(up_cmd, capture_output=True, timeout=5, check=False)
                    result2 = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
                    if result2.returncode == 0:
                        print(f"[BleServer] 蓝牙已唤醒并设置为可发现/可连接")
                        break
            except FileNotFoundError:
                break
            except Exception as e:
                print(f"[BleServer] 设置蓝牙可发现失败: {e}")

    def run(self):
        """主线程：监听连接 + 接收数据 + 发送数据"""
        self._setup_bluetooth(self.port)
        self._running = True
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

                with self._lock:
                    self.client_sock = client_sock
                    self.client_addr = client_info[0]

                print(f"[BleServer] App 已连接: {self.client_addr}")
                self.client_connected.emit(self.client_addr)

                # 发送欢迎消息
                self._send_raw(b"{\"event\":\"connected\",\"msg\":\"SMART RIDE ready\"}\r\n")

                # 进入与该客户端的通信循环
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
        sock.settimeout(0.05)  # 非阻塞式接收，让发送有机会执行
        buffer = b""

        while self._running:
            # 1. 尝试接收数据
            try:
                data = sock.recv(1024)
                if not data:
                    break
                buffer += data
                # 按换行符分割处理多条命令
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

            # 2. 尝试发送队列中的数据（非阻塞取）
            try:
                payload = self._send_queue.get_nowait()
                if isinstance(payload, str):
                    payload = payload.encode("utf-8")
                if not payload.endswith(b"\r\n"):
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

    server.start()

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        server.stop()
