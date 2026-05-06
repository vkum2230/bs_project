# SMART RIDE 智能骑行码表 — 项目上下文

> 本文件用于为 Claude Code 提供项目级上下文，帮助快速理解代码库状态和开发方向。

---

## 1. 项目定位

**SMART RIDE** 是一款基于 **树莓派 5B + STM32** 的智能骑行码表项目，目标是为骑行爱好者提供集数据采集、实时显示、语音交互、地图导航、智能问答、安全告警于一体的骑行终端。

**数据链路：**
```
[STM32 采集传感器数据：速度/踏频/功率/心率/坡度/温度/后方距离/GPS]
        │ UART 串口 /dev/ttyAMA2 (JSON 协议, 115200bps)
        ▼
[树莓派 PyQt5 码表] ←──── 处理/显示/语音播报/地图导航/数据存储/AI对话
        │ BLE GATT (主通道) / MQTT over WiFi (备用通道)
        ▼
[手机 App] ←──────────── 接收实时数据、发送控制命令、查看历史记录
```

**树莓派角色：** 带屏显示终端 + 边缘智能节点 + 通信中继网关

---

## 2. 当前已实现功能

| # | 功能 | 文件/模块 | 状态 |
|---|------|----------|------|
| 1 | PyQt5 主界面（仪表盘 + 数据卡片 + 消息框 + 多页面导航） | `main.py`, `widgets/`, `ui/` | 完成 |
| 2 | 自定义圆形仪表盘控件 | `widgets/circle_gauge.py` | 完成 |
| 3 | 数据指标卡片控件 | `widgets/metric_card.py` | 完成 |
| 4 | STM32 串口数据采集（JSON 协议） | `drivers/serial_handler.py`, `core/protocol.py` | 完成 |
| 5 | 高德在线地图 + Leaflet 引擎 + QWebEngineView 嵌入 | `widgets/map_widget.py` | 完成 |
| 6 | 本地瓦片服务器（离线地图） | `utils/tile_server.py` | 完成 |
| 7 | 离线导航引擎（Valhalla 路由 + 中文语音播报） | `services/nav_engine.py` | 完成 |
| 8 | 地图页面（在线/离线双模式导航 + 轨迹回放） | `ui/map_page.py` | 完成 |
| 9 | 离线省份判断 + 高德定位 API | `core/location_service.py` | 完成 |
| 10 | 混合语音播放器（阿里云 TTS + Edge-TTS + Piper 离线） | `drivers/audio/piper_voice.py`, `voice_final.py` | 完成 |
| 11 | 多音频后端适配（PyAudio/pygame/AOSS/ReSpeaker/espeak） | `drivers/audio/` | 完成 |
| 12 | 按钮语音交互 + LED 状态指示 | `drivers/audio/button_handler.py`, `led_controller.py` | 完成 |
| 13 | 语音识别（ReSpeaker 阵列 + 百度/讯飞 API） | `drivers/audio/voice_recorder.py` | 完成 |
| 14 | 阿里云百炼大模型客户端 | `llm/bailian_client.py` | 完成 |
| 15 | Ollama 本地大模型客户端（自动选模型 + 流式输出） | `llm/ollama_client.py` | 完成 |
| 16 | 统一大模型客户端（在线/离线自动切换 + 骑行上下文注入） | `llm/unified_llm_client.py` | 完成 |
| 17 | 全局骑行数据上下文管理器 | `core/data_context.py` | 完成 |
| 18 | 串口日志重定向调试器 | `utils/serial_debugger.py` | 完成 |
| 19 | **BLE GATT Peripheral 服务器**（dbus-python + BlueZ） | `drivers/ble_gatt_server.py` | 完成 |
| 20 | MQTT 通信桥接器（xinjia.txt 协议） | `services/comm_service.py` (`MqttBridge`) | 完成 |
| 21 | 通信调度器（BLE + MQTT 统一调度 + 断连缓存） | `services/comm_service.py` | 完成 |
| 22 | 断连缓存队列 | `persistence/buffer_queue.py` | 完成 |
| 23 | 骑行会话管理（开始/暂停/结束/实时统计） | `services/ride_service.py` | 完成 |
| 24 | 骑行记录本地 FIT/GPX 存储 | `persistence/ride_repository.py` | 完成 |
| 25 | 历史记录页面 + 轨迹回放 | `ui/history_page.py` | 完成 |
| 26 | 连接页面（蓝牙广播/WiFi 状态/品牌展示） | `ui/connect_page.py` | 完成 |
| 27 | 安全告警系统（后方来车/心率/疲劳/跌倒/偏离路线） | `services/alert_service.py` | 完成 |
| 28 | 用户配置管理 + 设置页面 | `persistence/config_manager.py`, `ui/settings_page.py` | 完成 |
| 29 | 地图拼音输入法 | `ui/smart_pinyin_ime.py` | 完成 |
| 30 | 地图服务（瓦片管理/地理编码/路径规划） | `services/map_service.py` | 完成 |

