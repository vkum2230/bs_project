#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一大模型客户端
根据在线/离线状态自动选择百炼（在线）或 Ollama（离线）
并自动注入实时骑行数据上下文
"""

from typing import Callable, Optional


class UnifiedLLMClient:
    """
    统一大模型客户端
    - 在线: 阿里云百炼（速度快，无需本地算力）
    - 离线: 本地 Ollama（不依赖网络）
    """

    def __init__(self,
                 bailian_client=None,
                 ollama_client=None,
                 force_offline: bool = False):
        """
        初始化统一客户端

        Args:
            bailian_client: 百炼在线客户端实例
            ollama_client: Ollama 本地客户端实例
            force_offline: 强制离线模式（不尝试在线模型）
        """
        self._bailian = bailian_client
        self._ollama = ollama_client
        self.force_offline = force_offline

    def _get_online_client(self):
        """获取在线客户端（如果可用）"""
        if self.force_offline or not self._bailian:
            return None
        return self._bailian

    def _get_offline_client(self):
        """获取离线客户端（如果可用）"""
        return self._ollama

    def _inject_ride_context(self, system_prompt: str = None) -> str:
        """注入骑行数据上下文到系统提示词"""
        try:
            from core.data_context import get_data_context
            ctx = get_data_context()
            ride_prompt = ctx.get_system_prompt_with_context(base_prompt=system_prompt)
            return ride_prompt
        except Exception as e:
            print(f"[UnifiedLLM] 注入骑行数据失败: {e}")
            return system_prompt or "你是骑行助手小智。"

    def chat(self, prompt: str, system_prompt: str = None,
             max_tokens: int = 128) -> str:
        """
        发送对话请求（非流式）

        在线 -> 百炼，离线 -> Ollama
        """
        enhanced_system = self._inject_ride_context(system_prompt)

        online = self._get_online_client()
        if online:
            print("[UnifiedLLM] 使用百炼在线模型")
            return online.chat(prompt, system_prompt=enhanced_system, max_tokens=max_tokens)

        offline = self._get_offline_client()
        if offline:
            print("[UnifiedLLM] 使用 Ollama 本地模型")
            return offline.chat(prompt, system_prompt=enhanced_system, max_tokens=max_tokens)

        print("[UnifiedLLM] 无可用模型")
        return "抱歉，我的大脑离线了。"

    def chat_stream(self, prompt: str,
                    on_token: Callable[[str], None],
                    on_complete: Callable[[str], None],
                    system_prompt: str = None,
                    max_tokens: int = 128):
        """
        流式对话（边生成边返回）

        在线 -> 百炼，离线 -> Ollama
        """
        enhanced_system = self._inject_ride_context(system_prompt)

        online = self._get_online_client()
        if online:
            print("[UnifiedLLM] 使用百炼在线模型（流式）")
            online.chat_stream(
                prompt=prompt,
                on_token=on_token,
                on_complete=on_complete,
                system_prompt=enhanced_system,
                max_tokens=max_tokens
            )
            return

        offline = self._get_offline_client()
        if offline:
            print("[UnifiedLLM] 使用 Ollama 本地模型（流式）")
            offline.chat_stream(
                prompt=prompt,
                on_token=on_token,
                on_complete=on_complete,
                system_prompt=enhanced_system,
                max_tokens=max_tokens
            )
            return

        print("[UnifiedLLM] 无可用模型")
        on_complete("抱歉，我的大脑离线了。")

    def check_available(self) -> bool:
        """检查是否有可用模型"""
        if self._get_online_client() and self._get_online_client().check_available():
            return True
        if self._get_offline_client() and self._get_offline_client().check_available():
            return True
        return False
