#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
骑行数据上下文管理器
用于向大模型提供实时骑行数据
"""

import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class RideData:
    """骑行数据结构"""
    speed: float = 0.0          # 速度 km/h
    power: float = 0.0          # 功率 W
    cadence: float = 0.0        # 踏频 rpm
    distance: float = 0.0       # 距离 km
    ride_time: int = 0          # 骑行时间秒
    slope: float = 0.0          # 坡度 %
    temperature: float = 0.0    # 温度 °C
    heart_rate: float = 0.0     # 心率 bpm
    rear_dist: float = 0.0      # 后方距离 m
    location: str = ""          # 当前位置/省份
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_context_string(self) -> str:
        """转换为自然语言描述"""
        parts = []
        
        if self.speed > 0:
            parts.append(f"当前速度{self.speed:.1f}公里每小时")
        if self.power > 0:
            parts.append(f"功率{self.power:.0f}瓦")
        if self.cadence > 0:
            parts.append(f"踏频{self.cadence:.0f}转每分钟")
        if self.distance > 0:
            parts.append(f"已骑行{self.distance:.1f}公里")
        if self.ride_time > 0:
            hours = self.ride_time // 3600
            minutes = (self.ride_time % 3600) // 60
            if hours > 0:
                parts.append(f"骑行时间{hours}小时{minutes}分钟")
            else:
                parts.append(f"骑行时间{minutes}分钟")
        if self.slope != 0:
            prefix = "上坡" if self.slope > 0 else "下坡"
            parts.append(f"{prefix}坡度{abs(self.slope):.1f}%")
        if self.temperature > 0:
            parts.append(f"环境温度{self.temperature:.1f}摄氏度")
        if self.heart_rate > 0:
            parts.append(f"心率{self.heart_rate:.0f}次每分钟")
        if self.rear_dist > 0:
            if self.rear_dist < 5:
                parts.append(f"后方有车辆接近，距离仅{self.rear_dist:.1f}米，请注意安全")
            else:
                parts.append(f"后方车辆距离{self.rear_dist:.1f}米")
        if self.location:
            parts.append(f"当前位置在{self.location}")
        
        if parts:
            return "当前骑行数据：" + "，".join(parts) + "。"
        return "暂无骑行数据。"


class DataContextManager:
    """
    数据上下文管理器 - 单例模式
    用于存储和提供实时骑行数据给大模型
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance
    
    def _init(self):
        self._data = RideData()
        self._data_lock = threading.Lock()
        self._callbacks = []
    
    def update_data(self, **kwargs):
        """更新数据"""
        with self._data_lock:
            for key, value in kwargs.items():
                if hasattr(self._data, key):
                    old_value = getattr(self._data, key)
                    setattr(self._data, key, value)
                    if old_value != value:
                        print(f"[DataContext] 更新 {key}: {old_value} -> {value}")
    
    def get_data(self) -> RideData:
        """获取当前数据副本"""
        with self._data_lock:
            return RideData(**self._data.to_dict())
    
    def get_context_string(self) -> str:
        """获取数据上下文描述"""
        with self._data_lock:
            return self._data.to_context_string()
    
    def register_callback(self, callback):
        """注册数据更新回调"""
        self._callbacks.append(callback)
    
    def get_system_prompt_with_context(self, base_prompt: str = None) -> str:
        """
        生成带数据上下文的系统提示词
        """
        context = self.get_context_string()
        
        base = base_prompt or "你是骑行助手小智，一个专业的骑行导航助手。"
        
        return f"""{base}

{context}

你可以根据上述实时骑行数据回答用户问题。数据会自动更新。
回答要简洁明了，适合骑行过程中听取。
不要加星号、下划线等Markdown格式符号。"""


# 全局实例
data_context = DataContextManager()


def get_data_context() -> DataContextManager:
    """获取数据上下文管理器实例"""
    return data_context


if __name__ == "__main__":
    # 测试
    ctx = get_data_context()
    
    # 更新一些数据
    ctx.update_data(speed=25.5, power=180, cadence=85, distance=12.3, 
                   slope=2.5, temperature=28, heart_rate=145)
    
    print("数据上下文:")
    print(ctx.get_context_string())
    print("\n系统提示词:")
    print(ctx.get_system_prompt_with_context())
