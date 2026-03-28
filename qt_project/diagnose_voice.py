#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音系统诊断脚本
"""

import subprocess
import os
import sys


def run_cmd(cmd, shell=True, timeout=5):
    """运行命令"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def diagnose():
    """诊断音频系统"""
    
    print_section("ReSpeaker 2-Mic 语音诊断")
    
    # 1. 检查 ReSpeaker 驱动
    print_section("1. ReSpeaker 驱动状态")
    if os.path.exists("/proc/asound/seeed2micvoicec"):
        print("✓ ReSpeaker 驱动目录存在")
    else:
        print("✗ ReSpeaker 驱动目录不存在")
    
    code, out, err = run_cmd("aplay -l | grep -i seeed")
    if out:
        print(f"✓ ReSpeaker 设备:\n{out}")
    else:
        print("✗ 未找到 ReSpeaker 音频设备")
    
    # 2. 检查声卡
    print_section("2. 声卡列表")
    code, out, err = run_cmd("aplay -l")
    print(out if out else "无输出")
    
    # 3. 检查音频进程
    print_section("3. 占用音频的进程")
    code, out, err = run_cmd("lsof /dev/snd/* 2>/dev/null | head -20")
    if out:
        print(out)
    else:
        print("无进程占用音频设备")
    
    # 4. 检查 TTS 命令
    print_section("4. TTS 引擎")
    
    for cmd in ["espeak-ng", "espeak", "festival"]:
        code, out, err = run_cmd(f"which {cmd}")
        if code == 0:
            print(f"✓ {cmd}: {out.strip()}")
            # 测试版本
            code2, out2, err2 = run_cmd(f"{cmd} --version 2>&1 | head -1")
            print(f"  版本: {out2.strip()}")
        else:
            print(f"✗ {cmd}: 未安装")
    
    # 5. 测试音频播放
    print_section("5. 音频播放测试")
    
    # 生成测试音
    test_wav = "/tmp/test_beep.wav"
    
    # 使用 sox 生成测试音
    code, out, err = run_cmd(f"sox -n -r 22050 -c 1 {test_wav} synth 1 sine 1000 2>&1")
    if code != 0:
        # 尝试使用 dd 生成简单的 WAV
        run_cmd(f"python3 -c \"
import struct
import wave
with wave.open('{test_wav}', 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(22050)
    for i in range(22050):
        val = int(32767 * 0.5 * (1 if (i // 25) % 2 else -1))
        w.writeframes(struct.pack('<h', val))
\"")
    
    if os.path.exists(test_wav):
        print("✓ 测试音频文件已生成")
        
        # 尝试播放
        print("\n尝试播放测试音频...")
        devices = [
            "hw:0,0",
            "hw:1,0", 
            "hw:2,0",
            "default",
            "plughw:0,0",
            "plughw:1,0",
        ]
        
        for dev in devices:
            print(f"\n  测试设备 {dev}...")
            code, out, err = run_cmd(f"aplay -D {dev} -d 1 {test_wav} 2>&1", timeout=3)
            if code == 0:
                print(f"  ✓ 设备 {dev} 可用！")
            else:
                err_str = err if err else out
                if "Unknown error 524" in err_str:
                    print(f"  ✗ 设备 {dev}: 被占用 (Error 524)")
                elif "No such file" in err_str:
                    print(f"  - 设备 {dev}: 不存在")
                else:
                    print(f"  ✗ 设备 {dev}: {err_str[:100]}")
    else:
        print("✗ 无法生成测试音频文件")
    
    # 6. 测试 TTS
    print_section("6. TTS 测试")
    
    # 使用 espeak-ng
    code, out, err = run_cmd("espeak-ng -v zh '测试' -w /tmp/test_tts.wav 2>&1")
    if code == 0 and os.path.exists("/tmp/test_tts.wav"):
        print("✓ espeak-ng 可生成语音文件")
        
        # 尝试播放
        code2, out2, err2 = run_cmd("aplay /tmp/test_tts.wav 2>&1", timeout=5)
        if code2 == 0:
            print("✓ TTS 语音可播放")
        else:
            print(f"✗ TTS 语音播放失败: {err2[:100] if err2 else out2[:100]}")
    else:
        print(f"✗ espeak-ng 失败: {err if err else out}")
    
    # 7. Python 模块
    print_section("7. Python 模块")
    
    modules = ["pyttsx3", "pygame", "sounddevice", "soundfile"]
    for mod in modules:
        try:
            __import__(mod)
            print(f"✓ {mod}: 已安装")
        except ImportError:
            print(f"✗ {mod}: 未安装")
    
    # 8. 配置检查
    print_section("8. 配置文件")
    
    for conf in ["~/.asoundrc", "/etc/asound.conf"]:
        path = os.path.expanduser(conf)
        if os.path.exists(path):
            print(f"✓ {conf} 存在")
            with open(path) as f:
                content = f.read()
                if "seeed" in content.lower():
                    print(f"  包含 ReSpeaker 配置")
        else:
            print(f"✗ {conf} 不存在")
    
    # 9. 权限检查
    print_section("9. 权限检查")
    
    code, out, err = run_cmd("groups")
    print(f"当前用户组: {out.strip()}")
    
    if "audio" in out:
        print("✓ 用户在 audio 组")
    else:
        print("✗ 用户不在 audio 组")
        print("  修复命令: sudo usermod -a -G audio $USER")
    
    # 总结
    print_section("诊断完成")
    print("\n建议修复步骤:")
    print("1. 运行 ReSpeaker 配置脚本: ./setup_respeaker_audio.sh")
    print("2. 重新登录系统")
    print("3. 再次运行诊断: python3 diagnose_voice.py")


if __name__ == "__main__":
    diagnose()
