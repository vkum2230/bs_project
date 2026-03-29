#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音录音模块 - ReSpeaker 2-Mic 录音功能
支持按钮触发录音、语音识别
"""

import os
import wave
import tempfile
import threading
import time
import subprocess
from typing import Callable, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RecognitionResult:
    """语音识别结果"""
    text: str
    confidence: float
    is_final: bool = True


class VoiceRecorder:
    """语音录音器 - 支持按钮触发录音"""
    
    def __init__(self, 
                 device_index: int = None,
                 sample_rate: int = 16000,
                 channels: int = 2,
                 chunk_duration: float = 0.1):
        """
        初始化录音器
        
        Args:
            device_index: 音频输入设备索引
            sample_rate: 采样率
            channels: 通道数（ReSpeaker 2-Mic 是 2 通道）
            chunk_duration: 每块录音时长（秒）
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = int(sample_rate * chunk_duration)
        self.device_index = device_index
        
        self._recording = False
        self._record_thread: Optional[threading.Thread] = None
        self._audio_data = []
        
        self._pa = None
        self._init_audio()
    
    def _init_audio(self):
        """初始化音频"""
        try:
            import pyaudio
            self._pa = pyaudio.PyAudio()
            
            # 查找 ReSpeaker 输入设备
            if self.device_index is None:
                for i in range(self._pa.get_device_count()):
                    info = self._pa.get_device_info_by_index(i)
                    name = info.get('name', '').lower()
                    if any(kw in name for kw in ['seeed', 'respeaker', '2mic']):
                        if info.get('maxInputChannels', 0) > 0:
                            self.device_index = i
                            print(f"[VoiceRecorder] 找到 ReSpeaker 输入设备: {info['name']} (index={i})")
                            break
                
                # 如果没找到，使用默认输入设备
                if self.device_index is None:
                    # 查找第一个有输入的设备
                    for i in range(self._pa.get_device_count()):
                        info = self._pa.get_device_info_by_index(i)
                        if info.get('maxInputChannels', 0) > 0:
                            self.device_index = i
                            print(f"[VoiceRecorder] 使用输入设备: {info['name']} (index={i})")
                            break
        except Exception as e:
            print(f"[VoiceRecorder] 初始化失败: {e}")
            self._pa = None
    
    def start_recording(self) -> bool:
        """开始录音"""
        if self._recording:
            return False
        
        if not self._pa:
            print("[VoiceRecorder] 音频未初始化")
            return False
        
        self._recording = True
        self._audio_data = []
        
        self._record_thread = threading.Thread(target=self._record_loop)
        self._record_thread.daemon = True
        self._record_thread.start()
        
        print("[VoiceRecorder] 开始录音...")
        return True
    
    def stop_recording(self) -> Optional[str]:
        """停止录音，返回录音文件路径"""
        if not self._recording:
            return None
        
        self._recording = False
        
        if self._record_thread:
            self._record_thread.join(timeout=2)
        
        print(f"[VoiceRecorder] 录音结束，共 {len(self._audio_data)} 块音频数据")
        
        # 保存为 WAV 文件
        if self._audio_data:
            return self._save_wav()
        
        return None
    
    def _record_loop(self):
        """录音循环"""
        try:
            import pyaudio
            
            stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size
            )
            
            print("[VoiceRecorder] 录音循环开始")
            
            while self._recording:
                try:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    self._audio_data.append(data)
                except Exception as e:
                    print(f"[VoiceRecorder] 读取音频错误: {e}")
                    break
            
            stream.stop_stream()
            stream.close()
            
            print("[VoiceRecorder] 录音循环结束")
            
        except Exception as e:
            print(f"[VoiceRecorder] 录音异常: {e}")
            self._recording = False
    
    def _save_wav(self) -> str:
        """保存为 WAV 文件"""
        import wave
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self._audio_data))
        
        file_size = os.path.getsize(wav_path)
        duration = len(self._audio_data) * self.chunk_size / self.sample_rate
        print(f"[VoiceRecorder] 保存录音: {wav_path} ({file_size} bytes, {duration:.1f}s)")
        
        return wav_path
    
    def is_recording(self) -> bool:
        """是否正在录音"""
        return self._recording
    
    def __del__(self):
        """清理资源"""
        if self._pa:
            self._pa.terminate()


