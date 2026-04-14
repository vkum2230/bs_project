#!/bin/bash
# Piper 离线语音安装脚本
# 适用于 Raspberry Pi 5

set -e

echo "================================"
echo "安装 Piper 离线语音合成"
echo "================================"

# 1. 安装依赖
echo "[1/5] 安装依赖..."
sudo apt-get update
sudo apt-get install -y libsndfile1 libsndfile1-dev

# 2. 下载 Piper
echo "[2/5] 下载 Piper..."
PIPER_DIR="$HOME/.local/share/piper"
mkdir -p "$PIPER_DIR"
cd "$PIPER_DIR"

# 根据架构选择版本
ARCH=$(uname -m)
if [ "$ARCH" == "aarch64" ]; then
    PIPER_URL="https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_arm64.tar.gz"
else
    PIPER_URL="https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_armv7.tar.gz"
fi

echo "  下载: $PIPER_URL"
wget -q --show-progress "$PIPER_URL" -O piper.tar.gz
tar -xzf piper.tar.gz
rm piper.tar.gz

# 3. 下载中文模型
echo "[3/5] 下载中文语音模型..."
MODEL_DIR="$PIPER_DIR/zh_CN"
mkdir -p "$MODEL_DIR"

# 使用 Chinese (Huayan) 女声模型
MODEL_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx"
JSON_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json"

wget -q --show-progress "$MODEL_URL" -O "$MODEL_DIR/zh_CN-huayan-medium.onnx"
wget -q --show-progress "$JSON_URL" -O "$MODEL_DIR/zh_CN-huayan-medium.onnx.json"

# 4. 创建启动脚本
echo "[4/5] 创建启动脚本..."
cat > "$PIPER_DIR/speak.sh" << 'EOF'
#!/bin/bash
# Piper 语音合成脚本

PIPER_DIR="$HOME/.local/share/piper"
MODEL="$PIPER_DIR/zh_CN/zh_CN-huayan-medium.onnx"

if [ -z "$1" ]; then
    echo "用法: speak.sh '要合成的文本'"
    exit 1
fi

# 生成语音并播放
"$PIPER_DIR/piper" --model "$MODEL" --output_file - --text "$1" | aplay -q -
EOF

chmod +x "$PIPER_DIR/speak.sh"

# 5. 添加到 PATH
echo "[5/5] 配置环境..."
if ! grep -q "piper" ~/.bashrc; then
    echo 'export PATH="$HOME/.local/share/piper:$PATH"' >> ~/.bashrc
fi

echo ""
echo "================================"
echo "Piper 安装完成!"
echo "================================"
echo "安装路径: $PIPER_DIR"
echo ""
echo "测试命令:"
echo "  ~/.local/share/piper/speak.sh '你好，我是骑行小智'"
echo ""
echo "模型大小: $(du -sh $MODEL_DIR | cut -f1)"
echo ""
echo "注意: 请重新登录或运行 'source ~/.bashrc' 使环境变量生效"
