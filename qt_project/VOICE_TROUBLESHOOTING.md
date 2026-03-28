# 语音播报故障排除指南

## 错误 524 说明

错误 `aplay: main:850: audio open error: Unknown error 524` 通常表示：
1. 音频设备被其他进程占用
2. 用户没有音频设备访问权限
3. ALSA/PulseAudio 配置问题

## 快速修复步骤

### 第 1 步：运行自动修复脚本

```bash
cd qt_project
./fix_audio.sh
```

修复后**必须重新登录或重启系统**！

### 第 2 步：测试语音

```bash
cd qt_project
python3 test_voice.py
```

### 第 3 步：如果仍然失败

#### 方案 A：使用 pyttsx3（推荐，无需外部播放器）

```bash
# 安装 pyttsx3
pip3 install pyttsx3 --user

# 测试
python3 -c "
import pyttsx3
engine = pyttsx3.init()
engine.say('测试成功')
engine.runAndWait()
"
```

#### 方案 B：使用 espeak（系统 TTS）

```bash
# 安装 espeak
sudo apt-get install espeak

# 测试
espeak -v zh "你好，我是骑行小智"
```

#### 方案 C：配置音频设备

```bash
# 查看音频设备
aplay -l

# 设置默认设备（编辑 ~/.asoundrc）
cat > ~/.asoundrc << 'EOF'
defaults.pcm.card 0
defaults.pcm.device 0
defaults.ctl.card 0
EOF

# 或使用 plughw
speaker-test -D plughw:0,0 -t sine -f 1000
```

## 手动诊断

### 检查音频设备

```bash
# 列出音频设备
aplay -l

# 示例输出（有设备）：
# card 0: Headphones [bcm2835 Headphones], device 0: bcm2835 Headphones [bcm2835 Headphones]

# 如果没有输出，说明系统没有识别到音频设备
```

### 检查用户权限

```bash
# 查看当前用户组
groups

# 应该有 audio 组
# 如果没有，添加用户到 audio 组
sudo usermod -a -G audio $USER
# 然后重新登录
```

### 检查 PulseAudio

```bash
# 检查 PulseAudio 状态
pactl info

# 重启 PulseAudio
pulseaudio -k
pulseaudio --start
```

### 检查进程占用

```bash
# 查看谁占用了音频设备
lsof /dev/snd/*
fuser -v /dev/snd/*
```

## 特定问题解决方案

### 问题：设备被占用

```bash
# 强制释放音频设备
sudo fuser -k /dev/snd/*

# 或重启 PulseAudio
killall pulseaudio
pulseaudio --start
```

### 问题：权限不足

```bash
# 临时使用 sudo 测试
sudo python3 -c "
import pyttsx3
engine = pyttsx3.init()
engine.say('测试成功')
engine.runAndWait()
"

# 如果 sudo 可以运行，说明是权限问题
# 将用户添加到 audio 组并重新登录
sudo usermod -a -G audio $USER
```

### 问题：树莓派 HDMI 音频

如果使用 HDMI 输出音频：

```bash
# 切换到 HDMI 音频
amixer cset numid=3 2

# 测试
speaker-test -c 2
```

### 问题：USB 音频设备

如果使用 USB 声卡：

```bash
# 查看 USB 设备
lsusb | grep Audio

# 创建配置使用 USB 设备为默认
cat > ~/.asoundrc << 'EOF'
defaults.pcm.card 1
defaults.ctl.card 1
EOF
```

## 程序配置修改

如果系统音频确实无法修复，可以禁用语音功能：

编辑 `main.py`，在初始化部分设置：

```python
self.voice_player = None  # 禁用语音
```

## 联系支持

如果以上方法都无法解决问题：

1. 运行诊断脚本获取详细信息：
   ```bash
   cd qt_project
   python3 -c "
   from voice_driver.audio_check import check_audio
   check_audio()
   "
   ```

2. 查看系统日志：
   ```bash
   dmesg | grep -i audio
   journalctl -xe | grep -i audio
   ```
