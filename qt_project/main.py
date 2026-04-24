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
from PyQt5.QtCore import QTimer, QDateTime, Qt
from PyQt5.QtGui import QFont, QCursor

os.environ["QT_WAYLAND_DISABLE_WINDOWDECORATION"] = "1"

from drivers.serial_handler import SerialReader
from core.location_service import LocationService
from widgets.map_widget import MapWidget
from widgets.circle_gauge import CircleGauge
from widgets.metric_card import MetricCard
from ui.history_page import HistoryPage
from ui.settings_page import SettingsPage
from utils.serial_debugger import SerialDebugger
from drivers.audio import VoicePlayer, LEDController
from drivers.audio.voice_recorder import ButtonVoiceAssistant
from llm.ollama_client import OllamaClient, DEFAULT_SYSTEM_PROMPT
from llm.bailian_client import BailianClient
from llm.unified_llm_client import UnifiedLLMClient
from core.protocol import SensorData, RideSessionState, RideSummary
from services.comm_service import CommService
from persistence.config_manager import get_config
from persistence.ride_repository import RideRepository
from services.ride_service import RideService
from services.alert_service import AlertService
from utils.tile_server import get_tile_server


class BikeComputerPro(QWidget):
    def __init__(self):
        super().__init__()

        # ========== 配置管理器初始化 ==========
        self.config = get_config()
        print(f"[Main] 配置加载完成，心率上限: {self.config.get('heart_rate_max')}")
        # =====================================

        self.debugger = SerialDebugger(port='/dev/ttyAMA10')

        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.icons_path = os.path.join(self.base_path, "TuBiao")

        # ========== 高德地图配置 ==========
        # 高德地图 API Key 配置
        self.amap_key = "8b657a470f4b69e82bf81f72b3a2b3c0"  # Web服务 API Key
        self.amap_jsapi_key = "c507e554a5bb6e08b7097fa61164f0e4"  # JS API Key
        self.amap_security_key = "8ee0cb41f7666cfd320749d269ab6121"  # 安全密钥
        self.location_service = LocationService()
        # ==================================

        # 地图页面访问标志：只有用户主动点击地图按钮后才播报加载结果
        self._map_page_visited = False

        # 全局在线/离线状态管理
        # 启动时始终先尝试在线状态，后续网络检测失败再自动切离线
        self._global_online_mode = True
        self._auto_fallback_count = 0  # 自动降级次数（防循环）

        # ========== 本地瓦片服务器 ==========
        self.tile_server = None
        try:
            from utils.tile_server import get_tile_server
            self.tile_server = get_tile_server(tiles_root="maps/xiangtan_tiles", port=8766)
            self.tile_server.start()
            print(f"[Main] 瓦片服务器 URL: {self.tile_server.url}")
        except Exception as e:
            print(f"[Main] 瓦片服务器启动失败: {e}")
        # ===================================

        # ========== 语音模块初始化 ==========
        self.voice_player = None
        self.led_controller = None
        
        # 尝试多种语音方案
        voice_initialized = False
        
        # 方案0: 混合语音播放器（在线Edge-TTS + 离线Piper）
        try:
            from drivers.audio.piper_voice import HybridVoicePlayer
            self.voice_player = HybridVoicePlayer(
                voice='xiaoxiao',
                message_callback=self.add_voice_message,  # 传入消息回调，播报时自动显示
                force_offline=not self._global_online_mode
            )
            print("[Main] 混合语音播放器初始化成功（支持离线）")
            voice_initialized = True
        except Exception as e0:
            print(f"[Main] 混合语音播放器初始化失败: {e0}")
        
        # 方案1: ReSpeaker 专用播放器（备用）
        if not voice_initialized:
            try:
                from drivers.audio.voice_respeaker import ReSpeakerVoicePlayer
                self.voice_player = ReSpeakerVoicePlayer()
                print("[Main] ReSpeaker 语音播放器初始化成功")
                voice_initialized = True
            except Exception as e1:
                print(f"[Main] ReSpeaker 语音播放器初始化失败: {e1}")
        
        # 方案1: 标准 VoicePlayer
        if not voice_initialized:
            try:
                from drivers.audio import VoicePlayer, LEDController
                self.voice_player = VoicePlayer()
                print("[Main] 语音播放器初始化成功")
                voice_initialized = True
            except Exception as e:
                print(f"[Main] 标准语音播放器初始化失败: {e}")
        
        # 方案2: AOSS 包装器播放器
        if not voice_initialized:
            try:
                from drivers.audio.voice_aoss import AOSSVoicePlayer
                self.voice_player = AOSSVoicePlayer()
                print("[Main] AOSS 语音播放器初始化成功")
                voice_initialized = True
            except Exception as e2:
                print(f"[Main] AOSS 语音播放器初始化失败: {e2}")
        
        # 方案3: PyAudio 播放器
        if not voice_initialized:
            try:
                from drivers.audio.voice_pyaudio import PyAudioVoicePlayer
                self.voice_player = PyAudioVoicePlayer()
                print("[Main] PyAudio 语音播放器初始化成功")
                voice_initialized = True
            except Exception as e3:
                print(f"[Main] PyAudio 语音播放器初始化失败: {e3}")
        
        # 方案4: pygame 播放器
        if not voice_initialized:
            try:
                from drivers.audio.voice_pygame import PygameVoicePlayer
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
            from drivers.audio import LEDController
            self.led_controller = LEDController()
            self.led_controller.start_pattern("breath", LEDController.COLOR_CYAN)
            print("[Main] LED 控制器初始化成功")
        except Exception as e:
            print(f"[Main] LED 控制器初始化失败: {e}")
        
        # 初始化 Ollama 本地大模型客户端
        self.ollama_client = None
        try:
            self.ollama_client = self._init_ollama_client()
        except Exception as e:
            print(f"[Main] Ollama 客户端初始化失败: {e}")
            import traceback
            traceback.print_exc()

        # 初始化百炼在线大模型客户端
        self.bailian_client = None
        try:
            bailian_key = self.config.get("aliyun_bailian_api_key")
            bailian_model = self.config.get("aliyun_bailian_model", "qwen-turbo")
            self.bailian_client = BailianClient(api_key=bailian_key, model=bailian_model)
            if self.bailian_client.check_available():
                print(f"[Main] 百炼在线模型初始化成功（模型: {bailian_model}）")
            else:
                print("[Main] 百炼服务暂不可达，在线 LLM 将不可用")
        except Exception as e:
            print(f"[Main] 百炼客户端初始化失败: {e}")
            import traceback
            traceback.print_exc()

        # 统一大模型客户端（自动切换在线/离线）
        self.unified_llm = UnifiedLLMClient(
            bailian_client=self.bailian_client,
            ollama_client=self.ollama_client,
            force_offline=not self._global_online_mode
        )
        print("[Main] 统一大模型客户端已初始化")

        # 按钮语音助手（按住说话功能）
        self.voice_assistant = None
        if self.voice_player:
            try:
                self.voice_assistant = ButtonVoiceAssistant(
                    voice_player=self.voice_player,
                    message_callback=self.add_voice_message,
                    button_pin=17,
                    ollama_client=self.unified_llm,  # 传入统一大模型客户端
                    led_controller=self.led_controller  # 传入 LED 控制器
                )
                print("[Main] 按钮语音助手初始化成功（已集成统一大模型）")
                print("[Main] 按住 ReSpeaker 按钮开始录音（红灯），松开处理（绿灯）")
            except Exception as e:
                print(f"[Main] 按钮语音助手初始化失败: {e}")
        # ==================================

        # ========== 骑行记录仓库初始化 ==========
        self.ride_repo = RideRepository()
        print("[Main] 骑行记录仓库已初始化")
        # ==========================================

        # ========== 通信服务初始化 ==========
        self.comm_service = CommService(parent=self, ride_repo=self.ride_repo)
        self.comm_service.command_received.connect(self.on_app_command)
        def _on_ble_connected(addr: str):
            print(f"[Main] BLE App 已连接: {addr}")
            self.add_voice_message("蓝牙连接成功", icon="🔵")

        self.comm_service.ble_client_connected.connect(_on_ble_connected)
        self.comm_service.wifi_client_connected.connect(
            lambda addr: print(f"[Main] WiFi App 已连接: {addr}")
        )
        self.comm_service.event_pushed.connect(self.on_comm_event)
        self.comm_service.start()
        print("[Main] 通信服务已启动（BLE + WiFi）")
        # ==================================

        # ========== 骑行服务初始化 ==========
        self.ride_service = RideService(parent=self, ride_repo=self.ride_repo)
        self.ride_service.state_changed.connect(self._on_ride_state_changed)
        self.ride_service.stats_updated.connect(self._on_ride_stats_updated)
        self.ride_service.ride_started.connect(self._on_ride_started)
        self.ride_service.ride_stopped.connect(self._on_ride_stopped)
        self.ride_service.ride_paused.connect(self._on_ride_paused)
        self.ride_service.ride_resumed.connect(self._on_ride_resumed)
        print("[Main] 骑行服务已初始化")
        # ==================================

        # ========== 安全告警服务初始化 ==========
        self.alert_service = AlertService(parent=self, comm_service=self.comm_service)
        self.alert_service.alert_triggered.connect(self._on_alert_triggered)
        self.ride_service.stats_updated.connect(self.alert_service.on_stats_updated)
        print("[Main] 安全告警服务已初始化")
        # ======================================

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
        self.status_bar.setFixedHeight(60)
        self.status_layout = QHBoxLayout(self.status_bar)
        self.status_layout.setContentsMargins(15, 3, 15, 3)
        self.status_layout.setSpacing(0)

        # 左侧导航
        self.left_container = QWidget()
        self.left_layout = QHBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(10)

        self.active_style = "color: #4DB8FF; background: transparent;"
        self.inactive_style = "color: #666666; background: transparent;"

        self.btn_data = QPushButton("数据")
        self.btn_data.setFont(QFont("Helvetica", 13, QFont.Medium))
        self.btn_data.setStyleSheet(self.active_style)
        self.btn_data.clicked.connect(self.show_data_page)

        self.v_line = QFrame()
        self.v_line.setFixedWidth(1)
        self.v_line.setFixedHeight(24)
        self.v_line.setStyleSheet("background-color: #444444;")

        self.btn_map = QPushButton("地图")
        self.btn_map.setFont(QFont("Helvetica", 13, QFont.Medium))
        self.btn_map.setStyleSheet(self.inactive_style)
        self.btn_map.clicked.connect(self.show_map_page)

        self.v_line2 = QFrame()
        self.v_line2.setFixedWidth(1)
        self.v_line2.setFixedHeight(24)
        self.v_line2.setStyleSheet("background-color: #444444;")

        self.btn_history = QPushButton("历史")
        self.btn_history.setFont(QFont("Helvetica", 13, QFont.Medium))
        self.btn_history.setStyleSheet(self.inactive_style)
        self.btn_history.clicked.connect(self.show_history_page)

        self.v_line3 = QFrame()
        self.v_line3.setFixedWidth(1)
        self.v_line3.setFixedHeight(24)
        self.v_line3.setStyleSheet("background-color: #444444;")

        self.btn_settings = QPushButton("设置")
        self.btn_settings.setFont(QFont("Helvetica", 13, QFont.Medium))
        self.btn_settings.setStyleSheet(self.inactive_style)
        self.btn_settings.clicked.connect(self.show_settings_page)

        self.v_line4 = QFrame()
        self.v_line4.setFixedWidth(1)
        self.v_line4.setFixedHeight(24)
        self.v_line4.setStyleSheet("background-color: #444444;")

        self.btn_exit = QPushButton("退出")
        self.btn_exit.setFont(QFont("Helvetica", 13, QFont.Medium))
        self.btn_exit.setStyleSheet("color: #e74c3c; background: transparent;")
        self.btn_exit.clicked.connect(self.safe_exit)

        self.left_layout.addWidget(self.btn_data)
        self.left_layout.addWidget(self.v_line)
        self.left_layout.addWidget(self.btn_map)
        self.left_layout.addWidget(self.v_line2)
        self.left_layout.addWidget(self.btn_history)
        self.left_layout.addWidget(self.v_line3)
        self.left_layout.addWidget(self.btn_settings)
        self.left_layout.addWidget(self.v_line4)
        self.left_layout.addWidget(self.btn_exit)

        self.title_label = QLabel("SMART RIDE")
        self.title_label.setStyleSheet("color: #555555; background: transparent;")
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))

        self.right_container = QWidget()
        self.right_layout = QHBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(20)
        self.right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.zt_status_label = QLabel("正常骑行")
        self.zt_status_label.setStyleSheet("color: #2ecc71; background: transparent;")
        self.zt_status_label.setFont(QFont("Helvetica", 12, QFont.Bold))

        self.heading_label = QLabel("")
        self.heading_label.setStyleSheet("color: #4DB8FF; background: transparent;")
        self.heading_label.setFont(QFont("Helvetica", 11, QFont.Bold))
        self.heading_label.hide()  # 初始为空，避免占据间距

        # 在线/离线地图切换按钮
        self.btn_map_mode = QPushButton("在线")
        self.btn_map_mode.setFont(QFont("Helvetica", 10, QFont.Bold))
        self.btn_map_mode.setFixedSize(50, 28)
        self.btn_map_mode.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: #FFFFFF; border-radius: 6px; }"
            "QPushButton:pressed { background-color: #27ae60; }"
        )
        self.btn_map_mode.clicked.connect(self._toggle_map_mode)

        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        self.time_label.setFont(QFont("Arial", 17, QFont.Bold))

        self.right_layout.addWidget(self.zt_status_label)
        self.right_layout.addWidget(self.heading_label)
        self.right_layout.addWidget(self.btn_map_mode)
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
        data_main_layout.setContentsMargins(12, 8, 12, 8)
        data_main_layout.setSpacing(12)

        # 左侧：窄边栏（仪表盘 + 状态 + 控制按钮）
        left_panel = QWidget()
        left_panel.setFixedWidth(170)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addSpacing(10)

        self.gauge_speed = CircleGauge("速度", "km/h", 60.0, "#4DB8FF")
        self.gauge_speed.setFixedSize(115, 115)
        left_layout.addWidget(self.gauge_speed, alignment=Qt.AlignCenter)

        self.gauge_power = CircleGauge("功率", "W", 500.0, "#e74c3c")
        self.gauge_power.setFixedSize(115, 115)
        left_layout.addWidget(self.gauge_power, alignment=Qt.AlignCenter)

        left_layout.addSpacing(4)

        self.status_text = QLabel("● 系统正常")
        self.status_text.setStyleSheet("color: #2ecc71; background: transparent;")
        self.status_text.setFont(QFont("Helvetica", 11))
        self.status_text.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.status_text)

        left_layout.addSpacing(6)

        # 骑行控制按钮
        self.btn_ride_action = QPushButton("开始骑行")
        self.btn_ride_action.setFont(QFont("Helvetica", 12, QFont.Bold))
        self.btn_ride_action.setFixedSize(116, 40)
        self.btn_ride_action.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: #FFFFFF; border-radius: 8px; }"
            "QPushButton:pressed { background-color: #27ae60; }"
        )
        self.btn_ride_action.clicked.connect(self._on_ride_action_clicked)
        left_layout.addWidget(self.btn_ride_action, alignment=Qt.AlignCenter)

        self.btn_ride_stop = QPushButton("结束")
        self.btn_ride_stop.setFont(QFont("Helvetica", 11, QFont.Bold))
        self.btn_ride_stop.setFixedSize(116, 34)
        self.btn_ride_stop.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: #FFFFFF; border-radius: 8px; }"
            "QPushButton:pressed { background-color: #c0392b; }"
        )
        self.btn_ride_stop.clicked.connect(self._on_ride_stop_clicked)
        self.btn_ride_stop.hide()
        left_layout.addWidget(self.btn_ride_stop, alignment=Qt.AlignCenter)

        left_layout.addStretch(1)
        data_main_layout.addWidget(left_panel)

        # 右侧：主内容区
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addSpacing(6)

        def _make_section_icon(text, color):
            """标题左侧小图标"""
            bg = QFrame()
            bg.setFixedSize(26, 26)
            bg.setFrameShape(QFrame.NoFrame)
            bg.setFrameShadow(QFrame.Plain)
            bg.setLineWidth(0)
            bg.setMidLineWidth(0)
            bg.setStyleSheet(f"background-color: {color}22; border-radius: 6px; border: none;")
            l = QVBoxLayout(bg)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(0)
            l.setAlignment(Qt.AlignCenter)
            icon = QLabel(text)
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            f = QFont()
            f.setPointSize(14)
            f.setFamilies([
                "Noto Color Emoji", "Segoe UI Emoji", "Apple Color Emoji",
                "Noto Sans CJK SC", "WenQuanYi Micro Hei", "Helvetica"
            ])
            icon.setFont(f)
            l.addWidget(icon)
            return bg

        def _make_section_icon_large(text, color):
            """标题左侧大图标（供传感器数据使用）"""
            bg = QFrame()
            bg.setFixedSize(38, 38)
            bg.setFrameShape(QFrame.NoFrame)
            bg.setFrameShadow(QFrame.Plain)
            bg.setLineWidth(0)
            bg.setMidLineWidth(0)
            bg.setStyleSheet(f"background-color: {color}22; border-radius: 10px; border: none;")
            l = QVBoxLayout(bg)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(0)
            l.setAlignment(Qt.AlignCenter)
            icon = QLabel(text)
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            f = QFont()
            f.setPointSize(18)
            f.setFamilies([
                "Noto Color Emoji", "Segoe UI Emoji", "Apple Color Emoji",
                "Noto Sans CJK SC", "WenQuanYi Micro Hei", "Helvetica"
            ])
            icon.setFont(f)
            l.addWidget(icon)
            return bg

        # --- 运动数据（大框） ---
        ride_frame = QFrame()
        ride_frame.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border-radius: 12px;
                border: 1px solid #3A3A4A;
            }
        """)
        ride_section_layout = QVBoxLayout(ride_frame)
        ride_section_layout.setSpacing(8)
        ride_section_layout.setContentsMargins(10, 8, 10, 8)

        ride_header_row = QHBoxLayout()
        ride_header_row.setSpacing(6)
        ride_header_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        ride_header_row.addWidget(_make_section_icon("🏃", "#4DB8FF"))
        ride_header = QLabel("运动数据")
        ride_header.setStyleSheet("color: #AAAAAA; background: transparent; border: none;")
        ride_header.setFont(QFont("Helvetica", 12, QFont.Bold))
        ride_header_row.addWidget(ride_header)
        ride_header_row.addStretch(1)
        ride_section_layout.setAlignment(Qt.AlignTop)
        ride_section_layout.addLayout(ride_header_row)

        ride_metrics = QHBoxLayout()
        ride_metrics.setSpacing(0)
        ride_metrics.setContentsMargins(0, 0, 0, 0)

        def _make_ride_metric(icon, title, color, font_size=28, default_text="--", unit=""):
            w = QWidget()
            w.setStyleSheet("background: transparent; border: none;")
            vl = QVBoxLayout(w)
            vl.setSpacing(4)
            vl.setContentsMargins(0, 0, 0, 0)
            vl.setAlignment(Qt.AlignCenter)

            ic = QLabel(icon)
            ic.setAlignment(Qt.AlignCenter)
            ic.setStyleSheet(f"color: {color}; background: transparent;")
            f = QFont()
            f.setPointSize(16)
            f.setFamilies([
                "Noto Color Emoji", "Segoe UI Emoji", "Apple Color Emoji",
                "Noto Sans CJK SC", "WenQuanYi Micro Hei", "Helvetica"
            ])
            ic.setFont(f)
            vl.addWidget(ic, alignment=Qt.AlignCenter)
            vl.addSpacing(8)

            # 数值 + 单位容器
            val_container = QWidget()
            val_container.setStyleSheet("background: transparent; border: none;")
            val_layout = QHBoxLayout(val_container)
            val_layout.setSpacing(4)
            val_layout.setContentsMargins(0, 0, 0, 0)
            val_layout.setAlignment(Qt.AlignCenter)

            val = QLabel(default_text)
            val.setAlignment(Qt.AlignCenter)
            val.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
            val.setFont(QFont("Arial", font_size, QFont.Bold))

            unit_lbl = QLabel(unit)
            unit_lbl.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
            unit_lbl.setStyleSheet("color: #AAAAAA; background: transparent; border: none;")
            unit_lbl.setFont(QFont("Helvetica", 10))

            val_layout.addWidget(val, alignment=Qt.AlignVCenter)
            val_layout.addWidget(unit_lbl, alignment=Qt.AlignLeft | Qt.AlignBottom)

            vl.addWidget(val_container, alignment=Qt.AlignCenter)

            t = QLabel(title)
            t.setAlignment(Qt.AlignCenter)
            t.setStyleSheet("color: #888888; background: transparent;")
            t.setFont(QFont("Helvetica", 10))
            vl.addWidget(t, alignment=Qt.AlignCenter)
            return w, val, unit_lbl

        self.ride_time_widget, self.ride_time_val, _ = _make_ride_metric("⏱️", "骑行时长", "#4DB8FF", 32, default_text="00:00:00")
        self.ride_dist_widget, self.ride_dist_val, self.ride_dist_unit = _make_ride_metric("📏", "骑行距离", "#2ecc71", 24, default_text="0", unit="m")
        self.ride_speed_widget, self.ride_speed_val, _ = _make_ride_metric("🚀", "平均速度", "#9b59b6", 24, default_text="0.0", unit="km/h")

        ride_metrics.addWidget(self.ride_time_widget, 1)

        line1 = QFrame()
        line1.setFixedWidth(1)
        line1.setStyleSheet("background-color: #555555;")
        ride_metrics.addWidget(line1)

        ride_metrics.addWidget(self.ride_dist_widget, 1)

        line2 = QFrame()
        line2.setFixedWidth(1)
        line2.setStyleSheet("background-color: #555555;")
        ride_metrics.addWidget(line2)

        ride_metrics.addWidget(self.ride_speed_widget, 1)
        ride_section_layout.addLayout(ride_metrics)
        right_layout.addWidget(ride_frame, 1)

        # --- 传感器数据（大框） ---
        sensor_frame = QFrame()
        sensor_frame.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border-radius: 12px;
                border: 1px solid #3A3A4A;
            }
        """)
        sensor_section_layout = QVBoxLayout(sensor_frame)
        sensor_section_layout.setSpacing(6)
        sensor_section_layout.setContentsMargins(10, 6, 10, 6)

        sensor_header_row = QHBoxLayout()
        sensor_header_row.setSpacing(6)
        sensor_header_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        sensor_header_row.addWidget(_make_section_icon_large("📡", "#00bcd4"))
        sensor_header = QLabel("传感器数据")
        sensor_header.setStyleSheet("color: #AAAAAA; background: transparent; border: none;")
        sensor_header.setFont(QFont("Helvetica", 14, QFont.Bold))
        sensor_header_row.addWidget(sensor_header)
        sensor_header_row.addStretch(1)
        sensor_section_layout.setAlignment(Qt.AlignTop)
        sensor_section_layout.addLayout(sensor_header_row)

        sensor_cards = QHBoxLayout()
        sensor_cards.setSpacing(8)

        self.card_cadence = MetricCard("踏频", "🔧", "#9b59b6", unit="rpm")
        self.card_slope = MetricCard("坡度", "📐", "#e67e22", unit="%")
        self.card_temp = MetricCard("温度", "🌡️", "#00bcd4", unit="°C")
        self.card_hr = MetricCard("心率", "❤️", "#e74c3c", unit="bpm")
        self.card_rear = MetricCard("后方来车", "🚗", "#2ecc71", unit="m")

        sensor_cards.addWidget(self.card_cadence, 1)
        sensor_cards.addWidget(self.card_slope, 1)
        sensor_cards.addWidget(self.card_temp, 1)
        sensor_cards.addWidget(self.card_hr, 1)
        sensor_cards.addWidget(self.card_rear, 1)
        sensor_section_layout.addLayout(sensor_cards, 1)
        right_layout.addWidget(sensor_frame, 2)
        data_main_layout.addWidget(right_panel, 1)

        # 地图页面（支持在线/离线双模式）
        tile_url = self.tile_server.url if self.tile_server else "http://localhost:8766/{z}/{x}/{y}.png"
        init_mode = "online" if self._global_online_mode else "offline"
        self.page_map = MapWidget(
            amap_key=self.amap_key,
            jsapi_key=self.amap_jsapi_key,
            security_key=self.amap_security_key,
            tile_server_url=tile_url,
            mode=init_mode
        )
        self.page_map.map_loaded.connect(self.on_map_loaded)
        self.page_map.mode_changed.connect(self._on_map_mode_changed)
        self.page_map.route_planning_failed.connect(self._on_online_fallback)

        # 连接导航信号
        self.page_map.nav_status_changed.connect(self.on_nav_status_changed)
        self.page_map.nav_instruction.connect(self.on_nav_instruction)

        # 连接新的导航处理器信号
        nav_handler = self.page_map.get_navigation_handler()
        nav_handler.nav_started.connect(self.on_nav_started)
        nav_handler.nav_stopped.connect(self.on_nav_stopped)
        nav_handler.nav_instruction.connect(self.on_nav_instruction_v2)
        nav_handler.nav_overview.connect(self.on_nav_overview)
        
        # --- 历史记录页面 ---
        self.page_history = HistoryPage(ride_repo=self.ride_repo, parent=self)
        self.page_history.ride_selected.connect(self._on_history_ride_selected)

        # --- 设置页面 ---
        self.page_settings = SettingsPage(config=self.config, parent=self)
        self.page_settings.config_saved.connect(self._on_config_saved)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setMinimumHeight(0)
        self.stacked_widget.addWidget(self.page_data)
        self.stacked_widget.addWidget(self.page_map)
        self.stacked_widget.addWidget(self.page_history)
        self.stacked_widget.addWidget(self.page_settings)

        # --- 消息框 ---
        self.dialog_container = QWidget()
        self.dialog_container.setFixedHeight(145)
        self.dialog_container.setStyleSheet("background: transparent;")

        dialog_layout = QVBoxLayout(self.dialog_container)
        dialog_layout.setContentsMargins(10, 4, 10, 4)
        dialog_layout.setSpacing(0)

        self.dialog_box = QFrame()
        self.dialog_box.setFixedHeight(120)
        self.dialog_box.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border-radius: 10px;
                border: 1px solid #4A4A4A;
            }
        """)
        box_layout = QVBoxLayout(self.dialog_box)
        box_layout.setContentsMargins(10, 6, 10, 6)
        box_layout.setSpacing(2)

        self.dialog_msg = QLabel("🤖 欢迎使用 SMART RIDE 智能助理...")
        self.dialog_msg.setFont(QFont("Helvetica", 12))
        self.dialog_msg.setStyleSheet("color: #CCCCCC; background: transparent;")
        self.dialog_msg.setWordWrap(True)
        self.dialog_msg.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.dialog_msg.setTextFormat(Qt.PlainText)
        self.dialog_msg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        box_layout.addWidget(self.dialog_msg)

        # 语音消息历史（最多显示最近2条，避免超出界面）
        self.voice_messages = []
        self.max_voice_messages = 3

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

        # 启动后 5 秒进行网络检测，无网则自动切离线
        QTimer.singleShot(5000, self._verify_startup_network)

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
        self.btn_history.setStyleSheet(self.inactive_style)
        self.btn_settings.setStyleSheet(self.inactive_style)

    def show_map_page(self):
        is_first_visit = not self._map_page_visited
        self._map_page_visited = True
        self.stacked_widget.setCurrentIndex(1)
        self.btn_data.setStyleSheet(self.inactive_style)
        self.btn_map.setStyleSheet(self.active_style)
        self.btn_history.setStyleSheet(self.inactive_style)
        self.btn_settings.setStyleSheet(self.inactive_style)
        # 只有第一次切换到地图页面时才播报加载成功
        if is_first_visit and self.page_map.is_map_loaded():
            self.on_map_loaded(True)

    def show_history_page(self):
        self.stacked_widget.setCurrentIndex(2)
        self.btn_data.setStyleSheet(self.inactive_style)
        self.btn_map.setStyleSheet(self.inactive_style)
        self.btn_history.setStyleSheet(self.active_style)
        self.btn_settings.setStyleSheet(self.inactive_style)
        self.page_history.refresh_list()

    def show_settings_page(self):
        self.stacked_widget.setCurrentIndex(3)
        self.btn_data.setStyleSheet(self.inactive_style)
        self.btn_map.setStyleSheet(self.inactive_style)
        self.btn_history.setStyleSheet(self.inactive_style)
        self.btn_settings.setStyleSheet(self.active_style)

    def _check_network(self) -> bool:
        """检查网络连接（多地址容错）"""
        import socket
        check_hosts = [
            ("223.5.5.5", 53),
            ("114.114.114.114", 53),
            ("8.8.8.8", 53),
        ]
        for host, port in check_hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((host, port))
                sock.close()
                return True
            except Exception:
                continue
        return False

    def _verify_startup_network(self):
        """启动后验证网络，无网络则自动切换至离线模式"""
        if not self._global_online_mode:
            return  # 已经是离线状态
        if not self._check_network():
            print("[Main] 启动检测：无网络，自动切换至离线模式")
            # 标记为已降级，避免 _on_map_mode_changed 重复播报
            self._auto_fallback_count = 1
            self.set_global_online_mode(False)
            self.add_voice_message("当前无网络，已切换至离线模式", icon="⚠️")
            if self.voice_player:
                self.voice_player.speak("当前无网络，已切换至离线模式", show_in_ui=False)

    def set_global_online_mode(self, online: bool, auto_fallback: bool = False):
        """设置全局在线/离线状态

        Args:
            online: True=在线, False=离线
            auto_fallback: 是否由自动降级触发
        """
        if self._global_online_mode == online:
            return

        self._global_online_mode = online
        self.config.set_last_online_mode(online)

        new_mode = "online" if online else "offline"
        self.page_map.set_mode(new_mode)

        # 同步语音播放器离线状态
        if self.voice_player and hasattr(self.voice_player, 'force_offline'):
            self.voice_player.force_offline = not online
            print(f"[Main] 语音播放器 force_offline={not online}")

        # 同步大模型客户端离线状态
        if self.unified_llm:
            self.unified_llm.force_offline = not online
            print(f"[Main] 大模型客户端 force_offline={not online}")

        if online:
            # 手动切回在线时重置降级计数，允许下次再次自动降级
            self._auto_fallback_count = 0
        elif auto_fallback:
            self._auto_fallback_count += 1
            print(f"[Main] 自动降级到离线模式 (第 {self._auto_fallback_count} 次)")

    def _toggle_map_mode(self):
        """切换在线/离线地图模式（带网络检查）"""
        if self._global_online_mode:
            # 在线 → 离线：直接切换
            self.set_global_online_mode(False)
        else:
            # 离线 → 在线：先检查网络
            if self._check_network():
                self.set_global_online_mode(True)
            else:
                print("[Main] 无网络，拒绝切换到在线模式")
                self.add_voice_message("当前无网络，无法切换在线模式", icon="⚠️")
                if self.voice_player:
                    self.voice_player.speak("当前无网络，无法切换在线模式", show_in_ui=False)

    def _on_online_fallback(self, auto_fallback: bool):
        """在线功能失败时的降级回调"""
        if not self._global_online_mode:
            return  # 已经是离线模式
        if self._auto_fallback_count >= 1:
            print("[Main] 已自动降级过，不再重复降级")
            return

        print("[Main] 在线功能失败，触发自动降级到离线")
        self.set_global_online_mode(False, auto_fallback=True)
        self.add_voice_message("网络异常，已自动切换至离线地图", icon="⚠️")
        if self.voice_player:
            self.voice_player.speak("网络异常，已自动切换至离线地图", show_in_ui=False)

    def _on_map_mode_changed(self, mode: str):
        """地图模式切换后的回调"""
        if mode == "offline":
            self.btn_map_mode.setText("离线")
            self.btn_map_mode.setStyleSheet(
                "QPushButton { background-color: #e74c3c; color: #FFFFFF; border-radius: 6px; }"
                "QPushButton:pressed { background-color: #c0392b; }"
            )
            if self._auto_fallback_count == 0:
                # 仅用户手动切换时才播报，避免自动降级时重复播报
                self.add_voice_message("已切换至离线地图", icon="🗺️")
                if self.voice_player:
                    self.voice_player.speak("已切换至离线地图", show_in_ui=False)
        else:
            self.btn_map_mode.setText("在线")
            self.btn_map_mode.setStyleSheet(
                "QPushButton { background-color: #2ecc71; color: #FFFFFF; border-radius: 6px; }"
                "QPushButton:pressed { background-color: #27ae60; }"
            )
            self.add_voice_message("已切换至在线地图", icon="🗺️")
            if self.voice_player:
                self.voice_player.speak("已切换至在线地图", show_in_ui=False)

    def _on_config_saved(self):
        print("[Main] 配置已更新并保存")
        self.add_voice_message("设置已保存", icon="⚙️")

    def safe_exit(self):
        print("退出程序...")
        if hasattr(self, 'serial_worker'):
            self.serial_worker.stop()
        if hasattr(self, 'debugger'):
            self.debugger.stop()
        # 停止瓦片服务器
        if hasattr(self, 'tile_server') and self.tile_server:
            try:
                self.tile_server.stop()
            except:
                pass
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
        if hasattr(self, 'comm_service'):
            try:
                self.comm_service.stop()
            except:
                pass
        self.close()

    @staticmethod
    def yaw_to_direction(yaw: float) -> str:
        """将 IMU 航偏角（0°正北，顺时针增加）转换为中文方向描述，精确到每一度。"""
        angle = yaw % 360.0
        # 四舍五入到整数度
        a = int(round(angle))
        if a >= 360:
            a = 0

        if a == 0:
            return "正北"
        if a == 90:
            return "正东"
        if a == 180:
            return "正南"
        if a == 270:
            return "正西"
        if a == 45:
            return "东北"
        if a == 135:
            return "东南"
        if a == 225:
            return "西南"
        if a == 315:
            return "西北"

        if 0 < a < 45:
            return f"北偏东{a}度"
        if 45 < a < 90:
            return f"东偏北{90 - a}度"
        if 90 < a < 135:
            return f"东偏南{a - 90}度"
        if 135 < a < 180:
            return f"南偏东{180 - a}度"
        if 180 < a < 225:
            return f"南偏西{a - 180}度"
        if 225 < a < 270:
            return f"西偏南{270 - a}度"
        if 270 < a < 315:
            return f"西偏北{a - 270}度"
        if 315 < a < 360:
            return f"北偏西{360 - a}度"
        return "未知方向"

    def on_data_received(self, data):
        formatted_data = json.dumps(data, indent=2, ensure_ascii=False)
        print(formatted_data)

        # 解析为协议层 SensorData
        try:
            from core.data_context import get_data_context
            sensor = SensorData.from_stm32_json(data)
            get_data_context().update_from_sensor(sensor)
            # 保存到文件，供LLM读取
            get_data_context().save_to_file()
            # DEBUG: 确认DataContextManager中的实际数据
            d = get_data_context().get_data()
            print(f"[Main] DataContext 更新后 -> speed={d.speed}, power={d.power}, cadence={d.cadence}, hr={d.heart_rate}")
            # 推送到通信服务（由 CommService 决定何时发给 App）
            self.comm_service.on_sensor_data(sensor)
            # 推送到骑行服务
            print(f"[Main] 推送 sensor 到 RideService, state={self.ride_service.state.value}, speed={sensor.speed}")
            self.ride_service.on_sensor_data(sensor)
            # 推送到告警服务
            self.alert_service.on_sensor_data(sensor, self.ride_service.state)
            print(f"[Main] RideService 返回, distance={self.ride_service.summary.total_distance:.4f}")
        except Exception as e:
            print(f"[DataContext] 更新失败: {e}")
            import traceback
            traceback.print_exc()

        # 更新数据卡片
        if "speed" in data:
            val = float(data["speed"])
            self.gauge_speed.set_value(val)

        if "power" in data:
            val = int(data["power"])
            self.gauge_power.set_value(val)

        if "cadence" in data:
            self.card_cadence.update_value(int(data["cadence"]))

        if "slope" in data:
            val = float(data["slope"])
            prefix = "+" if val > 0 else ""
            color = "#e74c3c" if abs(val) > 10 else "#2ecc71" if val > 0 else "#FFFFFF"
            self.card_slope.update_value(f"{prefix}{val:.1f}", color)

        if "temperature" in data:
            val = float(data["temperature"])
            color = "#e74c3c" if val > 35 else "#00bcd4" if val < 10 else "#FFFFFF"
            self.card_temp.update_value(f"{val:.1f}", color)

        if "heart_rate" in data:
            val = int(data["heart_rate"])
            color = "#e74c3c" if val > 180 else "#f39c12" if val > 160 else "#FFFFFF"
            self.card_hr.update_value(val, color)

        if "rear_dist" in data:
            val = float(data["rear_dist"])
            color = "#e74c3c" if val < 5 else "#f39c12" if val < 10 else "#2ecc71"
            self.card_rear.update_value(f"{val:.1f}", color)
            
        if "zt_flag" in data:
            zt = int(data["zt_flag"])
            zt_map = {
                0: ("跌倒", "#e74c3c"),
                1: ("向右转弯", "#f39c12"),
                2: ("向左转弯", "#f39c12"),
                3: ("上坡", "#3498db"),
                4: ("下坡", "#3498db"),
                5: ("正常骑行", "#2ecc71"),
            }
            text, color = zt_map.get(zt, (f"状态 {zt}", "#FFFFFF"))
            self.zt_status_label.setText(text)
            self.zt_status_label.setStyleSheet(f"color: {color}; background: transparent;")

        if "yaw" in data:
            yaw_val = float(data["yaw"])
            self.page_map.update_yaw(yaw_val)

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
            from core.data_context import get_data_context
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


    def update_info(self):
        self.time_label.setText(QDateTime.currentDateTime().toString("hh:mm"))

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
        """导航开始回调——总览播报已在 on_nav_overview 中处理，此处不再重复播报"""
        print("[Main] 导航开始（总览播报由 on_nav_overview 统一处理）")

    def on_nav_stopped(self):
        """导航结束回调——只语音播报，UI 由 voice player 回调统一显示"""
        print("[Main] 导航结束")
        if self.voice_player:
            try:
                self.voice_player.speak("导航结束")
            except Exception as e:
                print(f"[Voice] 导航结束播报失败: {e}")
    
    def on_nav_instruction_v2(self, instruction: str, detail: str):
        """导航指令回调 V2（带详细信息）——只语音播报，UI 由 voice player 回调统一显示"""
        print(f"[Main] 导航指令: {instruction} | {detail}")

        if self.voice_player:
            try:
                # 简化指令用于语音播报，voice player 内部会自动显示 🔊 消息
                speak_text = self._simplify_nav_instruction(instruction)
                self.voice_player.speak(speak_text)
            except Exception as e:
                print(f"[Voice] 导航语音播报失败: {e}")

    def on_nav_overview(self, text: str):
        """导航总览回调（在线地图导航开始时播报）"""
        print(f"[Main] 导航总览: {text}")
        if self.voice_player:
            try:
                self.voice_player.speak(text)
            except Exception as e:
                print(f"[Voice] 导航总览播报失败: {e}")

    def on_map_loaded(self, success: bool):
        """地图加载完成回调——只有用户主动进入地图页面后才播报"""
        if not self._map_page_visited:
            return
        if success:
            print("[Main] ✅ 地图页面加载成功！")
            if self.voice_player:
                try:
                    self.voice_player.speak("地图加载成功")
                except Exception as e:
                    print(f"[Voice] 地图加载成功播报失败: {e}")
        else:
            print("[Main] ❌ 地图页面加载失败！")
            if self.voice_player:
                try:
                    self.voice_player.speak("地图加载失败，请检查网络或API配置")
                except Exception as e:
                    print(f"[Voice] 地图加载失败播报失败: {e}")
    
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
        """导航指令回调（旧版，用于兼容）——只语音播报，UI 由 voice player 回调统一显示"""
        print(f"导航指令: {instruction}")

        # 语音播报导航指令，voice player 内部会自动显示 🔊 消息
        if self.voice_player:
            try:
                self.voice_player.speak(instruction)
            except Exception as e:
                print(f"[Voice] 导航语音播报失败: {e}")

    def _on_history_ride_selected(self, ride_id: str, track_points: list):
        """历史记录被选中：加载轨迹并切换到地图页"""
        print(f"[Main] 选中历史记录: {ride_id}, 轨迹点数: {len(track_points)}")
        # 先切换到地图页，确保地图可见后再加载轨迹，否则 setFitView 比例尺不对
        self.show_map_page()
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(300, lambda: self.page_map.load_history_track(track_points))
        self.add_voice_message(f"已加载历史轨迹，共 {len(track_points)} 个轨迹点", icon="🗺️")

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
        max_length = 500
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

    def on_app_command(self, cmd):
        """处理 App 发来的命令"""
        from core.protocol import AppCommandType
        print(f"[Main] 执行 App 命令: {cmd.cmd_type.value}")

        if cmd.cmd_type == AppCommandType.START_RIDE:
            self.ride_service.start_ride()

        elif cmd.cmd_type == AppCommandType.PAUSE_RIDE:
            self.ride_service.pause_ride()

        elif cmd.cmd_type == AppCommandType.RESUME_RIDE:
            self.ride_service.resume_ride()

        elif cmd.cmd_type == AppCommandType.STOP_RIDE:
            self.ride_service.stop_ride()

        elif cmd.cmd_type == AppCommandType.PING:
            pass

        else:
            print(f"[Main] 未处理的命令: {cmd.cmd_type.value}")

    def on_comm_event(self, event_type, payload):
        """处理通信服务推送的事件（如告警）"""
        msg = payload.get("message", "")
        if event_type == "alert" and msg:
            self.add_voice_message(msg, icon="⚠️")
            if self.voice_player:
                level = payload.get("level", "warning")
                self.voice_player.speak(msg)

    def _on_alert_triggered(self, alert_type: str, message: str, level: str):
        """处理 AlertService 触发的告警"""
        # UI 消息
        self.add_voice_message(message, icon="⚠️")

        # 语音播报
        if self.voice_player:
            self.voice_player.speak(message)

        # LED 闪灯：critical 红灯闪烁，warning 黄灯闪烁，其他蓝灯闪烁
        if self.led_controller:
            if level == "critical":
                self.led_controller.start_pattern("blink", LEDController.COLOR_RED)
            elif level == "warning":
                self.led_controller.start_pattern("blink", LEDController.COLOR_YELLOW)
            else:
                self.led_controller.start_pattern("blink", LEDController.COLOR_BLUE)

            # 3 秒后恢复绿色常亮（正常骑行状态指示灯）
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(3000, lambda: (
                self.led_controller.stop_pattern(),
                self.led_controller.set_all(LEDController.COLOR_GREEN)
            ))

    # --------------------------------------------------------------------------
    # 骑行服务回调
    # --------------------------------------------------------------------------

    def _on_ride_action_clicked(self):
        state = self.ride_service.get_state()
        if state == RideSessionState.IDLE or state == RideSessionState.FINISHED:
            self.ride_service.start_ride()
        elif state == RideSessionState.RIDING:
            self.ride_service.pause_ride()
        elif state == RideSessionState.PAUSED:
            self.ride_service.resume_ride()

    def _on_ride_stop_clicked(self):
        self.ride_service.stop_ride()

    def _on_ride_state_changed(self, state: str):
        self.comm_service.set_ride_state(RideSessionState(state))
        if state == "riding":
            self.btn_ride_action.setText("暂停")
            self.btn_ride_action.setStyleSheet(
                "QPushButton { background-color: #f39c12; color: #FFFFFF; border-radius: 8px; }"
                "QPushButton:pressed { background-color: #d35400; }"
            )
            self.btn_ride_stop.show()
        elif state == "paused":
            self.btn_ride_action.setText("继续")
            self.btn_ride_action.setStyleSheet(
                "QPushButton { background-color: #2ecc71; color: #FFFFFF; border-radius: 8px; }"
                "QPushButton:pressed { background-color: #27ae60; }"
            )
            self.btn_ride_stop.show()
        elif state == "idle" or state == "finished":
            self.btn_ride_action.setText("开始骑行")
            self.btn_ride_action.setStyleSheet(
                "QPushButton { background-color: #2ecc71; color: #FFFFFF; border-radius: 8px; }"
                "QPushButton:pressed { background-color: #27ae60; }"
            )
            self.btn_ride_stop.hide()
            # 结束后清空统计显示
            if state == "idle":
                self.ride_time_val.setText("00:00:00")
                self.ride_dist_val.setText("0")
                self.ride_dist_unit.setText("m")
                self.ride_speed_val.setText("0.0")

    def _on_ride_stats_updated(self, summary: RideSummary):
        mt = int(summary.moving_time)
        h = mt // 3600
        m = (mt % 3600) // 60
        s = mt % 60
        self.ride_time_val.setText(f"{h:02d}:{m:02d}:{s:02d}")

        # 骑行距离：小于 1km 用米，大于等于 1km 用 km
        if summary.total_distance < 1.0:
            self.ride_dist_val.setText(str(int(summary.total_distance * 1000)))
            self.ride_dist_unit.setText("m")
        else:
            self.ride_dist_val.setText(f"{summary.total_distance:.2f}")
            self.ride_dist_unit.setText("km")

        self.ride_speed_val.setText(f"{summary.avg_speed:.1f}")

    def _on_ride_started(self, summary: RideSummary):
        self.add_voice_message("骑行开始", icon="🚴")
        if self.voice_player:
            self.voice_player.speak("骑行开始", show_in_ui=False)
        if self.alert_service:
            self.alert_service.reset()

    def _on_ride_paused(self):
        self.add_voice_message("骑行暂停", icon="⏸")
        if self.voice_player:
            self.voice_player.speak("骑行暂停", show_in_ui=False)

    def _on_ride_resumed(self):
        self.add_voice_message("骑行继续", icon="▶")
        if self.voice_player:
            self.voice_player.speak("骑行继续", show_in_ui=False)

    def _on_ride_stopped(self, summary: RideSummary):
        self.add_voice_message("骑行结束", icon="🏁")
        if self.voice_player:
            self.voice_player.speak("骑行结束", show_in_ui=False)
        # 最终统计刷新一次
        self._on_ride_stats_updated(summary)
        if self.alert_service:
            self.alert_service.reset()

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