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
import queue
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
        stream = None
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
            
            print("[VoiceRecorder] 录音循环结束")
            
        except Exception as e:
            print(f"[VoiceRecorder] 录音异常: {e}")
            self._recording = False
        finally:
            # 确保流被正确关闭
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception as e:
                    print(f"[VoiceRecorder] 关闭音频流错误: {e}")
    
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
        self._lock = threading.Lock()  # 保护识别器的锁
        
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
        with self._lock:
            try:
                import wave
                import json
                
                # 先检查并转换音频格式
                actual_wav_path = wav_path
                with wave.open(wav_path, 'rb') as wf_check:
                    if wf_check.getnchannels() != 1 or wf_check.getframerate() != 16000:
                        # 需要转换
                        print("[VoiceRecognizer] 转换音频格式...")
                        actual_wav_path = self._convert_audio(wav_path)
                
                # 创建新的识别器实例（避免多线程冲突）
                from vosk import KaldiRecognizer
                recognizer = KaldiRecognizer(self._model, 16000)
                
                # 识别
                results = []
                with wave.open(actual_wav_path, 'rb') as wf:
                    while True:
                        data = wf.readframes(4000)
                        if len(data) == 0:
                            break
                        
                        if recognizer.AcceptWaveform(data):
                            result = json.loads(recognizer.Result())
                            if result.get('text'):
                                results.append(result['text'])
                    
                    # 获取最终结果
                    final_result = json.loads(recognizer.FinalResult())
                    if final_result.get('text'):
                        results.append(final_result['text'])
                
                text = ' '.join(results) if results else final_result.get('text', '')
                
                if text:
                    return RecognitionResult(text, 0.9)
                else:
                    return RecognitionResult("[未识别到语音]", 0.0)
                    
            except Exception as e:
                print(f"[VoiceRecognizer] Vosk 识别失败: {e}")
                import traceback
                traceback.print_exc()
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
                 button_pin: int = 17,
                 ollama_client = None,
                 led_controller = None):
        """
        初始化助手
        
        Args:
            voice_player: 语音播放器实例
            message_callback: 消息回调函数 (text, icon) -> None
            button_pin: 按钮 GPIO 引脚
            ollama_client: Ollama 大模型客户端（可选）
            led_controller: LED 控制器（可选，用于按钮状态指示）
        """
        self.voice_player = voice_player
        self.message_callback = message_callback
        self.button_pin = button_pin
        self.ollama_client = ollama_client
        self.led_controller = led_controller
        
        self.recorder = VoiceRecorder()
        self.recognizer = VoiceRecognizer()
        self.button_handler = None
        
        self._recording_indicator = False
        self._lock = threading.Lock()  # 保护状态变量的锁
        self._current_response = ""  # 用于流式输出累积回复
        self._stream_buffer = ""  # 流式缓冲区
        self._speak_started = False  # 是否已开始播报
        self._last_update_time = 0  # 上次UI更新时间
        self._stream_displayed = False  # 是否已显示流式结果
        self._processing = False  # 是否正在处理中，防止重复触发
        
        # 流式语音播报状态 - 可靠的存储机制
        self._cleaned_response = ""  # 已清理的完整响应文本
        self._played_len = 0         # 已播放的字符数
        self._last_speak_time = 0    # 上次播报时间
        self._sentence_buffer = []   # 句子缓存，满两条才入队播报
        
        # 语音队列 - 确保按顺序播放不重叠
        self._speak_queue = queue.Queue()
        self._speak_thread = None
        self._speak_thread_running = False
        
        self._init_button()
        self._start_speak_thread()
    
    def _start_speak_thread(self):
        """启动语音播放线程"""
        self._speak_thread_running = True
        self._speak_thread = threading.Thread(target=self._speak_worker, daemon=True)
        self._speak_thread.start()
        print("[ButtonVoiceAssistant] 语音队列线程已启动")
    
    def _speak_worker(self):
        """语音播放工作线程 - 预加载机制确保连贯"""
        preloaded_text = None
        
        while self._speak_thread_running:
            try:
                # 如果有预加载的文本，先播放它
                if preloaded_text:
                    text = preloaded_text
                    preloaded_text = None
                    is_preloaded = True
                else:
                    # 从队列获取
                    text = self._speak_queue.get(timeout=0.15)
                    is_preloaded = False
                
                if text and self.voice_player:
                    # 尝试预加载下一句
                    try:
                        preloaded_text = self._speak_queue.get_nowait()
                    except queue.Empty:
                        preloaded_text = None
                    
                    # 播放当前句子（异常隔离，单句失败不阻塞后续）
                    try:
                        self.voice_player.speak(text, block=True, show_in_ui=False)
                    except Exception as e:
                        print(f"[ButtonVoiceAssistant] 单句播放异常: {e}")

                    # 标记当前任务完成（如果是从队列取的）
                    if not is_preloaded:
                        self._speak_queue.task_done()
                    
                    # 如果预加载了，循环继续播放下一句
                    if preloaded_text:
                        continue
                elif not is_preloaded:
                    self._speak_queue.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[ButtonVoiceAssistant] 语音播放错误: {e}")
    
    def _queue_speak(self, text: str):
        """将语音加入播放队列"""
        if text and text.strip():
            self._speak_queue.put(text.strip())
            print(f"[ButtonVoiceAssistant] 加入队列: {text[:40]}...")
    
    def _stop_speak_thread(self):
        """停止语音播放线程"""
        self._speak_thread_running = False
        # 清空队列
        while not self._speak_queue.empty():
            try:
                self._speak_queue.get_nowait()
            except queue.Empty:
                break
        if self._speak_thread:
            self._speak_thread.join(timeout=2.0)
    
    def _init_button(self):
        """初始化按钮"""
        try:
            from .button_handler import ButtonHandler, ButtonEvent
            
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
        with self._lock:
            # 防止重复触发（如果已经在录音中或处理中则忽略）
            if self._recording_indicator or self._processing:
                return
        
        print("[ButtonVoiceAssistant] 按钮按下 - 开始录音")
        
        # LED 变红色（录音中）
        if self.led_controller:
            try:
                self.led_controller.set_all(self.led_controller.COLOR_RED)
                print("[ButtonVoiceAssistant] LED 已设置为红色（录音中）")
            except Exception as e:
                print(f"[ButtonVoiceAssistant] LED 设置失败: {e}")
        
        # 开始录音
        success = self.recorder.start_recording()
        
        if success:
            with self._lock:
                self._recording_indicator = True
        else:
            # 录音失败，LED 恢复
            if self.led_controller:
                try:
                    self.led_controller.set_all(self.led_controller.COLOR_GREEN)
                except:
                    pass
            if self.message_callback:
                self.message_callback("❌ 录音启动失败", icon="⚠️")
    
    def _on_button_release(self):
        """按钮释放 - 停止录音并处理"""
        print("[ButtonVoiceAssistant] 按钮释放 - 停止录音")
        
        with self._lock:
            if not self._recording_indicator:
                return
            self._recording_indicator = False
            self._processing = True
        
        # 停止录音
        wav_path = self.recorder.stop_recording()
        
        # LED 变绿色（处理中）
        if self.led_controller:
            try:
                self.led_controller.set_all(self.led_controller.COLOR_GREEN)
                print("[ButtonVoiceAssistant] LED 已设置为绿色（处理中）")
            except Exception as e:
                print(f"[ButtonVoiceAssistant] LED 设置失败: {e}")
        
        if not wav_path:
            if self.message_callback:
                self.message_callback("❌ 录音失败", icon="⚠️")
            with self._lock:
                self._processing = False
            return
        
        # 启动识别线程
        thread = threading.Thread(target=self._process_recording, args=(wav_path,))
        thread.daemon = True
        thread.start()
    
    def _process_recording(self, wav_path: str):
        """处理录音（识别+大模型处理+播报）"""
        try:
            # 1. 语音识别
            result = self.recognizer.recognize(wav_path)
            
            # 2. 处理识别结果（去掉空格）
            if result.text:
                # 去掉空格，使语音连贯
                clean_text = result.text.replace(" ", "").replace("  ", "")
                
                print(f"[ButtonVoiceAssistant] 识别结果: {clean_text} (置信度: {result.confidence:.2f})")
                
                # 3. 处理用户请求
                if self.ollama_client and result.confidence > 0.3:
                    # 先显示用户说的话
                    if self.message_callback:
                        self.message_callback(f"> {clean_text}", icon="💬")
                    
                    # 获取实时数据
                    try:
                        import sys
                        sys.path.insert(0, '/home/hedya/Desktop/bs_project/qt_project')
                        from core.data_context import get_data_context
                        d = get_data_context().get_data()
                        
                        # 只检测明确的数据查询关键词
                        data_keywords = ['速度', '功率', '踏频', '心率', '温度', '坡度', '距离', '时间', '里程', '数据']
                        is_data_query = any(kw in clean_text for kw in data_keywords)
                        
                        if is_data_query and d.speed > 0:
                            # 根据用户问题智能选择要回答的数据
                            print(f"[ButtonVoiceAssistant] 识别文本: '{clean_text}'")
                            parts = []
                            
                            # 检测用户具体问什么
                            if '速度' in clean_text:
                                parts.append(f"速度{d.speed:.1f}公里每小时")
                            if '功率' in clean_text:
                                parts.append(f"功率{d.power:.0f}瓦")
                            if '踏频' in clean_text:
                                parts.append(f"踏频{d.cadence:.0f}转每分钟")
                            if '心率' in clean_text:
                                parts.append(f"心率{d.heart_rate:.0f}次每分钟")
                            if '温度' in clean_text or '气温' in clean_text:
                                parts.append(f"环境温度{d.temperature:.1f}摄氏度")
                            if '距离' in clean_text or '里程' in clean_text:
                                parts.append(f"已骑行{d.distance:.1f}公里")
                            if '时间' in clean_text:
                                hours = d.ride_time // 3600
                                mins = (d.ride_time % 3600) // 60
                                parts.append(f"骑行时间{hours}小时{mins}分钟")
                            if '坡度' in clean_text:
                                prefix = "上坡" if d.slope > 0 else "下坡"
                                parts.append(f"{prefix}{abs(d.slope):.1f}%坡度")
                            
                            # 问"数据"时播报所有，否则只回答匹配的具体数据
                            if '数据' in clean_text:
                                parts = [f"速度{d.speed:.1f}公里每小时"]
                                if d.power > 0: parts.append(f"功率{d.power:.0f}瓦")
                                if d.cadence > 0: parts.append(f"踏频{d.cadence:.0f}")
                                if d.distance > 0: parts.append(f"骑行{d.distance:.1f}公里")
                                if d.heart_rate > 0: parts.append(f"心率{d.heart_rate:.0f}")
                                if d.temperature > 0: parts.append(f"温度{d.temperature:.1f}度")
                            
                            # 调试：查看匹配了哪些数据
                            print(f"[ButtonVoiceAssistant] 匹配到的数据项: {parts}")
                            
                            reply = "，".join(parts) + "。"
                            
                            print(f"[ButtonVoiceAssistant] 本地直接回复: {reply}")
                            
                            # 显示回复（带语音标识）
                            if self.message_callback:
                                self.message_callback(reply, icon="🔊")
                            
                            # 语音播报（加入队列顺序播放）
                            self._queue_speak(reply)
                            
                            # LED恢复
                            if self.led_controller:
                                try:
                                    self.led_controller.start_pattern("breath", self.led_controller.COLOR_GREEN)
                                except:
                                    pass
                            return  # 跳过大模型调用
                    except Exception as e:
                        print(f"[ButtonVoiceAssistant] 本地处理失败: {e}")
                    
                    # 非数据查询问题，走大模型（不传递骑行数据）
                    print(f"[ButtonVoiceAssistant] 调用大模型: {clean_text}")
                    
                    system_prompt = "你是骑行助手小智。简洁回答，无Markdown。每次回复严格控制在100字以内，务必完整收尾，绝不截断。"
                    enhanced_prompt = clean_text

                    # 使用流式输出，边生成边显示和播报
                    # 注意：流式输出是异步的，_on_stream_complete 会重置 _processing 状态
                    self._reset_stream_state()  # 重置所有流式状态
                    self.ollama_client.chat_stream(
                        prompt=enhanced_prompt,
                        on_token=lambda token: self._on_stream_token(token),
                        on_complete=lambda full: self._on_stream_complete(full),
                        system_prompt=system_prompt,
                        max_tokens=128  # 100字中文约130token，128足够
                    )
                    # 流式输出已启动，_processing 状态将在 _on_stream_complete 中重置
                    return  # 提前返回，不执行后面的清理
                else:
                    print(f"[ButtonVoiceAssistant] 没有Ollama客户端或置信度太低，直接播报")
                    # 没有 Ollama 时，直接显示识别结果
                    if self.message_callback:
                        self.message_callback(f"> {clean_text}", icon="💬")
                    
                    # 直接播报识别结果（加入队列）
                    if result.confidence > 0.3:
                        self._queue_speak(clean_text[:50])
                    
                    # LED 恢复
                    if self.led_controller:
                        try:
                            self.led_controller.start_pattern("breath", self.led_controller.COLOR_GREEN)
                        except:
                            pass
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
            import traceback
            traceback.print_exc()
            if self.message_callback:
                self.message_callback(f"❌ 处理失败: {str(e)}", icon="⚠️")
        finally:
            # 确保处理状态被重置（流式输出路径除外）
            with self._lock:
                self._processing = False
    
    def _on_stream_token(self, token: str):
        """流式输出 - 收到每个token时调用，实时更新UI和语音播报"""
        import time
        self._current_response += token
        current_time = time.time()
        
        # 每100ms更新一次UI，在同一行覆盖
        if current_time - self._last_update_time > 0.1:
            if self.message_callback:
                # 显示部分结果，使用特殊标记实现覆盖更新
                partial = self._clean_response(self._current_response)
                self.message_callback(partial, icon="__STREAM_UPDATE__")
                self._stream_displayed = True
            self._last_update_time = current_time
        
        # 流式语音播报：检测完整句子并分段播报
        self._check_and_speak_streaming()
    
    def _check_and_speak_streaming(self):
        """检查并播报新增内容 - 只以 '。' 断句，缓存满两句再入队"""
        # 重新清理当前响应（确保一致性）
        new_cleaned = self._clean_response(self._current_response)

        # 如果新清理的文本比已存储的短，使用已存储的
        if len(new_cleaned) < len(self._cleaned_response):
            new_cleaned = self._cleaned_response
        else:
            self._cleaned_response = new_cleaned

        # 检查是否有新内容需要处理
        if self._played_len >= len(self._cleaned_response):
            return

        # 获取未播报的部分
        new_part = self._cleaned_response[self._played_len:]
        if not new_part:
            return

        # 只在 '。' 处分段，其他标点（！？）不当作断句点
        while True:
            period_idx = new_part.find("。")
            if period_idx == -1:
                break

            # 提取包含句号在内的完整句子
            segment = new_part[:period_idx + 1]
            self._sentence_buffer.append(segment)
            self._played_len += len(segment)

            # 缓存满两条才一次性入队，给 TTS 足够缓冲
            if len(self._sentence_buffer) >= 2:
                for s in self._sentence_buffer:
                    self._queue_speak(s)
                self._sentence_buffer = []
                self._speak_started = True

            # 继续处理句号之后的剩余内容
            new_part = new_part[period_idx + 1:]
    
    def _clean_response(self, text: str) -> str:
        """清理模型回复，去除Markdown格式符号"""
        import re
        # 去除星号、下划线等Markdown格式符号
        text = re.sub(r'\*+', '', text)  # 去除 * 号
        text = re.sub(r'_+', '', text)   # 去除 _ 下划线
        text = re.sub(r'`+', '', text)   # 去除 ` 代码块
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _on_stream_complete(self, response: str):
        """流式输出完成 - 显示最终结果并播报剩余内容"""
        try:
            # 清理回复内容
            full_response = self._clean_response(response)
            print(f"[ButtonVoiceAssistant] 大模型完整回复: {full_response}")
            
            stream_was_displayed = self._stream_displayed
            self._stream_displayed = False
            
            # 如果回复为空或超时提示，不显示
            if not full_response or "抱歉" in full_response:
                self._speak_started = False
                if self.led_controller:
                    try:
                        self.led_controller.start_pattern("breath", self.led_controller.COLOR_GREEN)
                    except:
                        pass
                return
            
            # 显示模型回复到消息框（最终完整版，在同一行）
            if self.message_callback:
                if stream_was_displayed:
                    # 流式过程中已显示过，使用最终标记覆盖同一行
                    self.message_callback(full_response, icon="__STREAM_FINAL__")
                else:
                    # 流式过程中未显示（生成太快），直接显示新消息
                    self.message_callback(full_response, icon="🤖")
            
            # 更新清理后的文本
            self._cleaned_response = full_response

            # 1. 先 flush 缓存中的句子（即使不满两条，流式完成时也要播报）
            if self._sentence_buffer:
                print(f"[ButtonVoiceAssistant] 完成时 flush 缓存句子: {len(self._sentence_buffer)} 条")
                for s in self._sentence_buffer:
                    self._queue_speak(s)
                self._sentence_buffer = []

            # 2. 播报剩余未播报的内容（从已播放位置到结尾，没有句号结尾的剩余）
            if self._played_len < len(full_response):
                remaining = full_response[self._played_len:]
                if remaining.strip():
                    print(f"[ButtonVoiceAssistant] 完成时播报剩余: {remaining[:50]}...")
                    self._queue_speak(remaining)
                    self._played_len = len(full_response)

            # LED 恢复呼吸灯状态
            if self.led_controller:
                try:
                    self.led_controller.start_pattern("breath", self.led_controller.COLOR_GREEN)
                except:
                    pass
                
        except Exception as e:
            print(f"[ButtonVoiceAssistant] 处理大模型回复失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 重置所有流式状态
            self._reset_stream_state()
            # 重置处理状态，允许下次录音
            with self._lock:
                self._processing = False
    
    def _reset_stream_state(self):
        """重置流式输出状态"""
        self._current_response = ""      # 原始累积响应
        self._stream_buffer = ""
        self._speak_started = False
        self._cleaned_response = ""      # 清理后的响应
        self._played_len = 0             # 已播放长度
        self._last_speak_time = 0
        self._stream_displayed = False
        self._sentence_buffer = []       # 句子缓存
    
    def _handle_ollama_response(self, response: str):
        """处理 Ollama 大模型返回的结果（非流式，备用）"""
        try:
            # 清理回复内容
            response = self._clean_response(response)
            print(f"[ButtonVoiceAssistant] 大模型回复: {response}")
            
            # 显示模型回复到消息框
            if self.message_callback:
                self.message_callback(response, icon="🤖")
            
            # 语音播报模型回复（完整内容，加入队列）
            self._queue_speak(response)
            
            # LED 恢复呼吸灯状态
            if self.led_controller:
                try:
                    self.led_controller.start_pattern("breath", self.led_controller.COLOR_GREEN)
                except:
                    pass
                
        except Exception as e:
            print(f"[ButtonVoiceAssistant] 处理大模型回复失败: {e}")
    
    def stop(self):
        """停止助手"""
        if self.button_handler:
            self.button_handler.stop()
        if self.recorder.is_recording():
            self.recorder.stop_recording()
        # 停止语音队列线程
        self._stop_speak_thread()


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
