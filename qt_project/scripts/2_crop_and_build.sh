#!/bin/bash
# 第 2 步：裁剪湖南省数据为湘潭市 + 编译 Valhalla

set -e

PROJECT_DIR="/home/hedya/Desktop/bs_project/qt_project"
OSM_DIR="$PROJECT_DIR/maps/osm"
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
        "$OSM_DIR/hunan-latest.osm.pbf" \
        -o "$DATA_DIR/xiangtan.osm.pbf"
    echo "[Step 2] 裁剪完成！"
else
    echo "[Step 2] 湘潭数据已存在，跳过裁剪"
fi

echo ""
echo "========================================"
echo "[Step 2] 编译 Valhalla..."
echo "⚠️  这可能需要 30-90 分钟，请耐心等待"
echo "========================================"

cd "$VALHALLA_DIR/build"

cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF \
    -DENABLE_DATA_TOOLS=ON \
    -DENABLE_SERVICES=ON \
    -DENABLE_PYTHON_BINDINGS=OFF \
    -DBUILD_TESTING=OFF

make -j$(nproc)

echo ""
echo "[Step 2] 编译完成！"
