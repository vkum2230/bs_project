#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户配置管理器 (ConfigManager)

职责：
- 保存用户偏好：心率上限、年龄、体重、单位、告警开关等
- 单例模式，启动时自动加载，修改后自动持久化
- JSON 文件存储在 ~/smartride/config.json
"""

import json
import os
from typing import Any, Dict, Optional


class ConfigManager:
    """用户配置管理器（单例）"""

    _instance: Optional["ConfigManager"] = None

    DEFAULTS: Dict[str, Any] = {
        "heart_rate_max": 180,
        "heart_rate_min": 50,
        "age": 30,
        "weight_kg": 70,
        "rear_dist_alert_m": 5.0,
        "unit_system": "metric",  # metric / imperial
        "auto_start_ride": False,
        "ble_whitelist": [],
        "alerts_enabled": {
            "rear_vehicle": True,
            "heart_rate": True,
            "fatigue": True,
            "fall": True,
        },
        "aliyun_tts_api_key": "sk-c6ec991c7d9d4fba8c95803fe55b47e6",
        "aliyun_tts_voice": "Maia",
        "aliyun_tts_model": "qwen3-tts-flash",
        "aliyun_bailian_api_key": "sk-77b02cb7cc3448509e84cc5b005ea87a",
        "aliyun_bailian_model": "qwen-turbo",
        "last_online_mode": True,  # True=online, False=offline
    }

    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config: Dict[str, Any] = {}
            cls._instance._path = os.path.expanduser("~/smartride/config.json")
            cls._instance.load()
        return cls._instance

    def load(self):
        """从磁盘加载配置，若不存在则使用默认配置并保存"""
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # 合并默认值，防止新增字段缺失
                self._config = dict(self.DEFAULTS)
                self._config.update(loaded)
                # 深度合并 alerts_enabled
                if "alerts_enabled" in loaded:
                    default_alerts = dict(self.DEFAULTS["alerts_enabled"])
                    default_alerts.update(loaded["alerts_enabled"])
                    self._config["alerts_enabled"] = default_alerts
            except Exception as e:
                print(f"[ConfigManager] 加载配置失败: {e}，使用默认配置")
                self._config = dict(self.DEFAULTS)
                self.save()
        else:
            self._config = dict(self.DEFAULTS)
            self.save()
            print(f"[ConfigManager] 首次运行，已创建默认配置: {self._path}")

    def save(self):
        """保存配置到磁盘"""
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigManager] 保存配置失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置项并自动保存"""
        self._config[key] = value
        self.save()

    def get_alert(self, alert_name: str) -> bool:
        """获取某个告警开关状态"""
        alerts = self._config.get("alerts_enabled", {})
        return alerts.get(alert_name, True)

    def set_alert(self, alert_name: str, enabled: bool):
        """设置某个告警开关状态"""
        alerts = self._config.get("alerts_enabled", {})
        alerts[alert_name] = enabled
        self._config["alerts_enabled"] = alerts
        self.save()

    def get_last_online_mode(self) -> bool:
        """获取上次保存的在线/离线模式"""
        return self._config.get("last_online_mode", True)

    def set_last_online_mode(self, online: bool):
        """保存在线/离线模式"""
        self._config["last_online_mode"] = online
        self.save()

    def all(self) -> Dict[str, Any]:
        """返回完整配置字典（只读建议，不要直接修改）"""
        return dict(self._config)


def get_config() -> ConfigManager:
    """便捷函数：获取配置管理器单例"""
    return ConfigManager()


if __name__ == "__main__":
    cfg = get_config()
    print("当前配置:", json.dumps(cfg.all(), indent=2, ensure_ascii=False))
    print("心率上限:", cfg.get("heart_rate_max"))
    print("后方告警开关:", cfg.get_alert("rear_vehicle"))
