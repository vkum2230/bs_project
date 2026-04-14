#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音驱动模块 - 用于 SMART RIDE 智能骑行系统
基于 ReSpeaker 2-Mic 语音模块

模块说明:
- voice_player: 语音播报器，支持 pyttsx3/edge-tts/espeak
- voice_recorder: 语音录音和识别
- led_controller: APA102 LED 控制器
- button_handler: 按钮事件处理器

使用示例:
    from drivers.audio import VoicePlayer, LEDController, ButtonHandler, ButtonEvent
    from drivers.audio.voice_recorder import ButtonVoiceAssistant
    
    # 语音播报
    voice = VoicePlayer()
    voice.speak("你好，我是骑行小智")
    
    # 按钮语音助手（按住说话）
    assistant = ButtonVoiceAssistant(
        voice_player=voice,
        message_callback=lambda text, icon: print(f"{icon} {text}")
    )
    
    # LED 控制
    led = LEDController()
    led.set_all(LEDController.COLOR_BLUE)
    
    # 按钮处理
    btn = ButtonHandler()
    btn.on(ButtonEvent.CLICK, lambda: print("点击"))
    btn.start()
"""

from .voice_player import VoicePlayer, get_voice_player, speak
from .voice_respeaker import ReSpeakerVoicePlayer
from .voice_edge import EdgeVoicePlayer
from .voice_smart import SmartVoicePlayer
from .voice_edge_simple import SimpleEdgeVoicePlayer
from .voice_final import FinalVoicePlayer
from .led_controller import LEDController, get_led_controller
from .button_handler import ButtonHandler, ButtonEvent
from .voice_recorder import VoiceRecorder, VoiceRecognizer, ButtonVoiceAssistant

__all__ = [
    'VoicePlayer', 'get_voice_player', 'speak',
    'ReSpeakerVoicePlayer',
    'EdgeVoicePlayer',
    'SmartVoicePlayer',
    'SimpleEdgeVoicePlayer',
    'FinalVoicePlayer',
    'LEDController', 'get_led_controller',
    'ButtonHandler', 'ButtonEvent',
    'VoiceRecorder', 'VoiceRecognizer', 'ButtonVoiceAssistant'
]

__version__ = "1.1.0"
