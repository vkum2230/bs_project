#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama 本地大模型客户端
用于处理语音识别后的文本，生成回复
"""

import requests
import json
import threading
from typing import Callable, Optional


class OllamaClient:
    """Ollama 本地模型客户端"""
    
    def __init__(self, model_name: str = "my-llama", host: str = "http://localhost:11434"):
        """
        初始化 Ollama 客户端
        
        Args:
            model_name: 模型名称（默认 my-llama）
            host: Ollama 服务地址
        """
        self.model_name = model_name
        self.host = host
        self.api_url = f"{host}/api/generate"
        
    def chat(self, prompt: str, system_prompt: str = None, stream: bool = False) -> str:
        """
        发送对话请求
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            stream: 是否流式输出
            
        Returns:
            模型回复文本
        """
        try:
            # 构建请求数据
            data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": stream
            }
            
            # 添加系统提示词（如果提供）
            if system_prompt:
                data["system"] = system_prompt
            
            # 发送请求
            response = requests.post(
                self.api_url,
                json=data,
                timeout=60  # 60秒超时
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                print(f"[OllamaClient] 请求失败: {response.status_code}")
                return "抱歉，我现在无法回答。"
                
        except requests.exceptions.ConnectionError:
            print("[OllamaClient] 连接失败，请检查 Ollama 服务是否运行")
            return "抱歉，我的大脑离线了。"
        except requests.exceptions.Timeout:
            print("[OllamaClient] 请求超时")
            return "抱歉，我思考太久了。"
        except Exception as e:
            print(f"[OllamaClient] 错误: {e}")
            return "抱歉，出错了。"
    
    def chat_async(self, prompt: str, callback: Callable[[str], None], 
                   system_prompt: str = None):
        """
        异步发送对话请求（不阻塞）
        
        Args:
            prompt: 用户输入
            callback: 回调函数，接收回复文本
            system_prompt: 系统提示词
        """
        def _do_chat():
            response = self.chat(prompt, system_prompt)
            callback(response)
        
        thread = threading.Thread(target=_do_chat)
        thread.daemon = True
        thread.start()
    
    def check_available(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False


# 默认系统提示词（骑行助手角色）
DEFAULT_SYSTEM_PROMPT = """你是骑行助手小智，一个专业的骑行导航助手。
你可以回答关于骑行路线、路况、天气、骑行技巧等问题。
回答要简洁明了，适合在骑行过程中听取。"""


if __name__ == "__main__":
    # 测试
    client = OllamaClient()
    
    if client.check_available():
        print("Ollama 服务正常")
        response = client.chat("你好，介绍一下你自己")
        print(f"回复: {response}")
    else:
        print("Ollama 服务不可用")
