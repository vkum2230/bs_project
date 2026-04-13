# 语音系统使用说明

## 概述

系统支持三种语音合成方式，自动选择最佳方案：

| 优先级 | 方案 | 特点 | 网络要求 |
|--------|------|------|----------|
| 1 | Edge-TTS | 音质最好，晓晓女声 | 需要网络 |
| 2 | Piper | 离线神经网络，音质好 | 无需网络 |
| 3 | espeak | 机器人声音，保底用 | 无需网络 |

## 安装离线语音（Piper）

### 方式1：自动安装（推荐）

```bash
cd ~/Desktop/bs_project/qt_project
chmod +x setup_piper.sh
./setup_piper.sh
```

安装过程约需 2-5 分钟，会下载约 60MB 的模型文件。

### 方式2：手动安装

```bash
# 1. 创建目录
mkdir -p ~/.local/share/piper
cd ~/.local/share/piper

# 2. 下载 Piper（根据系统选择）
# For Raspberry Pi 5 (aarch64)
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_arm64.tar.gz

# For Pi 4/3 (armv7)
# wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_armv7.tar.gz

tar -xzf piper_arm64.tar.gz
rm piper_arm64.tar.gz

# 3. 下载中文模型
mkdir -p zh_CN
wget -O zh_CN/zh_CN-huayan-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx

wget -O zh_CN/zh_CN-huayan-medium.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json
```

## 测试语音

### 测试在线语音（Edge-TTS）
```bash
cd ~/Desktop/bs_project/qt_project
python3 -c "
from voice_driver.voice_final import FinalVoicePlayer
p = FinalVoicePlayer()
p.speak('这是在线语音测试', block=True)
"
```

### 测试离线语音（Piper）
```bash
cd ~/Desktop/bs_project/qt_project
python3 voice_driver/piper_voice.py
```

### 测试混合播放器
```bash
cd ~/Desktop/bs_project/qt_project
python3 voice_driver/piper_voice.py hybrid
```

## 离线使用

安装 Piper 后，系统会自动：
1. **有网络时**：使用 Edge-TTS（音质最好）
2. **无网络时**：自动切换到 Piper（离线，音质好）
3. **Piper 失败时**：使用 espeak（保底）

无需手动配置，系统会自动检测并选择最佳方案。

## 常见问题

### Q: Piper 安装后仍然使用 espeak
**A:** 检查 Piper 是否正确安装：
```bash
ls ~/.local/share/piper/piper
ls ~/.local/share/piper/zh_CN/zh_CN-huayan-medium.onnx
```
如果文件不存在，重新运行安装脚本。

### Q: 离线语音合成慢
**A:** Piper 首次加载模型需要 1-2 秒，后续合成较快。树莓派性能有限，长文本（>50字）建议分段播报。

### Q: 如何强制使用离线语音
**A:** 断开 WiFi/网线，系统会自动切换到 Piper。

### Q: 可以更换其他离线声音吗
**A:** 可以，从 [Piper Voices](https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0) 下载其他中文模型，替换 `~/.local/share/piper/zh_CN/` 中的文件。

## 文件位置

- Piper 安装：`~/.local/share/piper/`
- 中文模型：`~/.local/share/piper/zh_CN/`
- 播放器代码：`qt_project/voice_driver/piper_voice.py`
- 安装脚本：`qt_project/setup_piper.sh`
