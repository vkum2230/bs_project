#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 ALSA-OSS 或 PulseAudio 包装器的语音播放器
绕过设备占用问题
"""

import os
import subprocess
import threading
import tempfile
from typing import Optional


class AOSSVoicePlayer:
    """使用 aoss/padsp 包装器的语音播放器"""
    
    def __init__(self, rate: int = 150):
        self.rate = rate
        self._lock = threading.Lock()
        self._current_process: Optional[subprocess.Popen] = None
        
        # 检测可用的包装器
        self.wrapper = self._detect_wrapper()
        self.tts = self._detect_tts()
        
        print(f"[AOSSVoice] 使用包装器: {self.wrapper or '无'}")
        print(f"[AOSSVoice] 使用 TTS: {self.tts or '无'}")
    
    def _detect_wrapper(self) -> Optional[str]:
        """检测 ALSA/PulseAudio 包装器"""
        # 检测 aoss (ALSA-OSS)
        try:
            result = subprocess.run(
                ["which", "aoss"],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                return "aoss"
        except:
            pass
        
        # 检测 padsp (PulseAudio OSS)
        try:
            result = subprocess.run(
                ["which", "padsp"],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                return "padsp"
        except:
            pass
        
        return None
    
    def _detect_tts(self) -> Optional[str]:
        """检测 TTS 命令"""
        for cmd in ["espeak-ng", "espeak"]:
            try:
                result = subprocess.run(
                    ["which", cmd],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return cmd
            except:
                pass
        return None
    
    def speak(self, text: str, block: bool = False) -> bool:
        """播报文本"""
        if not text or not self.tts:
            return False
        
        print(f"[AOSSVoice] 播报: {text}")
        
        def _do_speak():
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    wav_path = f.name
                
                try:
                    # 生成 WAV
                    gen_cmd = [
                        self.tts,
                        "-v", "zh",
                        "-s", str(self.rate),
                        "-w", wav_path,
                        text
                    ]
                    
                    result = subprocess.run(
                        gen_cmd,
                        capture_output=True,
                        timeout=10
                    )
                    
                    if result.returncode != 0:
                        err = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
                        print(f"[AOSSVoice] TTS 失败: {err[:100]}")
                        return False
                    
                    # 播放 WAV
                    play_cmd = []
                    if self.wrapper:
                        play_cmd.append(self.wrapper)
                    play_cmd.extend(["aplay", "-q", wav_path])
                    
                    self._current_process = subprocess.Popen(
                        play_cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE
                    )
                    
                    stdout, stderr = self._current_process.communicate(timeout=30)
                    
                    if self._current_process.returncode == 0:
                        print("[AOSSVoice] 播放成功")
                        return True
                    else:
                        err = stderr.decode('utf-8', errors='ignore') if stderr else ""
                        print(f"[AOSSVoice] 播放失败: {err[:100]}")
                        return False
                        
                finally:
                    if os.path.exists(wav_path):
                        try:
                            os.remove(wav_path)
                        except:
                            pass
                            
            except Exception as e:
                print(f"[AOSSVoice] 播报失败: {e}")
                return False
        
        if block:
            return _do_speak()
        else:
            thread = threading.Thread(target=_do_speak)
            thread.daemon = True
            thread.start()
            return True
    
    def stop(self):
        """停止播放"""
        if self._current_process and self._current_process.poll() is None:
            self._current_process.terminate()
            try:
                self._current_process.wait(timeout=1)
            except:
                self._current_process.kill()


if __name__ == "__main__":
    player = AOSSVoicePlayer()
    player.speak("你好，我是骑行小智", block=True)
