#!/bin/bash
# 编译 Valhalla（纯 CLI 模式，不需要 prime_server）

set -e

PROJECT_DIR="/home/hedya/Desktop/bs_project/qt_project"
VALHALLA_DIR="$PROJECT_DIR/valhalla"
DATA_DIR="$PROJECT_DIR/maps/valhalla_data"

echo "========================================"
echo "[Step 2] 准备数据目录..."
mkdir -p "$DATA_DIR"
mkdir -p "$VALHALLA_DIR/build"

echo ""
echo "========================================"
echo "[Step 2] 裁剪湘潭市 OSM 数据..."
echo "边界框: 112.78,27.72 至 113.15,28.05"

if [ ! -f "$DATA_DIR/xiangtan.osm.pbf" ]; then
    osmium extract -b 112.78,27.72,113.15,28.05 \
        "$PROJECT_DIR/maps/osm/hunan-latest.osm.pbf" \
        -o "$DATA_DIR/xiangtan.osm.pbf"
    echo "[Step 2] 裁剪完成！"
else
    echo "[Step 2] 湘潭数据已存在，跳过裁剪"
fi

echo ""
echo "========================================"
echo "[Step 2] 编译 Valhalla（CLI 模式）..."
echo "⚠️  这约需 20-60 分钟，请耐心等待"
echo "========================================"

cd "$VALHALLA_DIR/build"

# 关键：ENABLE_SERVICES=OFF 不需要 prime_server
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF \
    -DENABLE_DATA_TOOLS=ON \
    -DENABLE_SERVICES=OFF \
    -DENABLE_PYTHON_BINDINGS=OFF \
    -DBUILD_TESTING=OFF

make -j$(nproc)

echo ""
echo "========================================"
echo "[Step 2] 编译完成！"
echo "可执行文件在: $VALHALLA_DIR/build/"
echo "========================================"
