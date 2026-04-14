#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全局串口日志重定向器"""

import sys
import serial


class SerialDebugger:
    def __init__(self, port='/dev/ttyAMA10', baudrate=115200):
        try:
            self.debug_serial = serial.Serial(port, baudrate, timeout=1)
            self.original_stdout = sys.stdout
            boot_msg = "\r\n" + "="*40 + "\r\n  SMART RIDE SYSTEM DEBUG ONLINE\r\n" + "="*40 + "\r\n"
            self.debug_serial.write(boot_msg.encode('utf-8'))
            sys.stdout = self
        except Exception as e:
            print(f"无法打开调试串口 {port}: {e}")
            self.debug_serial = None

    def write(self, message):
        self.original_stdout.write(message)
        if self.debug_serial and self.debug_serial.is_open:
            try:
                msg_crlf = message.replace('\n', '\r\n')
                self.debug_serial.write(msg_crlf.encode('utf-8'))
                self.debug_serial.flush()
            except Exception as e:
                # 调试串口写入失败时不应导致主程序崩溃
                self.original_stdout.write(f"\n[SerialDebugger] 调试串口写入失败: {e}\n")
                try:
                    self.debug_serial.close()
                except Exception:
                    pass
                self.debug_serial = None

    def flush(self):
        self.original_stdout.flush()

    def stop(self):
        if self.debug_serial and self.debug_serial.is_open:
            self.debug_serial.close()
            sys.stdout = self.original_stdout
