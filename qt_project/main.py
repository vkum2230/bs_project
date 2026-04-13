#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import socket
import os
import serial
import json
import math
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QHBoxLayout, QFrame, QPushButton, QStackedWidget,
                             QGridLayout, QSizePolicy, QWidget)
from PyQt5.QtCore import QTimer, QDateTime, Qt, QRect
from PyQt5.QtGui import QFont, QPixmap, QCursor, QPainter, QColor, QPen, QFontMetrics

os.environ["QT_WAYLAND_DISABLE_WINDOWDECORATION"] = "1"

from serial_handler import SerialReader
from location_service import LocationService
from map_widget import MapWidget
from voice_driver import VoicePlayer, LEDController
from voice_driver.voice_recorder import ButtonVoiceAssistant
from ollama_client import OllamaClient, DEFAULT_SYSTEM_PROMPT


class SerialDebugger:
    """全局串口日志重定向器"""
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
            msg_crlf = message.replace('\n', '\r\n')
            self.debug_serial.write(msg_crlf.encode('utf-8'))
            self.debug_serial.flush()

    def flush(self):
        self.original_stdout.flush()
        
    def stop(self):
        if self.debug_serial and self.debug_serial.is_open:
            self.debug_serial.close()
            sys.stdout = self.original_stdout


