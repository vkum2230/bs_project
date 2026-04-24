#!/bin/bash
# 第 3 步：生成 Valhalla Tile 数据 + 启动本地路由服务

set -e

PROJECT_DIR="/home/hedya/Desktop/bs_project/qt_project"
VALHALLA_DIR="$PROJECT_DIR/valhalla"
DATA_DIR="$PROJECT_DIR/maps/valhalla_data"
TILE_DIR="$DATA_DIR/valhalla_tiles"

mkdir -p "$TILE_DIR"

echo "========================================"
echo "[Step 3] 生成 Valhalla 配置文件..."
echo "========================================"

cd "$VALHALLA_DIR/build"

# 生成标准配置并清理不存在的路径
python3 "$VALHALLA_DIR/build/valhalla_build_config" \
    --mjolnir-tile-dir "$TILE_DIR" \
    --mjolnir-admin "$DATA_DIR/admins.sqlite" \
    --mjolnir-timezone "$DATA_DIR/timezones.sqlite" \
    > "$DATA_DIR/valhalla.json.raw"

# 清理配置中不存在的路径，避免 WARN 日志刷屏
python3 -c "
import json
d = json.load(open('$DATA_DIR/valhalla.json.raw'))
# 清空不存在的路径
d['mjolnir']['tile_extract'] = ''
d['mjolnir']['traffic_extract'] = ''
d['mjolnir']['landmarks'] = ''
d['additional_data']['elevation'] = ''
json.dump(d, open('$DATA_DIR/valhalla.json', 'w'), indent=2, ensure_ascii=False)
"
rm "$DATA_DIR/valhalla.json.raw"

echo "[Step 3] 配置文件已保存到 $DATA_DIR/valhalla.json"

echo ""
echo "========================================"
echo "[Step 3] 生成 Valhalla Tiles..."
echo "⚠️  这约需 5-20 分钟"
echo "========================================"

# 生成 timezone 数据（如果还没有）
if [ ! -f "$DATA_DIR/timezones.sqlite" ]; then
    ./valhalla_build_timezones > "$DATA_DIR/timezones.sqlite" 2>/dev/null || true
fi

# 生成 admin 数据
./valhalla_build_admins \
    --config "$DATA_DIR/valhalla.json" \
    "$DATA_DIR/xiangtan.osm.pbf" 2>/dev/null || true

# 生成 tiles
./valhalla_build_tiles \
    -c "$DATA_DIR/valhalla.json" \
    "$DATA_DIR/xiangtan.osm.pbf"

echo ""
echo "========================================"
echo "[Step 3] Tiles 生成完成！"
echo "目录: $TILE_DIR"
ls -lh "$TILE_DIR" | head -5
echo "..."
echo "========================================"
echo ""
echo "[Step 3] 启动 Valhalla 服务..."
echo "========================================"

# 杀掉之前的服务（如果有）
pkill -f "valhalla_service" 2>/dev/null || true
sleep 1

# 后台启动服务
nohup ./valhalla_service "$DATA_DIR/valhalla.json" > "$DATA_DIR/valhalla.log" 2>&1 &

sleep 3

# 检查服务是否启动
if curl -s http://localhost:8002/route >/dev/null 2>&1; then
    echo "✅ Valhalla 服务已启动: http://localhost:8002"
    echo ""
    echo "测试骑行路线："
    echo "  curl -X POST http://localhost:8002/route \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"locations\":[{\"lon\":112.93,\"lat\":27.83},{\"lon\":112.95,\"lat\":27.85}],\"costing\":\"bicycle\"}'"
else
    echo "⚠️ 服务可能还在启动中，查看日志："
    echo "  tail -f $DATA_DIR/valhalla.log"
fi
