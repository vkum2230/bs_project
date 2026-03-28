#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音系统调试脚本
"""

import os
import sys
import subprocess

# 确保 PATH 包含 ~/.local/bin
os.environ["PATH"] = os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", "")

print("=" * 60)
print("语音系统调试")
print("=" * 60)

# 1. 检查 edge-tts
print("\n[1] 检查 edge-tts")
print(f"PATH: {os.environ['PATH'][:80]}...")

edge_paths = [
    os.path.expanduser("~/.local/bin/edge-tts"),
    "/usr/local/bin/edge-tts",
    "/usr/bin/edge-tts",
]

edge_found = False
for path in edge_paths:
    if os.path.isfile(path):
        print(f"  ✓ 找到: {path}")
        edge_found = True
        break

if not edge_found:
    print("  ✗ 未找到 edge-tts 文件")

# 尝试运行
try:
    result = subprocess.run(
        ["edge-tts", "--version"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        print(f"  ✓ edge-tts 可运行: {result.stdout.strip()}")
    else:
        print(f"  ✗ edge-tts 运行失败: {result.stderr}")
except FileNotFoundError:
    print("  ✗ edge-tts 命令未找到（不在 PATH 中）")
except Exception as e:
    print(f"  ✗ edge-tts 错误: {e}")

# 2. 检查网络
print("\n[2] 检查网络连接")
try:
    import socket
    socket.setdefaulttimeout(3)
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
    print("  ✓ 网络连接正常")
    has_network = True
except:
    print("  ✗ 网络连接失败（Edge-TTS 需要网络）")
    has_network = False

# 3. 测试语音生成
print("\n[3] 测试语音生成")
if has_network:
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            mp3_path = f.name
        
        print("  生成测试语音...")
        result = subprocess.run(
            ["edge-tts", "--voice", "zh-CN-XiaoxiaoNeural", 
             "--text", "你好，我是骑行小智",
             "--write-media", mp3_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            size = os.path.getsize(mp3_path)
            print(f"  ✓ 语音生成成功: {size} bytes")
            
            # 测试播放
            print("  播放测试...")
            play_result = subprocess.run(
                ["mpg123", mp3_path],
                capture_output=True,
                timeout=10
            )
            if play_result.returncode == 0:
                print("  ✓ 播放成功！")
            else:
                print(f"  ✗ 播放失败（mpg123）")
                # 尝试 ffplay
                play_result2 = subprocess.run(
                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", mp3_path],
                    capture_output=True,
                    timeout=10
                )
                if play_result2.returncode == 0:
                    print("  ✓ 播放成功（ffplay）")
                else:
                    print(f"  ✗ 播放失败（ffplay）")
        else:
            print(f"  ✗ 语音生成失败: {result.stderr[:100]}")
        
        # 清理
        if os.path.exists(mp3_path):
            os.remove(mp3_path)
            
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
else:
    print("  跳过（无网络）")

# 4. 测试 SmartVoicePlayer
print("\n[4] 测试 SmartVoicePlayer")
try:
    from voice_driver.voice_smart import SmartVoicePlayer
    
    player = SmartVoicePlayer()
    status = player.get_status()
    print(f"  引擎: {status['engine']}")
    print(f"  网络: {'在线' if status['has_network'] else '离线'}")
    print(f"  语音: {status['voice']}")
    
    print("\n  播放测试语音...")
    player.speak("你好，我是骑行小智", block=True)
    print("  测试完成")
    
except Exception as e:
    print(f"  ✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("调试完成")
print("=" * 60)
