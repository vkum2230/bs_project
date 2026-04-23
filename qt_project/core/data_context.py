#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
骑行数据上下文管理器
用于向大模型提供实时骑行数据
"""

import json
import os
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from core.protocol import SensorData


@dataclass
class RideData:
    """骑行数据结构"""
    speed: float = 0.0          # 速度 km/h
    power: float = 0.0          # 功率 W
    cadence: float = 0.0        # 踏频 rpm
    distance: float = 0.0       # 距离 km
    ride_time: int = 0          # 骑行时间秒
    slope: float = 0.0          # 坡度 %
    posture: int = 0            # 骑行姿态
    temperature: float = 0.0    # 温度 °C
    heart_rate: float = 0.0     # 心率 bpm
    rear_dist: float = 0.0      # 后方距离 m
    location: str = ""          # 当前位置/省份
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_context_string(self, all_fields: bool = False) -> str:
        """转换为自然语言描述

        Args:
            all_fields: 为 True 时包含所有字段（包括 0 值）
        """
        parts = []

        if all_fields or self.speed > 0:
            parts.append(f"当前速度{self.speed:.1f}公里每小时")
        if all_fields or self.power > 0:
            parts.append(f"功率{self.power:.0f}瓦")
        if all_fields or self.cadence > 0:
            parts.append(f"踏频{self.cadence:.0f}转每分钟")
        if all_fields or self.distance > 0:
            parts.append(f"已骑行{self.distance:.1f}公里")
        if all_fields or self.ride_time > 0:
            hours = self.ride_time // 3600
            minutes = (self.ride_time % 3600) // 60
            if hours > 0:
                parts.append(f"骑行时间{hours}小时{minutes}分钟")
            else:
                parts.append(f"骑行时间{minutes}分钟")
        if all_fields or self.slope != 0:
            prefix = "上坡" if self.slope > 0 else "下坡"
            parts.append(f"{prefix}坡度{abs(self.slope):.1f}%")
        if all_fields or self.posture != 0:
            parts.append("注意骑行姿态异常")
        if all_fields or self.temperature > 0:
            parts.append(f"环境温度{self.temperature:.1f}摄氏度")
        if all_fields or self.heart_rate > 0:
            parts.append(f"心率{self.heart_rate:.0f}次每分钟")
        if all_fields or self.rear_dist > 0:
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
        self._context_file = os.path.expanduser("~/smartride/current_ride_state.json")

    def save_to_file(self):
        """将当前骑行数据保存到文件，供LLM读取"""
        try:
            os.makedirs(os.path.dirname(self._context_file), exist_ok=True)
            with self._data_lock:
                data_dict = self._data.to_dict()
            with open(self._context_file, "w", encoding="utf-8") as f:
                json.dump(data_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[DataContext] 保存数据到文件失败: {e}")
    
    def update_data(self, **kwargs):
        """更新数据"""
        with self._data_lock:
            for key, value in kwargs.items():
                if hasattr(self._data, key):
                    old_value = getattr(self._data, key)
                    setattr(self._data, key, value)
                    if old_value != value:
                        print(f"[DataContext] 更新 {key}: {old_value} -> {value}")
    
    def update_from_sensor(self, sensor: SensorData):
        """从协议层 SensorData 批量更新上下文"""
        update_dict = {
            "speed": sensor.speed,
            "power": sensor.power,
            "cadence": sensor.cadence,
            "distance": sensor.distance,
            "ride_time": sensor.ride_time,
            "slope": sensor.slope,
            "posture": sensor.zt_flag,
            "temperature": sensor.temperature,
            "heart_rate": sensor.heart_rate,
            "rear_dist": sensor.rear_dist,
        }
        self.update_data(**update_dict)

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
        生成系统提示词（不再包含实时数据，数据将放在user prompt中）
        """
        base = base_prompt or "你是骑行助手小智，一个专业的骑行导航助手。"

        return f"""{base}

【骑行场景】
用户正在户外骑行。你每次回答问题时，用户都会在消息开头附上他的实时骑行数据。请严格根据这些数据回答，不要编造任何数据。

【回答要求】
1. 请严格根据用户提供的实时数据回答，绝对不要编造任何数据。
2. 如果用户询问具体数值（如速度、心率、功率等），请直接给出当前数值，不要绕弯子。
3. 回答要简洁明了，适合骑行过程中听取，控制在100字以内。
4. 不要加星号、下划线等Markdown格式符号。
5. 如果数据为0，说明该传感器暂无读数或用户尚未开始骑行。"""


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
