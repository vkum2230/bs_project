#!/bin/bash
# 修复 googletest 缺失 + 清理错误的 submodule 记录

set -e

echo "========================================"
echo "[Fix] 清理错误的 submodule 记录..."
echo "========================================"

cd /home/hedya/Desktop/bs_project

# 移除错误的 submodule 索引（不影响实际文件）
git rm --cached voice_driver/mic_hat 2>/dev/null || true
rm -rf .git/modules/voice_driver 2>/dev/null || true

echo ""
echo "========================================"
echo "[Fix] 手动拉取 googletest..."
echo "========================================"

cd /home/hedya/Desktop/bs_project/qt_project/valhalla/third_party

# 如果目录存在但为空，删除它
if [ -d "googletest" ] && [ ! -f "googletest/CMakeLists.txt" ]; then
    rm -rf googletest
fi

# 克隆 googletest
if [ ! -d "googletest" ]; then
    git clone --depth=1 https://github.com/google/googletest.git
fi

echo ""
echo "========================================"
echo "[Fix] googletest 已就绪！"
echo "========================================"
echo ""
echo "现在重新编译 Valhalla："
echo "  cd /home/hedya/Desktop/bs_project/qt_project/scripts"
echo "  ./2_crop_and_build.sh"
