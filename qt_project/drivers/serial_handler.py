import serial
import json
import time
from PyQt5.QtCore import QThread, pyqtSignal

class SerialReader(QThread):
    data_received = pyqtSignal(dict)
    status_signal = pyqtSignal(bool)

    def __init__(self, port='/dev/ttyAMA2', baudrate=115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.buffer = ""

    def run(self):
        ser = None
        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=1)
            ser.flush()
            self.status_signal.emit(True)
            print(f"成功打开串口: {self.port}")

            while self.running:
                if ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode('utf-8')
                        self.buffer += line
                        json_obj = self._extract_json(self.buffer)
                        if json_obj:
                            self.buffer = ""
                            # 过滤掉 location 数据中的原始字段，保留处理后的
                            if 'location' in json_obj:
                                # 保留 location 供主程序处理
                                pass
                            self.data_received.emit(json_obj)
                    except UnicodeDecodeError:
                        self.buffer = ""
                    except Exception as e:
                        print(f"处理异常: {e}")
                        self.buffer = ""
                self.msleep(10)
        except Exception as e:
            print(f"无法打开串口 {self.port}: {e}")
            self.status_signal.emit(False)
        finally:
            if ser and ser.is_open:
                ser.close()

    def _extract_json(self, text):
        """从文本中提取第一个完整的 JSON 对象"""
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
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        return None
        return None

    def stop(self):
        self.running = False
        self.quit()
        self.wait()