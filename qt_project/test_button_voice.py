#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按钮语音功能测试
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("按钮语音功能测试")
print("=" * 60)

# 1. 测试按钮
print("\n[测试1] 按钮检测")
print("请按住 ReSpeaker 上的按钮...")

try:
    from voice_driver import ButtonHandler, ButtonEvent
    
    pressed = False
    released = False
    
    def on_press():
        global pressed
        pressed = True
        print("✓ 按钮按下事件触发")
    
    def on_release():
        global released
        released = True
        print("✓ 按钮释放事件触发")
    
    btn = ButtonHandler(pin=17)
    btn.on(ButtonEvent.PRESS, on_press)
    btn.on(ButtonEvent.RELEASE, on_release)
    btn.start()
    
    # 等待 5 秒
    for i in range(50):
        if pressed and released:
            break
        time.sleep(0.1)
    
    btn.stop()
    
    if pressed and released:
        print("✓ 按钮工作正常")
    else:
        print("✗ 按钮测试失败，请检查 GPIO 17 连接")
        
except Exception as e:
    print(f"✗ 按钮测试失败: {e}")

# 2. 测试录音
print("\n[测试2] 录音功能")
print("3秒后开始录音，请说话...")

try:
    from voice_driver.voice_recorder import VoiceRecorder
    
    recorder = VoiceRecorder()
    
    time.sleep(3)
    
    if recorder.start_recording():
        print("✓ 录音开始")
        print("  录音中... (3秒)")
        time.sleep(3)
        
        wav_path = recorder.stop_recording()
        if wav_path:
            print(f"✓ 录音完成: {wav_path}")
            print(f"  文件大小: {os.path.getsize(wav_path)} bytes")
        else:
            print("✗ 录音失败")
    else:
        print("✗ 录音启动失败")
        
except Exception as e:
    print(f"✗ 录音测试失败: {e}")
    import traceback
    traceback.print_exc()

# 3. 测试语音识别
print("\n[测试3] 语音识别")

try:
    from voice_driver.voice_recorder import VoiceRecognizer
    
    recognizer = VoiceRecognizer()
    
    # 使用刚才的录音
    if 'wav_path' in dir() and wav_path and os.path.exists(wav_path):
        print("识别中...")
        result = recognizer.recognize(wav_path)
        print(f"识别结果: {result.text}")
        print(f"置信度: {result.confidence:.2f}")
    else:
        print("跳过（没有录音文件）")
        
except Exception as e:
    print(f"✗ 识别测试失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
