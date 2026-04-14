#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线语音合成模块 - 支持多种引擎
支持：Piper、MeloTTS（如果安装）
"""

import os
import subprocess
import tempfile
import threading
from typing import Optional


class OfflineVoicePlayer:
    """
    离线语音播放器 - 自动选择最佳引擎
    优先级：Piper > MeloTTS > espeak
    """
    
    def __init__(self, audio_device: str = "plughw:2,0", message_callback=None):
        self._audio_device = audio_device
        self._message_callback = message_callback
        
        # 引擎
        self._piper = None
        self._melo = None
        
        # 初始化
        self._init_piper()
        self._init_melo()
    
    def _init_piper(self):
        """初始化 Piper"""
        try:
            from .piper_voice import PiperVoicePlayer
            self._piper = PiperVoicePlayer(
                audio_device=self._audio_device,
                message_callback=self._message_callback
            )
            if self._piper.is_available():
                print("[OfflineVoice] Piper 已加载")
            else:
                print("[OfflineVoice] Piper 不可用")
                self._piper = None
        except Exception as e:
            print(f"[OfflineVoice] Piper 初始化失败: {e}")
            self._piper = None
    
    def _init_melo(self):
        """初始化 MeloTTS"""
        try:
            # 尝试导入 MeloTTS
            from melo.api import TTS
            self._melo = TTS(language='ZH', device='cpu')
            print("[OfflineVoice] MeloTTS 已加载")
        except Exception as e:
            print(f"[OfflineVoice] MeloTTS 未安装: {e}")
            self._melo = None
    
    def is_available(self) -> bool:
        """检查是否有可用引擎"""
        return self._piper is not None or self._melo is not None
    
    def speak(self, text: str, block: bool = False, show_in_ui: bool = True) -> bool:
        """播报文本"""
        if not text:
            return False
        
        if show_in_ui and self._message_callback:
            self._message_callback(text, icon="🔊")
        
        def _do_speak():
            # 优先使用 Piper（最快）
            if self._piper:
                try:
                    print("[OfflineVoice] 使用 Piper...")
                    result = self._piper.speak(text, block=True, show_in_ui=False)
                    if result:
                        print("[OfflineVoice] Piper 成功")
                        return True
                except Exception as e:
                    print(f"[OfflineVoice] Piper 失败: {e}")
            
            # 尝试 MeloTTS（音质更好但较慢）
            if self._melo:
                try:
                    print("[OfflineVoice] 使用 MeloTTS...")
                    return self._speak_melo(text)
                except Exception as e:
                    print(f"[OfflineVoice] MeloTTS 失败: {e}")
            
            # 保底 espeak
            print("[OfflineVoice] 使用 espeak...")
            return self._speak_espeak(text)
        
        if block:
            return _do_speak()
        else:
            thread = threading.Thread(target=_do_speak)
            thread.daemon = True
            thread.start()
            return True
    
    def _speak_melo(self, text: str) -> bool:
        """使用 MeloTTS 播报"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            
            # 合成
            speaker_ids = self._melo.hps.data.spk2id
            speaker_id = speaker_ids['ZH']
            
            self._melo.tts_to_file(text, speaker_id, wav_path, speed=1.0)
            
            # 播放
            subprocess.run(
                ["aplay", "-q", "-D", self._audio_device, wav_path],
                capture_output=True,
                timeout=30
            )
            
            os.remove(wav_path)
            return True
            
        except Exception as e:
            print(f"[OfflineVoice] MeloTTS 错误: {e}")
            return False
    
    def _speak_espeak(self, text: str) -> bool:
        """使用 espeak 保底"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            
            subprocess.run(
                ["espeak", "-v", "zh", "-w", wav_path, text],
                capture_output=True,
                timeout=10
            )
            
            subprocess.run(
                ["aplay", "-q", "-D", self._audio_device, wav_path],
                capture_output=True,
                timeout=30
            )
            
            os.remove(wav_path)
            return True
            
        except Exception as e:
            print(f"[OfflineVoice] espeak 错误: {e}")
            return False


def install_melotts():
    """安装 MeloTTS（音质更好的中文TTS）"""
    print("="*50)
    print("安装 MeloTTS 离线语音")
    print("="*50)
    print()
    print("MeloTTS 特点：")
    print("  - 基于深度学习，声音更自然")
    print("  - 专门为中文优化")
    print("  - 支持多种语速、音调调节")
    print()
    print("安装命令：")
    print("  pip3 install melotts")
    print("  pip3 install unidecode")
    print()
    print("注意：首次使用时会自动下载模型（约100MB）")
    print("      树莓派上生成较慢，请耐心等待")
    print()
    print("="*50)


def install_piper_high_quality():
    """安装 Piper 高质量模型"""
    print("="*50)
    print("安装 Piper 高质量中文模型")
    print("="*50)
    print()
    print("当前使用的是 medium 质量模型，可以升级为 high 质量：")
    print()
    print("1. 下载高质量模型：")
    print("   wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/high/zh_CN-huayan-high.onnx")
    print("   wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/high/zh_CN-huayan-high.onnx.json")
    print()
    print("2. 放置到目录：")
    print("   ~/.local/share/piper/zh_CN/")
    print()
    print("3. 修改代码使用高质量模型")
    print()
    print("high 质量特点：")
    print("  - 文件更大（~120MB vs ~60MB）")
    print("  - 生成稍慢（~1秒 vs ~0.5秒）")
    print("  - 声音更自然、更清晰")
    print()
    print("="*50)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "install-melo":
            install_melotts()
        elif sys.argv[1] == "install-hq":
            install_piper_high_quality()
        else:
            print(f"未知命令: {sys.argv[1]}")
            print("用法: python3 offline_voice.py [install-melo|install-hq]")
    else:
        # 测试
        print("测试离线语音...")
        player = OfflineVoicePlayer()
        
        if player.is_available():
            print("\n测试播报...")
            player.speak("你好，我是骑行小智，现在使用离线语音播报。", block=True)
        else:
            print("没有可用的离线语音引擎")
