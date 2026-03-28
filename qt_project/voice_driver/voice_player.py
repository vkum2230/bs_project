#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音播报模块 - SMART RIDE 智能骑行系统
针对 ReSpeaker 2-Mic 模块优化
"""

import os
import sys
import threading
import tempfile
import subprocess
import time
from typing import Optional, Callable, List


class VoicePlayer:
    """语音播报器 - 针对 ReSpeaker 2-Mic 优化"""
    
    # ReSpeaker 2-Mic 常用音频设备
    AUDIO_DEVICES = [
        "seeed2micvoicec",      # ReSpeaker 2-Mic 默认设备
        "hw:0,0",
        "hw:1,0",
        "hw:2,0",
        "plughw:0,0",
        "plughw:1,0",
        "plughw:2,0",
        "default",
        "sysdefault",
        "pulse",
    ]
    
    def __init__(self, engine: str = "auto", rate: int = 150, volume: float = 0.9):
        """
        初始化语音播报器
        
        Args:
            engine: TTS 引擎选择 ("auto", "espeak", "espeak-ng", "pyttsx3")
            rate: 语速
            volume: 音量
        """
        self.engine = engine
        self.rate = rate
        self.volume = volume
        self._lock = threading.Lock()
        self._current_process: Optional[subprocess.Popen] = None
        
        # 检测最佳音频设备
        self.audio_device = self._detect_audio_device()
        print(f"[VoicePlayer] 使用音频设备: {self.audio_device}")
        
        # 自动检测最佳引擎
        if engine == "auto":
            self.engine = self._detect_best_engine()
            print(f"[VoicePlayer] 自动选择 TTS 引擎: {self.engine}")
        
        # 初始化引擎
        self._init_engine()
    
    def _detect_audio_device(self) -> str:
        """检测可用的音频设备"""
        print("[VoicePlayer] 检测音频设备...")
        
        # 首先检查 ReSpeaker 2-Mic 设备
        try:
            result = subprocess.run(
                ["aplay", "-l"],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout
            
            # 查找 ReSpeaker 设备
            if "seeed" in output.lower() or "respeaker" in output.lower():
                print("[VoicePlayer] 找到 ReSpeaker 设备")
                # 找到 seeed2micvoicec 对应的 card 号
                for line in output.split('\n'):
                    if 'seeed' in line.lower() or 'respeaker' in line.lower():
                        # 解析 card 号，例如：card 1: seeed2micvoicec [seeed-2mic-voicecard], device 0
                        if 'card' in line:
                            try:
                                card_num = line.split('card ')[1].split(':')[0]
                                device = f"hw:{card_num},0"
                                print(f"[VoicePlayer] 使用 ReSpeaker 设备: {device}")
                                return device
                            except:
                                pass
        except Exception as e:
            print(f"[VoicePlayer] 检测设备失败: {e}")
        
        # 测试各个设备
        for device in self.AUDIO_DEVICES:
            try:
                result = subprocess.run(
                    ["aplay", "-D", device, "-d", "0", "/dev/zero"],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    print(f"[VoicePlayer] 设备可用: {device}")
                    return device
            except:
                pass
        
        return "default"
    
    def _detect_best_engine(self) -> str:
        """检测最佳的 TTS 引擎"""
        # 优先 espeak-ng（中文支持更好）
        if self._check_command("espeak-ng"):
            return "espeak-ng"
        
        # 其次 espeak
        if self._check_command("espeak"):
            return "espeak"
        
        # 最后 pyttsx3
        try:
            import pyttsx3
            return "pyttsx3"
        except ImportError:
            pass
        
        return "espeak"
    
    def _check_command(self, cmd: str) -> bool:
        """检查系统命令是否可用"""
        try:
            subprocess.run([cmd, "--version"], capture_output=True, check=True)
            return True
        except:
            return False
    
    def _init_engine(self):
        """初始化选定的 TTS 引擎"""
        if self.engine == "pyttsx3":
            self._init_pyttsx3()
    
    def _init_pyttsx3(self):
        """初始化 pyttsx3 引擎"""
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty('rate', self.rate)
            self._tts_engine.setProperty('volume', self.volume)
            
            # 尝试设置中文语音
            voices = self._tts_engine.getProperty('voices')
            for voice in voices:
                if any(kw in voice.name.lower() for kw in ['chinese', 'zh', 'mandarin', 'cmn']):
                    self._tts_engine.setProperty('voice', voice.id)
                    print(f"[VoicePlayer] 找到中文语音: {voice.name}")
                    break
        except Exception as e:
            print(f"[VoicePlayer] pyttsx3 初始化失败: {e}")
            self._tts_engine = None
    
    def speak(self, text: str, block: bool = False) -> bool:
        """播报文本"""
        if not text:
            return False
        
        print(f"[VoicePlayer] 播报: {text}")
        
        if block:
            return self._do_speak(text)
        else:
            thread = threading.Thread(target=self._do_speak, args=(text,))
            thread.daemon = True
            thread.start()
            return True
    
    def _do_speak(self, text: str) -> bool:
        """执行播报"""
        with self._lock:
            try:
                if self.engine == "espeak-ng":
                    return self._speak_espeak_ng(text)
                elif self.engine == "espeak":
                    return self._speak_espeak(text)
                elif self.engine == "pyttsx3":
                    return self._speak_pyttsx3(text)
                else:
                    return self._speak_espeak(text)
            except Exception as e:
                print(f"[VoicePlayer] 播报失败: {e}")
                return False
    
    def _speak_espeak_ng(self, text: str) -> bool:
        """使用 espeak-ng 播报 - 直接输出到指定设备"""
        try:
            # espeak-ng 直接输出到 ALSA
            env = os.environ.copy()
            env['AUDIODEV'] = self.audio_device
            
            cmd = [
                "espeak-ng",
                "-v", "zh",           # 中文
                "-s", str(self.rate), # 语速
                "-a", str(int(self.volume * 100)),  # 音量
                text
            ]
            
            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=env
            )
            stdout, stderr = self._current_process.communicate(timeout=30)
            
            if self._current_process.returncode == 0:
                print(f"[VoicePlayer] espeak-ng 播报成功")
                return True
            else:
                err = stderr.decode('utf-8', errors='ignore') if stderr else ""
                print(f"[VoicePlayer] espeak-ng 警告: {err[:200]}")
                return False
                
        except Exception as e:
            print(f"[VoicePlayer] espeak-ng 失败: {e}")
            return False
    
    def _speak_espeak(self, text: str) -> bool:
        """使用 espeak 播报"""
        try:
            # 先生成 WAV 文件，再用 aplay 播放
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            
            try:
                # 生成语音文件
                gen_cmd = [
                    "espeak",
                    "-v", "zh",
                    "-s", str(self.rate),
                    "-w", wav_path,
                    text
                ]
                
                result = subprocess.run(gen_cmd, capture_output=True, timeout=10)
                if result.returncode != 0:
                    err = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
                    print(f"[VoicePlayer] espeak 生成失败: {err[:200]}")
                    return False
                
                # 播放 WAV 文件
                return self._play_wav(wav_path)
                
            finally:
                # 清理临时文件
                if os.path.exists(wav_path):
                    try:
                        os.remove(wav_path)
                    except:
                        pass
                    
        except Exception as e:
            print(f"[VoicePlayer] espeak 失败: {e}")
            return False
    
    def _speak_pyttsx3(self, text: str) -> bool:
        """使用 pyttsx3 播报 - 导出 WAV 后用 aplay 播放"""
        if self._tts_engine is None:
            return self._speak_espeak(text)
        
        try:
            # 导出到临时 WAV 文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            
            try:
                # 保存到文件
                self._tts_engine.save_to_file(text, wav_path)
                self._tts_engine.runAndWait()
                
                # 检查文件是否生成
                if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
                    print("[VoicePlayer] pyttsx3 未生成有效音频文件")
                    return self._speak_espeak(text)
                
                # 播放
                return self._play_wav(wav_path)
                
            finally:
                if os.path.exists(wav_path):
                    try:
                        os.remove(wav_path)
                    except:
                        pass
                    
        except Exception as e:
            print(f"[VoicePlayer] pyttsx3 失败: {e}")
            return self._speak_espeak(text)
    
    def _play_wav(self, wav_path: str) -> bool:
        """播放 WAV 文件到指定设备"""
        try:
            # 使用指定设备播放
            cmd = ["aplay", "-D", self.audio_device, wav_path]
            
            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            stdout, stderr = self._current_process.communicate(timeout=30)
            
            if self._current_process.returncode == 0:
                print(f"[VoicePlayer] 播放成功")
                return True
            else:
                err = stderr.decode('utf-8', errors='ignore') if stderr else ""
                if "Unknown error 524" in err or "设备或资源忙" in err:
                    print(f"[VoicePlayer] 设备忙，尝试其他设备...")
                    # 尝试默认设备
                    cmd = ["aplay", wav_path]
                    result = subprocess.run(cmd, capture_output=True, timeout=30)
                    return result.returncode == 0
                else:
                    print(f"[VoicePlayer] 播放失败: {err[:200]}")
                    return False
                    
        except Exception as e:
            print(f"[VoicePlayer] 播放异常: {e}")
            return False
    
    def stop(self):
        """停止当前播报"""
        with self._lock:
            if self._current_process and self._current_process.poll() is None:
                self._current_process.terminate()
                try:
                    self._current_process.wait(timeout=1)
                except:
                    self._current_process.kill()
    
    def test(self):
        """测试语音播报"""
        print("[VoicePlayer] 开始语音测试...")
        print(f"[VoicePlayer] 引擎: {self.engine}, 设备: {self.audio_device}")
        
        # 测试中文
        print("[VoicePlayer] 测试中文...")
        self.speak("你好，我是骑行小智", block=True)
        
        time.sleep(0.5)
        
        # 测试英文
        print("[VoicePlayer] 测试英文...")
        self.speak("Hello, Bike Assistant", block=True)
        
        print("[VoicePlayer] 测试完成")


# 全局实例
_voice_player: Optional[VoicePlayer] = None


def get_voice_player() -> VoicePlayer:
    """获取全局语音播放器实例"""
    global _voice_player
    if _voice_player is None:
        _voice_player = VoicePlayer()
    return _voice_player


def speak(text: str, block: bool = False) -> bool:
    """便捷函数：播报文本"""
    return get_voice_player().speak(text, block)


if __name__ == "__main__":
    player = VoicePlayer()
    player.test()
