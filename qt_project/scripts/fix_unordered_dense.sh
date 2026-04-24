#!/bin/bash
# 修复 ankerl/unordered_dense 缺失

set -e

THIRD_PARTY="/home/hedya/Desktop/bs_project/qt_project/valhalla/third_party"

echo "========================================"
echo "[Fix] 下载 unordered_dense 库..."
echo "========================================"

cd "$THIRD_PARTY"

# 清空空目录并克隆
rm -rf unordered_dense

# 尝试多个镜像
git clone --depth=1 https://github.com/martinus/unordered_dense.git unordered_dense || \
git clone --depth=1 https://ghproxy.com/https://github.com/martinus/unordered_dense.git unordered_dense || \
git clone --depth=1 https://gh.api.99988866.xyz/https://github.com/martinus/unordered_dense.git unordered_dense

echo ""
echo "========================================"
echo "[Fix] unordered_dense 已就绪！"
echo "========================================"
echo ""
echo "现在重新编译 Valhalla："
echo "  cd /home/hedya/Desktop/bs_project/qt_project/scripts"
echo "  ./2_crop_and_build.sh"
