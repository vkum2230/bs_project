#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云通义 TTS 语音播放器
使用 dashscope 流式输出，边合成边播放
- 在线：阿里云 qwen3-tts-flash（流式，国内网络稳定）
- 失败时自动 fallback 到 espeak
"""

import os
import sys
import base64
import subprocess
import threading
import tempfile
import time
from typing import Optional

# 设置阿里云 API endpoint（北京地域）
import dashscope
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'


class FinalVoicePlayer:
    """
    最终版语音播放器
    - 优先使用阿里云通义 TTS（流式输出，国内直连）
    - 失败时自动 fallback 到 espeak
    """

    def __init__(self, voice: str = 'Maia', message_callback=None, fallback_to_espeak: bool = True):
        """
        初始化

        Args:
            voice: 音色名称，默认 'Maia'（四月）
            message_callback: 消息回调，用于在UI显示播报内容
            fallback_to_espeak: 失败时是否 fallback 到 espeak
        """
        self.voice = voice
        self._message_callback = message_callback
        self._fallback_to_espeak = fallback_to_espeak
        self._audio_device = "plughw:2,0"
        self._lock = threading.Lock()

        # 从配置管理器读取 API key 和模型
        try:
            from persistence.config_manager import get_config
            cfg = get_config()
            self._api_key = cfg.get("aliyun_tts_api_key", "")
            self._model = cfg.get("aliyun_tts_model", "qwen3-tts-flash")
            self.voice = cfg.get("aliyun_tts_voice", voice)
        except Exception:
            self._api_key = ""
            self._model = "qwen3-tts-flash"

        if not self._api_key:
            print("[FinalVoice] 警告: 阿里云 TTS API Key 未配置")
        else:
            print(f"[FinalVoice] 阿里云 TTS 就绪，模型: {self._model}, 音色: {self.voice}")

        # 调大系统播放音量
        self._set_system_volume()

    def _set_system_volume(self):
        """将 ReSpeaker 播放音量调到合适大小"""
        try:
            # ReSpeaker 声卡通常是 card 2，音量设为 85%
            subprocess.run(
                ["amixer", "-c", "2", "set", "PCM", "85%", "unmute"],
                capture_output=True, timeout=3
            )
            subprocess.run(
                ["amixer", "-c", "2", "set", "Headphone", "85%", "unmute"],
                capture_output=True, timeout=3
            )
            subprocess.run(
                ["amixer", "-c", "2", "set", "Speaker", "85%", "unmute"],
                capture_output=True, timeout=3
            )
            print("[FinalVoice] 系统音量已调至 85%")
        except Exception as e:
            print(f"[FinalVoice] 音量设置失败: {e}")

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
                # 优先尝试阿里云通义 TTS（流式输出）
                if self._api_key:
                    try:
                        result = self._speak_aliyun_stream(text)
                        if result:
                            print("[FinalVoice] ✓ 阿里云 TTS 播报成功")
                            return True
                        print("[FinalVoice] ✗ 阿里云 TTS 失败")
                        if not fallback_to_espeak:
                            return False
                    except Exception as e:
                        print(f"[FinalVoice] ✗ 阿里云 TTS 错误: {e}")
                        if not fallback_to_espeak:
                            return False
                else:
                    print("[FinalVoice] API Key 未配置，跳过阿里云 TTS")
                    if not fallback_to_espeak:
                        return False

                # 备用：espeak
                if fallback_to_espeak:
                    print("[FinalVoice] 使用 espeak 保底...")
                    return self._speak_espeak(text)
                return False

        if block:
            return _do_speak()
        else:
            thread = threading.Thread(target=_do_speak)
            thread.daemon = True
            thread.start()
            return True

    def _speak_aliyun_stream(self, text: str, max_retries: int = 2) -> bool:
        """使用阿里云通义 TTS 流式输出并播放（正常语速）"""
        import dashscope

        # 先检查网络
        if not self._check_network():
            print("[FinalVoice] 网络不可用，跳过阿里云 TTS")
            return False

        for attempt in range(max_retries):
            aplay_proc = None
            audio_received = False
            try:
                print(f"[FinalVoice] 阿里云 TTS 尝试 {attempt + 1}/{max_retries}...")

                # 启动 aplay 子进程，从 stdin 读取 PCM 数据实时播放
                # 流式输出格式：pcm, 24kHz, 16bit, 单声道
                aplay_proc = subprocess.Popen(
                    ["aplay", "-q", "-f", "S16_LE", "-r", "24000", "-c", "1", "-D", self._audio_device, "-"],
                    stdin=subprocess.PIPE
                )

                response = dashscope.MultiModalConversation.call(
                    api_key=self._api_key,
                    model=self._model,
                    text=text,
                    voice=self.voice,
                    language_type="Chinese",
                    stream=True
                )

                for chunk in response:
                    try:
                        output = getattr(chunk, 'output', None)
                        if output is None:
                            continue

                        audio = getattr(output, 'audio', None)
                        if audio is not None:
                            data = getattr(audio, 'data', None)
                            if data is not None:
                                wav_bytes = base64.b64decode(data)
                                aplay_proc.stdin.write(wav_bytes)
                                aplay_proc.stdin.flush()
                                audio_received = True

                        finish_reason = getattr(output, 'finish_reason', None)
                        if finish_reason == "stop":
                            print("[FinalVoice] 流式合成完成")
                            break
                    except BrokenPipeError:
                        print("[FinalVoice] aplay 管道已关闭，停止写入")
                        break
                    except Exception as chunk_err:
                        print(f"[FinalVoice] 处理 chunk 出错: {chunk_err}")
                        continue

                # 关闭 stdin，等待 aplay 播放完毕
                try:
                    aplay_proc.stdin.close()
                except Exception:
                    pass

                try:
                    aplay_proc.wait(timeout=60)
                    if audio_received and aplay_proc.returncode == 0:
                        print("[FinalVoice] ✓ aplay 播放成功")
                        return True
                    elif not audio_received:
                        print("[FinalVoice] 未收到音频数据")
                        return False
                    else:
                        print(f"[FinalVoice] aplay 返回码: {aplay_proc.returncode}")
                        return False
                except subprocess.TimeoutExpired:
                    print("[FinalVoice] aplay 播放超时，强制终止")
                    try:
                        aplay_proc.terminate()
                        aplay_proc.wait(timeout=5)
                    except Exception:
                        try:
                            aplay_proc.kill()
                        except Exception:
                            pass
                    # 即使超时，如果已收到音频也算成功
                    if audio_received:
                        return True
                    return False

            except Exception as e:
                print(f"[FinalVoice] 阿里云 TTS 失败 (尝试 {attempt + 1}/{max_retries}): {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    return False
            finally:
                # 确保 aplay 进程被清理，防止泄漏占用音频设备
                if aplay_proc:
                    try:
                        if aplay_proc.poll() is None:
                            aplay_proc.terminate()
                            try:
                                aplay_proc.wait(timeout=2)
                            except Exception:
                                aplay_proc.kill()
                    except Exception:
                        pass

        return False

    def _check_network(self) -> bool:
        """检查网络连接（多地址容错）"""
        import socket
        check_hosts = [
            ("223.5.5.5", 53),
            ("114.114.114.114", 53),
            ("8.8.8.8", 53),
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

    def _speak_espeak(self, text: str) -> bool:
        """使用 espeak 保底"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name

            result = subprocess.run(
                ["espeak", "-v", "zh", "-w", wav_path, text],
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0:
                result2 = subprocess.run(
                    ["aplay", "-q", "-D", self._audio_device, wav_path],
                    capture_output=True,
                    timeout=30
                )
                if result2.returncode == 0:
                    print("[FinalVoice] espeak 播放完成")
                    return True
                else:
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
        """停止播放（通过停止 aplay）"""
        try:
            subprocess.run(["pkill", "-f", "aplay"], capture_output=True)
        except Exception:
            pass


if __name__ == "__main__":
    print("=" * 60)
    print("阿里云通义 TTS 语音播放器测试")
    print("=" * 60)

    player = FinalVoicePlayer()

    print("\n测试1: 基础播报")
    player.speak("你好，我是骑行小智", block=True)

    time.sleep(1)

    print("\n测试2: 较长文本")
    player.speak("前方五百米右转，进入建设大道", block=True)

    print("\n" + "=" * 60)
    print("测试完成")
