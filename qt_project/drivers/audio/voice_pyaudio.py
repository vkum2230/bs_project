#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 PyAudio 直接播放 - 绕过 aplay 和 ALSA 配置问题
"""

import os
import io
import wave
import subprocess
import threading
import tempfile
from typing import Optional


class PyAudioVoicePlayer:
    """使用 PyAudio 直接输出到音频设备"""
    
    def __init__(self, rate: int = 150):
        self.rate = rate
        self._lock = threading.Lock()
        self._initialized = False
        self._stream = None
        self._pa = None
        
        try:
            import pyaudio
            self._pa = pyaudio.PyAudio()
            self._initialized = True
            print("[PyAudioVoice] 初始化成功")
            
            # 列出设备
            print("[PyAudioVoice] 可用音频设备:")
            for i in range(self._pa.get_device_count()):
                info = self._pa.get_device_info_by_index(i)
                if info['maxOutputChannels'] > 0:
                    print(f"  设备 {i}: {info['name']}")
                    
        except Exception as e:
            print(f"[PyAudioVoice] 初始化失败: {e}")
    
    def _detect_tts(self) -> Optional[str]:
        """检测 TTS 命令"""
        import shutil
        for cmd in ["espeak-ng", "espeak"]:
            if shutil.which(cmd):
                return cmd
        return None
    
    def speak(self, text: str, block: bool = False) -> bool:
        """播报文本"""
        if not text or not self._initialized:
            return False
        
        print(f"[PyAudioVoice] 播报: {text}")
        
        def _do_speak():
            try:
                tts = self._detect_tts()
                if not tts:
                    print("[PyAudioVoice] 未找到 TTS 引擎")
                    return False
                
                # 生成 WAV 文件
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    wav_path = f.name
                
                try:
                    # 生成语音
                    gen_cmd = [
                        tts,
                        "-v", "zh",
                        "-s", str(self.rate),
                        "-w", wav_path,
                        text
                    ]
                    
                    result = subprocess.run(gen_cmd, capture_output=True, timeout=10)
                    if result.returncode != 0:
                        err = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
                        print(f"[PyAudioVoice] TTS 失败: {err[:100]}")
                        return False
                    
                    # 使用 PyAudio 播放
                    return self._play_wav(wav_path)
                    
                finally:
                    if os.path.exists(wav_path):
                        try:
                            os.remove(wav_path)
                        except:
                            pass
                            
            except Exception as e:
                print(f"[PyAudioVoice] 播报失败: {e}")
                return False
        
        if block:
            return _do_speak()
        else:
            thread = threading.Thread(target=_do_speak)
            thread.daemon = True
            thread.start()
            return True
    
    def _play_wav(self, wav_path: str) -> bool:
        """使用 PyAudio 播放 WAV"""
        try:
            import pyaudio
            
            # 打开 WAV 文件
            with wave.open(wav_path, 'rb') as wf:
                # 打开音频流
                stream = self._pa.open(
                    format=self._pa.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                
                # 读取并播放数据
                chunk = 1024
                data = wf.readframes(chunk)
                
                while data:
                    stream.write(data)
                    data = wf.readframes(chunk)
                
                # 关闭流
                stream.stop_stream()
                stream.close()
                
                print("[PyAudioVoice] 播放成功")
                return True
                
        except Exception as e:
            print(f"[PyAudioVoice] 播放失败: {e}")
            return False
    
    def stop(self):
        """停止播放"""
        pass
    
    def __del__(self):
        """清理资源"""
        if self._pa:
            self._pa.terminate()


if __name__ == "__main__":
    player = PyAudioVoicePlayer()
    player.speak("你好，我是骑行小智", block=True)
