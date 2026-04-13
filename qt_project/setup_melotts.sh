#!/bin/bash
# MeloTTS 安装脚本（音质更好的中文TTS）

set -e

echo "================================"
echo "安装 MeloTTS 离线语音"
echo "================================"
echo ""
echo "MeloTTS 特点："
echo "  - 基于深度学习，声音非常自然"
echo "  - 专门为中文优化"
echo "  - 比 Piper 音质更好，但生成较慢"
echo ""
echo "注意：树莓派上安装可能需要较长时间"
echo "      首次使用时会下载模型（约100MB）"
echo ""
read -p "是否继续安装? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

echo ""
echo "[1/4] 安装依赖..."
sudo apt-get update
sudo apt-get install -y libsndfile1 libsndfile1-dev espeak-ng

echo ""
echo "[2/4] 安装 MeloTTS..."
pip3 install melotts unidecode --break-system-packages

echo ""
echo "[3/4] 下载中文模型..."
# 预下载模型，避免首次使用时等待
python3 -c "
from melo.api import TTS
print('下载模型...')
model = TTS(language='ZH', device='cpu')
print('模型下载完成')
" 2>&1 || echo "模型将在首次使用时自动下载（首次使用需要下载约100MB模型）"

echo ""
echo "[4/4] 测试..."
python3 -c "
from melo.api import TTS
import tempfile
import subprocess
import os

print('初始化 MeloTTS...')
tts = TTS(language='ZH', device='cpu')

print('生成测试语音...')
text = '你好，我是骑行小智，使用 MeloTTS 播报。'
speaker_ids = tts.hps.data.spk2id
speaker_id = speaker_ids['ZH']

with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
    wav_path = f.name

tts.tts_to_file(text, speaker_id, wav_path, speed=1.0)

print('播放测试...')
subprocess.run(['aplay', '-q', '-D', 'plughw:2,0', wav_path], check=True)
os.remove(wav_path)

print('测试完成！')
" 2>&1 || echo "测试失败，请检查安装"

echo ""
echo "================================"
echo "MeloTTS 安装完成！"
echo "================================"
echo ""
echo "使用方法:"
echo "  在 voice_driver/offline_voice.py 中会自动检测并使用"
echo ""
echo "注意事项："
echo "  1. 首次生成语音需要加载模型，可能需要 5-10 秒"
echo "  2. 树莓派上生成速度较慢（约 3-5 秒/句）"
echo "  3. 音质明显优于 Piper 和 espeak"
echo ""
