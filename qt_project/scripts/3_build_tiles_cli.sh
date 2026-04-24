#!/bin/bash
# 第 3 步：生成 Valhalla Tile 数据（CLI 模式）

set -e

PROJECT_DIR="/home/hedya/Desktop/bs_project/qt_project"
VALHALLA_DIR="$PROJECT_DIR/valhalla"
DATA_DIR="$PROJECT_DIR/maps/valhalla_data"
TILE_DIR="$DATA_DIR/valhalla_tiles"

echo "========================================"
echo "[Step 3] 生成 Valhalla 配置文件..."

mkdir -p "$TILE_DIR"

cat > "$DATA_DIR/valhalla.json" << 'EOF'
{
  "mjolnir": {
    "tile_dir": "/home/hedya/Desktop/bs_project/qt_project/maps/valhalla_data/valhalla_tiles",
    "tile_extract": "",
    "timezone": "/home/hedya/Desktop/bs_project/qt_project/maps/valhalla_data/timezones.sqlite",
    "admin": "/home/hedya/Desktop/bs_project/qt_project/maps/valhalla_data/admins.sqlite"
  },
  "loki": {
    "actions": ["locate", "route", "sources_to_targets", "optimized_route", "isochrone", "trace_route", "trace_attributes"],
    "logging": {"long_request": 100.0},
    "service_defaults": {"minimum_reachability": 50, "radius": 0, "search_cutoff": 35000, "node_snap_tolerance": 5, "street_side_tolerance": 5, "heading_tolerance": 60}
  },
  "thor": {
    "logging": {"long_request": 110.0},
    "source_to_target_algorithm": "select_optimal"
  },
  "odin": {
    "logging": {"long_request": 110.0},
    "markup_formatter": {"markup_enabled": false}
  },
  "costing_options": {
    "bicycle": {"maneuver_penalty": 5.0, "destination_only_penalty": 600.0, "alley_penalty": 5.0, "alley_factor": 1.0, "service_penalty": 15.0, "service_factor": 1.0, "country_crossing_cost": 600.0, "country_crossing_penalty": 0.0, "use_ferry": 0.5, "ferry_cost": 300.0, "use_living_streets": 0.5, "use_tracks": 0.0, "private_access_penalty": 450.0, "bicycle_type": "Road", "cycling_speed": 20.0, "use_roads": 0.5, "use_hills": 0.5, "avoid_bad_surfaces": 0.25, "top_speed": 60.0}
  },
  "service_limits": {
    "bicycle": {"max_distance": 500000.0, "max_locations": 50, "max_matrix_distance": 200000.0, "max_matrix_locations": 50}
  }
}
EOF

echo "[Step 3] 配置文件已保存到 $DATA_DIR/valhalla.json"

echo ""
echo "========================================"
echo "[Step 3] 生成 Valhalla Tiles..."
echo "⚠️  这约需 5-20 分钟"
echo "========================================"

cd "$VALHALLA_DIR/build"

# 生成 timezone 和 admin 数据
./valhalla_build_timezones 2>/dev/null || true
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
echo "现在可以测试路线规划了："
echo "  cd $VALHALLA_DIR/build"
echo "  echo '{\"locations\":[{\"lon\":112.93,\"lat\":27.83},{\"lon\":112.95,\"lat\":27.85}],\"costing\":\"bicycle\",\"directions_options\":{\"units\":\"kilometers\"}}' | \\"
echo "    ./valhalla_run_route -c $DATA_DIR/valhalla.json"
