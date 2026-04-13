# 语音升级指南

## 推荐方案：Piper 高质量模型（最简单可靠）

由于 MeloTTS 在树莓派上安装复杂，推荐升级 Piper 到高质量版本。

### 手动安装（推荐）

```bash
# 1. 进入模型目录
cd ~/.local/share/piper/zh_CN

# 2. 下载高质量模型（约120MB，可能需要几分钟）
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/high/zh_CN-huayan-high.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/high/zh_CN-huayan-high.onnx.json

# 3. 备份旧模型
mv zh_CN-huayan-medium.onnx zh_CN-huayan-medium.onnx.bak
mv zh_CN-huayan-medium.onnx.json zh_CN-huayan-medium.onnx.json.bak

# 4. 使用高质量模型
ln -s zh_CN-huayan-high.onnx zh_CN-huayan-medium.onnx
ln -s zh_CN-huayan-high.onnx.json zh_CN-huayan-medium.onnx.json
```

### 验证安装

```bash
# 测试语音
~/.local/share/piper/speak.sh '你好，我是骑行小智，现在使用高质量语音'
```

### 对比

| 特性 | Medium（当前） | High（升级后） |
|------|---------------|----------------|
| 音质 | 机械感较重 | 更自然流畅 |
| 大小 | 60MB | 120MB |
| 速度 | 0.5秒 | 1秒 |
| 推荐度 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 备选方案

如果 Piper High 仍不满意，可以考虑：

1. **Edge-TTS**（当前在线方案）- 音质最好，但需要网络
2. **espeak** - 机器人声音，保底用

## 当前配置

你现在使用的是：
- ✅ **Edge-TTS** - 在线，音质最好
- ✅ **Piper Medium** - 离线，快速但机械感重
- ✅ **espeak** - 保底

升级后：
- ✅ **Edge-TTS** - 在线
- ✅ **Piper High** - 离线，音质更好
- ✅ **espeak** - 保底
