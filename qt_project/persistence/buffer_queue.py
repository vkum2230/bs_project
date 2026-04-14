#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
断连缓存队列

用途：
- 当 BLE 和 WiFi 都断开时，缓存实时数据
- 重连后按时间顺序批量补发给 App

策略：
- 内存缓存最近 30 分钟或 5000 条数据
- 超出限制时采用滑动窗口丢弃最旧数据
"""

import json
import time
from collections import deque
from typing import List, Dict, Any

from core.protocol import AppRealtimeData


class BufferQueue:
    """断连数据缓存队列"""

    def __init__(self, max_items: int = 5000, max_age_seconds: float = 1800):
        """
        Args:
            max_items: 最大缓存条目数
            max_age_seconds: 最大缓存时间（默认 30 分钟）
        """
        self.max_items = max_items
        self.max_age_seconds = max_age_seconds
        self._buffer: deque[Dict[str, Any]] = deque()

    def push(self, data: AppRealtimeData):
        """缓存一条数据"""
        self._buffer.append(data.to_dict())
        self._cleanup()

    def push_many(self, data_list: List[AppRealtimeData]):
        """批量缓存"""
        for d in data_list:
            self._buffer.append(d.to_dict())
        self._cleanup()

    def _cleanup(self):
        """清理过期和超量数据"""
        now = time.time()
        cutoff = now - self.max_age_seconds

        # 移除过期数据
        while self._buffer and self._buffer[0].get("timestamp", 0) < cutoff:
            self._buffer.popleft()

        # 移除超量数据（保留最新的）
        while len(self._buffer) > self.max_items:
            self._buffer.popleft()

    def drain(self) -> List[Dict[str, Any]]:
        """取出所有缓存数据并清空队列"""
        items = list(self._buffer)
        self._buffer.clear()
        return items

    def peek(self) -> List[Dict[str, Any]]:
        """查看缓存数据（不清空）"""
        return list(self._buffer)

    def is_empty(self) -> bool:
        return len(self._buffer) == 0

    def size(self) -> int:
        return len(self._buffer)

    def get_summary(self) -> Dict[str, Any]:
        """获取缓存摘要"""
        if not self._buffer:
            return {"count": 0, "duration": 0, "from": None, "to": None}
        first_ts = self._buffer[0].get("timestamp", 0)
        last_ts = self._buffer[-1].get("timestamp", 0)
        return {
            "count": len(self._buffer),
            "duration": int(last_ts - first_ts),
            "from": first_ts,
            "to": last_ts,
        }