class CircleGauge(QWidget):
    """圆形仪表盘"""
    def __init__(self, title, unit, max_value, color1="#4DB8FF", parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.max_value = max_value
        self.color1 = QColor(color1)
        self.value = 0.0
        self.setMinimumSize(170, 170)
        self.setMaximumSize(190, 190)
        
    def set_value(self, value):
        self.value = float(value)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        size = min(width, height) - 8
        rect = QRect((width - size) // 2, (height - size) // 2, size, size)
        
        # 背景圆环
        pen_bg = QPen(QColor("#3A3A3A"))
        pen_bg.setWidth(10)
        painter.setPen(pen_bg)
        painter.drawEllipse(rect)
        
        # 进度圆弧
        angle = int(270 * min(self.value / self.max_value, 1.0))
        pen_arc = QPen(self.color1)
        pen_arc.setWidth(10)
        pen_arc.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_arc)
        painter.drawArc(rect, 225 * 16, -angle * 16)
        
        # 中心数值
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Arial", 32, QFont.Bold)
        painter.setFont(font)
        value_text = f"{self.value:.1f}" if self.value < 100 else f"{int(self.value)}"
        fm = QFontMetrics(font)
        text_rect = fm.boundingRect(value_text)
        painter.drawText((width - text_rect.width()) // 2, height // 2 - 8, value_text)
        
        # 单位
        painter.setPen(QColor("#888888"))
        font_unit = QFont("Helvetica", 11)
        painter.setFont(font_unit)
        fm_unit = QFontMetrics(font_unit)
        unit_rect = fm_unit.boundingRect(self.unit)
        painter.drawText((width - unit_rect.width()) // 2, height // 2 + 20, self.unit)
        
        # 标题
        painter.setPen(self.color1)
        font_title = QFont("Helvetica", 13, QFont.Bold)
        painter.setFont(font_title)
        fm_title = QFontMetrics(font_title)
        title_rect = fm_title.boundingRect(self.title)
        painter.drawText((width - title_rect.width()) // 2, height - 12, self.title)
        
        painter.end()


class SmallDataBox(QFrame):
    """右侧数据格子"""
    def __init__(self, title, unit, icon_text="●", color="#888888", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.color = QColor(color)
        self.setStyleSheet(f"""
            SmallDataBox {{
                background-color: #353535;
                border-radius: 8px;
                border: 1px solid #4A4A4A;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(6, 4, 6, 4)
        
        # 顶部：图标+标题
        header = QHBoxLayout()
        header.setSpacing(4)
        header.setAlignment(Qt.AlignCenter)
        
        icon = QLabel(icon_text)
        icon.setStyleSheet(f"color: {color}; background: transparent;")
        icon.setFont(QFont("Helvetica", 11))
        header.addWidget(icon)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; background: transparent;")
        title_label.setFont(QFont("Helvetica", 10))
        header.addWidget(title_label)
        layout.addLayout(header)
        
        # 数值
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        self.value_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
        # 单位
        unit_label = QLabel(unit)
        unit_label.setStyleSheet("color: #666666; background: transparent;")
        unit_label.setFont(QFont("Helvetica", 9))
        unit_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(unit_label)
        
    def update_value(self, value, color=None):
        self.value_label.setText(str(value))
        if color:
            self.value_label.setStyleSheet(f"color: {color}; background: transparent;")


class BikeComputerPro(QWidget):
    def __init__(self):
        super().__init__()
        self.debugger = SerialDebugger(port='/dev/ttyAMA10')

        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.icons_path = os.path.join(self.base_path, "TuBiao")
        self.wifi_on_path = os.path.join(self.icons_path, "wifi_on.png")
        self.wifi_off_path = os.path.join(self.icons_path, "wifi_off.png")

        # ========== 高德地图配置 ==========
        # 高德地图 API Key 配置
        self.amap_key = "8b657a470f4b69e82bf81f72b3a2b3c0"  # Web服务 API Key
        self.amap_jsapi_key = "c507e554a5bb6e08b7097fa61164f0e4"  # JS API Key
        self.amap_security_key = "8ee0cb41f7666cfd320749d269ab6121"  # 安全密钥
        self.location_service = LocationService()
        # ==================================

        # ========== 语音模块初始化 ==========
        self.voice_player = None
        self.led_controller = None
        
        # 尝试多种语音方案
        voice_initialized = False
        
        # 方案0: 混合语音播放器（在线Edge-TTS + 离线Piper）
        try:
            from voice_driver.piper_voice import HybridVoicePlayer
            self.voice_player = HybridVoicePlayer(
                voice='xiaoxiao',
                message_callback=self.add_voice_message  # 传入消息回调，播报时自动显示
            )
            print("[Main] 混合语音播放器初始化成功（支持离线）")
            voice_initialized = True
        except Exception as e0:
            print(f"[Main] 混合语音播放器初始化失败: {e0}")
        
        # 方案1: ReSpeaker 专用播放器（备用）
        if not voice_initialized:
            try:
                from voice_driver.voice_respeaker import ReSpeakerVoicePlayer
                self.voice_player = ReSpeakerVoicePlayer()
                print("[Main] ReSpeaker 语音播放器初始化成功")
                voice_initialized = True
            except Exception as e1:
                print(f"[Main] ReSpeaker 语音播放器初始化失败: {e1}")
        
        # 方案1: 标准 VoicePlayer
        if not voice_initialized:
            try:
                from voice_driver import VoicePlayer, LEDController
                self.voice_player = VoicePlayer()
                print("[Main] 语音播放器初始化成功")
                voice_initialized = True
            except Exception as e:
                print(f"[Main] 标准语音播放器初始化失败: {e}")
        
        # 方案2: AOSS 包装器播放器
        if not voice_initialized:
            try:
                from voice_driver.voice_aoss import AOSSVoicePlayer
                self.voice_player = AOSSVoicePlayer()
                print("[Main] AOSS 语音播放器初始化成功")
                voice_initialized = True
            except Exception as e2:
                print(f"[Main] AOSS 语音播放器初始化失败: {e2}")
        
        # 方案3: PyAudio 播放器
        if not voice_initialized:
            try:
                from voice_driver.voice_pyaudio import PyAudioVoicePlayer
                self.voice_player = PyAudioVoicePlayer()
                print("[Main] PyAudio 语音播放器初始化成功")
                voice_initialized = True
            except Exception as e3:
                print(f"[Main] PyAudio 语音播放器初始化失败: {e3}")
        
        # 方案4: pygame 播放器
        if not voice_initialized:
            try:
                from voice_driver.voice_pygame import PygameVoicePlayer
                self.voice_player = PygameVoicePlayer()
                print("[Main] Pygame 语音播放器初始化成功")
                voice_initialized = True
            except Exception as e4:
                print(f"[Main] Pygame 语音播放器初始化失败: {e4}")
        
        # 方案4: pyttsx3 直接
        if not voice_initialized:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                
                class SimpleTTS:
                    def __init__(self, engine):
                        self._engine = engine
                    def speak(self, text, block=False):
                        print(f"[SimpleTTS] 播报: {text}")
                        try:
                            self._engine.say(text)
                            if block:
                                self._engine.runAndWait()
                            else:
                                import threading
                                t = threading.Thread(target=self._engine.runAndWait)
                                t.daemon = True
                                t.start()
                            return True
                        except Exception as e:
                            print(f"[SimpleTTS] 播报失败: {e}")
                            return False
                    def stop(self):
                        pass
                
                self.voice_player = SimpleTTS(engine)
                print("[Main] 备用语音播放器初始化成功")
                voice_initialized = True
            except Exception as e4:
                print(f"[Main] 备用语音播放器初始化失败: {e4}")
        
        # LED 控制器
        try:
            from voice_driver import LEDController
            self.led_controller = LEDController()
            self.led_controller.start_pattern("breath", LEDController.COLOR_CYAN)
            print("[Main] LED 控制器初始化成功")
        except Exception as e:
            print(f"[Main] LED 控制器初始化失败: {e}")
        
        # 初始化 Ollama 大模型客户端
        self.ollama_client = None
        try:
            self.ollama_client = self._init_ollama_client()
        except Exception as e:
            print(f"[Main] Ollama 客户端初始化失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 按钮语音助手（按住说话功能）
        self.voice_assistant = None
        if self.voice_player:
            try:
                self.voice_assistant = ButtonVoiceAssistant(
                    voice_player=self.voice_player,
                    message_callback=self.add_voice_message,
                    button_pin=17,
                    ollama_client=self.ollama_client,  # 传入大模型客户端
                    led_controller=self.led_controller  # 传入 LED 控制器
                )
                print("[Main] 按钮语音助手初始化成功（已集成大模型）")
                print("[Main] 按住 ReSpeaker 按钮开始录音（红灯），松开处理（绿灯）")
            except Exception as e:
                print(f"[Main] 按钮语音助手初始化失败: {e}")
        # ==================================

        self.current_province = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        self.showFullScreen()
        self.raise_()           
        self.activateWindow()   
        self.setFocus()         
        
        screen = QApplication.primaryScreen()
        if screen:
            QCursor.setPos(screen.geometry().center())
        self.setCursor(Qt.BlankCursor) 

        self.setStyleSheet("""
            QWidget {
                background-color: #2C2C2C;
                border: none;
                outline: none;
            }
        """)

        # 主布局
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ==================== 状态栏 ====================
        self.status_bar = QWidget()
        self.status_bar.setFixedHeight(45)
        self.status_layout = QHBoxLayout(self.status_bar)
        self.status_layout.setContentsMargins(15, 3, 15, 3) 
        self.status_layout.setSpacing(0)

        # 左侧导航
        self.left_container = QWidget()
        self.left_layout = QHBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(8)

        self.active_style = "color: #4DB8FF; background: transparent;"
        self.inactive_style = "color: #666666; background: transparent;"

        self.btn_data = QPushButton("数据")
        self.btn_data.setFont(QFont("Helvetica", 12, QFont.Medium))
        self.btn_data.setStyleSheet(self.active_style)
        self.btn_data.clicked.connect(self.show_data_page)

        self.v_line = QFrame()
        self.v_line.setFixedWidth(1)
        self.v_line.setFixedHeight(16)
        self.v_line.setStyleSheet("background-color: #444444;")

        self.btn_map = QPushButton("地图")
        self.btn_map.setFont(QFont("Helvetica", 12, QFont.Medium))
        self.btn_map.setStyleSheet(self.inactive_style)
        self.btn_map.clicked.connect(self.show_map_page)

        self.v_line2 = QFrame()
        self.v_line2.setFixedWidth(1)
        self.v_line2.setFixedHeight(16)
        self.v_line2.setStyleSheet("background-color: #444444;")

        self.btn_exit = QPushButton("退出")
        self.btn_exit.setFont(QFont("Helvetica", 12, QFont.Medium))
        self.btn_exit.setStyleSheet("color: #e74c3c; background: transparent;") 
        self.btn_exit.clicked.connect(self.safe_exit)

        self.left_layout.addWidget(self.btn_data)
        self.left_layout.addWidget(self.v_line)
        self.left_layout.addWidget(self.btn_map)
        self.left_layout.addWidget(self.v_line2)
        self.left_layout.addWidget(self.btn_exit)

        self.title_label = QLabel("SMART RIDE")
        self.title_label.setStyleSheet("color: #555555; background: transparent;")
        self.title_label.setFont(QFont("Arial", 11, QFont.Bold))

        self.right_container = QWidget()
        self.right_layout = QHBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.wifi_icon_label = QLabel()
        self.wifi_icon_label.setFixedSize(32, 18)
        self.wifi_icon_label.setStyleSheet("background: transparent; margin-right: 8px;")

        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        self.time_label.setFont(QFont("Arial", 15, QFont.Bold))

        self.right_layout.addWidget(self.wifi_icon_label)
        self.right_layout.addWidget(self.time_label)

        self.status_layout.addWidget(self.left_container, 1)
        self.status_layout.addWidget(self.title_label, 1, Qt.AlignCenter)
        self.status_layout.addWidget(self.right_container, 1)

        # 分割线
        self.line = QFrame()
        self.line.setFixedHeight(1)
        self.line.setStyleSheet("background-color: #3A3A3A;")

        # ==================== 内容区域 ====================
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # --- 数据页面 ---
        self.page_data = QWidget()
        data_main_layout = QHBoxLayout(self.page_data)
        data_main_layout.setContentsMargins(12, 8, 12, 4)
        data_main_layout.setSpacing(15)

        # 左侧：圆形仪表盘
        left_panel = QWidget()
        left_panel.setFixedWidth(220)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setAlignment(Qt.AlignCenter)

        self.gauge_speed = CircleGauge("速度", "km/h", 60.0, "#4DB8FF")
        left_layout.addWidget(self.gauge_speed, alignment=Qt.AlignCenter)

        self.gauge_power = CircleGauge("功率", "W", 500.0, "#e74c3c")
        left_layout.addWidget(self.gauge_power, alignment=Qt.AlignCenter)

        self.status_text = QLabel("● 系统正常")
        self.status_text.setStyleSheet("color: #2ecc71; background: transparent;")
        self.status_text.setFont(QFont("Helvetica", 11))
        self.status_text.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.status_text)

        data_main_layout.addWidget(left_panel)

        # 右侧：网格数据
        right_panel = QWidget()
        right_layout = QGridLayout(right_panel)
        right_layout.setSpacing(6)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.box_cadence = SmallDataBox("踏频", "rpm", "◉", "#9b59b6")
        self.box_distance = SmallDataBox("距离", "km", "▶", "#2ecc71")
        self.box_time = SmallDataBox("时间", "", "◷", "#f39c12")
        self.box_slope = SmallDataBox("坡度", "%", "▲", "#1abc9c")
        self.box_temp = SmallDataBox("温度", "°C", "◉", "#3498db")
        self.box_hr = SmallDataBox("心率", "bpm", "♥", "#e74c3c")
        self.box_rear = SmallDataBox("后方", "m", "◐", "#e67e22")

        right_layout.addWidget(self.box_cadence, 0, 0)
        right_layout.addWidget(self.box_distance, 0, 1)
        right_layout.addWidget(self.box_time, 0, 2)
        right_layout.addWidget(self.box_slope, 1, 0)
        right_layout.addWidget(self.box_temp, 1, 1)
        right_layout.addWidget(self.box_hr, 1, 2)
        right_layout.addWidget(self.box_rear, 2, 0, 1, 3)

        right_layout.setRowStretch(0, 1)
        right_layout.setRowStretch(1, 1)
        right_layout.setRowStretch(2, 1)

        data_main_layout.addWidget(right_panel, 1)

        # 地图页面（使用高德在线地图组件）
        self.page_map = MapWidget(
            amap_key=self.amap_key,
            jsapi_key=self.amap_jsapi_key,
            security_key=self.amap_security_key
        )
        self.page_map.map_loaded.connect(self.on_map_loaded)
        
        # 连接导航信号
        # 连接导航信号
        self.page_map.nav_status_changed.connect(self.on_nav_status_changed)
        self.page_map.nav_instruction.connect(self.on_nav_instruction)
        
        # 连接新的导航处理器信号
        nav_handler = self.page_map.get_navigation_handler()
        nav_handler.nav_started.connect(self.on_nav_started)
        nav_handler.nav_stopped.connect(self.on_nav_stopped)
        nav_handler.nav_instruction.connect(self.on_nav_instruction_v2)
        
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.page_data)
        self.stacked_widget.addWidget(self.page_map)

        # --- 消息框 ---
        self.dialog_container = QWidget()
        self.dialog_container.setMinimumHeight(110)
        self.dialog_container.setMaximumHeight(250)  # 增加最大高度以显示更多内容
        self.dialog_container.setStyleSheet("background: transparent;")
        
        dialog_layout = QVBoxLayout(self.dialog_container)
        dialog_layout.setContentsMargins(15, 3, 15, 5)
        dialog_layout.setSpacing(0)

        self.dialog_box = QFrame()
        self.dialog_box.setMinimumHeight(95)
        self.dialog_box.setMaximumHeight(220)  # 增加最大高度以显示多行
        self.dialog_box.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border-radius: 14px;
                border: 1px solid #4A4A4A;
            }
        """)
        box_layout = QVBoxLayout(self.dialog_box)  # 改为垂直布局
        box_layout.setContentsMargins(15, 10, 15, 10)
        box_layout.setSpacing(5)
        
        self.dialog_msg = QLabel("🤖 欢迎使用 SMART RIDE 智能助理...")
        self.dialog_msg.setFont(QFont("Helvetica", 13))
        self.dialog_msg.setStyleSheet("color: #CCCCCC; background: transparent;")
        self.dialog_msg.setWordWrap(True)  # 启用自动换行
        self.dialog_msg.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # 左对齐，顶部对齐
        self.dialog_msg.setTextFormat(Qt.PlainText)  # 纯文本模式，保留换行符
        # 设置尺寸策略，允许垂直扩展
        self.dialog_msg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        box_layout.addWidget(self.dialog_msg)
        
        # 语音消息历史（最多显示最近2条，避免超出界面）
        self.voice_messages = []
        self.max_voice_messages = 2
        
        dialog_layout.addWidget(self.dialog_box)

        # 组装
        self.content_layout.addWidget(self.stacked_widget, 1)
        self.content_layout.addWidget(self.dialog_container, 0)

        # 最终组装
        self.main_layout.addWidget(self.status_bar)
        self.main_layout.addWidget(self.line)
        self.main_layout.addWidget(self.content_container, 1)
        self.setLayout(self.main_layout)

        # 定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_info)
        self.timer.start(1000) 
        self.wifi_counter = 0

        # 串口读取
        self.serial_worker = SerialReader(port='/dev/ttyAMA2')
        self.serial_worker.data_received.connect(self.on_data_received)
        self.serial_worker.start()

        self.update_info()

        # ========== 启动语音播报 ==========
        # 延迟 3 秒后播报欢迎语（给语音播放器初始化时间）
        self.voice_timer = QTimer(self)
        self.voice_timer.singleShot(3000, self._play_welcome_voice)
        # ================================== 

    def _init_ollama_client(self):
        """
        初始化 Ollama 大模型客户端
        自动检测可用模型并创建连接，如未运行则自动启动服务
        """
        import requests
        import subprocess
        import time
        
        host = "http://localhost:11434"
        print("[Ollama] 正在检查 Ollama 服务...")
        
        # 1. 检查服务是否运行
        service_running = False
        try:
            response = requests.get(f"{host}/api/tags", timeout=2)
            if response.status_code == 200:
                service_running = True
                print("[Ollama] 服务已在运行")
        except:
            service_running = False
        
        # 2. 如果服务未运行，尝试自动启动
        if not service_running:
            print("[Ollama] 服务未运行，尝试自动启动...")
            try:
                # 在后台启动 ollama serve
                # 使用 nohup 确保进程不会在终端关闭时退出
                subprocess.Popen(
                    ["nohup", "ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True  # 创建新会话，避免被父进程终止
                )
                
                # 等待服务启动（最多等待 15 秒）
                print("[Ollama] 等待服务启动...")
                for i in range(15):
                    time.sleep(1)
                    try:
                        response = requests.get(f"{host}/api/tags", timeout=2)
                        if response.status_code == 200:
                            service_running = True
                            print(f"[Ollama] 服务启动成功！（耗时 {i+1} 秒）")
                            break
                    except:
                        continue
                
                if not service_running:
                    print("[Ollama] 服务启动超时，可能启动失败")
                    print("[Ollama] 请手动执行: ollama serve")
                    return None
                
                # 服务启动后，等待模型完全加载（给 Ollama 预热时间）
                print("[Ollama] 等待模型预热...")
                time.sleep(3)
                    
            except Exception as e:
                print(f"[Ollama] 自动启动失败: {e}")
                print("[Ollama] 请手动执行: ollama serve")
                return None
        
        # 2. 获取可用模型列表
        try:
            data = response.json()
            models = data.get('models', [])
            
            if not models:
                print("[Ollama] 没有可用的模型，请先拉取模型:")
                print("  ollama pull llama3.2")
                print("  ollama pull qwen:1.8b")
                return None
            
            print(f"[Ollama] 发现 {len(models)} 个可用模型:")
            for m in models:
                model_name = m.get('name', m.get('model', 'unknown'))
                print(f"  - {model_name}")
            
            # 3. 选择最佳模型（优先级排序）
            preferred_models = [
                "my-llama",           # 自定义模型（最高优先级）
                "llama3.2",           # Llama 3.2
                "llama3.2:3b",        # Llama 3.2 3B
                "llama3.1",           # Llama 3.1
                "llama3",             # Llama 3
                "qwen2.5:3b",         # 通义千问 3B
                "qwen2.5:1.5b",       # 通义千问 1.5B
                "qwen:1.8b",          # 通义千问 1.8B
                "qwen2:0.5b",         # 通义千问 0.5B
                "gemma2:2b",          # Gemma 2 2B
                "phi3",               # Phi-3
                "phi3:mini",          # Phi-3 Mini
                "tinyllama",          # TinyLlama
            ]
            
            selected_model = None
            available_model_names = [m.get('name', m.get('model', '')) for m in models]
            
            # 先尝试优先模型
            for preferred in preferred_models:
                if preferred in available_model_names:
                    selected_model = preferred
                    break
            
            # 如果没匹配到，使用第一个可用模型
            if not selected_model:
                selected_model = available_model_names[0]
            
            print(f"[Ollama] 选择模型: {selected_model}")
            
            # 4. 创建客户端
            client = OllamaClient(model_name=selected_model, host=host)
            
            # 简单测试（带重试）
            print("[Ollama] 测试模型连接...")
            test_success = False
            for attempt in range(2):  # 尝试2次
                try:
                    # 使用超短的测试，只检查模型是否响应
                    test_response = client.chat("1+1=", max_tokens=5)
                    if test_response and "抱歉" not in test_response:
                        print(f"[Ollama] 大模型连接成功！使用模型: {selected_model}")
                        test_success = True
                        break
                    else:
                        print(f"[Ollama] 测试返回异常: {test_response}")
                        if attempt == 0:
                            print("[Ollama] 重试中...")
                            time.sleep(2)
                except Exception as e:
                    print(f"[Ollama] 测试失败 (尝试 {attempt+1}/2): {e}")
                    if attempt == 0:
                        print("[Ollama] 重试中...")
                        time.sleep(2)
            
            if test_success:
                return client
            else:
                print("[Ollama] 模型测试失败，但服务可用，将继续尝试使用")
                # 即使测试失败，也返回客户端，因为可能是模型加载慢
                return client
                
        except Exception as e:
            print(f"[Ollama] 获取模型列表失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def show_data_page(self):
        self.stacked_widget.setCurrentIndex(0)
        self.btn_data.setStyleSheet(self.active_style)
        self.btn_map.setStyleSheet(self.inactive_style)

    def show_map_page(self):
        self.stacked_widget.setCurrentIndex(1)
        self.btn_data.setStyleSheet(self.inactive_style)
        self.btn_map.setStyleSheet(self.active_style)

    def safe_exit(self):
        print("退出程序...")
        if hasattr(self, 'serial_worker'):
            self.serial_worker.stop()
        if hasattr(self, 'debugger'):
            self.debugger.stop()
        # 清理语音模块资源
        if self.voice_player:
            try:
                self.voice_player.stop()
            except:
                pass
        if self.led_controller:
            try:
                self.led_controller.close()
            except:
                pass
        if self.voice_assistant:
            try:
                self.voice_assistant.stop()
            except:
                pass
        self.close()

    def on_data_received(self, data):
        formatted_data = json.dumps(data, indent=2, ensure_ascii=False)
        print(formatted_data)

        # 更新数据上下文（供大模型使用）
        try:
            from data_context import get_data_context
            data_ctx = get_data_context()
            update_dict = {}
            
            if "speed" in data:
                update_dict["speed"] = float(data["speed"])
            if "power" in data:
                update_dict["power"] = float(data["power"])
            if "cadence" in data:
                update_dict["cadence"] = float(data["cadence"])
            if "distance" in data:
                update_dict["distance"] = float(data["distance"])
            if "ride_time" in data:
                update_dict["ride_time"] = int(data["ride_time"])
            if "slope" in data:
                update_dict["slope"] = float(data["slope"])
            if "temperature" in data:
                update_dict["temperature"] = float(data["temperature"])
            if "heart_rate" in data:
                update_dict["heart_rate"] = float(data["heart_rate"])
            if "rear_dist" in data:
                update_dict["rear_dist"] = float(data["rear_dist"])
            
            if update_dict:
                data_ctx.update_data(**update_dict)
        except Exception as e:
            print(f"[DataContext] 更新失败: {e}")

        # 更新数据卡片
        if "speed" in data:
            val = float(data["speed"])
            self.gauge_speed.set_value(val)
            
        if "power" in data:
            val = int(data["power"])
            self.gauge_power.set_value(val)
            
        if "cadence" in data:
            self.box_cadence.update_value(int(data["cadence"]))
            
        if "distance" in data:
            self.box_distance.update_value(f"{float(data['distance']):.1f}")
            
        if "ride_time" in data:
            seconds = int(data["ride_time"])
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            self.box_time.update_value(f"{hours:02d}:{minutes:02d}")
            
        if "slope" in data:
            val = float(data["slope"])
            prefix = "+" if val > 0 else ""
            color = "#e74c3c" if abs(val) > 10 else "#2ecc71" if val > 0 else "#FFFFFF"
            self.box_slope.update_value(f"{prefix}{val:.1f}", color)
            
        if "temperature" in data:
            val = float(data["temperature"])
            color = "#e74c3c" if val > 35 else "#3498db" if val < 10 else "#FFFFFF"
            self.box_temp.update_value(f"{val:.1f}", color)
            
        if "heart_rate" in data:
            val = int(data["heart_rate"])
            color = "#e74c3c" if val > 180 else "#f39c12" if val > 160 else "#FFFFFF"
            self.box_hr.update_value(val, color)
            
        if "rear_dist" in data:
            val = float(data["rear_dist"])
            color = "#e74c3c" if val < 5 else "#f39c12" if val < 10 else "#2ecc71"
            self.box_rear.update_value(f"{val:.1f}", color)
            
        if "err_code" in data:
            err = int(data["err_code"])
            if err == 0:
                self.status_text.setText("● 系统正常")
                self.status_text.setStyleSheet("color: #2ecc71; background: transparent;")
            else:
                self.status_text.setText(f"● 错误 {err}")
                self.status_text.setStyleSheet("color: #e74c3c; background: transparent;")

        # 处理位置信息
        if "location" in data:
            loc = data["location"]
            lat = loc.get("lat")
            lon = loc.get("lon")
            if lat and lon:
                print(f"[DEBUG] 收到位置数据: {lat}, {lon}")
                self.handle_location_update(lon, lat)

    def handle_location_update(self, lon, lat):
        """处理位置更新，更新地图显示"""
        # 1. 离线判断省份
        province = self.location_service.get_province(lon, lat)
        if not province:
            province = "未知区域"

        # 2. 更新数据上下文中的位置
        try:
            from data_context import get_data_context
            get_data_context().update_data(location=province)
        except Exception as e:
            print(f"[DataContext] 更新位置失败: {e}")

        # 3. 更新地图页面显示（实时更新位置标记）
        self.page_map.update_location(lat, lon, province)

        # 4. 记录当前省份
        import traceback
        stack = traceback.extract_stack()
        caller = stack[-2]
        print(f"[DEBUG] 省份检查: 当前={self.current_province}, 新={province}, 是否变化={province != self.current_province} [来自: {caller.name}]")
        if province != self.current_province:
            self.current_province = province
            print(f"[DEBUG] 进入新区域: {province}")
            
            # 添加带声音标识的消息到UI（🔊表示有语音播报，📍表示位置更新）
            self.add_voice_message(f"进入{province}", icon="🔊📍")
            
            # 语音播报（不显示在UI）
            if self.voice_player:
                try:
                    self.voice_player.speak(f"进入{province}", show_in_ui=False)
                except:
                    pass
        # 5. 更新对话框显示位置（仅在未播报省份变化时显示位置信息）
        elif not self.voice_messages:
            self.dialog_msg.setText(f"📍 {province} · {lat:.4f}°N {lon:.4f}°E")


    def check_wifi(self):
        try:
            socket.setdefaulttimeout(0.5)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        except: 
            return False

    def update_info(self):
        self.time_label.setText(QDateTime.currentDateTime().toString("hh:mm"))
        if self.wifi_counter % 5 == 0:
            image_path = self.wifi_on_path if self.check_wifi() else self.wifi_off_path
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(self.wifi_icon_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.wifi_icon_label.setPixmap(scaled)
        self.wifi_counter += 1

    def on_nav_status_changed(self, status):
        """导航状态变化回调"""
        print(f"导航状态: {status}")
        
        # 导航状态变化也显示到消息框（但优先级较低，不强制语音播报）
        if not self.voice_messages:
            # 如果没有语音消息，直接显示状态
            self.dialog_msg.setText(f"🧭 {status}")
        
        # 可选：重要状态变化也语音播报
        # if self.voice_player:
        #     self.add_voice_message(status, icon="🧭")
        #     self.voice_player.speak(status)

    def on_nav_started(self):
        """导航开始回调"""
        print("[Main] 导航开始")
        self.add_voice_message("开始导航", icon="🧭")
        if self.voice_player:
            try:
                self.voice_player.speak("开始导航")
            except Exception as e:
                print(f"[Voice] 导航开始播报失败: {e}")
    
    def on_nav_stopped(self):
        """导航结束回调"""
        print("[Main] 导航结束")
        self.add_voice_message("导航结束", icon="🧭")
        if self.voice_player:
            try:
                self.voice_player.speak("导航结束")
            except Exception as e:
                print(f"[Voice] 导航结束播报失败: {e}")
    
    def on_nav_instruction_v2(self, instruction: str, detail: str):
        """导航指令回调 V2（带详细信息）"""
        print(f"[Main] 导航指令: {instruction} | {detail}")
        
        # 添加到语音消息框
        self.add_voice_message(instruction, icon="🧭")
        
        # 语音播报导航指令（简化版，去除HTML标签和距离数字）
        if self.voice_player:
            try:
                # 简化指令用于语音播报
                speak_text = self._simplify_nav_instruction(instruction)
                self.voice_player.speak(speak_text)
            except Exception as e:
                print(f"[Voice] 导航语音播报失败: {e}")
    
    def on_map_loaded(self, success: bool):
        """地图加载完成回调"""
        if success:
            print("[Main] ✅ 地图页面加载成功！")
            self.add_voice_message("地图加载成功", icon="🗺️")
        else:
            print("[Main] ❌ 地图页面加载失败！")
            self.add_voice_message("地图加载失败，请检查网络或API配置", icon="⚠️")
    
    def _simplify_nav_instruction(self, instruction: str) -> str:
        """简化导航指令用于语音播报"""
        import re
        # 去除HTML标签
        text = re.sub(r'<[^>]+>', '', instruction)
        # 简化距离描述
        text = text.replace("米", "米")
        text = text.replace("公里", "公里")
        return text
    
    def on_nav_instruction(self, instruction):
        """导航指令回调（旧版，用于兼容）"""
        print(f"导航指令: {instruction}")
        
        # 添加到语音消息框
        self.add_voice_message(instruction, icon="🧭")
        
        # 语音播报导航指令
        if self.voice_player:
            try:
                self.voice_player.speak(instruction)
            except Exception as e:
                print(f"[Voice] 导航语音播报失败: {e}")

    def add_voice_message(self, text: str, icon: str = "🔊"):
        """
        添加语音消息到消息框
        
        Args:
            text: 消息内容
            icon: 消息图标，特殊值：
                - __STREAM_UPDATE__: 流式更新（同一行覆盖）
                - __STREAM_FINAL__: 流式完成（同一行显示最终结果）
        """
        # 限制单条消息长度，防止超出界面
        max_length = 120
        cleaned_text = text.replace('\n', ' ').replace('\r', ' ').strip()
        if len(cleaned_text) > max_length:
            cleaned_text = cleaned_text[:max_length] + "..."
        
        # 处理流式更新标记：同一行覆盖更新
        if icon == "__STREAM_UPDATE__":
            # 检查最后一条是否是流式消息（以 > 🤖 开头）
            if self.voice_messages and "> 🤖 " in self.voice_messages[-1]:
                # 替换最后一条，保持格式一致
                self.voice_messages[-1] = f"> 🤖 {cleaned_text}"
            else:
                # 还没有流式消息，添加一条（不带>前缀，由后续更新添加）
                self.voice_messages.append(f"> 🤖 {cleaned_text}")
            
            # 更新显示
            display_text = "\n".join(self.voice_messages)
            self.dialog_msg.setText(display_text)
            return
        
        # 处理流式完成标记：在同一行显示最终结果
        if icon == "__STREAM_FINAL__":
            # 查找并替换最后一条流式消息
            if self.voice_messages and "> 🤖 " in self.voice_messages[-1]:
                self.voice_messages[-1] = f"> 🤖 {cleaned_text}"
            else:
                # 没有流式消息，添加最终结果
                self.voice_messages.append(f"> 🤖 {cleaned_text}")
            
            # 限制历史长度
            if len(self.voice_messages) > self.max_voice_messages:
                self.voice_messages.pop(0)
            
            # 更新显示
            display_text = "\n".join(self.voice_messages)
            self.dialog_msg.setText(display_text)
            print(f"[VoiceMessage] > 🤖 {cleaned_text}")
            return
        
        # 普通消息处理
        message = f"> {icon} {cleaned_text}"
        
        # 添加到历史
        self.voice_messages.append(message)
        
        # 限制历史长度
        if len(self.voice_messages) > self.max_voice_messages:
            self.voice_messages.pop(0)
        
        # 更新显示
        display_text = "\n".join(self.voice_messages)
        self.dialog_msg.setText(display_text)
        
        # 打印调用栈来追踪来源
        import traceback
        stack = traceback.extract_stack()
        caller = stack[-2]  # 获取调用者信息
        print(f"[VoiceMessage] {message} [来自: {caller.filename}:{caller.lineno} {caller.name}]")

    def _play_welcome_voice(self):
        """播放欢迎语音（自动选择在线/离线）"""
        print("[Voice] ========== 播放欢迎语音 ==========")
        
        if not self.voice_player:
            print("[Voice] 错误: 语音播放器未初始化")
            return
        
        # 检查语音播放器类型
        player_type = type(self.voice_player).__name__
        print(f"[Voice] 使用播放器: {player_type}")
        
        try:
            # 混合播放器自动选择：网络好->Edge-TTS，无网络->Piper离线
            print("[Voice] 开始播报: '你好，我是骑行小智'...")
            result = self.voice_player.speak("你好，我是骑行小智", block=False)
            print(f"[Voice] 播报调用返回: {'成功' if result else '失败'}")
            
            if not result:
                print("[Voice] 警告: 播报调用返回失败")
                
        except Exception as e:
            print(f"[Voice] 播报异常: {e}")
            import traceback
            traceback.print_exc()
        
        # 停止呼吸灯，改为常亮
        if self.led_controller:
            try:
                self.led_controller.stop_pattern()
                self.led_controller.set_all(LEDController.COLOR_GREEN)
                print("[Voice] LED 设置为常亮绿色")
            except Exception as e:
                print(f"[LED] 设置绿色失败: {e}")
        
        print("[Voice] ========== 欢迎语音处理完成 ==========")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: 
            self.safe_exit()


if __name__ == "__main__":
    # 启用高 DPI 支持和触摸支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_SynthesizeTouchForUnhandledMouseEvents, True)
    app.setAttribute(Qt.AA_SynthesizeMouseForUnhandledTouchEvents, False)
    
    window = BikeComputerPro()
    window.show()
    sys.exit(app.exec_())