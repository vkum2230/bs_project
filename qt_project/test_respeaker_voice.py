#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReSpeaker 2-Mic 语音测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("ReSpeaker 2-Mic 语音测试")
print("=" * 60)

# 测试 ReSpeaker 专用播放器
print("\n[测试] ReSpeakerVoicePlayer...")
try:
    from voice_driver.voice_respeaker import ReSpeakerVoicePlayer
    player = ReSpeakerVoicePlayer()
    
    print("\n[测试] 播放中文...")
    result = player.speak("你好，我是骑行小智", block=True)
    print(f"结果: {'成功' if result else '失败'}")
    
    if not result:
        print("\n[诊断] 检查系统配置...")
        print("1. 检查 espeak-ng 是否安装:")
        os.system("which espeak-ng || which espeak")
        
        print("\n2. 检查 PyAudio 是否安装:")
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            print(f"   PyAudio 版本: {pa.get_portaudio_version_text()}")
            print("   可用设备:")
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info['maxOutputChannels'] > 0:
                    print(f"     {i}: {info['name']}")
            pa.terminate()
        except Exception as e:
            print(f"   PyAudio 错误: {e}")
        
        print("\n3. 检查 ReSpeaker 驱动:")
        os.system("ls -la /proc/asound/ | grep -i seeed || echo 'ReSpeaker 驱动未加载'")
        os.system("aplay -l | grep -i seeed || echo '未找到 ReSpeaker 音频设备'")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
