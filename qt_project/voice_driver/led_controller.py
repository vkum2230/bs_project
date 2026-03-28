#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LED 控制器 - ReSpeaker 2-Mic 语音模块的 APA102 LED 控制
"""

import time
import threading
from typing import Tuple, Optional


class LEDController:
    """APA102 LED 控制器"""
    
    # 预定义颜色
    COLOR_OFF = (0, 0, 0)
    COLOR_RED = (255, 0, 0)
    COLOR_GREEN = (0, 255, 0)
    COLOR_BLUE = (0, 0, 255)
    COLOR_YELLOW = (255, 255, 0)
    COLOR_CYAN = (0, 255, 255)
    COLOR_MAGENTA = (255, 0, 255)
    COLOR_WHITE = (255, 255, 255)
    COLOR_ORANGE = (255, 165, 0)
    
    def __init__(self, num_leds: int = 3, brightness: int = 31):
        """
        初始化 LED 控制器
        
        Args:
            num_leds: LED 数量（ReSpeaker 2-Mic 有 3 个 LED）
            brightness: 亮度 (0-31)
        """
        self.num_leds = num_leds
        self.brightness = brightness
        self._running = False
        self._pattern_thread: Optional[threading.Thread] = None
        
        try:
            import spidev
            self.spi = spidev.SpiDev()
            self.spi.open(0, 1)  # SPI0, CE1
            self.spi.max_speed_hz = 500000
            self.spi.mode = 0
            self._spi_available = True
        except Exception as e:
            print(f"[LEDController] SPI 初始化失败: {e}")
            self._spi_available = False
            self.spi = None
        
        # 初始化 LED 状态
        self._current_colors = [(0, 0, 0)] * num_leds
        self.off()
    
    def _send_data(self, data: list):
        """发送 SPI 数据"""
        if self._spi_available and self.spi:
            try:
                self.spi.xfer2(data)
            except Exception as e:
                print(f"[LEDController] SPI 传输失败: {e}")
    
    def _build_frame(self, colors: list) -> list:
        """构建 APA102 数据帧"""
        # 起始帧
        frame = [0x00, 0x00, 0x00, 0x00]
        
        # LED 数据 (亮度 + BGR)
        brightness_byte = 0xE0 | (self.brightness & 0x1F)
        for r, g, b in colors:
            frame.extend([brightness_byte, b, g, r])
        
        # 结束帧
        frame.extend([0xFF, 0xFF, 0xFF, 0xFF])
        
        return frame
    
    def set_pixel(self, index: int, color: Tuple[int, int, int]):
        """
        设置单个 LED 颜色
        
        Args:
            index: LED 索引 (0-2)
            color: (R, G, B) 颜色元组
        """
        if 0 <= index < self.num_leds:
            self._current_colors[index] = color
            self._send_data(self._build_frame(self._current_colors))
    
    def set_all(self, color: Tuple[int, int, int]):
        """
        设置所有 LED 颜色
        
        Args:
            color: (R, G, B) 颜色元组
        """
        self._current_colors = [color] * self.num_leds
        self._send_data(self._build_frame(self._current_colors))
    
    def off(self):
        """关闭所有 LED"""
        self._current_colors = [(0, 0, 0)] * self.num_leds
        self._send_data(self._build_frame(self._current_colors))
    
    def set_brightness(self, brightness: int):
        """
        设置亮度
        
        Args:
            brightness: 亮度值 (0-31)
        """
        self.brightness = max(0, min(31, brightness))
        self._send_data(self._build_frame(self._current_colors))
    
    def start_pattern(self, pattern: str = "breath", color: Tuple[int, int, int] = None):
        """
        启动 LED 动画模式
        
        Args:
            pattern: 动画模式 ("breath", "blink", "rainbow")
            color: 基础颜色
        """
        self.stop_pattern()
        self._running = True
        
        if pattern == "breath":
            self._pattern_thread = threading.Thread(
                target=self._breath_pattern, 
                args=(color or self.COLOR_BLUE,)
            )
        elif pattern == "blink":
            self._pattern_thread = threading.Thread(
                target=self._blink_pattern, 
                args=(color or self.COLOR_RED,)
            )
        elif pattern == "rainbow":
            self._pattern_thread = threading.Thread(target=self._rainbow_pattern)
        
        if self._pattern_thread:
            self._pattern_thread.daemon = True
            self._pattern_thread.start()
    
    def stop_pattern(self):
        """停止 LED 动画"""
        self._running = False
        if self._pattern_thread and self._pattern_thread.is_alive():
            self._pattern_thread.join(timeout=1)
    
    def _breath_pattern(self, color: Tuple[int, int, int]):
        """呼吸灯效果"""
        r, g, b = color
        while self._running:
            for i in range(32):
                if not self._running:
                    break
                ratio = i / 31.0
                self.set_all((int(r * ratio), int(g * ratio), int(b * ratio)))
                time.sleep(0.05)
            for i in range(31, -1, -1):
                if not self._running:
                    break
                ratio = i / 31.0
                self.set_all((int(r * ratio), int(g * ratio), int(b * ratio)))
                time.sleep(0.05)
    
    def _blink_pattern(self, color: Tuple[int, int, int]):
        """闪烁效果"""
        while self._running:
            self.set_all(color)
            time.sleep(0.5)
            if not self._running:
                break
            self.off()
            time.sleep(0.5)
    
    def _rainbow_pattern(self):
        """彩虹效果"""
        def hsv_to_rgb(h, s, v):
            """HSV 转 RGB"""
            import math
            c = v * s
            x = c * (1 - abs((h / 60) % 2 - 1))
            m = v - c
            
            if h < 60:
                r, g, b = c, x, 0
            elif h < 120:
                r, g, b = x, c, 0
            elif h < 180:
                r, g, b = 0, c, x
            elif h < 240:
                r, g, b = 0, x, c
            elif h < 300:
                r, g, b = x, 0, c
            else:
                r, g, b = c, 0, x
            
            return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))
        
        while self._running:
            for hue in range(0, 360, 5):
                if not self._running:
                    break
                r, g, b = hsv_to_rgb(hue, 1, 1)
                self.set_all((r, g, b))
                time.sleep(0.05)
    
    def close(self):
        """关闭控制器"""
        self.stop_pattern()
        self.off()
        if self.spi:
            self.spi.close()


# 便捷函数
def get_led_controller() -> LEDController:
    """获取 LED 控制器实例"""
    return LEDController()


if __name__ == "__main__":
    # 测试
    led = LEDController()
    
    print("测试红色...")
    led.set_all(LEDController.COLOR_RED)
    time.sleep(1)
    
    print("测试绿色...")
    led.set_all(LEDController.COLOR_GREEN)
    time.sleep(1)
    
    print("测试蓝色...")
    led.set_all(LEDController.COLOR_BLUE)
    time.sleep(1)
    
    print("测试呼吸灯...")
    led.start_pattern("breath", LEDController.COLOR_CYAN)
    time.sleep(5)
    
    print("关闭...")
    led.close()
