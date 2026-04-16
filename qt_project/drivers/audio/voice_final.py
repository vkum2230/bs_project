#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终版语音播放器 - 最稳定可靠
结合 Edge-TTS + 离线备用 + 正确音频设备
"""

import os
import sys
import asyncio
import tempfile
import subprocess
import threading
import time
from typing import Optional


class FinalVoicePlayer:
    """
    最终版语音播放器
    - 优先使用 Edge-TTS（音质好）
    - 失败时自动使用 espeak（稳定）
    - 正确指定 ReSpeaker 音频设备
    """
    
    # Edge-TTS 语音选项
    EDGE_VOICES = {
        'xiaoxiao': 'zh-CN-XiaoxiaoNeural',
        'xiaoyi': 'zh-CN-XiaoyiNeural',
        'yunyang': 'zh-CN-YunyangNeural',
        'yunxi': 'zh-CN-YunxiNeural',
    }
    
    def __init__(self, voice: str = 'xiaoxiao', message_callback=None, fallback_to_espeak: bool = True):
        self.voice = self.EDGE_VOICES.get(voice, voice)
        self._lock = threading.Lock()
        self._audio_device = "plughw:2,0"  # ReSpeaker 设备（plughw 支持自动格式转换）
        self._message_callback = message_callback  # 消息回调，用于在UI显示播报内容
        self._fallback_to_espeak = fallback_to_espeak

        # 检查 edge-tts
        try:
            import edge_tts
            self._edge_tts = edge_tts
            print(f"[FinalVoice] Edge-TTS 就绪，使用语音: {self.voice}")
        except ImportError:
            self._edge_tts = None
            if fallback_to_espeak:
                print("[FinalVoice] Edge-TTS 未安装，将使用 espeak")
            else:
                print("[FinalVoice] Edge-TTS 未安装，且已禁用 espeak 兜底")
    
    def speak(self, text: str, block: bool = False, show_in_ui: bool = True, fallback_to_espeak: bool = None) -> bool:
        """播报文本

        Args:
            text: 要播报的文本
            block: 是否阻塞等待
            show_in_ui: 是否在UI消息框中显示（默认True）
            fallback_to_espeak: 是否允许兜底到 espeak，None 则使用初始化时的默认值
        """
        if not text:
            return False

        if fallback_to_espeak is None:
            fallback_to_espeak = self._fallback_to_espeak

        print(f"[FinalVoice] 播报: {text[:50]}")

        # 在UI消息框中显示播报内容
        if show_in_ui and self._message_callback:
            self._message_callback(text, icon="🔊")

        def _do_speak():
            with self._lock:
                # 优先尝试 Edge-TTS
                if self._edge_tts:
                    try:
                        # 在新线程中使用新的事件循环
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(self._speak_edge(text))
                        loop.close()
                        if result:
                            return True
                        print("[FinalVoice] Edge-TTS 失败")
                        if not fallback_to_espeak:
                            return False
                        print("[FinalVoice] 使用 espeak 备用")
                    except Exception as e:
                        print(f"[FinalVoice] Edge-TTS 错误: {e}")
                        if not fallback_to_espeak:
                            return False

                # 备用：espeak
                if fallback_to_espeak:
                    return self._speak_espeak(text)
                return False

        if block:
            return _do_speak()
        else:
            thread = threading.Thread(target=_do_speak)
            thread.daemon = True
            thread.start()
            return True
    
    async def _speak_edge(self, text: str, max_retries: int = 2) -> bool:
        """使用 Edge-TTS（带重试）"""
        mp3_path = None
        
        # 先检查网络连接
        if not self._check_network():
            print("[FinalVoice] 网络不可用，跳过 Edge-TTS")
            return False
        
        for attempt in range(max_retries):
            try:
                print(f"[FinalVoice] Edge-TTS 尝试 {attempt + 1}/{max_retries}...")
                
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    mp3_path = f.name
                
                # 生成语音 - 增加超时控制
                communicate = self._edge_tts.Communicate(
                    text=text,
                    voice=self.voice,
                    rate="+0%",
                    volume="+0%"
                )
                
                # 使用 asyncio.wait_for 添加超时
                await asyncio.wait_for(communicate.save(mp3_path), timeout=5.0)
                
                # 检查文件
                size = os.path.getsize(mp3_path)
                if size < 1000:
                    print(f"[FinalVoice] 生成的文件太小: {size} bytes")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)
                        continue
                    return False
                
                print(f"[FinalVoice] 语音生成成功: {size} bytes")
                
                # 转换为 WAV 并播放
                return self._play_with_aplay(mp3_path)
                
            except asyncio.TimeoutError:
                print(f"[FinalVoice] Edge-TTS 超时 (尝试 {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                else:
                    return False
            except Exception as e:
                print(f"[FinalVoice] Edge-TTS 失败 (尝试 {attempt + 1}/{max_retries}): {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                else:
                    return False
            finally:
                if mp3_path and os.path.exists(mp3_path):
                    try:
                        os.remove(mp3_path)
                    except:
                        pass
        
        return False
    
    def _check_network(self) -> bool:
        """检查网络连接"""
        try:
            import socket
            socket.setdefaulttimeout(2)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        except:
            return False
    
    def _play_with_aplay(self, mp3_path: str) -> bool:
        """使用 aplay 播放，指定 ReSpeaker 设备"""
        wav_path = None
        
        try:
            # 先转换为 WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            
            # 使用 ffmpeg 转换
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", mp3_path, 
                 "-acodec", "pcm_s16le", 
                 "-ar", "22050", 
                 "-ac", "1",
                 wav_path],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode != 0:
                print(f"[FinalVoice] 转换失败: {result.stderr.decode()[:100]}")
                return False
            
            # 使用 aplay 播放，指定设备
            result = subprocess.run(
                ["aplay", "-q", "-D", self._audio_device, wav_path],
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("[FinalVoice] 播放完成")
                return True
            else:
                err = result.stderr.decode()[:200] if result.stderr else ""
                if "Unknown error 524" in err:
                    print(f"[FinalVoice] 设备忙，尝试默认设备")
                else:
                    print(f"[FinalVoice] aplay 失败: {err}")
                
                # 尝试默认设备
                result2 = subprocess.run(
                    ["aplay", "-q", wav_path],
                    capture_output=True,
                    timeout=60
                )
                if result2.returncode == 0:
                    print("[FinalVoice] 播放完成（默认设备）")
                    return True
                return False
                
        except Exception as e:
            print(f"[FinalVoice] 播放错误: {e}")
            return False
        finally:
            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except:
                    pass
    
    def _speak_espeak(self, text: str) -> bool:
        """使用 espeak 播报（离线备用）"""
        try:
            # 生成 WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            
            result = subprocess.run(
                ["espeak", "-v", "zh", "-w", wav_path, text],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # 播放
                result2 = subprocess.run(
                    ["aplay", "-q", "-D", self._audio_device, wav_path],
                    capture_output=True,
                    timeout=30
                )
                if result2.returncode == 0:
                    print("[FinalVoice] espeak 播放完成")
                    return True
                else:
                    # 尝试默认设备
                    subprocess.run(
                        ["aplay", "-q", wav_path],
                        capture_output=True,
                        timeout=30
                    )
                    print("[FinalVoice] espeak 播放完成（默认设备）")
                    return True
            
            return False
        except Exception as e:
            print(f"[FinalVoice] espeak 失败: {e}")
            return False
    
    def stop(self):
        pass


if __name__ == "__main__":
    print("=" * 60)
    print("语音播放器测试")
    print("=" * 60)
    
    player = FinalVoicePlayer()
    
    print("\n测试1: Edge-TTS")
    player.speak("你好，我是骑行小智", block=True)
    
    time.sleep(1)
    
    print("\n测试2: 较长文本")
    player.speak("前方五百米右转，进入建设大道", block=True)
    
    print("\n" + "=" * 60)
    print("测试完成")
