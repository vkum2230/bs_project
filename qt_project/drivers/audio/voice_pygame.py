#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 pygame 的语音播放器 - 不依赖外部播放器
"""

import os
import io
import threading
import tempfile
import subprocess
from typing import Optional


class PygameVoicePlayer:
    """使用 pygame 播放音频 - 绕过 aplay"""
    
    def __init__(self, rate: int = 150):
        self.rate = rate
        self._lock = threading.Lock()
        self._initialized = False
        
        try:
            import pygame
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self._initialized = True
            print("[PygameVoice] 初始化成功")
        except Exception as e:
            print(f"[PygameVoice] 初始化失败: {e}")
    
    def speak(self, text: str, block: bool = False) -> bool:
        """播报文本"""
        if not text or not self._initialized:
            return False
        
        print(f"[PygameVoice] 播报: {text}")
        
        def _do_speak():
            try:
                # 生成 WAV
                import pygame
                
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    wav_path = f.name
                
                try:
                    # 使用 espeak/espeak-ng 生成语音
                    if self._check_command("espeak-ng"):
                        cmd = ["espeak-ng", "-v", "zh", "-s", str(self.rate), "-w", wav_path, text]
                    elif self._check_command("espeak"):
                        cmd = ["espeak", "-v", "zh", "-s", str(self.rate), "-w", wav_path, text]
                    else:
                        return False
                    
                    result = subprocess.run(cmd, capture_output=True, timeout=10)
                    if result.returncode != 0:
                        return False
                    
                    # 使用 pygame 播放
                    pygame.mixer.music.load(wav_path)
                    pygame.mixer.music.play()
                    
                    # 等待播放完成
                    while pygame.mixer.music.get_busy():
                        import time
                        time.sleep(0.1)
                    
                    return True
                    
                finally:
                    if os.path.exists(wav_path):
                        try:
                            os.remove(wav_path)
                        except:
                            pass
                            
            except Exception as e:
                print(f"[PygameVoice] 播报失败: {e}")
                return False
        
        if block:
            return _do_speak()
        else:
            thread = threading.Thread(target=_do_speak)
            thread.daemon = True
            thread.start()
            return True
    
    def _check_command(self, cmd: str) -> bool:
        """检查命令是否存在"""
        try:
            import shutil
            return shutil.which(cmd) is not None
        except:
            return False
    
    def stop(self):
        """停止播放"""
        if self._initialized:
            try:
                import pygame
                pygame.mixer.music.stop()
            except:
                pass


if __name__ == "__main__":
    player = PygameVoicePlayer()
    player.speak("你好，我是骑行小智", block=True)
