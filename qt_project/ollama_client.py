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
        
    def chat(self, prompt: str, system_prompt: str = None, 
             max_tokens: int = 100, temperature: float = 0.7) -> str:
        """
        发送对话请求（快速模式）
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            max_tokens: 最大生成token数（默认100，约50个汉字）
            temperature: 创造性程度（越低越快，默认0.7）
            
        Returns:
            模型回复文本
        """
        try:
            # 构建请求数据（优化参数）
            data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,  # 限制生成长度
                    "temperature": temperature,  # 降低创造性，提高速度
                    "top_k": 40,  # 降低采样范围
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            }
            
            # 添加系统提示词（如果提供）
            if system_prompt:
                data["system"] = system_prompt
            
            # 发送请求（缩短超时）
            response = requests.post(
                self.api_url,
                json=data,
                timeout=15  # 15秒超时，避免等待太久
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
                   system_prompt: str = None, max_tokens: int = 100):
        """
        异步发送对话请求（不阻塞）
        
        Args:
            prompt: 用户输入
            callback: 回调函数，接收回复文本
            system_prompt: 系统提示词
            max_tokens: 最大生成长度
        """
        def _do_chat():
            response = self.chat(prompt, system_prompt, max_tokens=max_tokens)
            callback(response)
        
        thread = threading.Thread(target=_do_chat)
        thread.daemon = True
        thread.start()
    
    def chat_stream(self, prompt: str, 
                    on_token: Callable[[str], None],
                    on_complete: Callable[[str], None],
                    system_prompt: str = None,
                    max_tokens: int = 100):
        """
        流式对话（边生成边返回，体验更好）
        
        Args:
            prompt: 用户输入
            on_token: 收到每个token时的回调
            on_complete: 完成时的回调（接收完整文本）
            system_prompt: 系统提示词
            max_tokens: 最大生成长度
        """
        def _do_stream():
            try:
                data = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": True,  # 流式输出
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.7,
                        "top_k": 40,
                        "top_p": 0.9
                    }
                }
                
                if system_prompt:
                    data["system"] = system_prompt
                
                full_response = ""
                response = requests.post(
                    self.api_url,
                    json=data,
                    stream=True,  # 流式接收
                    timeout=15
                )
                
                for line in response.iter_lines():
                    if line:
                        try:
                            json_line = json.loads(line)
                            token = json_line.get("response", "")
                            if token:
                                full_response += token
                                on_token(token)  # 实时回调
                            
                            # 检查是否完成
                            if json_line.get("done", False):
                                break
                        except:
                            pass
                
                on_complete(full_response.strip())
                
            except Exception as e:
                print(f"[OllamaClient] 流式请求错误: {e}")
                on_complete("抱歉，出错了。")
        
        thread = threading.Thread(target=_do_stream)
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
