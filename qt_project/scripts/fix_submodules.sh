#!/bin/bash
# 修复 prime_server 子模块缺失问题

set -e

echo "========================================"
echo "[Fix] 拉取 prime_server 子模块..."
echo "========================================"

cd /home/hedya/Desktop/bs_project/qt_project/valhalla_deps/prime_server

# 拉取子模块（logging 和 testing）
git submodule update --init --recursive

echo ""
echo "========================================"
echo "[Fix] 重新编译安装 prime_server..."
echo "⚠️  约需 3-10 分钟"
echo "========================================"

make clean 2>/dev/null || true
./autogen.sh
./configure
make -j$(nproc)
sudo make install
sudo ldconfig

echo ""
echo "========================================"
echo "[Fix] prime_server 修复完成！"
echo "========================================"
echo ""
echo "现在重新编译 Valhalla："
echo "  cd /home/hedya/Desktop/bs_project/qt_project/scripts"
echo "  ./2_crop_and_build.sh"
