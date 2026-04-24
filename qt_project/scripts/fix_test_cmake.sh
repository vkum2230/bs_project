#!/bin/bash
# 修复 Valhalla 测试目录 CMake 依赖问题

set -e

VALHALLA_DIR="/home/hedya/Desktop/bs_project/qt_project/valhalla"

echo "========================================"
echo "[Fix] 移除 Valhalla 测试目录（不需要）..."
echo "========================================"

# 备份并移除 test 目录
if [ -d "$VALHALLA_DIR/test" ]; then
    mv "$VALHALLA_DIR/test" "$VALHALLA_DIR/test.bak"
    echo "[Fix] test 目录已移开"
fi

# 同时修改顶层 CMakeLists.txt，注释掉 add_subdirectory(test)
TOP_CMAKE="$VALHALLA_DIR/CMakeLists.txt"
if grep -q "add_subdirectory(test)" "$TOP_CMAKE"; then
    sed -i 's/add_subdirectory(test)/# add_subdirectory(test)/' "$TOP_CMAKE"
    echo "[Fix] 顶层 CMakeLists.txt 已注释掉 test"
fi

echo ""
echo "========================================"
echo "[Fix] 修复完成！"
echo "========================================"
echo ""
echo "现在重新编译 Valhalla："
echo "  cd /home/hedya/Desktop/bs_project/qt_project/scripts"
echo "  ./2_crop_and_build.sh"