### 重要历史变更
- **BLE 通信已迁移**：旧版 `drivers/ble_server.py` 是 RFCOMM/SPP 经典蓝牙实现（已废弃），当前使用 `drivers/ble_gatt_server.py`（BLE GATT Peripheral，dbus-python + BlueZ）。旧实现保留在 git tag `checkpoint-2026-04-24`（commit `4309660`）。
- **WiFi WebSocket Server 已移除**：原先 `drivers/wifi_server.py` 的 WebSocket 方案已废弃，通信统一由 BLE GATT + MQTT 双通道覆盖。

---

## 3. 当前核心状态与待解决问题

### 已完成的 P0/P1 功能
- BLE GATT Peripheral 注册/广播/连接/数据传输/断开重连 ✅
- MQTT 通信桥接 + 心跳机制 + 断线恢复 ✅
- 骑行会话全生命周期管理 + FIT/GPX 导出 ✅
- 安全告警系统（4类告警场景）✅
- 历史记录页面 + 轨迹回放 ✅
- 设置页面 + 配置持久化 ✅
- 地图导航（在线高德 + 离线 Valhalla 双模式）✅
- 语音交互（混合 TTS + ASR + LLM 对话）✅

### 当前待验证/优化项（按优先级）
- **BLE 数据发送验证**：App 端订阅 Notify（FF01）后，需验证 `PropertiesChanged` 信号能否稳定到达手机
- **BLE 写通道验证**：App 向 FF03 写入命令，需验证 `WriteValue` 回调和 `command_received` 信号
- **MQTT 断连缓存补发联调**：`BufferQueue` 已就绪，需在真实断网/重连场景下验证批量补发
- **导航语音播报时机微调**：当前 50 米触发阈值在快速骑行时可能偏晚，需实测调整
- **Piper TTS 中文模型自然度**：离线语音质量仍有提升空间，可尝试更大模型

### 中长期扩展方向（P2+）
- BLE/ANT+ 外设直连（树莓派直接连心率带/功率计，绕过 STM32）
- 行车记录仪（摄像头循环录制 + OSD 数据叠加）
- 结构化功率训练课程（ZWO/JSON 导入）
- 云同步后端（骑行记录增量上传）
- OTA 固件升级（App 远程升级 STM32 + 树莓派）
- 电子围栏/防盗定位（停车监测 + 位移告警）
- 组队骑行（多设备位置共享）

---

## 4. 技术栈

| 层级 | 技术 |
|------|------|
| UI 框架 | PyQt5（纯 QWidget，无 QML） |
| 地图引擎 | Leaflet.js + 高德 JS API（在线）+ 本地瓦片服务器（离线） |
| 离线路由 | Valhalla（OpenStreetMap PBF → 图贴片） |
| 语音 TTS | 阿里云通义 TTS（dashscope，首选）+ Edge-TTS（在线回退）+ Piper（本地 ONNX，离线兜底） |
| 语音 ASR | 百度/讯飞语音 API（在线）+ Whisper tiny/base（本地备选） |
| 大模型 | 阿里云百炼 API（在线）+ Ollama 本地服务（Qwen2.5/Llama3-Chinese） |
| BLE 通信 | `python-dbus` + `dbus-python` + BlueZ D-Bus API（GATT Peripheral） |
| MQTT 通信 | `paho-mqtt` (CallbackAPIVersion.VERSION2) |
| 文件格式 | FIT (`garmin-fit-sdk`) / GPX (`gpxpy`) |
| 地图瓦片 | 本地文件系统 (Z/X/Y.png) + HTTP 服务器 |
| 数据库 | SQLite (`sqlite3` 内置模块) |

---

## 5. 当前目录结构

