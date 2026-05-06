#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BLE GATT 服务器独立测试脚本

用法：
    cd /home/hedya/Desktop/bs_project/qt_project
    sudo python3 tests/test_ble_gatt.py

功能：
    - 单独启动 BLE GATT 服务器（不依赖 main.py）
    - 打印所有调试日志
    - 支持键盘发送测试消息
    - 测试 App 连接、数据收发

退出：按 Ctrl+C
"""

import sys
import os
import time
import threading

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import QCoreApplication
from drivers.ble_gatt_server import BleGattServer


def main():
    app = QCoreApplication(sys.argv)
    server = BleGattServer(device_name="SMART-RIDE")

    server.client_connected.connect(lambda addr: print(f"\n>>> [信号] 客户端连接: {addr}\n"))
    server.client_disconnected.connect(lambda: print(f"\n>>> [信号] 客户端断开\n"))
    server.command_received.connect(lambda cmd: print(f"\n>>> [信号] 收到命令: {cmd}\n"))
    server.error_occurred.connect(lambda e: print(f"\n>>> [信号] 错误: {e}\n"))
    server.advertising_started.connect(lambda: print(f"\n>>> [信号] 广播已启动\n"))
    server.advertising_stopped.connect(lambda: print(f"\n>>> [信号] 广播已停止\n"))

    print("=" * 60)
    print("BLE GATT 服务器测试工具")
    print("=" * 60)
    print("\n命令:")
    print("  start  - 开始广播")
    print("  stop   - 停止广播")
    print("  send   - 发送测试消息到已连接的 App")
    print("  status - 查看连接状态")
    print("  quit   - 退出")
    print("=" * 60)
    print()

    # 自动开始广播
    server.start_advertising()

    # 键盘输入线程
    def input_loop():
        while True:
            try:
                cmd = input("cmd> ").strip()
            except EOFError:
                break

            if cmd == "start":
                if not server._advertising:
                    server.start_advertising()
                else:
                    print("广播已经在运行中")

            elif cmd == "stop":
                server.stop_advertising()

            elif cmd == "send":
                if not server.has_connected_client():
                    print("没有已连接的客户端，无法发送")
                    continue
                print("输入要发送的 JSON 消息（回车结束）：")
                try:
                    msg = input("json> ").strip()
                except EOFError:
                    continue
                if msg:
                    server.notify(msg)
                    print(f"已放入发送队列: {msg}")

            elif cmd == "status":
                print(f"  广播中: {server._advertising}")
                print(f"  运行中: {server._running}")
                print(f"  有客户端: {server.has_connected_client()}")
                print(f"  队列大小: {server._send_queue.qsize()}")
                if server._app:
                    print(f"  notifying: {server._app.service.notify_char.notifying}")

            elif cmd == "quit":
                print("正在退出...")
                server.stop()
                app.quit()
                break

            else:
                print(f"未知命令: {cmd}")

    t = threading.Thread(target=input_loop, daemon=True)
    t.start()

    try:
        app.exec_()
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，正在退出...")
    finally:
        server.stop()
        print("已退出")


if __name__ == "__main__":
    main()
