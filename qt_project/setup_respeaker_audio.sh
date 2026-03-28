#!/bin/bash
# ReSpeaker 2-Mic 音频配置脚本

echo "======================================"
echo "ReSpeaker 2-Mic 音频配置"
echo "======================================"

# 1. 检查 ReSpeaker 驱动
echo ""
echo "1. 检查 ReSpeaker 驱动..."
if [ -d "/proc/asound/seeed2micvoicec" ] || aplay -l | grep -qi "seeed\|respeaker"; then
    echo "   ✓ ReSpeaker 驱动已加载"
else
    echo "   ✗ ReSpeaker 驱动未找到"
    echo "   请先安装驱动:"
    echo "   cd ~/seeed-voicecard && sudo ./install.sh"
    exit 1
fi

# 2. 查看音频设备
echo ""
echo "2. 音频设备列表:"
aplay -l | grep -E "(card|seeed|respeaker)"

# 3. 配置默认音频设备
echo ""
echo "3. 配置默认音频设备..."

# 查找 ReSpeaker 设备号
CARD_NUM=$(aplay -l | grep -i "seeed\|respeaker" | head -1 | sed -n 's/card \([0-9]*\):.*/\1/p')

if [ -z "$CARD_NUM" ]; then
    echo "   未找到 ReSpeaker 设备，使用默认配置"
    CARD_NUM=0
else
    echo "   找到 ReSpeaker 在 card $CARD_NUM"
fi

# 创建 ALSA 配置
mkdir -p ~/.config/alsa

cat > ~/.asoundrc << EOF
# ReSpeaker 2-Mic 音频配置

defaults.pcm.card $CARD_NUM
defaults.pcm.device 0
defaults.ctl.card $CARD_NUM

pcm.!default {
    type asym
    playback.pcm {
        type plug
        slave.pcm "hw:$CARD_NUM,0"
    }
    capture.pcm {
        type plug
        slave.pcm "hw:$CARD_NUM,0"
    }
}

ctl.!default {
    type hw
    card $CARD_NUM
}

# 直接访问 ReSpeaker
pcm.respeaker {
    type hw
    card $CARD_NUM
    device 0
}

ctl.respeaker {
    type hw
    card $CARD_NUM
}
EOF

echo "   ALSA 配置已写入 ~/.asoundrc"

# 4. 安装 espeak-ng（支持更好的中文）
echo ""
echo "4. 安装 TTS 引擎..."
sudo apt-get update
sudo apt-get install -y espeak-ng espeak-data

# 5. 配置音频路由
echo ""
echo "5. 配置音频路由..."

# 检查是否有 asound.conf
if [ -f "/etc/asound.conf" ]; then
    echo "   备份 /etc/asound.conf..."
    sudo cp /etc/asound.conf /etc/asound.conf.bak.$(date +%Y%m%d)
fi

# 6. 设置音量
echo ""
echo "6. 设置默认音量..."
amixer -c $CARD_NUM set "Headphone" 80% unmute 2>/dev/null || true
amixer -c $CARD_NUM set "PCM" 80% unmute 2>/dev/null || true
amixer -c $CARD_NUM set "Master" 80% unmute 2>/dev/null || true

# 7. 测试音频
echo ""
echo "7. 测试音频输出..."
echo "   播放测试音到 ReSpeaker..."
speaker-test -D "hw:$CARD_NUM,0" -t sine -f 1000 -c 1 -s 1 -d 2 &
SPID=$!
sleep 3
kill $SPID 2>/dev/null
wait $SPID 2>/dev/null

echo ""
echo "8. 测试语音播报..."
espeak-ng -v zh "配置成功" 2>/dev/null || espeak -v zh "配置成功" 2>/dev/null || echo "   TTS 测试完成"

echo ""
echo "======================================"
echo "配置完成！"
echo "======================================"
echo ""
echo "请重新登录系统以应用配置"
echo ""
echo "测试命令:"
echo "  cd qt_project && python3 test_voice.py"
