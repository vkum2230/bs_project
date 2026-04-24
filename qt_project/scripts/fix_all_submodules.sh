#!/bin/bash
# 修复 Valhalla 所有缺失的 third_party 子模块

set -e

THIRD_PARTY="/home/hedya/Desktop/bs_project/qt_project/valhalla/third_party"

echo "========================================"
echo "[Fix] 检查并修复所有 third_party 子模块..."
echo "========================================"

cd "$THIRD_PARTY"

# microtar
if [ ! -f "microtar/src/microtar.h" ]; then
    echo "[Fix] 下载 microtar..."
    rm -rf microtar
    git clone --depth=1 https://github.com/rxi/microtar.git microtar || \
        git clone --depth=1 https://ghproxy.com/https://github.com/rxi/microtar.git microtar || \
        git clone --depth=1 https://gh.api.99988866.xyz/https://github.com/rxi/microtar.git microtar
fi

# rapidjson (可能也需要)
if [ ! -d "rapidjson" ]; then
    echo "[Fix] 下载 rapidjson..."
    git clone --depth=1 https://github.com/Tencent/rapidjson.git rapidjson || \
        git clone --depth=1 https://ghproxy.com/https://github.com/Tencent/rapidjson.git rapidjson || \
        git clone --depth=1 https://gh.api.99988866.xyz/https://github.com/Tencent/rapidjson.git rapidjson
fi

# date (可能也需要)
if [ ! -d "date" ]; then
    echo "[Fix] 下载 date..."
    git clone --depth=1 https://github.com/HowardHinnant/date.git date || \
        git clone --depth=1 https://ghproxy.com/https://github.com/HowardHinnant/date.git date || \
        git clone --depth=1 https://gh.api.99988866.xyz/https://github.com/HowardHinnant/date.git date
fi

echo ""
echo "========================================"
echo "[Fix] 子模块修复完成！"
echo "========================================"
echo ""
echo "现在重新编译 Valhalla："
echo "  cd /home/hedya/Desktop/bs_project/qt_project/scripts"
echo "  ./2_crop_and_build.sh"
