#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReSpeaker 2-Mic 专用语音播放器
使用 PyAudio 直接输出到 seeed2micvoicec 设备
"""

import os
import wave
import subprocess
import threading
import tempfile
import time
import struct
from typing import Optional


class ReSpeakerVoicePlayer:
    """专为 ReSpeaker 2-Mic 优化的语音播放器"""
    
    def __init__(self, rate: int = 150, device_index: int = None, volume: float = 0.9):
        """
        初始化 ReSpeaker 语音播放器
        
        Args:
            rate: 语速
            device_index: PyAudio 设备索引，None 则自动检测
            volume: 音量 (0.0 - 1.0)
        """
        self.rate = rate
        self.volume = max(0.0, min(1.0, volume))
        self.device_index = device_index
        self._lock = threading.Lock()
        self._pa = None
        self._stream = None
        
        # 检测 TTS
        self.tts_cmd = self._detect_tts()
        
        # 初始化 PyAudio
        self._init_pyaudio()
        
        # 设置初始音量
        self._set_alsa_volume()
    
    def _detect_tts(self) -> Optional[str]:
        """检测可用的 TTS 命令"""
        import shutil
        for cmd in ["espeak-ng", "espeak"]:
            if shutil.which(cmd):
                return cmd
        print("[ReSpeakerVoice] 警告: 未找到 espeak/espeak-ng")
        return None
    
    def _init_pyaudio(self):
        """初始化 PyAudio"""
        try:
            import pyaudio
            self._pa = pyaudio.PyAudio()
            
            print("[ReSpeakerVoice] 可用音频设备:")
            respeaker_found = False
            
            for i in range(self._pa.get_device_count()):
                info = self._pa.get_device_info_by_index(i)
                name = info.get('name', '')
                channels = info.get('maxOutputChannels', 0)
                
                if channels > 0:
                    is_seeed = any(kw in name.lower() for kw in ['seeed', 'respeaker', '2mic'])
                    marker = " <-- ReSpeaker" if is_seeed else ""
                    print(f"  [{i}] {name} (输出通道: {channels}){marker}")
                    
                    if is_seeed and not respeaker_found:
                        self.device_index = i
                        respeaker_found = True
            
            # 如果没找到 ReSpeaker，使用默认输出设备
            if self.device_index is None:
                # 查找第一个有输出的设备
                for i in range(self._pa.get_device_count()):
                    info = self._pa.get_device_info_by_index(i)
                    if info.get('maxOutputChannels', 0) > 0:
                        self.device_index = i
                        print(f"[ReSpeakerVoice] 使用设备: {info['name']} (index={i})")
                        break
            else:
                info = self._pa.get_device_info_by_index(self.device_index)
                print(f"[ReSpeakerVoice] 已选择 ReSpeaker: {info['name']} (index={self.device_index})")
                
        except Exception as e:
            print(f"[ReSpeakerVoice] PyAudio 初始化失败: {e}")
            self._pa = None
    
    def _set_alsa_volume(self):
        """设置 ALSA 音量"""
        try:
            # 尝试设置 ReSpeaker 的音量
            subprocess.run(
                ["amixer", "-c", "2", "set", "PCM", "90%", "unmute"],
                capture_output=True,
                timeout=2
            )
            subprocess.run(
                ["amixer", "-c", "2", "set", "Headphone", "90%", "unmute"],
                capture_output=True,
                timeout=2
            )
            print("[ReSpeakerVoice] 已设置音量为 90%")
        except:
            pass
    
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
        
        if not self.tts_cmd:
            print("[ReSpeakerVoice] 错误: 无 TTS 引擎")
            return False
        
        if not self._pa:
            print("[ReSpeakerVoice] 错误: PyAudio 未初始化")
            return False
        
        print(f"[ReSpeakerVoice] 播报: {text}")
        
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
        wav_path = None
        
        try:
            # 创建临时 WAV 文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            
            # 使用 TTS 生成 WAV
            gen_cmd = [
                self.tts_cmd,
                "-v", "zh",           # 中文语音
                "-s", str(self.rate), # 语速
                "-w", wav_path,       # 输出到文件
                text
            ]
            
            print(f"[ReSpeakerVoice] 生成语音文件...")
            result = subprocess.run(
                gen_cmd,
                capture_output=True,
                timeout=15
            )
            
            if result.returncode != 0:
                err = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
                print(f"[ReSpeakerVoice] TTS 失败: {err[:200]}")
                return False
            
            # 检查文件
            if not os.path.exists(wav_path):
                print("[ReSpeakerVoice] TTS 未生成音频文件")
                return False
            
            file_size = os.path.getsize(wav_path)
            if file_size < 100:
                print(f"[ReSpeakerVoice] 音频文件太小 ({file_size} bytes)，可能 TTS 失败")
                return False
            
            print(f"[ReSpeakerVoice] 音频文件生成成功 ({file_size} bytes)")
            
            # 播放 WAV
            return self._play_wav(wav_path)
            
        except subprocess.TimeoutExpired:
            print("[ReSpeakerVoice] TTS 超时")
            return False
        except Exception as e:
            print(f"[ReSpeakerVoice] 播报异常: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # 清理临时文件
            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except:
                    pass
    
    def _apply_volume(self, data: bytes, sample_width: int) -> bytes:
        """应用音量增益"""
        if self.volume >= 1.0:
            return data
        
        if sample_width == 1:
            # 8-bit unsigned
            samples = struct.unpack(f'{len(data)}B', data)
            samples = [int((s - 128) * self.volume + 128) for s in samples]
            samples = [max(0, min(255, s)) for s in samples]
            return struct.pack(f'{len(samples)}B', *samples)
        elif sample_width == 2:
            # 16-bit signed
            num_samples = len(data) // 2
            samples = struct.unpack(f'{num_samples}h', data)
            samples = [int(s * self.volume) for s in samples]
            samples = [max(-32768, min(32767, s)) for s in samples]
            return struct.pack(f'{num_samples}h', *samples)
        else:
            return data
    
    def _play_wav(self, wav_path: str) -> bool:
        """使用 PyAudio 播放 WAV 文件"""
        try:
            import pyaudio
            
            print(f"[ReSpeakerVoice] 开始播放 (设备 index={self.device_index})...")
            
            # 打开 WAV 文件
            with wave.open(wav_path, 'rb') as wf:
                # 获取音频参数
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                frame_rate = wf.getframerate()
                n_frames = wf.getnframes()
                
                print(f"[ReSpeakerVoice] 音频参数: {channels}ch, {sample_width}bytes, {frame_rate}Hz, {n_frames}frames")
                
                # 打开音频流
                stream = self._pa.open(
                    format=self._pa.get_format_from_width(sample_width),
                    channels=channels,
                    rate=frame_rate,
                    output=True,
                    output_device_index=self.device_index
                )
                
                print("[ReSpeakerVoice] 音频流已打开，开始播放...")
                
                # 读取并播放
                chunk = 1024
                frames_played = 0
                
                data = wf.readframes(chunk)
                while data:
                    # 应用音量
                    if self.volume < 1.0:
                        data = self._apply_volume(data, sample_width)
                    
                    stream.write(data)
                    frames_played += len(data) // (sample_width * channels)
                    data = wf.readframes(chunk)
                
                # 确保所有数据都播放完成
                stream.stop_stream()
                stream.close()
                
                print(f"[ReSpeakerVoice] 播放完成 ({frames_played} frames)")
                return True
                
        except Exception as e:
            print(f"[ReSpeakerVoice] 播放失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop(self):
        """停止播放"""
        pass
    
    def test(self):
        """测试语音播报"""
        print("=" * 60)
        print("ReSpeakerVoice 测试开始")
        print("=" * 60)
        
        print(f"\n配置:")
        print(f"  TTS 引擎: {self.tts_cmd}")
        print(f"  设备索引: {self.device_index}")
        print(f"  音量: {self.volume}")
        
        # 测试中文
        print("\n[测试1] 中文播报: 你好，我是骑行小智")
        result = self.speak("你好，我是骑行小智", block=True)
        print(f"结果: {'成功' if result else '失败'}")
        
        if result:
            time.sleep(0.5)
            
            # 测试英文
            print("\n[测试2] 英文播报: Hello, Bike Assistant")
            result = self.speak("Hello, Bike Assistant", block=True)
            print(f"结果: {'成功' if result else '失败'}")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
    
    def __del__(self):
        """析构函数"""
        if self._pa:
            self._pa.terminate()


# 便捷函数
def speak(text: str, block: bool = False) -> bool:
    """便捷函数：播报文本"""
    player = ReSpeakerVoicePlayer()
    return player.speak(text, block)


if __name__ == "__main__":
    player = ReSpeakerVoicePlayer()
    player.test()
