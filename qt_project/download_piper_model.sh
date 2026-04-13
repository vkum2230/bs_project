#!/bin/bash
# 手动下载 Piper 中文模型（使用镜像加速）

echo "================================"
echo "下载 Piper 中文语音模型"
echo "================================"

MODEL_DIR="$HOME/.local/share/piper/zh_CN"
mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

echo ""
echo "下载中...这可能需要几分钟"
echo ""

# 尝试多个镜像源
MIRRORS=(
    "https://hf-mirror.com"
    "https://huggingface.co"
)

for MIRROR in "${MIRRORS[@]}"; do
    echo "尝试镜像: $MIRROR"
    
    # 下载模型文件
    wget --timeout=60 -O zh_CN-huayan-medium.onnx \
        "$MIRROR/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx" 2>&1 | tail -5
    
    if [ $? -eq 0 ] && [ -s zh_CN-huayan-medium.onnx ]; then
        echo "✓ 模型文件下载成功"
        
        # 下载配置文件
        wget --timeout=30 -O zh_CN-huayan-medium.onnx.json \
            "$MIRROR/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json" 2>&1 | tail -3
        
        if [ $? -eq 0 ] && [ -s zh_CN-huayan-medium.onnx.json ]; then
            echo "✓ 配置文件下载成功"
            break
        fi
    fi
    
    echo "✗ 该镜像失败，尝试下一个..."
done

# 验证文件
if [ -f zh_CN-huayan-medium.onnx ] && [ -f zh_CN-huayan-medium.onnx.json ]; then
    echo ""
    echo "================================"
    echo "下载完成!"
    echo "================================"
    echo "模型大小: $(du -h zh_CN-huayan-medium.onnx | cut -f1)"
    echo ""
    echo "测试命令:"
    echo "  ~/.local/share/piper/piper --model ~/.local/share/piper/zh_CN/zh_CN-huayan-medium.onnx --text '你好' --output_file - | aplay"
else
    echo ""
    echo "================================"
    echo "下载失败"
    echo "================================"
    echo "请手动下载："
    echo "1. 浏览器访问: https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0/zh/zh_CN/huayan/medium"
    echo "2. 下载 zh_CN-huayan-medium.onnx 和 zh_CN-huayan-medium.onnx.json"
    echo "3. 放入目录: ~/.local/share/piper/zh_CN/"
fi
