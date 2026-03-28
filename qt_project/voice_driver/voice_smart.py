#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能语音播放器 - 自动选择最佳 TTS
有网络时用 Edge-TTS（音质好），离线时用 espeak（稳定）
"""

import os
import sys
import subprocess
import threading
import tempfile
import socket
from typing import Optional
from pathlib import Path


class SmartVoicePlayer:
    """
    智能语音播放器
    
    优先级：
    1. Edge-TTS（在线，音质最好）
    2. pyttsx3（离线，无需网络）
    3. espeak（离线，系统自带）
    """
    
    # Edge-TTS 语音选项
    EDGE_VOICES = {
        'xiaoxiao': 'zh-CN-XiaoxiaoNeural',      # 晓晓 - 温柔女声
        'xiaoyi': 'zh-CN-XiaoyiNeural',          # 小怡 - 活泼女声
        'yunyang': 'zh-CN-YunyangNeural',        # 云扬 - 男声
        'yunxi': 'zh-CN-YunxiNeural',            # 云希 - 年轻男声
    }
    
    def __init__(self,
                 voice: str = 'xiaoxiao',
                 rate: str = "+10%",
                 volume: str = "+10%",
                 offline_fallback: bool = True):
        """
        初始化智能播放器
        
        Args:
            voice: 语音名称
            rate: 语速
            volume: 音量
            offline_fallback: 离线时是否使用备用引擎
        """
        self.voice_name = voice
        self.edge_voice = self.EDGE_VOICES.get(voice, voice)
        self.rate = rate
        self.volume = volume
        self.offline_fallback = offline_fallback
        
        self._lock = threading.Lock()
        self._current_engine = None
        self._pyttsx3_engine = None
        self._edge_path = self._find_edge_tts()
        
        # 检测网络状态
        self.has_network = self._check_network()
        
        # 初始化最佳引擎
        self._init_engine()
    
    def _find_edge_tts(self) -> Optional[str]:
        """查找 edge-tts 可执行文件"""
        # 确保 PATH 包含 ~/.local/bin
        os.environ["PATH"] = os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", "")
        
        # 常见路径
        possible_paths = [
            os.path.expanduser("~/.local/bin/edge-tts"),
            "/usr/local/bin/edge-tts",
            "/usr/bin/edge-tts",
            "edge-tts",  # 如果在 PATH 中
        ]
        
        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                print(f"[SmartVoice] 找到 edge-tts: {path}")
                return path
        
        # 尝试使用 Python 模块方式
        try:
            result = subprocess.run(
                [sys.executable, "-m", "edge_tts", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"[SmartVoice] 使用 Python 模块方式: {sys.executable} -m edge_tts")
                return f"{sys.executable} -m edge_tts"
        except Exception as e:
            print(f"[SmartVoice] Python 模块方式失败: {e}")
        
        print("[SmartVoice] 警告: 未找到 edge-tts")
        return None
    
    def _check_network(self) -> bool:
        """检查网络连接"""
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        except:
            return False
    
    def _init_engine(self):
        """初始化最佳引擎"""
        print(f"[SmartVoice] 网络状态: {'在线' if self.has_network else '离线'}")
        print(f"[SmartVoice] edge-tts 路径: {self._edge_path}")
        
        # 1. 优先尝试 Edge-TTS（有网络时）
        if self.has_network and self._edge_path:
            try:
                # 测试 Edge-TTS 是否可用
                test_cmd = self._edge_path.split() + ["--version"]
                print(f"[SmartVoice] 测试 Edge-TTS: {' '.join(test_cmd)}")
                result = subprocess.run(test_cmd, capture_output=True, timeout=5)
                print(f"[SmartVoice] Edge-TTS 测试结果: returncode={result.returncode}")
                if result.returncode == 0:
                    self._current_engine = 'edge'
                    print(f"[SmartVoice] ✅ 使用 Edge-TTS 引擎")
                    print(f"[SmartVoice] 语音: {self.edge_voice}")
                    return
                else:
                    err = result.stderr.decode() if result.stderr else "未知错误"
                    print(f"[SmartVoice] Edge-TTS 测试失败: {err[:100]}")
            except Exception as e:
                print(f"[SmartVoice] Edge-TTS 测试异常: {e}")
        
        # 2. 离线备用：pyttsx3
        if self.offline_fallback:
            try:
                import pyttsx3
                self._pyttsx3_engine = pyttsx3.init()
                self._pyttsx3_engine.setProperty('rate', 160)
                self._pyttsx3_engine.setProperty('volume', 0.9)
                
                # 找中文语音
                voices = self._pyttsx3_engine.getProperty('voices')
                for v in voices:
                    if 'chinese' in v.name.lower() or 'zh' in v.id.lower():
                        self._pyttsx3_engine.setProperty('voice', v.id)
                        break
                
                self._current_engine = 'pyttsx3'
                print(f"[SmartVoice] ✅ 使用 pyttsx3 引擎（离线）")
                return
            except Exception as e:
                print(f"[SmartVoice] pyttsx3 初始化失败: {e}")
            
            # 3. 最后的备用：espeak
            try:
                result = subprocess.run(
                    ["which", "espeak"],
                    capture_output=True
                )
                if result.returncode == 0:
                    self._current_engine = 'espeak'
                    print(f"[SmartVoice] ✅ 使用 espeak 引擎（离线）")
                    return
            except Exception as e:
                print(f"[SmartVoice] espeak 检查失败: {e}")
        
        print("[SmartVoice] ⚠️ 警告: 未找到可用的 TTS 引擎")
        self._current_engine = None
    
    def speak(self, text: str, block: bool = False) -> bool:
        """播报文本"""
        if not text or not self._current_engine:
            return False
        
        print(f"[SmartVoice] 播报: {text[:50]}...")
        
        def _do_speak():
            with self._lock:
                if self._current_engine == 'edge':
                    return self._speak_edge(text)
                elif self._current_engine == 'pyttsx3':
                    return self._speak_pyttsx3(text)
                elif self._current_engine == 'espeak':
                    return self._speak_espeak(text)
                return False
        
        if block:
            return _do_speak()
        else:
            thread = threading.Thread(target=_do_speak)
            thread.daemon = True
            thread.start()
            return True
    
    def _speak_edge(self, text: str) -> bool:
        """使用 Edge-TTS"""
        mp3_path = None
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                mp3_path = f.name
            
            # 构建命令
            cmd = self._edge_path.split() + [
                "--voice", self.edge_voice,
                "--rate", self.rate,
                "--volume", self.volume,
                "--text", text,
                "--write-media", mp3_path
            ]
            
            print(f"[SmartVoice] 生成语音: {' '.join(cmd[:6])}...")
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode != 0:
                err = result.stderr.decode() if result.stderr else "未知错误"
                print(f"[SmartVoice] Edge-TTS 生成失败: {err[:200]}")
                # Edge-TTS 失败，可能是网络问题，切换到离线引擎
                print(f"[SmartVoice] 切换到离线引擎")
                self._current_engine = 'pyttsx3'
                return self._speak_pyttsx3(text)
            
            print(f"[SmartVoice] 语音生成成功: {os.path.getsize(mp3_path)} bytes")
            
            # 播放 MP3
            play_result = self._play_mp3(mp3_path)
            if not play_result:
                print("[SmartVoice] MP3 播放失败，尝试其他方式...")
            return play_result
            
        except Exception as e:
            print(f"[SmartVoice] Edge-TTS 错误: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if mp3_path and os.path.exists(mp3_path):
                try:
                    os.remove(mp3_path)
                except:
                    pass
    
    def _speak_pyttsx3(self, text: str) -> bool:
        """使用 pyttsx3"""
        try:
            self._pyttsx3_engine.say(text)
            self._pyttsx3_engine.runAndWait()
            return True
        except Exception as e:
            print(f"[SmartVoice] pyttsx3 错误: {e}")
            # 回退到 espeak
            return self._speak_espeak(text)
    
    def _speak_espeak(self, text: str) -> bool:
        """使用 espeak"""
        try:
            result = subprocess.run(
                ["espeak", "-v", "zh", text],
                capture_output=True,
                timeout=30
            )
            return result.returncode == 0
        except:
            return False
    
    def _play_mp3(self, mp3_path: str) -> bool:
        """播放 MP3"""
        players = [
            ["mpg123", mp3_path],
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", mp3_path],
        ]
        
        for cmd in players:
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=60)
                if result.returncode == 0:
                    return True
            except:
                pass
        
        return False
    
    def stop(self):
        """停止播放"""
        pass
    
    def get_status(self) -> dict:
        """获取当前状态"""
        return {
            'engine': self._current_engine,
            'has_network': self.has_network,
            'voice': self.edge_voice if self._current_engine == 'edge' else 'default'
        }


if __name__ == "__main__":
    # 测试
    player = SmartVoicePlayer()
    status = player.get_status()
    print(f"\n状态: {status}")
    
    player.speak("你好，我是骑行小智", block=True)
