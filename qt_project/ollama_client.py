#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama 本地大模型客户端
用于处理语音识别后的文本，生成回复
"""

import requests
import json
import threading
import time
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
             max_tokens: int = 256) -> str:
        """
        发送对话请求（极速模式）
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            max_tokens: 最大生成token数（默认256，足够生成完整回复）
            
        Returns:
            模型回复文本
        """
        try:
            # 构建请求数据（极速参数）
            data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,  # 限制生成长度
                    "temperature": 0.3,  # 低温度，更确定更快
                    "top_k": 20,  # 减少候选
                    "top_p": 0.8,
                    "repeat_penalty": 1.2,
                    "num_ctx": 1024,  # 减少上下文
                }
            }
            
            # 添加系统提示词（如果提供）
            if system_prompt:
                data["system"] = system_prompt
            
            # 发送请求
            response = requests.post(
                self.api_url,
                json=data,
                timeout=30  # 30秒超时，树莓派需要更长时间
            )
            
            if response.status_code == 200:
                result = response.json()
                reply = result.get("response", "").strip()
                return reply if reply else "抱歉，我没听清。"
            else:
                print(f"[OllamaClient] 请求失败: {response.status_code}")
                return "抱歉，我现在无法回答。"
                
        except requests.exceptions.ConnectionError:
            print("[OllamaClient] 连接失败，请检查 Ollama 服务是否运行")
            return "抱歉，我的大脑离线了。"
        except requests.exceptions.Timeout:
            print("[OllamaClient] 请求超时")
            return "抱歉，我反应慢了。"
        except Exception as e:
            print(f"[OllamaClient] 错误: {e}")
            return "抱歉，出错了。"
    
    def chat_async(self, prompt: str, callback: Callable[[str], None], 
                   system_prompt: str = None, max_tokens: int = 256):
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
                    max_tokens: int = 256):
        """
        流式对话（边生成边返回，更快响应）
        
        Args:
            prompt: 用户输入
            on_token: 收到每个token时的回调
            on_complete: 完成时的回调（接收完整文本）
            system_prompt: 系统提示词
            max_tokens: 最大生成长度（默认256，足够生成完整回复）
        """
        def _do_stream():
            try:
                print(f"[OllamaClient] 开始流式请求，模型: {self.model_name}, 提示: {prompt[:30]}...")
                
                data = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": True,  # 流式输出
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.5,  # 稍高一点，生成更快
                        "top_k": 40,
                        "top_p": 0.9,
                        "repeat_penalty": 1.1,
                        "num_ctx": 512,  # 进一步减小上下文
                        "num_batch": 256,  # 批处理大小
                        "num_thread": 4,  # 使用多线程
                    }
                }
                
                if system_prompt:
                    data["system"] = system_prompt
                    print(f"[OllamaClient] 使用系统提示词: {system_prompt[:50]}...")
                
                full_response = ""
                token_count = 0
                
                print("[OllamaClient] 发送请求...")
                response = requests.post(
                    self.api_url,
                    json=data,
                    stream=True,
                    timeout=60  # 60秒超时，长文本需要更多时间
                )
                print(f"[OllamaClient] 收到响应，状态码: {response.status_code}")
                
                # 实时显示模式：立即开始回调
                last_update_time = time.time()
                
                for line in response.iter_lines():
                    if line:
                        try:
                            line_str = line.decode('utf-8')
                            json_line = json.loads(line_str)
                            token = json_line.get("response", "")
                            
                            if token:
                                full_response += token
                                token_count += 1
                                # 立即回调每个token，实现快速显示
                                on_token(token)
                            
                            # 检查是否完成（done字段或done_reason字段）
                            if json_line.get("done", False) or json_line.get("done_reason"):
                                print(f"[OllamaClient] 生成完成，共 {token_count} 个token")
                                if json_line.get("done_reason"):
                                    print(f"[OllamaClient] 完成原因: {json_line.get('done_reason')}")
                                break
                        except Exception as parse_err:
                            # 记录解析错误但不中断流式输出
                            print(f"[OllamaClient] 解析行失败: {parse_err}, 行内容: {line[:100]}")
                
                print(f"[OllamaClient] 总token数: {token_count}")
                
                if not full_response.strip():
                    print("[OllamaClient] 警告: 回复为空")
                    full_response = "抱歉，我没听清。"
                else:
                    print(f"[OllamaClient] 完整回复: {full_response[:100]}...")
                    
                on_complete(full_response.strip())
                
            except requests.exceptions.Timeout:
                print("[OllamaClient] 流式请求超时（60秒）")
                print(f"[OllamaClient] 已生成内容长度: {len(full_response)} 字符")
                # 超时但已经有内容，返回已生成的内容
                if full_response.strip():
                    on_complete(full_response.strip())
                else:
                    on_complete("抱歉，我想得太久了，请再说一次。")
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
