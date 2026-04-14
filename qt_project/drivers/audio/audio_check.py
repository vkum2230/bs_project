#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频设备诊断工具
"""

import subprocess
import os
import sys


def run_cmd(cmd, capture=True):
    """运行命令并返回输出"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=capture, 
            text=True,
            timeout=5
        )
        return result.stdout if capture else ""
    except Exception as e:
        return f"Error: {e}"


def check_audio():
    """检查音频系统状态"""
    print("=" * 60)
    print("音频设备诊断")
    print("=" * 60)
    
    # 1. 检查用户是否在 audio 组
    print("\n1. 用户权限:")
    user = run_cmd("whoami").strip()
    groups = run_cmd("groups")
    print(f"   当前用户: {user}")
    print(f"   用户组: {groups}")
    if "audio" in groups:
        print("   ✓ 用户在 audio 组")
    else:
        print("   ✗ 用户不在 audio 组，请运行: sudo usermod -a -G audio $USER")
    
    # 2. 检查音频设备
    print("\n2. 音频设备:")
    devices = run_cmd("aplay -l")
    print(devices if devices else "   未找到音频设备")
    
    # 3. 检查默认设备
    print("\n3. 默认音频设备:")
    default = run_cmd("aplay -L | grep -A2 default")
    print(default if default else "   未设置默认设备")
    
    # 4. 检查 PulseAudio 状态
    print("\n4. PulseAudio 状态:")
    pulse = run_cmd("pactl info 2>/dev/null || echo 'PulseAudio 未运行'")
    print(pulse)
    
    # 5. 检查 ALSA 混音器
    print("\n5. ALSA 混音器状态:")
    mixer = run_cmd("amixer sget Master 2>/dev/null || echo '无法获取混音器状态'")
    print(mixer[:500] + "..." if len(mixer) > 500 else mixer)
    
    # 6. 检查占用音频的进程
    print("\n6. 占用音频的进程:")
    procs = run_cmd("lsof /dev/snd/* 2>/dev/null || fuser -v /dev/snd/* 2>&1 || echo '无进程占用音频设备'")
    print(procs if procs else "   无")
    
    # 7. 测试音频文件
    print("\n7. 生成测试音频...")
    test_wav = "/tmp/test_audio.wav"
    
    # 使用 speaker-test 生成测试音
    print("   尝试播放测试音...")
    print("   运行: speaker-test -t sine -f 1000 -c 2 -s 1 -d 1")
    result = run_cmd("speaker-test -t sine -f 1000 -c 2 -s 1 -d 1 2>&1", capture=False)
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)
    
    # 8. 可能的解决方案
    print("\n可能的解决方案:")
    print("1. 如果是权限问题: sudo usermod -a -G audio $USER")
    print("2. 如果是设备被占用: killall pulseaudio; pulseaudio --start")
    print("3. 如果是配置问题: rm -rf ~/.config/pulse; pulseaudio --start")
    print("4. 尝试使用具体设备: aplay -D plughw:0,0 your_file.wav")


def fix_audio_issues():
    """尝试修复音频问题"""
    print("\n尝试自动修复...")
    
    # 1. 重启 PulseAudio
    print("1. 重启 PulseAudio...")
    run_cmd("pulseaudio -k 2>/dev/null; sleep 1; pulseaudio --start 2>/dev/null", capture=False)
    
    # 2. 释放音频设备
    print("2. 释放音频设备...")
    run_cmd("sudo fuser -k /dev/snd/* 2>/dev/null", capture=False)
    
    # 3. 设置默认音量
    print("3. 设置默认音量...")
    run_cmd("amixer set Master 80% unmute 2>/dev/null", capture=False)
    run_cmd("amixer set PCM 80% unmute 2>/dev/null", capture=False)
    
    print("修复完成，请再次运行诊断检查")


if __name__ == "__main__":
    check_audio()
    
    print("\n是否尝试自动修复? (y/n): ", end="")
    try:
        response = input().strip().lower()
        if response == 'y':
            fix_audio_issues()
    except:
        pass
