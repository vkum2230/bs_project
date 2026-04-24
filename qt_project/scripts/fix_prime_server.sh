#!/bin/bash
# 修复 prime_server 缺失问题

set -e

PROJECT_DIR="/home/hedya/Desktop/bs_project/qt_project"
DEPS_DIR="$PROJECT_DIR/valhalla_deps"

echo "========================================"
echo "[Fix] 安装 GeoTIFF 依赖（可选但推荐）..."
sudo apt install -y libgeotiff-dev

echo ""
echo "========================================"
echo "[Fix] 下载并编译 prime_server..."
echo "⚠️  约需 5-15 分钟"
echo "========================================"

mkdir -p "$DEPS_DIR"
cd "$DEPS_DIR"

# 下载 prime_server 源码
if [ ! -d "prime_server" ]; then
    git clone https://github.com/kevinkreiser/prime_server.git
fi

cd prime_server

# 安装 prime_server 的依赖
sudo apt install -y libczmq-dev

# 编译安装
./autogen.sh
./configure
make -j$(nproc)
sudo make install

# 更新动态链接库缓存
sudo ldconfig

echo ""
echo "========================================"
echo "[Fix] prime_server 安装完成！"
echo "========================================"
echo ""
echo "现在重新执行 Step 2 编译 Valhalla："
echo "  cd $PROJECT_DIR/scripts"
echo "  ./2_crop_and_build.sh"