```
qt_project/
├── main.py                      # 入口，BikeComputerPro 主窗口逻辑
│
├── ui/                          # UI 页面层
│   ├── connect_page.py          # 首屏连接页（蓝牙广播/WiFi/品牌展示）
│   ├── map_page.py              # 地图页（导航/轨迹显示）
│   ├── history_page.py          # 历史记录页（列表 + 轨迹回放）
│   ├── settings_page.py         # 系统设置页（心率阈值/告警开关/语音偏好）
│   └── smart_pinyin_ime.py      # 智能拼音输入法（地图搜索）
│
├── widgets/                     # 可复用控件
│   ├── map_widget.py            # 高德/Leaflet 地图组件（位置标记 + 航向 + 导航）
│   ├── circle_gauge.py          # 圆形仪表盘（速度/功率）
│   ├── metric_card.py           # 传感器数据卡片
│   └── small_data_box.py        # 小型数据展示框
│
├── services/                    # 业务服务层
│   ├── comm_service.py          # BLE + MQTT 统一调度（xinjia.txt 协议）
│   ├── ride_service.py          # 骑行会话管理（开始/暂停/结束/统计）
│   ├── alert_service.py         # 安全告警（后方来车/心率/疲劳/跌倒/偏离路线）
│   ├── nav_engine.py            # 离线导航引擎（Valhalla 路由 + 中文指令）
│   └── map_service.py           # 地图服务（瓦片/地理编码/路径规划）
│
├── core/                        # 核心领域层
│   ├── data_context.py          # 全局骑行数据上下文（单例，供 LLM 使用）
│   ├── location_service.py      # 定位服务（离线省份判断 + 高德定位 API）
│   ├── protocol.py              # 统一数据协议（SensorData / RideSummary / AppCommand）
│   └── __init__.py
│
├── drivers/                     # 硬件驱动层
│   ├── serial_handler.py        # STM32 串口读取（QThread + JSON 解析）
│   ├── ble_gatt_server.py       # **[当前]** BLE GATT Peripheral（dbus-python + BlueZ）
│   ├── ble_server.py            # **[旧版/废弃]** RFCOMM 经典蓝牙（保留于 checkpoint-2026-04-24）
│   └── audio/                   # 语音子模块
│       ├── piper_voice.py       # HybridVoicePlayer（Piper + Edge-TTS + 阿里云 TTS）
│       ├── voice_final.py       # 阿里云通义 TTS 播放器（流式输出 + espeak 兜底）
│       ├── voice_player.py      # 基础语音播放器
│       ├── voice_recorder.py    # 按钮语音助手 + ReSpeaker 录音
│       ├── voice_smart.py       # 智能语音调度
│       ├── voice_aoss.py        # AOSS 音频输出适配
│       ├── voice_edge.py        # Edge-TTS 播放器
│       ├── voice_pyaudio.py     # PyAudio 音频输出
│       ├── voice_pygame.py      # pygame 音频输出
│       ├── voice_respeaker.py   # ReSpeaker 专用播放器
│       ├── voice_simple.py      # 简化版语音播放器
│       ├── offline_voice.py     # 离线语音引擎适配
│       ├── led_controller.py    # APA102 LED 灯控制
│       ├── button_handler.py    # GPIO 按钮事件处理
│       └── audio_check.py       # 音频设备自检
│
├── persistence/                 # 持久化层
│   ├── ride_repository.py       # FIT/GPX 读写 + SQLite 骑行记录管理
│   ├── config_manager.py        # 用户配置管理（JSON 文件）
│   └── buffer_queue.py          # 断连缓存队列（时间/容量双限制）
│
├── llm/                         # 大模型层
│   ├── unified_llm_client.py    # 统一客户端（百炼/Ollama 自动切换 + 骑行上下文注入）
│   ├── bailian_client.py        # 阿里云百炼 API 客户端
│   ├── ollama_client.py         # Ollama 本地客户端（自动选模型 + 流式输出）
│   └── __init__.py
│
├── utils/                       # 工具类
│   ├── serial_debugger.py       # 串口日志重定向调试器
│   └── tile_server.py           # 本地 HTTP 瓦片服务器
│
├── tests/                       # 测试
│   ├── test_ble_gatt.py
│   ├── test_buffer_queue.py
│   ├── test_data_context.py
│   ├── test_navigation.py
│   ├── test_voice_system.py
│   └── ...
│
├── old_files/                   # 历史归档（诊断脚本、测试脚本）
│   ├── diagnose/
│   ├── scripts/
│   └── tests/
│
├── maps/                        # 地图数据
│   ├── xiangtan_tiles/          # 本地离线瓦片 (Z/X/Y.png)
│   ├── osm/                     # OpenStreetMap 数据
│   └── valhalla_data/           # Valhalla 路由图贴片
│
├── leaflet/                     # Leaflet.js 静态资源
│   ├── leaflet.js
│   └── leaflet.css
│
├── TuBiao/                      # 图标资源
│   └── *.png
│
└── valhalla/                    # Valhalla 路由引擎源码/依赖（子模块）
```

