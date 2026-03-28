#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按钮处理器 - ReSpeaker 2-Mic 语音模块的按钮控制
"""

import threading
import time
from typing import Callable, Optional
from enum import Enum


class ButtonEvent(Enum):
    """按钮事件类型"""
    PRESS = "press"           # 按下
    RELEASE = "release"       # 释放
    CLICK = "click"           # 单击
    DOUBLE_CLICK = "double"   # 双击
    LONG_PRESS = "long"       # 长按


class ButtonHandler:
    """按钮处理器 - 支持单击、双击、长按检测"""
    
    def __init__(self, pin: int = 17, 
                 pull_up: bool = True,
                 long_press_ms: int = 800,
                 double_click_ms: int = 300):
        """
        初始化按钮处理器
        
        Args:
            pin: GPIO 引脚号
            pull_up: 是否启用上拉电阻
            long_press_ms: 长按阈值（毫秒）
            double_click_ms: 双击阈值（毫秒）
        """
        self.pin = pin
        self.long_press_ms = long_press_ms
        self.double_click_ms = double_click_ms
        
        self._callbacks: dict = {
            ButtonEvent.PRESS: [],
            ButtonEvent.RELEASE: [],
            ButtonEvent.CLICK: [],
            ButtonEvent.DOUBLE_CLICK: [],
            ButtonEvent.LONG_PRESS: []
        }
        
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # 状态变量
        self._last_state = None
        self._last_press_time = 0
        self._click_count = 0
        self._is_long_press = False
        
        try:
            from gpiozero import DigitalInputDevice
            self.button = DigitalInputDevice(pin=pin, pull_up=pull_up)
            self._gpio_available = True
        except Exception as e:
            print(f"[ButtonHandler] GPIO 初始化失败: {e}")
            self.button = None
            self._gpio_available = False
    
    def on(self, event: ButtonEvent, callback: Callable):
        """
        注册按钮事件回调
        
        Args:
            event: 事件类型
            callback: 回调函数
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def off(self, event: ButtonEvent = None, callback: Callable = None):
        """
        移除按钮事件回调
        
        Args:
            event: 事件类型（None 表示所有事件）
            callback: 回调函数（None 表示所有回调）
        """
        if event is None:
            events = list(self._callbacks.keys())
        else:
            events = [event]
        
        for e in events:
            if callback is None:
                self._callbacks[e] = []
            else:
                self._callbacks[e] = [cb for cb in self._callbacks[e] if cb != callback]
    
    def _trigger(self, event: ButtonEvent):
        """触发事件回调"""
        for callback in self._callbacks.get(event, []):
            try:
                callback()
            except Exception as e:
                print(f"[ButtonHandler] 回调执行错误: {e}")
    
    def start(self):
        """启动按钮监控"""
        if not self._gpio_available:
            print("[ButtonHandler] GPIO 不可用，无法启动")
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        print(f"[ButtonHandler] 按钮监控已启动 (GPIO {self.pin})")
    
    def stop(self):
        """停止按钮监控"""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1)
    
    def _monitor_loop(self):
        """按钮监控循环"""
        current_state = self.button.value
        
        while self._running:
            try:
                new_state = self.button.value
                current_time = time.time() * 1000  # 毫秒
                
                # 状态变化检测
                if new_state != current_state:
                    if new_state == 1:  # 按下
                        self._trigger(ButtonEvent.PRESS)
                        self._last_press_time = current_time
                        self._is_long_press = False
                    else:  # 释放
                        self._trigger(ButtonEvent.RELEASE)
                        
                        if not self._is_long_press:
                            self._click_count += 1
                            
                            # 检测双击
                            if self._click_count == 2:
                                self._trigger(ButtonEvent.DOUBLE_CLICK)
                                self._click_count = 0
                            else:
                                # 延迟检测单击
                                time.sleep(self.double_click_ms / 1000.0)
                                if self._click_count == 1:
                                    self._trigger(ButtonEvent.CLICK)
                                    self._click_count = 0
                    
                    current_state = new_state
                
                # 长按检测
                if current_state == 1 and not self._is_long_press:
                    press_duration = current_time - self._last_press_time
                    if press_duration >= self.long_press_ms:
                        self._is_long_press = True
                        self._trigger(ButtonEvent.LONG_PRESS)
                
                time.sleep(0.01)  # 10ms 轮询
                
            except Exception as e:
                print(f"[ButtonHandler] 监控循环错误: {e}")
                time.sleep(0.1)
    
    def is_pressed(self) -> bool:
        """检查按钮是否按下"""
        if self._gpio_available and self.button:
            return self.button.value == 1
        return False
    
    def close(self):
        """关闭处理器"""
        self.stop()
        if self.button:
            self.button.close()


def test_button():
    """测试按钮功能"""
    handler = ButtonHandler()
    
    def on_press():
        print("[测试] 按钮按下")
    
    def on_release():
        print("[测试] 按钮释放")
    
    def on_click():
        print("[测试] 单击")
    
    def on_double():
        print("[测试] 双击")
    
    def on_long():
        print("[测试] 长按")
    
    handler.on(ButtonEvent.PRESS, on_press)
    handler.on(ButtonEvent.RELEASE, on_release)
    handler.on(ButtonEvent.CLICK, on_click)
    handler.on(ButtonEvent.DOUBLE_CLICK, on_double)
    handler.on(ButtonEvent.LONG_PRESS, on_long)
    
    handler.start()
    
    print("按 Ctrl+C 退出...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n退出...")
    finally:
        handler.close()


if __name__ == "__main__":
    test_button()