class VoiceRecognizer:
    """语音识别器 - 支持离线识别"""
    
    def __init__(self, model_path: str = None):
        """
        初始化识别器
        
        Args:
            model_path: Vosk 模型路径，None 则使用简单命令识别
        """
        self.model_path = model_path
        self._model = None
        self._recognizer = None
        
        # 尝试初始化 Vosk
        self._init_vosk()
    
    def _init_vosk(self):
        """初始化 Vosk 语音识别"""
        try:
            from vosk import Model, KaldiRecognizer
            
            # 如果未指定模型路径，使用默认路径
            if self.model_path is None:
                # 常见模型路径
                possible_paths = [
                    "/home/pi/vosk-model-small-cn-0.22",
                    "./vosk-model-small-cn-0.22",
                    "/home/hedya/vosk-model-small-cn-0.22",
                    "vosk-model-small-cn-0.22",
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        self.model_path = path
                        break
            
            if self.model_path and os.path.exists(self.model_path):
                print(f"[VoiceRecognizer] 加载 Vosk 模型: {self.model_path}")
                self._model = Model(self.model_path)
                self._recognizer = KaldiRecognizer(self._model, 16000)
                print("[VoiceRecognizer] Vosk 模型加载成功")
            else:
                print("[VoiceRecognizer] 未找到 Vosk 模型，将使用模拟识别")
                print("[VoiceRecognizer] 如需语音识别，请下载模型:")
                print("  wget https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip")
                print("  unzip vosk-model-small-cn-0.22.zip")
                
        except ImportError:
            print("[VoiceRecognizer] Vosk 未安装，将使用模拟识别")
            print("[VoiceRecognizer] 安装命令: pip3 install vosk")
        except Exception as e:
            print(f"[VoiceRecognizer] Vosk 初始化失败: {e}")
    
    def recognize(self, wav_path: str) -> RecognitionResult:
        """
        识别音频文件
        
        Args:
            wav_path: WAV 文件路径
        
        Returns:
            识别结果
        """
        if not os.path.exists(wav_path):
            return RecognitionResult("[未找到音频文件]", 0.0)
        
        # 使用 Vosk 识别
        if self._recognizer:
            return self._recognize_vosk(wav_path)
        
        # 降级：使用 whisper 或其他在线服务
        return self._recognize_fallback(wav_path)
    
    def _recognize_vosk(self, wav_path: str) -> RecognitionResult:
        """使用 Vosk 识别"""
        try:
            import wave
            import json
            
            # 重置识别器
            from vosk import KaldiRecognizer
            self._recognizer = KaldiRecognizer(self._model, 16000)
            
            with wave.open(wav_path, 'rb') as wf:
                # 检查格式
                if wf.getnchannels() != 1 or wf.getframerate() != 16000:
                    # 需要转换
                    print("[VoiceRecognizer] 转换音频格式...")
                    wav_path = self._convert_audio(wav_path)
                    wf.close()
                    wf = wave.open(wav_path, 'rb')
                
                # 识别
                results = []
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    
                    if self._recognizer.AcceptWaveform(data):
                        result = json.loads(self._recognizer.Result())
                        if result.get('text'):
                            results.append(result['text'])
                
                # 获取最终结果
                final_result = json.loads(self._recognizer.FinalResult())
                if final_result.get('text'):
                    results.append(final_result['text'])
                
                text = ' '.join(results) if results else final_result.get('text', '')
                
                if text:
                    return RecognitionResult(text, 0.9)
                else:
                    return RecognitionResult("[未识别到语音]", 0.0)
                    
        except Exception as e:
            print(f"[VoiceRecognizer] Vosk 识别失败: {e}")
            return RecognitionResult(f"[识别错误: {str(e)}]", 0.0)
    
    def _convert_audio(self, wav_path: str) -> str:
        """转换音频为单声道 16kHz"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
        
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", wav_path,
                "-acodec", "pcm_s16le",
                "-ac", "1", "-ar", "16000",
                output_path
            ], capture_output=True, timeout=30, check=True)
            return output_path
        except:
            # 如果 ffmpeg 失败，返回原文件
            return wav_path
    
    def _recognize_fallback(self, wav_path: str) -> RecognitionResult:
        """降级识别方案 - 模拟识别"""
        # 获取音频时长
        try:
            import wave
            with wave.open(wav_path, 'rb') as wf:
                duration = wf.getnframes() / wf.getframerate()
        except:
            duration = 0
        
        # 根据录音时长返回模拟结果
        if duration < 1.0:
            return RecognitionResult("[录音太短]", 0.0)
        
        # 提示用户安装 Vosk
        return RecognitionResult(
            "[请安装语音识别模型]\n"
            "1. pip3 install vosk\n"
            "2. wget https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip\n"
            "3. unzip vosk-model-small-cn-0.22.zip", 
            0.0
        )


class ButtonVoiceAssistant:
    """按钮语音助手 - 集成按钮、录音、识别、播报"""
    
    def __init__(self,
                 voice_player,
                 message_callback: Callable[[str, str], None],
                 button_pin: int = 17):
        """
        初始化助手
        
        Args:
            voice_player: 语音播放器实例
            message_callback: 消息回调函数 (text, icon) -> None
            button_pin: 按钮 GPIO 引脚
        """
        self.voice_player = voice_player
        self.message_callback = message_callback
        self.button_pin = button_pin
        
        self.recorder = VoiceRecorder()
        self.recognizer = VoiceRecognizer()
        self.button_handler = None
        
        self._recording_indicator = False
        
        self._init_button()
    
    def _init_button(self):
        """初始化按钮"""
        try:
            from voice_driver import ButtonHandler, ButtonEvent
            
            self.button_handler = ButtonHandler(pin=self.button_pin)
            
            # 按下按钮 - 开始录音
            self.button_handler.on(ButtonEvent.PRESS, self._on_button_press)
            
            # 释放按钮 - 停止录音并识别
            self.button_handler.on(ButtonEvent.RELEASE, self._on_button_release)
            
            self.button_handler.start()
            print(f"[ButtonVoiceAssistant] 按钮监听已启动 (GPIO {self.button_pin})")
            
        except Exception as e:
            print(f"[ButtonVoiceAssistant] 按钮初始化失败: {e}")
    
    def _on_button_press(self):
        """按钮按下 - 开始录音"""
        # 防止重复触发（如果已经在录音中则忽略）
        if self._recording_indicator:
            return
        
        print("[ButtonVoiceAssistant] 按钮按下 - 开始录音")
        
        # 显示录音提示
        if self.message_callback:
            self.message_callback("🎤 正在录音...请说话", icon="🔴")
        
        # 开始录音
        success = self.recorder.start_recording()
        
        if success:
            self._recording_indicator = True
            # 可选：播放提示音
            # if self.voice_player:
            #     self.voice_player.speak("开始录音", block=False)
        else:
            if self.message_callback:
                self.message_callback("❌ 录音启动失败", icon="⚠️")
    
    def _on_button_release(self):
        """按钮释放 - 停止录音并处理"""
        print("[ButtonVoiceAssistant] 按钮释放 - 停止录音")
        
        if not self.recorder.is_recording():
            return
        
        # 停止录音
        wav_path = self.recorder.stop_recording()
        self._recording_indicator = False
        
        if not wav_path:
            if self.message_callback:
                self.message_callback("❌ 录音失败", icon="⚠️")
            return
        
        # 不显示"识别中"，直接启动识别线程
        # 启动识别线程
        thread = threading.Thread(target=self._process_recording, args=(wav_path,))
        thread.daemon = True
        thread.start()
    
    def _process_recording(self, wav_path: str):
        """处理录音（识别+播报）"""
        try:
            # 1. 语音识别
            result = self.recognizer.recognize(wav_path)
            
            # 2. 处理识别结果（去掉空格）
            if result.text:
                # 去掉空格，使语音连贯
                clean_text = result.text.replace(" ", "").replace("  ", "")
                
                # 显示识别结果（不显示"你说"）
                if self.message_callback:
                    self.message_callback(clean_text, icon="💬")
                
                print(f"[ButtonVoiceAssistant] 识别结果: {clean_text} (置信度: {result.confidence:.2f})")
                
                # 3. 语音播报识别结果（使用去掉空格的文本）
                if self.voice_player and result.confidence > 0.3:
                    speak_text = clean_text[:50]  # 限制长度
                    self.voice_player.speak(speak_text, block=False)
            else:
                if self.message_callback:
                    self.message_callback("❌ 未能识别语音", icon="⚠️")
            
            # 4. 清理临时文件
            try:
                os.remove(wav_path)
            except:
                pass
                
        except Exception as e:
            print(f"[ButtonVoiceAssistant] 处理录音失败: {e}")
            if self.message_callback:
                self.message_callback(f"❌ 处理失败: {str(e)}", icon="⚠️")
    
    def stop(self):
        """停止助手"""
        if self.button_handler:
            self.button_handler.stop()
        if self.recorder.is_recording():
            self.recorder.stop_recording()


if __name__ == "__main__":
    # 测试录音功能
    print("=" * 60)
    print("录音功能测试")
    print("=" * 60)
    
    recorder = VoiceRecorder()
    recognizer = VoiceRecognizer()
    
    print("\n3秒后开始录音，请说话...")
    time.sleep(3)
    
    if recorder.start_recording():
        print("录音中... (5秒)")
        time.sleep(5)
        
        wav_path = recorder.stop_recording()
        print(f"录音保存: {wav_path}")
        
        if wav_path:
            print("识别中...")
            result = recognizer.recognize(wav_path)
            print(f"识别结果: {result.text}")
    else:
        print("录音启动失败")
