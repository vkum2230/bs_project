#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音系统诊断测试
"""

import sys
sys.path.insert(0, '/home/hedya/Desktop/bs_project/qt_project')

def test_network():
    """测试网络"""
    print("="*50)
    print("1. 网络连接测试")
    print("="*50)
    try:
        import socket
        socket.setdefaulttimeout(2)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        print("✓ 网络连接正常")
        return True
    except Exception as e:
        print(f"✗ 网络连接失败: {e}")
        return False

def test_edge_tts():
    """测试 Edge-TTS"""
    print("\n" + "="*50)
    print("2. Edge-TTS 测试")
    print("="*50)
    
    # 检查模块
    try:
        import edge_tts
        print("✓ edge_tts 模块已安装")
    except ImportError:
        print("✗ edge_tts 模块未安装")
        print("  安装命令: pip3 install edge-tts")
        return False
    
    # 测试生成
    import asyncio
    async def test_generate():
        try:
            communicate = edge_tts.Communicate(
                text="你好",
                voice="zh-CN-XiaoxiaoNeural",
                rate="+0%",
                volume="+0%"
            )
            await asyncio.wait_for(communicate.save("/tmp/test_edge.mp3"), timeout=5.0)
            import os
            size = os.path.getsize("/tmp/test_edge.mp3")
            print(f"✓ Edge-TTS 生成成功: {size} bytes")
            os.remove("/tmp/test_edge.mp3")
            return True
        except asyncio.TimeoutError:
            print("✗ Edge-TTS 超时")
            return False
        except Exception as e:
            print(f"✗ Edge-TTS 失败: {e}")
            return False
    
    return asyncio.run(test_generate())

def test_piper():
    """测试 Piper"""
    print("\n" + "="*50)
    print("3. Piper 离线语音测试")
    print("="*50)
    
    from voice_driver.piper_voice import PiperVoicePlayer
    
    player = PiperVoicePlayer()
    
    if player.is_available():
        print("✓ Piper 已安装并可用")
        
        # 测试播报
        print("  测试播报...")
        result = player.speak("Piper测试", block=True, show_in_ui=False)
        if result:
            print("✓ Piper 播报成功")
        else:
            print("✗ Piper 播报失败")
        return result
    else:
        print("✗ Piper 不可用")
        print("  安装命令: ./setup_piper.sh")
        return False

def test_hybrid():
    """测试混合播放器"""
    print("\n" + "="*50)
    print("4. 混合播放器测试")
    print("="*50)
    
    from voice_driver.piper_voice import HybridVoicePlayer
    
    player = HybridVoicePlayer()
    
    print("测试播报: '你好，我是骑行小智'...")
    result = player.speak("你好，我是骑行小智", block=True, show_in_ui=False)
    
    if result:
        print("✓ 混合播放器工作正常")
    else:
        print("✗ 混合播放器失败")
    
    return result

def main():
    print("="*50)
    print("语音系统诊断")
    print("="*50)
    
    network = test_network()
    edge = test_edge_tts()
    piper = test_piper()
    hybrid = test_hybrid()
    
    print("\n" + "="*50)
    print("诊断结果")
    print("="*50)
    print(f"网络连接: {'✓' if network else '✗'}")
    print(f"Edge-TTS: {'✓' if edge else '✗'}")
    print(f"Piper: {'✓' if piper else '✗'}")
    print(f"混合播放器: {'✓' if hybrid else '✗'}")
    
    if not network and not piper:
        print("\n⚠️  警告: 无网络且 Piper 未安装，将只能使用机器音(espeak)")
        print("建议: 运行 ./setup_piper.sh 安装离线语音")
    elif not edge and not piper:
        print("\n⚠️  警告: Edge-TTS 和 Piper 都不可用")
        print("建议: 安装 edge-tts (pip3 install edge-tts) 或 Piper (./setup_piper.sh)")

if __name__ == "__main__":
    main()
