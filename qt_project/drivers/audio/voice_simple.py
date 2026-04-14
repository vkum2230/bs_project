#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版语音播报 - 使用系统命令直接播放
作为 pyttsx3 的备选方案
"""

import os
import subprocess
import threading
from typing import Optional


class SimpleVoicePlayer:
    """简化版语音播放器 - 使用 espeak 或 festival"""
    
    def __init__(self, rate: int = 150):
        self.rate = rate
        self._lock = threading.Lock()
        
        # 检测可用的 TTS
        self.tts_cmd = self._detect_tts()
        print(f"[SimpleVoice] 使用 TTS: {self.tts_cmd}")
    
    def _detect_tts(self) -> Optional[list]:
        """检测可用的 TTS 命令"""
        # 1. 尝试 espeak (带中文支持)
        try:
            result = subprocess.run(
                ["which", "espeak"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return ["espeak", "-v", "zh", "-s", str(self.rate)]
        except:
            pass
        
        # 2. 尝试 festival
        try:
            result = subprocess.run(
                ["which", "festival"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return ["festival", "--tts"]
        except:
            pass
        
        # 3. 尝试 say (macOS)
        try:
            result = subprocess.run(
                ["which", "say"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return ["say"]
        except:
            pass
        
        return None
    
    def speak(self, text: str, block: bool = False) -> bool:
        """播报文本"""
        if not text or self.tts_cmd is None:
            return False
        
        print(f"[SimpleVoice] 播报: {text}")
        
        def _do_speak():
            with self._lock:
                try:
                    if "festival" in self.tts_cmd:
                        # festival 从 stdin 读取
                        proc = subprocess.Popen(
                            self.tts_cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE
                        )
                        proc.communicate(text.encode('utf-8'), timeout=30)
                    else:
                        # 其他命令直接在参数中传递
                        cmd = self.tts_cmd + [text]
                        proc = subprocess.Popen(
                            cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE
                        )
                        proc.communicate(timeout=30)
                    
                    return proc.returncode == 0
                except Exception as e:
                    print(f"[SimpleVoice] 播报失败: {e}")
                    return False
        
        if block:
            return _do_speak()
        else:
            thread = threading.Thread(target=_do_speak)
            thread.daemon = True
            thread.start()
            return True


def test_simple_voice():
    """测试简化版语音"""
    print("测试简化版语音...")
    player = SimpleVoicePlayer()
    if player.tts_cmd:
        player.speak("你好，我是骑行小智", block=True)
    else:
        print("未找到可用的 TTS 命令")


if __name__ == "__main__":
    test_simple_voice()
