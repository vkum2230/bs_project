#!/bin/bash
# 修复 GCC 14 弃用警告导致的编译失败

set -e

PROJECT_DIR="/home/hedya/Desktop/bs_project/qt_project"
VALHALLA_DIR="$PROJECT_DIR/valhalla"

echo "========================================"
echo "[Fix] 清理旧 build 目录..."
cd "$VALHALLA_DIR"
rm -rf build
mkdir -p build
cd build

echo ""
echo "========================================"
echo "[Fix] 重新配置 CMake（兼容 GCC 14）..."
echo "========================================"

# 关键改动：
# -DCMAKE_CXX_FLAGS="-Wno-error=deprecated-declarations"
#   GCC 14 弃用了 std::atomic_store_explicit(shared_ptr*)
#   这个 flag 让弃用声明只报 warning 不终止编译

cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF \
    -DENABLE_DATA_TOOLS=ON \
    -DENABLE_SERVICES=ON \
    -DENABLE_PYTHON_BINDINGS=OFF \
    -DENABLE_TESTS=OFF \
    -DCMAKE_CXX_FLAGS="-Wno-error=deprecated-declarations"

echo ""
echo "========================================"
echo "[Fix] 开始编译..."
echo "========================================"
make -j$(nproc)

echo ""
echo "========================================"
echo "[Fix] 编译完成！"
echo "========================================"
