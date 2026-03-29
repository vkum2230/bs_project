#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音测试脚本
"""

import sys
import os

# 添加到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_driver import VoicePlayer, speak


def main():
    print("=" * 60)
    print("SMART RIDE 语音测试")
    print("=" * 60)
    
    # 创建播放器
    print("\n初始化语音播放器...")
    try:
        player = VoicePlayer()
        print(f"使用引擎: {player.engine}")
    except Exception as e:
        print(f"初始化失败: {e}")
        return 1
    
    # 测试播报
    print("\n测试1: 中文播报")
    result1 = player.speak("你好，我是骑行小智", block=True)
    print(f"结果: {'成功' if result1 else '失败'}")
    
    if not result1:
        print("\n建议修复步骤:")
        print("1. 运行修复脚本: ./fix_audio.sh")
        print("2. 检查音频设备: aplay -l")
        print("3. 重新登录系统以应用权限更改")
        return 1
    
    print("\n测试2: 英文播报")
    result2 = player.speak("Hello, I am Bike Assistant", block=True)
    print(f"结果: {'成功' if result2 else '失败'}")
    
    print("\n测试3: 使用便捷函数")
    result3 = speak("测试完成", block=True)
    print(f"结果: {'成功' if result3 else '失败'}")
    
    print("\n" + "=" * 60)
    if all([result1, result2, result3]):
        print("✓ 所有测试通过！")
        return 0
    else:
        print("✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
