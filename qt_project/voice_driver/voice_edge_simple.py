#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版 Edge-TTS 播放器 - 使用 Python API 而不是命令行
更稳定，避免 SSL/网络问题
"""

import os
import sys
import asyncio
import tempfile
import subprocess
import threading
from typing import Optional


class SimpleEdgeVoicePlayer:
    """
    简化版 Edge-TTS 播放器
    直接使用 edge-tts Python 库
    """
    
    VOICES = {
        'xiaoxiao': 'zh-CN-XiaoxiaoNeural',      # 晓晓 - 温柔女声
        'xiaoyi': 'zh-CN-XiaoyiNeural',          # 小怡 - 活泼女声
        'yunyang': 'zh-CN-YunyangNeural',        # 云扬 - 男声
        'yunxi': 'zh-CN-YunxiNeural',            # 云希 - 年轻男声
    }
    
    def __init__(self, voice: str = 'xiaoxiao', rate: str = "+10%", volume: str = "+10%"):
        self.voice = self.VOICES.get(voice, voice)
        self.rate = rate
        self.volume = volume
        self._lock = threading.Lock()
        
        # 检查 edge-tts 库
        try:
            import edge_tts
            self._edge_tts = edge_tts
            print(f"[SimpleEdgeVoice] Edge-TTS 库加载成功")
            print(f"[SimpleEdgeVoice] 使用语音: {self.voice}")
        except ImportError:
            print("[SimpleEdgeVoice] 错误: edge-tts 库未安装")
            print("[SimpleEdgeVoice] 运行: pip3 install edge-tts")
            self._edge_tts = None
    
    def speak(self, text: str, block: bool = False) -> bool:
        """播报文本"""
        if not text or not self._edge_tts:
            return False
        
        print(f"[SimpleEdgeVoice] 播报: {text[:50]}...")
        
        def _do_speak():
            try:
                # 使用 asyncio 运行
                asyncio.run(self._speak_async(text))
                return True
            except Exception as e:
                print(f"[SimpleEdgeVoice] 播报失败: {e}")
                return False
        
        if block:
            return _do_speak()
        else:
            thread = threading.Thread(target=_do_speak)
            thread.daemon = True
            thread.start()
            return True
    
    async def _speak_async(self, text: str):
        """异步播报"""
        mp3_path = None
        
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                mp3_path = f.name
            
            # 使用 edge-tts 生成
            communicate = self._edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume
            )
            
            print(f"[SimpleEdgeVoice] 生成语音文件...")
            await communicate.save(mp3_path)
            
            file_size = os.path.getsize(mp3_path)
            print(f"[SimpleEdgeVoice] 语音生成成功 ({file_size} bytes)")
            
            # 播放 MP3
            self._play_mp3(mp3_path)
            
        finally:
            # 清理
            if mp3_path and os.path.exists(mp3_path):
                try:
                    os.remove(mp3_path)
                except:
                    pass
    
    def _play_mp3(self, mp3_path: str) -> bool:
        """播放 MP3 文件"""
        # 优先使用 mpg123
        try:
            result = subprocess.run(
                ["mpg123", "-q", mp3_path],
                capture_output=True,
                timeout=60
            )
            if result.returncode == 0:
                print("[SimpleEdgeVoice] 播放完成")
                return True
        except Exception as e:
            print(f"[SimpleEdgeVoice] mpg123 失败: {e}")
        
        # 回退到 ffplay
        try:
            result = subprocess.run(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", mp3_path],
                capture_output=True,
                timeout=60
            )
            if result.returncode == 0:
                print("[SimpleEdgeVoice] 播放完成 (ffplay)")
                return True
        except Exception as e:
            print(f"[SimpleEdgeVoice] ffplay 失败: {e}")
        
        return False
    
    def stop(self):
        pass
    
    def test(self):
        """测试"""
        print("=" * 60)
        print("Edge-TTS 简单版测试")
        print("=" * 60)
        self.speak("你好，我是骑行小智，很高兴为你服务", block=True)
        print("=" * 60)


if __name__ == "__main__":
    player = SimpleEdgeVoicePlayer()
    player.test()
