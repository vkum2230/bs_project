# 语音选项说明

系统支持多种语音合成方案，自动选择最佳可用选项。

## 当前可用方案

### 1. Edge-TTS（在线）
- **特点**：音质最好，晓晓女声
- **网络要求**：需要网络
- **速度**：快（约1-2秒）
- **当前状态**：✅ 已启用

### 2. Piper（离线）
- **特点**：轻量级神经网络TTS，无需网络
- **模型大小**：约60MB
- **速度**：快（约0.5秒）
- **当前状态**：✅ 已启用
- **声音质量**：机械感较重

### 3. espeak（保底）
- **特点**：机器人声音，保底用
- **当前状态**：✅ 可用

## 升级选项

### 方案A：Piper 高质量模型（推荐）
文件更大但声音更自然：

```bash
cd ~/Desktop/bs_project/qt_project
chmod +x setup_piper_hq.sh
./setup_piper_hq.sh
```

**对比**：
| 特性 | Medium（当前） | High（升级后） |
|------|---------------|----------------|
| 文件大小 | ~60MB | ~120MB |
| 生成速度 | ~0.5秒 | ~1秒 |
| 声音自然度 | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 适合场景 | 快速响应 | 自然对话 |

### 方案B：MeloTTS（音质最好）
基于深度学习的自然语音：

```bash
cd ~/Desktop/bs_project/qt_project
chmod +x setup_melotts.sh
./setup_melotts.sh
```

**特点**：
- 声音非常自然，接近真人
- 专门为中文优化
- 树莓派上生成较慢（约3-5秒/句）
- 模型约100MB

**适合**：对音质要求高，不介意等待的场景

## 语音优先级

当前优先级（从高到低）：
1. **离线优先**（Piper/MeloTTS）- 带20秒超时
2. **在线备用**（Edge-TTS）- 网络可用时
3. **保底**（espeak）- 都失败时

## 测试语音

测试当前语音：
```bash
cd ~/Desktop/bs_project/qt_project
python3 -c "
from voice_driver.piper_voice import HybridVoicePlayer
p = HybridVoicePlayer()
p.speak('你好，我是骑行小智', block=True)
"
```

测试 Piper 单独：
```bash
~/.local/share/piper/speak.sh '你好，我是骑行小智'
```

测试 MeloTTS（安装后）：
```bash
python3 voice_driver/offline_voice.py
```

## 推荐配置

| 场景 | 推荐方案 | 原因 |
|------|---------|------|
| 快速响应 | Piper medium | 生成快，占用资源少 |
| 自然对话 | Piper high | 平衡速度和音质 |
| 最佳音质 | MeloTTS | 声音最自然 |
| 离线使用 | Piper | 无需网络，稳定可靠 |

## 问题排查

### Piper 超时
- 检查路径：`ls ~/.local/share/piper/piper/piper`
- 检查模型：`ls ~/.local/share/piper/zh_CN/*.onnx`
- 测试命令：`echo "测试" | ~/.local/share/piper/piper/piper --model ~/.local/share/piper/zh_CN/zh_CN-huayan-medium.onnx --output_file /tmp/test.wav`

### 声音不自然
- 升级为 high 质量模型
- 或安装 MeloTTS

### 生成太慢
- 使用 Piper 替代 MeloTTS
- 或使用 Edge-TTS（需要网络）
