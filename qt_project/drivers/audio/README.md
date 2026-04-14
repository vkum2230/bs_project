# 语音驱动模块 - SMART RIDE 智能骑行系统

## 概述

本模块为 ReSpeaker 2-Mic 语音模块的驱动封装，提供语音播报、LED 控制和按钮事件处理功能。

## 硬件要求

- ReSpeaker 2-Mic Pi HAT 语音模块
- 树莓派（已测试 Raspberry Pi 4/5）

## 安装依赖

### 1. 系统依赖

```bash
# 安装音频工具
sudo apt-get update
sudo apt-get install -y python3-pip python3-pyaudio portaudio19-dev

# 安装 TTS 引擎（可选，推荐至少安装一个）
sudo apt-get install -y espeak espeak-data  # 系统 TTS

# 安装音频播放器（可选）
sudo apt-get install -y alsa-utils mpg123
```

### 2. Python 依赖

```bash
# 离线 TTS 引擎（推荐）
pip install pyttsx3

# 在线 TTS 引擎（音质更好，需要网络）
pip install edge-tts

# SPI 通信（LED 控制必需）
pip install spidev

# GPIO 控制（按钮处理必需）
pip install gpiozero
```

## 快速开始

### 语音播报

```python
from voice_driver import VoicePlayer, speak

# 方法1：创建实例
voice = VoicePlayer()
voice.speak("你好，我是骑行小智")

# 方法2：使用便捷函数
speak("开始导航")

# 方法3：指定引擎
voice = VoicePlayer(engine="pyttsx3")  # 离线引擎
voice = VoicePlayer(engine="edge-tts")  # 在线引擎
```

### LED 控制

```python
from voice_driver import LEDController

led = LEDController()

# 设置颜色
led.set_all(LEDController.COLOR_BLUE)   # 蓝色
led.set_all(LEDController.COLOR_RED)    # 红色
led.set_all(LEDController.COLOR_GREEN)  # 绿色

# 动画效果
led.start_pattern("breath", LEDController.COLOR_CYAN)  # 呼吸灯
led.start_pattern("blink", LEDController.COLOR_RED)    # 闪烁
led.start_pattern("rainbow")                            # 彩虹

# 停止动画
led.stop_pattern()
led.off()
```

### 按钮处理

```python
from voice_driver import ButtonHandler, ButtonEvent

btn = ButtonHandler()

# 注册事件回调
btn.on(ButtonEvent.CLICK, lambda: print("单击"))
btn.on(ButtonEvent.DOUBLE_CLICK, lambda: print("双击"))
btn.on(ButtonEvent.LONG_PRESS, lambda: print("长按"))

# 启动监听
btn.start()

# 停止监听
btn.stop()
```

## API 文档

### VoicePlayer

```python
VoicePlayer(engine="auto", rate=150, volume=0.9)
```

| 参数 | 说明 | 可选值 |
|------|------|--------|
| engine | TTS 引擎 | "auto", "pyttsx3", "edge-tts", "espeak" |
| rate | 语速 | 100-300 |
| volume | 音量 | 0.0-1.0 |

### LEDController

```python
LEDController(num_leds=3, brightness=31)
```

| 方法 | 说明 |
|------|------|
| set_all(color) | 设置所有 LED 颜色 |
| set_pixel(index, color) | 设置单个 LED 颜色 |
| set_brightness(val) | 设置亮度 (0-31) |
| start_pattern(name, color) | 启动动画 |
| stop_pattern() | 停止动画 |
| off() | 关闭 LED |

### ButtonHandler

```python
ButtonHandler(pin=17, pull_up=True, long_press_ms=800, double_click_ms=300)
```

| 事件 | 说明 |
|------|------|
| ButtonEvent.PRESS | 按下 |
| ButtonEvent.RELEASE | 释放 |
| ButtonEvent.CLICK | 单击 |
| ButtonEvent.DOUBLE_CLICK | 双击 |
| ButtonEvent.LONG_PRESS | 长按 |

## 在 main.py 中的集成

语音播报已自动集成到主程序中：

1. **启动欢迎语音**：程序启动 1.5 秒后播报"你好，我是骑行小智"
2. **导航语音**：导航指令自动语音播报
3. **LED 效果**：启动时蓝色呼吸灯，就绪后变为绿色常亮

## 故障排除

### 没有声音

1. 检查音频输出设备：`aplay -l`
2. 检查音量设置：`alsamixer`
3. 测试音频：`speaker-test -t wav`

### LED 不亮

1. 检查 SPI 是否启用：`ls /dev/spi*`
2. 检查 GPIO 5 是否拉高：`pinctrl set 5 op dh`

### 按钮无响应

1. 检查 GPIO 17 连接
2. 确认 gpiozero 已安装

## 许可

MIT License
