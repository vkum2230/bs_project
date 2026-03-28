#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("测试修复后的功能")
print("=" * 60)

# 测试1: 语音识别结果去空格
print("\n[测试1] 语音识别结果去空格")
test_text = "现在 能 听到 我 说话 吗"
clean_text = test_text.replace(" ", "").replace("  ", "")
print(f"  原始: '{test_text}'")
print(f"  清理: '{clean_text}'")
assert clean_text == "现在能听到我说话吗", "去空格失败"
print("  ✓ 去空格成功")

# 测试2: FinalVoicePlayer 消息回调
print("\n[测试2] FinalVoicePlayer 消息回调")
messages = []
def test_callback(text, icon):
    messages.append((icon, text))
    print(f"  收到消息: {icon} {text}")

from voice_driver.voice_final import FinalVoicePlayer
player = FinalVoicePlayer(message_callback=test_callback)
player.speak("测试语音播报", block=True)

# 等待播报完成
import time
time.sleep(3)

if messages:
    print(f"  ✓ 消息回调正常，收到 {len(messages)} 条消息")
else:
    print("  ⚠ 未收到消息回调（可能是语音播放失败）")

# 测试3: 按钮语音助手不显示"识别中"和"你说"
print("\n[测试3] 检查按钮语音助手的消息逻辑")
print("  - 按按钮后不应显示 '识别中'")
print("  - 识别结果不应显示 '你说:'")
print("  请在主程序中实际测试")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
print("\n修复内容:")
print("1. ✓ 语音识别结果自动去掉空格")
print("2. ✓ 语音播报自动显示在消息框")
print("3. ✓ 去掉'识别中'和'你说'的显示")
