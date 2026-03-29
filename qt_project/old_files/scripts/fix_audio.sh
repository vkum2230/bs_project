#!/bin/bash
# 音频问题修复脚本

echo "======================================"
echo "SMART RIDE 音频问题修复"
echo "======================================"

# 1. 添加用户到 audio 组
echo ""
echo "1. 添加当前用户到 audio 组..."
sudo usermod -a -G audio $USER
echo "   完成 (需要重新登录生效)"

# 2. 安装必要的软件包
echo ""
echo "2. 安装音频软件包..."
sudo apt-get update
sudo apt-get install -y \
    alsa-utils \
    libasound2-dev \
    pulseaudio \
    pulseaudio-utils \
    mpg123 \
    sox \
    libsox-fmt-mp3 \
    python3-pyaudio \
    espeak \
    espeak-data

# 3. 修复 ALSA 配置
echo ""
echo "3. 检查 ALSA 配置..."

# 创建用户 ALSA 配置（如果软卡有问题）
mkdir -p ~/.config/alsa
cat > ~/.asoundrc << 'EOF'
defaults.pcm.card 0
defaults.pcm.device 0
defaults.ctl.card 0

pcm.!default {
    type hw
    card 0
    device 0
}

ctl.!default {
    type hw
    card 0
}
EOF

echo "   ALSA 配置已更新"

# 4. 重启音频服务
echo ""
echo "4. 重启音频服务..."
killall pulseaudio 2>/dev/null || true
sleep 1
pulseaudio --start 2>/dev/null || true
sleep 1

echo "   PulseAudio 已重启"

# 5. 释放音频设备
echo ""
echo "5. 释放音频设备..."
sudo fuser -k /dev/snd/* 2>/dev/null || true

# 6. 设置默认音量
echo ""
echo "6. 设置默认音量..."
amixer set Master 80% unmute 2>/dev/null || true
amixer set PCM 80% unmute 2>/dev/null || true
amixer set Headphone 80% unmute 2>/dev/null || true
amixer set Speaker 80% unmute 2>/dev/null || true

# 7. 测试音频
echo ""
echo "7. 测试音频输出..."
echo "   播放测试音..."
speaker-test -t sine -f 1000 -c 1 -s 1 -d 2 || echo "   测试失败，请检查硬件"

# 8. 安装 Python 依赖
echo ""
echo "8. 安装 Python 语音依赖..."
pip3 install pyttsx3 --user

echo ""
echo "======================================"
echo "修复完成！"
echo "======================================"
echo ""
echo "重要提示:"
echo "1. 请重新登录或重启系统以应用权限更改"
echo "2. 运行以下命令测试语音:"
echo "   cd qt_project && python3 -c \"from voice_driver import speak; speak('测试成功')\""
echo ""
echo "如果仍有问题，请检查:"
echo "- 音频线是否正确连接"
echo "- 扬声器/耳机是否有电"
echo "- 是否选择了正确的音频输出设备"
