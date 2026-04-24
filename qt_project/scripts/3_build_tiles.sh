#!/bin/bash
# 第 3 步：生成 Valhalla Tile 数据 + 启动本地路由服务

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
    "actions": ["locate", "route", "sources_to_targets", "optimized_route", "isochrone", "trace_route", "trace_attributes", "transit_available"],
    "logging": {"long_request": 100.0},
    "service": {"proxy": "ipc:///tmp/loki"},
    "service_defaults": {"minimum_reachability": 50, "radius": 0, "search_cutoff": 35000, "node_snap_tolerance": 5, "street_side_tolerance": 5, "heading_tolerance": 60}
  },
  "thor": {
    "logging": {"long_request": 110.0},
    "service": {"proxy": "ipc:///tmp/thor"},
    "source_to_target_algorithm": "select_optimal"
  },
  "odin": {
    "logging": {"long_request": 110.0},
    "service": {"proxy": "ipc:///tmp/odin"},
    "markup_formatter": {"markup_enabled": false}
  },
  "tyr": {
    "logging": {"long_request": 100.0},
    "service": {"proxy": "ipc:///tmp/tyr"},
    "costmatrix": {"max_matrix_distance": 400000.0, "max_matrix_locations": 50}
  },
  "meili": {
    "mode": "multimodal",
    "customizable": ["mode", "search_radius", "turn_penalty_factor", "gps_accuracy", "interpolation_distance", "sigma_z", "beta", "max_route_distance_factor", "max_route_time_factor"],
    "verbose": false,
    "default": {
      "sigma_z": 4.07,
      "gps_accuracy": 5.0,
      "beta": 3,
      "max_route_distance_factor": 5,
      "max_route_time_factor": 5,
      "turn_penalty_factor": 0
    }
  },
  "httpd": {
    "service": {
      "listen": "tcp://*:8002",
      "loopback": "ipc:///tmp/valhalla",
      "interrupt": "ipc:///tmp/valhalla_interrupt"
    }
  },
  "costing_options": {
    "auto": {"maneuver_penalty": 5.0, "destination_only_penalty": 600.0, "alley_penalty": 5.0, "alley_factor": 1.0, "service_penalty": 15.0, "service_factor": 1.0, "country_crossing_cost": 600.0, "country_crossing_penalty": 0.0, "use_tolls": 0.5, "use_highways": 1.0, "use_ferry": 0.5, "ferry_cost": 300.0, "use_living_streets": 0.5, "use_tracks": 0.0, "private_access_penalty": 450.0, "ignore_closures": false, "ignore_restrictions": false, "closure_factor": 9.0, "disable_hierarchy_pruning": false, "top_speed": 140},
    "bicycle": {"maneuver_penalty": 5.0, "destination_only_penalty": 600.0, "alley_penalty": 5.0, "alley_factor": 1.0, "service_penalty": 15.0, "service_factor": 1.0, "country_crossing_cost": 600.0, "country_crossing_penalty": 0.0, "use_ferry": 0.5, "ferry_cost": 300.0, "use_living_streets": 0.5, "use_tracks": 0.0, "private_access_penalty": 450.0, "bicycle_type": "Road", "cycling_speed": 20.0, "use_roads": 0.5, "use_hills": 0.5, "avoid_bad_surfaces": 0.25, "top_speed": 60.0},
    "pedestrian": {"maneuver_penalty": 5.0, "alley_factor": 1.0, "alley_penalty": 5.0, "destination_only_penalty": 600.0, "service_penalty": 15.0, "service_factor": 1.0, "country_crossing_cost": 600.0, "country_crossing_penalty": 0.0, "use_ferry": 0.5, "ferry_cost": 300.0, "use_living_streets": 0.5, "use_tracks": 0.0, "private_access_penalty": 450.0, "step_penalty": 30.0, "max_hiking_difficulty": 1, "use_hills": 0.5}
  },
  "service_limits": {
    "auto": {"max_distance": 5000000.0, "max_locations": 20, "max_matrix_distance": 400000.0, "max_matrix_locations": 50},
    "auto_shorter": {"max_distance": 5000000.0, "max_locations": 20, "max_matrix_distance": 400000.0, "max_matrix_locations": 50},
    "bicycle": {"max_distance": 500000.0, "max_locations": 50, "max_matrix_distance": 200000.0, "max_matrix_locations": 50},
    "bus": {"max_distance": 5000000.0, "max_locations": 50, "max_matrix_distance": 400000.0, "max_matrix_locations": 50},
    "hov": {"max_distance": 5000000.0, "max_locations": 20, "max_matrix_distance": 400000.0, "max_matrix_locations": 50},
    "motor_scooter": {"max_distance": 500000.0, "max_locations": 50, "max_matrix_distance": 200000.0, "max_matrix_locations": 50},
    "multimodal": {"max_distance": 500000.0, "max_locations": 50, "max_matrix_distance": 0.0, "max_matrix_locations": 0},
    "pedestrian": {"max_distance": 250000.0, "max_locations": 50, "max_matrix_distance": 200000.0, "max_matrix_locations": 50},
    "transit": {"max_distance": 500000.0, "max_locations": 50, "max_matrix_distance": 200000.0, "max_matrix_locations": 50},
    "truck": {"max_distance": 5000000.0, "max_locations": 20, "max_matrix_distance": 400000.0, "max_matrix_locations": 50},
    "skadi": {"max_shape": 750000, "min_resample": 10.0},
    "isochrone": {"max_contours": 4, "max_time": 120, "max_distance": 25000, "max_locations": 1},
    "trace": {"max_distance": 200000.0, "max_gps_accuracy": 100.0, "max_search_radius": 100, "max_shape": 16000, "max_best_paths": 4, "max_best_paths_shape": 100},
    "max_exclude_locations": 50
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

# 下载 timezone 和 admin 数据（Valhalla 需要）
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
echo "[Step 3] 现在可以启动 Valhalla 服务了："
echo "  cd $VALHALLA_DIR/build"
echo "  ./valhalla_service $DATA_DIR/valhalla.json 1"
echo ""
echo "服务启动后，测试路由："
echo "  curl -X POST http://localhost:8002/route \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"locations\":[{\"lon\":112.93,\"lat\":27.83},{\"lon\":112.95,\"lat\":27.85}],\"costing\":\"bicycle\"}'"