---

## 6. 关键数据协议

### STM32 → 树莓派（JSON 格式）
```json
{
  "speed": 25.4,
  "cadence": 90,
  "power": 220,
  "distance": 15.25,
  "ride_time": 3600,
  "slope": 3.5,
  "zt_flag": 5,
  "yaw": 60,
  "temperature": 26.5,
  "heart_rate": 145,
  "rear_dist": 12.5,
  "err_code": 0,
  "location": {
    "lat": 27.8293,
    "lon": 112.9448
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `speed` | float | 速度 km/h |
| `cadence` | float | 踏频 rpm |
| `power` | float | 功率 W |
| `distance` | float | 骑行距离 km |
| `ride_time` | int | 骑行时间秒 |
| `slope` | float | 坡度 % |
| `zt_flag` | int | 姿态：0=跌倒 1=右转 2=左转 3=上坡 4=下坡 5=正常 |
| `yaw` | float | IMU 航偏角，0°指北，顺时针增加 |
| `temperature` | float | 温度 °C |
| `heart_rate` | float | 心率 bpm |
| `rear_dist` | float | 后方来车距离 m |
| `err_code` | int | 错误码（0=正常） |
| `location` | object | GPS 坐标 {lat, lon} |

### 树莓派 ↔ App（xinjia.txt 协议）
- **BLE GATT 通道**：Service UUID `0000FF00-0000-1000-8000-00805F9B34FB`
  - Notify 特征值 `FF01`：码表 → App 推送数据（JSON，>180B 自动分包 `[seq,total,payload...]`）
  - Write 特征值 `FF03`：App → 码表发送命令（JSON）
- **MQTT 通道**（备用）：`paho-mqtt` 桥接 EMQX Broker

### MQTT Topic 定义（xinjia.txt）
| Topic | 方向 | 频率 | 说明 |
|-------|------|------|------|
| `deviceData_1` | 码表 → App | 1Hz | 实时骑行数据（JSON） |
| `delayData_1` | 码表 → App | 事件触发 | 告警、状态变化、非实时数据 |
| `deviceHeart_1` | 码表 → App | 5秒 | 设备心跳 + 连接握手 |
| `appHeart_1` | App → 码表 | 5秒 | App 心跳 / 连接请求 |
| `appData_1` | App → 码表 | 事件触发 | App 命令（开始/暂停/导航等） |

### App 命令格式
```json
{"cmd": "start_ride", "payload": {}, "timestamp": 1713532800.0}
```
支持命令：`start_ride`, `pause_ride`, `resume_ride`, `stop_ride`, `set_target`, `load_route`, `set_nav_destination`, `update_config`, `ping` 等。

---

## 7. BLE GATT 关键设计与注意事项

### 架构概览
`BleGattServer(QThread)` 通过 `dbus-python` 与 BlueZ D-Bus 交互：
1. `run()` 中注册 `Application`（ObjectManager + GetManagedObjects）到 `GattManager1`
2. 注册 `Advertisement`（LEAdvertisement1）到 `LEAdvertisingManager1`
3. 启动 `GLib.MainLoop`，通过 `timeout_add` 处理发送队列和连接检测

### 关键 UUID
| 角色 | UUID |
|------|------|
| Service | `0000FF00-0000-1000-8000-00805F9B34FB` |
| Notify Characteristic | `0000FF01-0000-1000-8000-00805F9B34FB` |
| Write Characteristic | `0000FF03-0000-1000-8000-00805F9B34FB` |
| 设备广播名 | `SMART-RIDE` |

### 已知坑点与解决方案
1. **BlueZ experimental 模式**：`bluetoothd` 必须带 `--experimental` 启动，否则 `GattManager1` / `LEAdvertisingManager1` 不可用。修改方式：`sudo systemctl edit bluetooth` → 在 `ExecStart` 后加 `--experimental`。
2. **DBus 类型签名严格**：`GetManagedObjects` 返回值必须使用显式 `dbus.Dictionary(..., signature="sa{sv}")` 和 `dbus.Array(..., signature="o")`，否则 bluez 报 `No valid service object found`。
3. **断开重连后 dbus 路径冲突**：旧 `dbus.service.Object` 在 `__del__` 中会调用 `remove_from_connection()`，若在新对象创建后执行会误注销新路径。**解决方案**：`_unregister()` 中显式 `remove_from_connection()` 后将 `_object_path` 设为 `"/__removed__"`，阻断 `__del__` 竞争；`start_advertising()` 前调用 `gc.collect()` 强制旧对象析构。
4. **QThread 生命周期**：`QThread.start()` 在线程仍在运行时会静默忽略。`start_advertising()` / `stop_advertising()` 中必须先 `wait()` 等待前一次线程结束，再启动新线程。
5. **MTU 限制**：Notify 包安全长度 180B，超限需按 `[seq(1B), total(1B), payload...]` 格式分包，App 端负责重组。

---

## 8. 开发优先级与当前建议

**当前最重要的事：** 验证 App 端 BLE Notify 订阅后的端到端数据通路（`_send_raw` → `PropertiesChanged` → App 接收），以及 App Write 命令的接收链路。

**建议的调试/优化顺序：**
1. **BLE 数据通量验证**：用 nRF Connect 或自研 App 测试 Notify 订阅后的大包数据传输
2. **BLE 写命令验证**：测试 App 向 FF03 写入 JSON 命令，确认 `WriteValue` → `command_received` 链路
3. **MQTT 断连缓存补发联调**：`BufferQueue` 已就绪，在真实弱网场景下验证批量补发
4. **导航语音播报阈值实测**：快速骑行（>40km/h）时 50 米触发可能偏晚，需根据实际路测调整
5. **LLM 对话响应优化**：当前非流式调用延迟 2-5 秒，可考虑流式输出 + 首 token 即播

**不要先做/可以后放的功能：**
- 行车记录仪、功率训练课程、云同步、组队骑行、OTA、防盗 —— 当前 P0/P1 已跑通，这些是锦上添花。

---

## 9. 给 Claude Code 的开发提示

1. **主文件 `main.py` 已瘦身**：控件和工具已拆分到 `widgets/`、`utils/`、`ui/` 目录。新增功能继续按分层目录开发，不要往 `main.py` 堆代码。

2. **语音模块已高度封装**：`drivers/audio/piper_voice.py` 的 `HybridVoicePlayer` 是统一入口，内部自动调度阿里云 TTS → Edge-TTS → Piper 三个引擎。新功能需要语音播报时直接复用 `self.voice_player.speak()`。

3. **DataContext 是中心数据源**：所有需要向 LLM 提供上下文或刷新 UI 的功能，都应通过 `core/data_context.py` 读写，不要绕过它直接改 UI。

4. **BLE GATT 是当前的通信主干**：`drivers/ble_gatt_server.py` 是活跃实现，`drivers/ble_server.py`（RFCOMM）已废弃。修改 BLE 相关代码时务必注意 dbus 对象生命周期和 `__del__` 竞争问题。

5. **高德地图在线，但已有离线兜底**：`widgets/map_widget.py` 默认加载在线高德地图；无网时 `utils/tile_server.py` 提供本地瓦片，`services/nav_engine.py` 提供 Valhalla 离线路由。修改地图逻辑时需同时考虑两种模式。

6. **树莓派性能有限**：Ollama 已通过 `num_ctx=512`、`num_thread=4` 优化。新增 heavy 计算（如 Whisper ASR、视频编码）要先评估 CPU 占用和延迟。

7. **通信协议统一走 xinjia.txt**：BLE 和 MQTT 使用同一套 JSON 协议格式，由 `services/comm_service.py` 统一调度。新增通信功能时不要重复造协议。

---

## 10. 高频修改点速查

| 需求 | 修改位置 |
|------|---------|
| 新增数据字段显示 | `core/protocol.py` (SensorData) → `core/data_context.py` → `main.py` `on_data_received()` → UI 控件 |
| 新增语音播报场景 | 复用 `drivers.audio.piper_voice.HybridVoicePlayer.speak()` |
| 新增 AI 回答能力 | 改 `llm/unified_llm_client.py` 的 system prompt 或 model 参数 |
| 新增 BLE 服务/特征值 | 改 `drivers/ble_gatt_server.py` 中的 UUID 常量和 Characteristic 类 |
| 新增地图交互 | `widgets/map_widget.py`（JS 侧）+ `services/map_service.py`（Python 侧） |
| 新增骑行记录保存 | 改 `persistence/ride_repository.py` 的 `save_ride()` |
| 新增安全告警类型 | 改 `core/protocol.py` (AlertType) + `services/alert_service.py` |
| 新增 App 命令 | 改 `core/protocol.py` (AppCommandType) + `services/comm_service.py` `_on_ble_command()` |

---

*最后更新：2026-05-02*
