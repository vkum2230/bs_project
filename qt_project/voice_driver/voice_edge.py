#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edge-TTS 语音播放器 - 使用微软 Edge 在线语音
声音自然、免费、支持多种中文语音
"""

import os
import sys
import subprocess
import threading
import tempfile
import asyncio
from typing import Optional
from pathlib import Path


class EdgeVoicePlayer:
    """
    Edge-TTS 语音播放器
    使用微软 Edge 浏览器的在线 TTS 服务，声音非常自然
    """
    
    # 可用的中文语音
    VOICES = {
        # 女声
        'xiaoxiao': 'zh-CN-XiaoxiaoNeural',      # 晓晓 - 温柔女声（默认）
        'xiaoyi': 'zh-CN-XiaoyiNeural',          # 小怡 - 活泼女声
        'yunyang': 'zh-CN-YunyangNeural',        # 云扬 - 男声
        'yunxi': 'zh-CN-YunxiNeural',            # 云希 - 年轻男声
        'yunyue': 'zh-CN-YunyueNeural',          # 云月 - 童声
        'liaoning': 'zh-CN-liaoning-XiaobeiNeural',  # 东北话
        'shaanxi': 'zh-CN-shaanxi-XiaoniNeural',     # 陕西话
        'taiwan': 'zh-TW-HsiaoChenNeural',       # 台湾女声
        'hongkong': 'zh-HK-HiuMaanNeural',       # 香港女声
    }
    
    def __init__(self, 
                 voice: str = 'xiaoxiao',
                 rate: str = "+0%",      # 语速调整 (+50% 更快, -50% 更慢)
                 volume: str = "+0%",    # 音量调整
                 pitch: str = "+0Hz"):   # 音调调整
        """
        初始化 Edge-TTS 播放器
        
        Args:
            voice: 语音名称，可选 xiaoxiao/xiaoyi/yunyang/yunxi 等
            rate: 语速，如 "+20%" 或 "-10%"
            volume: 音量，如 "+20%" 或 "-10%"
            pitch: 音调，如 "+10Hz" 或 "-5Hz"
        """
        self.voice = self.VOICES.get(voice, voice)
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
        self._lock = threading.Lock()
        self._current_process = None
        
        # 检查 edge-tts 是否安装
        self._check_edge_tts()
        
        print(f"[EdgeVoice] 使用语音: {self.voice}")
        print(f"[EdgeVoice] 语速: {self.rate}, 音量: {self.volume}, 音调: {self.pitch}")
    
    def _check_edge_tts(self):
        """检查 edge-tts 是否安装"""
        try:
            result = subprocess.run(
                ["edge-tts", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"[EdgeVoice] edge-tts 版本: {result.stdout.strip()}")
            else:
                print("[EdgeVoice] 警告: edge-tts 可能未正确安装")
                print("[EdgeVoice] 安装命令: pip3 install edge-tts")
        except FileNotFoundError:
            print("[EdgeVoice] 错误: edge-tts 未安装!")
            print("[EdgeVoice] 请运行: pip3 install edge-tts")
            raise RuntimeError("edge-tts 未安装")
    
    def speak(self, text: str, block: bool = False) -> bool:
        """
        播报文本
        
        Args:
            text: 要播报的文本
            block: 是否阻塞等待
        
        Returns:
            是否成功
        """
        if not text:
            return False
        
        print(f"[EdgeVoice] 播报: {text[:50]}...")
        
        def _do_speak():
            with self._lock:
                return self._speak_impl(text)
        
        if block:
            return _do_speak()
        else:
            thread = threading.Thread(target=_do_speak)
            thread.daemon = True
            thread.start()
            return True
    
    def _speak_impl(self, text: str) -> bool:
        """实际播报实现"""
        mp3_path = None
        wav_path = None
        
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                mp3_path = f.name
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            
            # 1. 使用 edge-tts 生成 MP3
            cmd = [
                "edge-tts",
                "--voice", self.voice,
                "--rate", self.rate,
                "--volume", self.volume,
                "--text", text,
                "--write-media", mp3_path
            ]
            
            print(f"[EdgeVoice] 生成语音...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                err = result.stderr if result.stderr else "未知错误"
                print(f"[EdgeVoice] TTS 生成失败: {err[:200]}")
                return False
            
            # 检查文件
            if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) < 100:
                print("[EdgeVoice] 生成的音频文件太小")
                return False
            
            file_size = os.path.getsize(mp3_path)
            print(f"[EdgeVoice] MP3 生成成功 ({file_size} bytes)")
            
            # 2. 转换为 WAV（使用 ffmpeg 或 mpg123）
            if not self._convert_to_wav(mp3_path, wav_path):
                # 转换失败，尝试直接用播放器播放 MP3
                return self._play_mp3(mp3_path)
            
            # 3. 播放 WAV
            return self._play_wav(wav_path)
            
        except subprocess.TimeoutExpired:
            print("[EdgeVoice] TTS 生成超时")
            return False
        except Exception as e:
            print(f"[EdgeVoice] 播报异常: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # 清理临时文件
            for path in [mp3_path, wav_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass
    
    def _convert_to_wav(self, mp3_path: str, wav_path: str) -> bool:
        """将 MP3 转换为 WAV"""
        try:
            # 尝试使用 ffmpeg
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", mp3_path, 
                 "-acodec", "pcm_s16le", 
                 "-ar", "22050", 
                 "-ac", "1", 
                 wav_path],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                return True
        except:
            pass
        
        # 尝试使用 mpg123
        try:
            result = subprocess.run(
                ["mpg123", "-w", wav_path, mp3_path],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                return True
        except:
            pass
        
        return False
    
    def _play_mp3(self, mp3_path: str) -> bool:
        """直接播放 MP3"""
        players = [
            ["mpg123", mp3_path],
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", mp3_path],
        ]
        
        for cmd in players:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=60
                )
                if result.returncode == 0:
                    print("[EdgeVoice] 播放成功")
                    return True
            except:
                pass
        
        return False
    
    def _play_wav(self, wav_path: str) -> bool:
        """播放 WAV 文件"""
        import wave
        
        try:
            import pyaudio
            
            print(f"[EdgeVoice] 播放音频...")
            
            wf = wave.open(wav_path, 'rb')
            
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pa.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )
            
            chunk = 1024
            data = wf.readframes(chunk)
            
            while data:
                stream.write(data)
                data = wf.readframes(chunk)
            
            stream.stop_stream()
            stream.close()
            pa.terminate()
            wf.close()
            
            print("[EdgeVoice] 播放完成")
            return True
            
        except Exception as e:
            print(f"[EdgeVoice] 播放失败: {e}")
            # 回退到 aplay
            try:
                result = subprocess.run(
                    ["aplay", wav_path],
                    capture_output=True,
                    timeout=60
                )
                return result.returncode == 0
            except:
                return False
    
    def stop(self):
        """停止播放"""
        if self._current_process:
            try:
                self._current_process.terminate()
                self._current_process.wait(timeout=1)
            except:
                pass
    
    def list_voices(self):
        """列出所有可用语音"""
        print("\n可用的中文语音:")
        print("-" * 50)
        for key, value in self.VOICES.items():
            print(f"  {key:12} -> {value}")
        print("-" * 50)
        print("使用示例: EdgeVoicePlayer(voice='xiaoxiao')")
    
    def test(self):
        """测试所有语音"""
        test_text = "你好，我是骑行小智，很高兴为你服务"
        
        print("=" * 60)
        print("Edge-TTS 语音测试")
        print("=" * 60)
        
        # 测试默认语音
        print(f"\n[测试] 使用默认语音: {self.voice}")
        self.speak(test_text, block=True)
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)


def main():
    """主函数 - 命令行测试"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Edge-TTS 语音播放器')
    parser.add_argument('--voice', '-v', default='xiaoxiao', help='语音名称')
    parser.add_argument('--text', '-t', default='你好，我是骑行小智', help='要播报的文本')
    parser.add_argument('--list', '-l', action='store_true', help='列出可用语音')
    parser.add_argument('--rate', '-r', default='+0%', help='语速 (+20% 更快)')
    parser.add_argument('--volume', '-V', default='+0%', help='音量 (+20% 更大)')
    
    args = parser.parse_args()
    
    player = EdgeVoicePlayer(
        voice=args.voice,
        rate=args.rate,
        volume=args.volume
    )
    
    if args.list:
        player.list_voices()
    else:
        player.speak(args.text, block=True)


if __name__ == "__main__":
    main()
