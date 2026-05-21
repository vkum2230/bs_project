import serial
import json
import time
from PyQt5.QtCore import QThread, pyqtSignal, QTimer

class SerialReader(QThread):
    data_received = pyqtSignal(dict)
    status_signal = pyqtSignal(bool)

    def __init__(self, port='/dev/ttyAMA2', baudrate=115200, max_buffer_size=1024):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.buffer = ""
        self.max_buffer_size = max_buffer_size  # 最大缓冲区大小

    def run(self):
        ser = None
        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            ser.flush()
            self.status_signal.emit(True)
            print(f"成功打开串口: {self.port}")

            while self.running:
                if ser.in_waiting > 0:
                    try:
                        # 一次性读取所有可用数据
                        chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                        self.buffer += chunk

                        # 限制缓冲区大小，防止内存爆炸
                        if len(self.buffer) > self.max_buffer_size:
                            print(f"[Serial] 缓冲区溢出，丢弃旧数据 ({len(self.buffer)} bytes)")
                            self.buffer = self.buffer[-self.max_buffer_size:]

                        # 处理缓冲区中的所有完整 JSON
                        while True:
                            json_obj = self._extract_json(self.buffer)
                            if json_obj:
                                self.buffer = self.buffer[json_obj['end_pos']:]
                                self.data_received.emit(json_obj)
                            else:
                                break
                    except UnicodeDecodeError:
                        # 忽略解码错误，继续处理
                        pass
                    except Exception as e:
                        print(f"处理异常: {e}")
                        self.buffer = ""
                self.msleep(20)  # 增加到20ms，避免CPU占用过高
        except Exception as e:
            print(f"无法打开串口 {self.port}: {e}")
            self.status_signal.emit(False)
        finally:
            if ser and ser.is_open:
                ser.close()

    def _extract_json(self, text):
        """从文本中提取第一个完整的 JSON 对象，返回带结束位置的结果"""
        start = text.find('{')
        if start == -1:
            return None
        count = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                count += 1
            elif text[i] == '}':
                count -= 1
                if count == 0:
                    json_str = text[start:i+1]
                    try:
                        result = json.loads(json_str)
                        result['end_pos'] = i + 1  # 标记结束位置
                        return result
                    except json.JSONDecodeError:
                        return None
        return None

    def stop(self):
        self.running = False
        self.quit()
        self.wait()