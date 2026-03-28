#!/bin/bash
# ReSpeaker 2-Mic 硬件检查脚本

echo "======================================"
echo "ReSpeaker 2-Mic 硬件检查"
echo "======================================"

# 1. 检查 ReSpeaker 驱动
echo ""
echo "1. ReSpeaker 驱动检查"
if [ -d "/proc/asound/seeed2micvoicec" ]; then
    echo "✓ 驱动已加载"
    ls -la /proc/asound/seeed2micvoicec/
else
    echo "✗ 驱动未加载"
    echo "  请运行: cd ~/seeed-voicecard && sudo ./install.sh"
fi

# 2. 检查 I2C 设备
echo ""
echo "2. I2C 设备检查"
if [ -e "/dev/i2c-1" ]; then
    echo "✓ I2C 设备存在"
    echo "  I2C 地址扫描:"
    sudo i2cdetect -y 1 2>/dev/null || echo "  需要 sudo 权限运行 i2cdetect"
else
    echo "✗ I2C 设备不存在"
fi

# 3. 检查音频设备
echo ""
echo "3. 音频设备检查"
echo "ALSA 设备列表:"
aplay -l | grep -E "card|seeed|respeaker"

echo ""
echo "设备详细信息:"
cat /proc/asound/cards | grep -E "seeed|respeaker"

# 4. 检查 GPIO
echo ""
echo "4. GPIO 检查"
echo "GPIO 5 (电源控制):"
pinctrl get 5 2>/dev/null || raspi-gpio get 5 2>/dev/null || echo "  无法读取 GPIO 状态"

# 5. 检查连接的设备
echo ""
echo "5. 检查音频输出设备"
echo "请确认以下连接:"
echo "  - ReSpeaker 板上的 3.5mm 音频接口是否接了耳机/扬声器？"
echo "  - 如果是 JST 接口，是否接了扬声器？"
echo "  - 扬声器/耳机是否有电？"

# 6. 测试音频输出
echo ""
echo "6. 音频输出测试"
echo "即将播放测试音，请听是否有声音..."
echo "按 Enter 继续，或 Ctrl+C 跳过..."
read

# 找到 ReSpeaker 设备号
CARD_NUM=$(aplay -l | grep -i "seeed\|respeaker" | head -1 | sed -n 's/card \([0-9]*\):.*/\1/p')

if [ -n "$CARD_NUM" ]; then
    echo "使用 ReSpeaker (card $CARD_NUM) 播放测试音..."
    speaker-test -D "hw:$CARD_NUM,0" -t sine -f 1000 -c 2 -s 1 -d 2
else
    echo "未找到 ReSpeaker，使用默认设备..."
    speaker-test -t sine -f 1000 -c 2 -s 1 -d 2
fi

echo ""
echo "======================================"
echo "检查完成"
echo "======================================"
echo ""
echo "常见问题:"
echo "1. 如果听不到声音，请检查:"
echo "   - ReSpeaker 板上的 3.5mm 接口是否接了耳机/扬声器"
echo "   - 扬声器是否有电（如果是无源扬声器）"
echo "   - 音量是否调到最大: amixer set Master 100%"
echo ""
echo "2. 如果是树莓派 5，需要手动拉高 GPIO 5:"
echo "   pinctrl set 5 op dh"
echo ""
echo "3. ReSpeaker 2-Mic 的音频输出接口:"
echo "   - 3.5mm 音频接口 (绿色)"
echo "   - JST 2.0 扬声器接口 (白色)"
