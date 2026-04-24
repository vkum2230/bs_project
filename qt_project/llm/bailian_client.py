#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云百炼（Bailian）在线大模型客户端
OpenAI-compatible API，用于在线状态下的智能对话
"""

import json
import requests
import threading
import time
from typing import Callable, Optional


class BailianClient:
    """阿里云百炼在线模型客户端"""

    def __init__(self, api_key: str = None, model: str = "qwen-turbo", base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        """
        初始化百炼客户端

        Args:
            api_key: API Key，默认从 ConfigManager 读取
            model: 模型名称
            base_url: API 基础地址
        """
        if api_key is None:
            from persistence.config_manager import get_config
            api_key = get_config().get("aliyun_bailian_api_key", "")

        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.chat_url = f"{self.base_url}/chat/completions"

    def _build_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _build_messages(self, prompt: str, system_prompt: str = None) -> list:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def chat(self, prompt: str, system_prompt: str = None, max_tokens: int = 128) -> str:
        """
        发送对话请求（非流式）

        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            max_tokens: 最大生成token数

        Returns:
            模型回复文本
        """
        try:
            print(f"[BailianClient] 发送请求，模型: {self.model}")
            data = {
                "model": self.model,
                "messages": self._build_messages(prompt, system_prompt),
                "stream": False,
                "max_tokens": max_tokens,
                "temperature": 0.5,
            }
            response = requests.post(
                self.chat_url,
                headers=self._build_headers(),
                json=data,
                timeout=30,
            )
            if response.status_code != 200:
                print(f"[BailianClient] 请求失败: {response.status_code} {response.text[:200]}")
                return "抱歉，我现在无法回答。"

            result = response.json()
            choices = result.get("choices", [])
            if choices:
                reply = choices[0].get("message", {}).get("content", "").strip()
                return reply if reply else "抱歉，我没听清。"
            return "抱歉，我没听清。"

        except requests.exceptions.Timeout:
            print("[BailianClient] 请求超时")
            return "抱歉，我反应慢了。"
        except Exception as e:
            print(f"[BailianClient] 错误: {e}")
            return "抱歉，出错了。"

    def chat_stream(self, prompt: str,
                    on_token: Callable[[str], None],
                    on_complete: Callable[[str], None],
                    system_prompt: str = None,
                    max_tokens: int = 128):
        """
        流式对话（边生成边返回）

        Args:
            prompt: 用户输入
            on_token: 收到每个token时的回调
            on_complete: 完成时的回调（接收完整文本）
            system_prompt: 系统提示词
            max_tokens: 最大生成长度
        """
        def _do_stream():
            full_response = ""
            try:
                messages = self._build_messages(prompt, system_prompt)
                print(f"[BailianClient] 请求消息: {json.dumps(messages, ensure_ascii=False)}")
                print(f"[BailianClient] 开始流式请求，模型: {self.model}, 提示前100字: {prompt[:100]}...")
                data = {
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "max_tokens": max_tokens,
                    "temperature": 0.5,
                }
                response = requests.post(
                    self.chat_url,
                    headers=self._build_headers(),
                    json=data,
                    stream=True,
                    timeout=60,
                )
                print(f"[BailianClient] 收到响应，状态码: {response.status_code}")

                if response.status_code != 200:
                    err = response.text[:200]
                    print(f"[BailianClient] 流式请求失败: {response.status_code} {err}")
                    on_complete("抱歉，我现在无法回答。")
                    return

                token_count = 0
                for line in response.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode("utf-8", errors="replace")
                    if not line_str.startswith("data: "):
                        continue
                    json_str = line_str[6:]
                    if json_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(json_str)
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            full_response += token
                            token_count += 1
                            on_token(token)
                        finish_reason = choices[0].get("finish_reason")
                        if finish_reason:
                            print(f"[BailianClient] 完成原因: {finish_reason}")
                            break
                    except Exception as parse_err:
                        print(f"[BailianClient] 解析行失败: {parse_err}, 行: {line_str[:100]}")

                print(f"[BailianClient] 总token数: {token_count}")
                if not full_response.strip():
                    print("[BailianClient] 警告: 回复为空")
                    full_response = "抱歉，我没听清。"
                else:
                    print(f"[BailianClient] 完整回复: {full_response[:100]}...")

                on_complete(full_response.strip())

            except requests.exceptions.Timeout:
                print("[BailianClient] 流式请求超时（60秒）")
                if full_response.strip():
                    on_complete(full_response.strip())
                else:
                    on_complete("抱歉，我想得太久了，请再说一次。")
            except Exception as e:
                print(f"[BailianClient] 流式请求错误: {e}")
                import traceback
                traceback.print_exc()
                if full_response.strip():
                    on_complete(full_response.strip())
                else:
                    on_complete("抱歉，出错了。")

        thread = threading.Thread(target=_do_stream)
        thread.daemon = True
        thread.start()

    def check_available(self) -> bool:
        """检查服务是否可用（简单网络测试）"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect(("dashscope.aliyuncs.com", 443))
            sock.close()
            return True
        except Exception:
            return False


if __name__ == "__main__":
    client = BailianClient()
    if client.check_available():
        print("百炼服务可达")
        response = client.chat("你好，介绍一下你自己")
        print(f"回复: {response}")
    else:
        print("百炼服务不可达")
