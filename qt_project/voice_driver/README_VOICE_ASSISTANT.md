# 按钮语音助手功能

按住 ReSpeaker 2-Mic 上的按钮开始录音，松开后自动识别语音并播报识别结果。

## 功能说明

- **按住按钮**：开始录音（红灯亮起）
- **松开按钮**：停止录音，自动识别语音内容
- **播报结果**：语音播报识别到的文字
- **显示结果**：在消息框中显示识别文字

## 安装依赖

### 1. 安装 Python 依赖

```bash
pip3 install vosk pyaudio --user
```

### 2. 下载语音识别模型（推荐）

```bash
# 进入项目目录
cd qt_project

# 下载中文模型（约 40MB）
wget https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip

# 解压
unzip vosk-model-small-cn-0.22.zip

# 删除压缩包
rm vosk-model-small-cn-0.22.zip
```

如果不安装模型，系统会提示安装，但不会崩溃。

### 3. 系统依赖

```bash
sudo apt-get install -y python3-pyaudio portaudio19-dev
```

## 硬件连接

ReSpeaker 2-Mic 的按钮默认连接到 **GPIO 17**。

如果使用其他 GPIO 引脚，修改 `main.py` 中的初始化参数：

```python
self.voice_assistant = ButtonVoiceAssistant(
    voice_player=self.voice_player,
    message_callback=self.add_voice_message,
    button_pin=17  # 修改为你的 GPIO 引脚
)
```

## 使用方法

1. 启动程序：
```bash
cd qt_project
python3 main.py
```

2. 按住 ReSpeaker 上的按钮（GPIO 17 对应的位置）
   - 消息框会显示 "🔴 正在录音...请说话"

3. 对着麦克风说话

4. 松开按钮
   - 消息框会显示 "⏳ 识别中..."
   - 识别完成后显示 "💬 你说: [识别文字]"
   - 同时语音播报识别结果

## 消息框图标说明

| 图标 | 含义 |
|------|------|
| 🔴 | 正在录音 |
| ⏳ | 识别中 |
| 💬 | 识别结果 |
| ⚠️ | 错误提示 |

## 故障排除

### 录音失败

1. 检查麦克风权限：
```bash
sudo usermod -a -G audio $USER
# 重新登录
```

2. 检查 ReSpeaker 驱动：
```bash
ls /proc/asound/ | grep seeed
```

3. 测试录音：
```bash
arecord -D hw:2,0 -f S16_LE -r 16000 -c 2 test.wav
```

### 识别失败

1. 检查 Vosk 是否安装：
```bash
python3 -c "import vosk; print(vosk.__version__)"
```

2. 检查模型文件是否存在：
```bash
ls -la vosk-model-small-cn-0.22/
```

### 按钮无响应

1. 检查 GPIO 连接：
```bash
# 测试按钮状态
python3 -c "
from gpiozero import Button
btn = Button(17)
print('按住按钮...')
btn.wait_for_press()
print('按钮已按下!')
"
```

2. 检查按钮引脚是否正确连接。

## 自定义设置

### 调整录音参数

编辑 `voice_driver/voice_recorder.py`：

```python
recorder = VoiceRecorder(
    sample_rate=16000,  # 采样率
    channels=2,         # 通道数（ReSpeaker 2-Mic 是 2）
    chunk_duration=0.1  # 每块录音时长
)
```

### 调整识别灵敏度

在 `ButtonVoiceAssistant._process_recording` 中修改置信度阈值：

```python
# 置信度大于 0.3 才播报
if self.voice_player and result.confidence > 0.3:
    self.voice_player.speak(f"你说{speak_text}", block=False)
```
