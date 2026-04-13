#!/bin/bash
# Piper 高质量中文语音模型安装脚本

set -e

echo "================================"
echo "安装 Piper 高质量中文模型"
echo "================================"

PIPER_DIR="$HOME/.local/share/piper"
MODEL_DIR="$PIPER_DIR/zh_CN"

# 创建目录
mkdir -p "$MODEL_DIR"

# 下载高质量模型
echo "[1/2] 下载高质量模型..."
cd "$MODEL_DIR"

# high 质量模型 (~120MB)
MODEL_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/high/zh_CN-huayan-high.onnx"
JSON_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/high/zh_CN-huayan-high.onnx.json"

if [ -f "zh_CN-huayan-high.onnx" ]; then
    echo "  高质量模型已存在，跳过下载"
else
    echo "  下载模型文件 (~120MB)..."
    wget -q --show-progress "$MODEL_URL" -O zh_CN-huayan-high.onnx
fi

if [ -f "zh_CN-huayan-high.onnx.json" ]; then
    echo "  配置文件已存在，跳过下载"
else
    echo "  下载配置文件..."
    wget -q --show-progress "$JSON_URL" -O zh_CN-huayan-high.onnx.json
fi

# 备份旧模型
echo "[2/2] 配置模型..."
if [ -f "zh_CN-huayan-medium.onnx" ]; then
    echo "  备份 medium 模型..."
    mv zh_CN-huayan-medium.onnx zh_CN-huayan-medium.onnx.bak
    mv zh_CN-huayan-medium.onnx.json zh_CN-huayan-medium.onnx.json.bak 2>/dev/null || true
fi

# 创建软链接使用高质量模型
echo "  启用高质量模型..."
ln -sf zh_CN-huayan-high.onnx zh_CN-huayan-medium.onnx
ln -sf zh_CN-huayan-high.onnx.json zh_CN-huayan-medium.onnx.json 2>/dev/null || true

echo ""
echo "================================"
echo "高质量模型安装完成！"
echo "================================"
echo "模型路径: $MODEL_DIR/zh_CN-huayan-high.onnx"
echo "模型大小: $(du -sh zh_CN-huayan-high.onnx | cut -f1)"
echo ""
echo "测试命令:"
echo "  ~/.local/share/piper/speak.sh '你好，我是骑行小智'"
echo ""
echo "注意：高质量模型生成稍慢，但声音更自然"
echo "      如需恢复 medium 质量，运行:"
echo "      cd $MODEL_DIR && mv zh_CN-huayan-medium.onnx.bak zh_CN-huayan-medium.onnx"
echo ""
