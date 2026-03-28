#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试声音输出 - 不依赖 TTS
"""

import wave
import struct
import tempfile
import os


def generate_beep_wav(filename, frequency=1000, duration=1.0, volume=0.8):
    """生成蜂鸣测试音"""
    sample_rate = 22050
    num_samples = int(sample_rate * duration)
    
    with wave.open(filename, 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        
        for i in range(num_samples):
            # 生成正弦波
            t = i / sample_rate
            sample = int(32767 * volume * (1 if int(t * frequency * 2) % 2 else -1))
            wav.writeframes(struct.pack('<h', sample))


def test_pyaudio_playback():
    """使用 PyAudio 播放测试音"""
    print("=" * 60)
    print("PyAudio 声音测试")
    print("=" * 60)
    
    try:
        import pyaudio
        
        pa = pyaudio.PyAudio()
        
        print("\n可用音频设备:")
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                print(f"  [{i}] {info['name']}")
        
        # 生成测试音
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        
        generate_beep_wav(wav_path, frequency=800, duration=2.0, volume=0.9)
        print(f"\n生成测试音: {wav_path}")
        
        # 尝试每个设备
        for device_idx in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(device_idx)
            if info['maxOutputChannels'] == 0:
                continue
            
            device_name = info['name']
            print(f"\n测试设备 [{device_idx}]: {device_name}")
            
            try:
                with wave.open(wav_path, 'rb') as wf:
                    stream = pa.open(
                        format=pa.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True,
                        output_device_index=device_idx
                    )
                    
                    data = wf.readframes(1024)
                    while data:
                        stream.write(data)
                        data = wf.readframes(1024)
                    
                    stream.stop_stream()
                    stream.close()
                
                print(f"  ✓ 设备 [{device_idx}] 播放成功！")
                
                # 询问用户是否听到声音
                response = input("  是否听到蜂鸣声？(y/n/q退出): ").strip().lower()
                if response == 'y':
                    print(f"  --> 设备 [{device_idx}] {device_name} 正常工作！")
                    break
                elif response == 'q':
                    break
                    
            except Exception as e:
                print(f"  ✗ 设备 [{device_idx}] 失败: {e}")
        
        pa.terminate()
        
        # 清理
        if os.path.exists(wav_path):
            os.remove(wav_path)
        
    except ImportError:
        print("错误: PyAudio 未安装")
        print("请运行: pip3 install pyaudio")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


def test_alsa_playback():
    """使用 ALSA 直接播放"""
    print("\n" + "=" * 60)
    print("ALSA 声音测试")
    print("=" * 60)
    
    import subprocess
    
    # 使用 speaker-test
    print("\n使用 speaker-test 播放测试音...")
    print("你应该听到 1 秒的蜂鸣声")
    
    try:
        result = subprocess.run(
            ["speaker-test", "-t", "sine", "-f", "1000", "-c", "1", "-s", "1", "-d", "1"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ speaker-test 执行成功")
        else:
            print(f"✗ speaker-test 失败: {result.stderr.decode()[:100]}")
    except Exception as e:
        print(f"✗ speaker-test 错误: {e}")


def test_tts():
    """测试 TTS + 播放"""
    print("\n" + "=" * 60)
    print("TTS 语音测试")
    print("=" * 60)
    
    import shutil
    import subprocess
    
    tts_cmd = None
    for cmd in ["espeak-ng", "espeak"]:
        if shutil.which(cmd):
            tts_cmd = cmd
            break
    
    if not tts_cmd:
        print("错误: 未安装 espeak/espeak-ng")
        print("请运行: sudo apt-get install espeak-ng")
        return
    
    print(f"使用 TTS: {tts_cmd}")
    
    # 生成语音文件
    wav_path = "/tmp/tts_test.wav"
    
    print("\n生成语音文件...")
    result = subprocess.run(
        [tts_cmd, "-v", "zh", "你好，我是骑行小智", "-w", wav_path],
        capture_output=True
    )
    
    if result.returncode != 0:
        print(f"TTS 失败: {result.stderr.decode()[:100]}")
        return
    
    print(f"语音文件生成: {wav_path} ({os.path.getsize(wav_path)} bytes)")
    
    # 播放
    print("\n播放语音...")
    try:
        result = subprocess.run(
            ["aplay", wav_path],
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✓ 播放成功")
        else:
            err = result.stderr.decode()[:100] if result.stderr else "未知错误"
            print(f"✗ 播放失败: {err}")
    except Exception as e:
        print(f"✗ 播放错误: {e}")
    
    # 清理
    if os.path.exists(wav_path):
        os.remove(wav_path)


if __name__ == "__main__":
    test_alsa_playback()
    test_pyaudio_playback()
    test_tts()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
