#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Piper 离线语音合成播放器
轻量级神经网络 TTS，支持中文，无需网络
"""

import os
import subprocess
import tempfile
import threading
from typing import Optional


class PiperVoicePlayer:
    """
    Piper 离线语音播放器
    基于本地神经网络模型，无需网络连接
    """
    
    def __init__(self, 
                 model_path: str = None,
                 audio_device: str = "plughw:2,0",
                 message_callback=None):
        """
        初始化 Piper 播放器
        
        Args:
            model_path: 模型文件路径，默认使用自动检测
            audio_device: 音频输出设备
            message_callback: 消息回调函数
        """
        self._audio_device = audio_device
        self._message_callback = message_callback
        self._piper_path = None
        self._model_path = model_path
        
        # 初始化
        self._init_piper()
    
    def _init_piper(self):
        """查找 Piper 可执行文件和模型"""
        # 可能的 Piper 路径
        possible_paths = [
            os.path.expanduser("~/.local/share/piper/piper/piper"),  # 实际安装路径
            os.path.expanduser("~/.local/share/piper/piper"),        # 备用路径
            "/usr/local/bin/piper",
            "/usr/bin/piper",
            "./piper/piper",
        ]
        
        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                self._piper_path = path
                print(f"[PiperVoice] 找到 Piper: {path}")
                break
        
        if not self._piper_path:
            print("[PiperVoice] Piper 未找到，请运行 setup_piper.sh 安装")
            return
        
        # 如果未指定模型，自动查找
        if not self._model_path:
            possible_models = [
                os.path.expanduser("~/.local/share/piper/zh_CN/zh_CN-huayan-medium.onnx"),
                os.path.expanduser("~/.local/share/piper/zh/zh_CN-huayan-medium.onnx"),
                "./piper/models/zh_CN-huayan-medium.onnx",
            ]
            
            for model in possible_models:
                if os.path.isfile(model):
                    self._model_path = model
                    print(f"[PiperVoice] 使用模型: {model}")
                    break
        
        if not self._model_path:
            print("[PiperVoice] 未找到中文模型，请下载模型文件")
    
    def is_available(self) -> bool:
        """检查是否可用"""
        return self._piper_path is not None and self._model_path is not None
    
    def speak(self, text: str, block: bool = False, show_in_ui: bool = True) -> bool:
        """
        播报文本
        
        Args:
            text: 要播报的文本
            block: 是否阻塞等待
            show_in_ui: 是否在UI显示
        
        Returns:
            是否成功
        """
        if not text:
            return False
        
        if not self.is_available():
            print("[PiperVoice] Piper 不可用")
            return False
        
        # 限制文本长度（Piper 长文本处理较慢）
        text = text[:200] if len(text) > 200 else text
        
        print(f"[PiperVoice] 播报: {text[:50]}...")
        
        # UI 回调
        if show_in_ui and self._message_callback:
            self._message_callback(text, icon="🔊")
        
        def _do_speak():
            wav_path = None
            try:
                # 使用 piper 生成并播放
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    wav_path = f.name
                
                print(f"[PiperVoice] 开始合成，模型: {self._model_path}")
                
                # 生成语音 - Piper 需要从 stdin 读取文本
                result = subprocess.run(
                    [
                        self._piper_path,
                        "--model", self._model_path,
                        "--output_file", wav_path
                    ],
                    input=text.encode('utf-8'),  # 通过 stdin 传递文本
                    capture_output=True,
                    timeout=15  # 合成最多15秒
                )
                
                if result.returncode != 0:
                    err = result.stderr.decode()[:200] if result.stderr else "未知错误"
                    print(f"[PiperVoice] 合成失败: {err}")
                    return False
                
                print(f"[PiperVoice] 合成完成，开始播放...")
                
                # 播放
                play_result = subprocess.run(
                    ["aplay", "-q", "-D", self._audio_device, wav_path],
                    capture_output=True,
                    timeout=30  # 播放最多30秒
                )
                
                if play_result.returncode != 0:
                    err = play_result.stderr.decode()[:200] if play_result.stderr else "未知错误"
                    print(f"[PiperVoice] 播放失败: {err}")
                    return False
                
                print("[PiperVoice] 播放完成")
                return True
                
            except subprocess.TimeoutExpired as e:
                print(f"[PiperVoice] 超时: {e}")
                return False
            except Exception as e:
                print(f"[PiperVoice] 错误: {e}")
                import traceback
                traceback.print_exc()
                return False
            finally:
                # 清理临时文件
                if wav_path:
                    try:
                        if os.path.exists(wav_path):
                            os.remove(wav_path)
                            print(f"[PiperVoice] 清理临时文件")
                    except:
                        pass
        
        if block:
            return _do_speak()
        else:
            thread = threading.Thread(target=_do_speak)
            thread.daemon = True
            thread.start()
            return True
    
    def stop(self):
        """停止播放（通过停止 aplay）"""
        try:
            subprocess.run(["pkill", "-f", "aplay"], capture_output=True)
        except:
            pass


class HybridVoicePlayer:
    """
    混合语音播放器：优先在线，离线备用
    - 在线优先：使用 Edge-TTS（音质好）
    - 在线失败/超时：使用 Piper（离线）
    - 都失败：使用 espeak（保底）
    """
    
    def __init__(self, voice: str = 'xiaoxiao', message_callback=None, force_offline: bool = False):
        """
        初始化混合播放器

        Args:
            voice: Edge-TTS 语音选择
            message_callback: 消息回调
            force_offline: 强制离线模式，不尝试任何网络请求
        """
        self._message_callback = message_callback
        self.force_offline = force_offline
        self._online_player = None
        self._offline_player = None
        
        # 初始化在线播放器 (Edge-TTS)
        # 使用 FinalVoicePlayer（基于 asyncio + edge_tts Python API，比 CLI 更稳定）
        # 但禁用其内部的 espeak 兜底，这样 Edge-TTS 失败时才能正确 fallback 到 Piper
        try:
            from .voice_final import FinalVoicePlayer
            self._online_player = FinalVoicePlayer(
                voice=voice,
                message_callback=message_callback,
                fallback_to_espeak=False
            )
            print("[HybridVoice] 在线播放器 (Edge-TTS) 已加载")
        except Exception as e:
            print(f"[HybridVoice] 在线播放器加载失败: {e}")
            self._online_player = None
        
        # 初始化离线播放器 (使用新的 OfflineVoicePlayer)
        try:
            # 尝试使用增强版离线语音
            from .offline_voice import OfflineVoicePlayer
            self._offline_player = OfflineVoicePlayer(
                audio_device="plughw:2,0",
                message_callback=message_callback
            )
            
            if self._offline_player.is_available():
                print("[HybridVoice] 离线播放器已加载")
            else:
                print("[HybridVoice] 离线播放器不可用")
                self._offline_player = None
        except Exception as e:
            print(f"[HybridVoice] 增强版离线语音加载失败: {e}")
            # 回退到原版 Piper
            try:
                self._offline_player = PiperVoicePlayer(
                    audio_device="plughw:2,0",
                    message_callback=message_callback
                )
                if self._offline_player.is_available():
                    print("[HybridVoice] 离线播放器 (Piper) 已加载")
                else:
                    print("[HybridVoice] 离线播放器不可用，将使用 espeak 备用")
            except Exception as e2:
                print(f"[HybridVoice] 离线播放器初始化失败: {e2}")
                self._offline_player = None
        
        self._lock = threading.Lock()
    
    def _check_network(self) -> bool:
        """检查网络连接（多地址容错，避免误判）"""
        import socket
        check_hosts = [
            ("223.5.5.5", 53),    # 阿里云 DNS
            ("114.114.114.114", 53), # 114 DNS
            ("8.8.8.8", 53),      # Google DNS（备用）
        ]
        for host, port in check_hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((host, port))
                sock.close()
                return True
            except Exception:
                continue
        return False
    
    def speak(self, text: str, block: bool = False, show_in_ui: bool = True) -> bool:
        """
        播报文本（优先在线，超时切换离线）

        优先级：
        1. 阿里云通义 TTS（在线，流式输出，国内直连）
        2. Piper/MeloTTS（在线超时/失败或网络不可用时）
        3. espeak（保底方案）
        """
        if not text:
            return False
        
        def _do_speak():
            import threading
            thread_id = threading.current_thread().ident
            
            # 使用超时获取锁，防止前一个线程死锁导致永久阻塞
            if not self._lock.acquire(timeout=30):
                print(f"[HybridVoice] ✗ 获取播报锁超时（30秒），跳过本次播报: {text[:30]} (线程{thread_id})")
                return False
            try:
                print(f"[HybridVoice] [线程{thread_id}] 开始播报: {text[:30]}...")
                
                # 清理可能卡住的 aplay 进程，防止音频设备被占用
                try:
                    subprocess.run(["pkill", "-9", "-f", "aplay"], capture_output=True, timeout=2)
                except Exception:
                    pass
                
                # 离线模式强制跳过网络检查
                if self.force_offline:
                    has_network = False
                    print("[HybridVoice] 强制离线模式，跳过网络检查")
                else:
                    has_network = self._check_network()
                    print(f"[HybridVoice] 网络状态: {'可用' if has_network else '不可用'}")
                
                # UI 回调统一在这里处理
                if show_in_ui and self._message_callback:
                    self._message_callback(text, icon="🔊")

                # 优先尝试在线播放（阿里云通义 TTS），流式输出
                if self._online_player and has_network:
                    print("[HybridVoice] 优先尝试阿里云 TTS 在线播报（60秒总超时）...")
                    try:
                        import threading
                        online_result = [None]

                        def _online_speak():
                            try:
                                print("[HybridVoice] 阿里云 TTS 线程启动...")
                                # UI 回调由 HybridVoicePlayer 统一处理，在线播放器不重复显示
                                online_result[0] = self._online_player.speak(text, block=True, show_in_ui=False)
                                print(f"[HybridVoice] 阿里云 TTS 线程完成，结果: {online_result[0]}")
                            except Exception as e:
                                print(f"[HybridVoice] 阿里云 TTS 线程错误: {e}")
                                import traceback
                                traceback.print_exc()
                                online_result[0] = False

                        online_thread = threading.Thread(target=_online_speak)
                        online_thread.daemon = True
                        online_thread.start()
                        print("[HybridVoice] 等待阿里云 TTS 完成...")
                        online_thread.join(timeout=60)  # 最多等待60秒

                        if online_thread.is_alive():
                            print("[HybridVoice] ✗ 阿里云 TTS 超时（60秒），切换到离线语音")
                        elif online_result[0] is True:
                            print("[HybridVoice] ✓ 阿里云 TTS 在线播报成功")
                            return True
                        else:
                            print(f"[HybridVoice] ✗ 阿里云 TTS 失败，结果: {online_result[0]}")
                    except Exception as e:
                        print(f"[HybridVoice] ✗ 阿里云 TTS 错误: {e}")
                        import traceback
                        traceback.print_exc()
                elif not self._online_player:
                    print("[HybridVoice] 阿里云 TTS 播放器未初始化")
                else:
                    print("[HybridVoice] 网络不可用，跳过阿里云 TTS")
                
                # Edge-TTS 失败或超时，尝试离线播放（Piper）
                piper_available = self._offline_player and self._offline_player.is_available()
                print(f"[HybridVoice] Piper 状态: {'可用' if piper_available else '不可用'}")
                
                if piper_available:
                    print("[HybridVoice] 尝试 Piper 离线播报...")
                    try:
                        # UI 回调已由 HybridVoicePlayer 统一处理，离线播放器不重复显示
                        result = self._offline_player.speak(text, block=True, show_in_ui=False)
                        if result:
                            print("[HybridVoice] ✓ Piper 离线播报成功")
                            return True
                        print("[HybridVoice] ✗ Piper 失败")
                    except Exception as e:
                        print(f"[HybridVoice] ✗ Piper 错误: {e}")
                
                # 保底方案：espeak
                print("[HybridVoice] 使用 espeak 保底...")
                return self._speak_espeak(text)
            finally:
                try:
                    self._lock.release()
                    print(f"[HybridVoice] [线程{thread_id}] 锁已释放")
                except RuntimeError:
                    pass  # 锁未被当前线程持有
        
        if block:
            return _do_speak()
        else:
            thread = threading.Thread(target=_do_speak)
            thread.daemon = True
            thread.start()
            return True
    
    def _speak_espeak(self, text: str) -> bool:
        """使用 espeak 保底"""
        try:
            import tempfile
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            
            # 生成
            result = subprocess.run(
                ["espeak", "-v", "zh", "-w", wav_path, text],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # 播放
                subprocess.run(
                    ["aplay", "-q", "-D", "plughw:2,0", wav_path],
                    capture_output=True,
                    timeout=30
                )
                print("[HybridVoice] 使用 espeak 播报成功")
                return True
            
            return False
        except Exception as e:
            print(f"[HybridVoice] espeak 失败: {e}")
            return False
    
    def stop(self):
        """停止播放"""
        if self._online_player:
            self._online_player.stop()
        if self._offline_player:
            self._offline_player.stop()


def test_piper():
    """测试 Piper"""
    print("="*50)
    print("测试 Piper 离线语音")
    print("="*50)
    
    player = PiperVoicePlayer()
    
    if not player.is_available():
        print("Piper 不可用，请先运行 setup_piper.sh 安装")
        return
    
    print("\n测试1: 阻塞模式")
    player.speak("你好，我是骑行小智", block=True)
    
    import time
    time.sleep(1)
    
    print("\n测试2: 非阻塞模式")
    player.speak("这是离线语音合成测试", block=False)
    
    time.sleep(3)
    print("\n测试完成")


def test_hybrid():
    """测试混合播放器"""
    print("="*50)
    print("测试混合语音播放器")
    print("="*50)
    
    player = HybridVoicePlayer()
    
    print("\n测试播报...")
    player.speak("你好，我是骑行小智，现在可以离线使用了", block=True)
    
    print("\n测试完成")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "hybrid":
        test_hybrid()
    else:
        test_piper()
