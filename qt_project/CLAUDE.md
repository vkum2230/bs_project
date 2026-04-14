# SMART RIDE 智能骑行码表 — 项目上下文

> 本文件用于为 Claude Code 提供项目级上下文，帮助快速理解代码库状态和开发方向。

---

## 1. 项目定位

**SMART RIDE** 是一款基于 **树莓派 5B + STM32** 的智能骑行码表项目。

**数据链路：**
```
[STM32 采集传感器数据]
        │ UART 串口 /dev/ttyAMA2
        ▼
[树莓派 PyQt 码表] ←──── 处理/显示/语音/导航/存储
        │ BLE / WiFi
        ▼
[手机 App] ←──────────── 接收实时数据、历史记录、配置设备
```

**树莓派角色：** 带屏显示终端 + 边缘智能节点 + 通信中继网关

---

## 2. 当前已实现功能

| # | 功能 | 文件/模块 | 状态 |
|---|------|----------|------|
| 1 | PyQt5 主界面（仪表盘 + 数据卡片 + 消息框） | `main.py`, `ui_main_window.py` | 完成 |
| 2 | 自定义圆形仪表盘控件 | `widgets/circle_gauge.py` | 完成 |
| 3 | STM32 串口数据采集（JSON 协议） | `drivers/serial_handler.py` | 完成 |
| 4 | 高德在线地图（JS API）+ 实时位置标记 | `widgets/map_widget.py` | 完成 |
| 5 | 离线省份判断 + 语音播报 | `core/location_service.py` | 完成 |
| 6 | Piper 本地 TTS + Edge-TTS 在线回退 | `drivers/audio/piper_voice.py` | 完成 |
| 7 | 按钮语音交互（GPIO 17）+ LED 状态指示 | `drivers/audio/voice_recorder.py` | 完成 |
| 8 | Ollama 本地大模型自动连接/选择/流式输出 | `llm/ollama_client.py` | 完成 |
| 9 | 全局骑行数据上下文管理器 | `core/data_context.py` | 完成 |
| 10 | 串口日志重定向调试器 | `utils/serial_debugger.py` | 完成 |
| 11 | 经典蓝牙 RFCOMM Server | `drivers/ble_server.py` | 完成 |
| 12 | WiFi WebSocket Server | `drivers/wifi_server.py` | 完成 |
| 13 | 通信调度器（BLE + WiFi 统一调度） | `services/comm_service.py` | 完成 |
| 14 | MQTT 调试桥接器（MQTTX 兼容） | `services/comm_service.py` | 完成 |
| 15 | 断连缓存队列 | `persistence/buffer_queue.py` | 完成 |

---

## 3. 当前未完成的核心功能（按优先级排序）

### P0 — 通信层
- **~~BLE RFCOMM Server~~** ✅ 已完成
- **~~WiFi WebSocket Server~~** ✅ 已完成
- **~~通信调度器 + MQTT 调试通道~~** ✅ 已完成
- **~~断连缓存队列~~** ✅ 已完成
- **断连缓存补发联调**：需要在真实断开/重连场景下验证批量补发逻辑

### P1 — 数据持久化与安全
- **本地 FIT/GPX 文件存储**：骑行记录生成标准运动文件
- **骑行会话管理**：开始/暂停/结束骑行，时间/距离/爬升计算
- **历史记录页面**：PyQt 上查看骑行列表和回放
- **安全告警系统**：后方来车告警、心率超限告警、疲劳提醒
- **用户配置管理**：心率上限、年龄体重、BLE 白名单等

### P2 — 离线智能增强
- **离线地图瓦片**：OpenStreetMap + MBTiles，替代高德在线地图
- **离线导航引擎**：GPX 路线导入 + 路线跟随 + 偏离检测 + 语音导航
- **AI Agent**：语音控制设备（开始骑行、导航回家、打开车灯）

### P3+ — 扩展硬件与生态
- **BLE/ANT+ 外设直连**：树莓派直接连心率带/功率计/踏频器
- **行车记录仪（DVR）**：摄像头循环录制 + OSD 数据叠加
- **功率训练课程**：结构化训练模式（ZWO/JSON）
- **云同步后端**：骑行记录增量上传
- **OTA 固件升级**：App 远程升级 STM32 + 树莓派
- **电子围栏/防盗定位**：停车监测 + 位移告警
- **组队骑行**：多设备位置共享

---

## 4. 技术栈

| 层级 | 技术 |
|------|------|
| UI 框架 | PyQt5（纯 QWidget，无 QML） |
| 地图 | 高德 JS API（在线），计划迁移到 OpenStreetMap 离线瓦片 |
| 语音 TTS | Piper（本地 ONNX）+ Edge-TTS（在线回退） |
| ASR | 当前依赖云端或第三方，计划迁移到本地 Whisper tiny/base |
| 大模型 | Ollama + Llama 3.2 3B / Qwen 系列 |
| BLE 通信 | 计划使用 `bleak` + `bluez` |
| WiFi 通信 | 计划使用 `websockets` |
| 文件格式 | FIT (`fitdecode`/`python-fitparse`) / GPX (`gpxpy`) |
| 地图瓦片 | MBTiles (SQLite) |

---

## 5. 当前目录结构

**步骤 0.1 目录重构已完成**。新功能应按以下结构继续开发：

```
qt_project/
├── main.py                      # 入口，仅剩 BikeComputerPro 主窗口逻辑
├── app.py                       # [待建] QApplication + 全局异常处理
│
├── ui/                          # UI 页面层
│   ├── ui_main_window.py
│   ├── map_page.py              # 现有
│   ├── smart_pinyin_ime.py      # 现有
│   ├── styles.qss               # [待建] 统一 QSS 样式
│   ├── history_page.py          # [待建] 历史记录页
│   └── settings_page.py         # [待建] 设置页
│
├── widgets/                     # 可复用控件
│   ├── map_widget.py            # 现有
│   ├── circle_gauge.py          # 现有（从 main.py 拆分）
│   ├── small_data_box.py        # 现有（从 main.py 拆分）
│   ├── metric_card.py           # [待建]
│   └── message_bubble.py        # [待建]
│
├── services/                    # 业务服务层 [待建]
│   ├── map_service.py           # 现有
│   ├── comm_service.py          # 现有
│   ├── ride_service.py          # [待建] 骑行会话管理
│   ├── alert_service.py         # [待建] 安全告警
│   ├── nav_engine.py            # [待建] 离线导航
│   └── ai_assistant.py          # [待建] AI Agent（升级 ollama_client）
│
├── core/                        # 核心领域层
│   ├── data_context.py          # 现有
│   ├── location_service.py      # 现有
│   ├── protocol.py              # 现有
│   ├── models.py                # [待建] RideRecord, GPSPoint 等
│   └── calculator.py            # [待建] 骑行指标计算
│
├── drivers/                     # 硬件驱动层
│   ├── serial_handler.py        # 现有
│   ├── ble_server.py            # 现有（RFCOMM 经典蓝牙）
│   ├── ble_central.py           # [待建] BLE Central 连外设
│   ├── wifi_server.py           # 现有
│   └── audio/                   # 语音子模块
│       ├── voice_recorder.py    # 现有
│       ├── piper_voice.py       # 现有
│       ├── voice_final.py       # 现有
│       └── asr_whisper.py       # [待建] 本地 ASR
│
├── persistence/                 # 持久化层 [待建]
│   ├── ride_repository.py       # FIT/GPX 读写
│   ├── config_manager.py        # 配置管理
│   ├── buffer_queue.py          # 现有
│   └── tile_cache_manager.py    # 离线瓦片管理
│
├── llm/                         # 大模型层
│   ├── ollama_client.py         # 现有
│   └── prompts.py               # [待建] 提示词模板
│
├── utils/                       # 工具类
│   └── serial_debugger.py       # 现有（从 main.py 拆分）
│
├── scripts/                     # 运维脚本
│   ├── download_tiles.py        # [待建] 瓦片预下载
│   ├── setup_piper.sh           # 现有
│   ├── setup_piper_hq.sh        # 现有
│   ├── setup_melotts.sh         # 现有
│   └── download_piper_model.sh  # 现有
│
└── tests/                       # 测试
    ├── test_data_context.py     # 现有
    ├── test_navigation.py       # 现有
    ├── test_voice_system.py     # 现有
    ├── test_nav_console.py      # 现有
    ├── test_nav_simple.py       # 现有
    └── ...
```

---

## 6. 关键数据协议

### STM32 → 树莓派（当前 JSON 格式）
```json
{
  "speed": 25.5,
  "power": 180,
  "cadence": 85,
  "distance": 12.3,
  "ride_time": 1800,
  "slope": 2.5,
  "temperature": 28,
  "heart_rate": 145,
  "rear_dist": 8.5,
  "location": {"lat": 39.9, "lon": 116.4},
  "err_code": 0
}
```

### 树莓派 ↔ App（已实现）
- **BLE 通道**：经典蓝牙 RFCOMM，发送 18 字节紧凑二进制 + JSON 事件
- **WiFi 通道**：JSON over WebSocket（端口 8765）
- **MQTT 调试通道**：`paho-mqtt` 桥接，Topic 见下文
- **文件传输**：FIT / GPX 文件通过 WiFi 批量下发（待实现）

### MQTT 调试 Topic 定义
| Topic | 方向 | 说明 |
|-------|------|------|
| `smartride/realtime` | 树莓派 → MQTTX | 每秒 1 次实时骑行数据（JSON） |
| `smartride/event` | 树莓派 → MQTTX | 即时事件：告警、骑行状态变化 |
| `smartride/buffer` | 树莓派 → MQTTX | 断连重连后的批量补发数据 |
| `smartride/command` | MQTTX → 树莓派 | 发送调试命令（JSON），会被转发到主程序 |

### MQTTX 连接配置
| 配置项 | 值 |
|--------|-----|
| Host | `broker.emqx.io` |
| Port | `1883` |
| Protocol | `mqtt://` |

> 使用公用 EMQ X Broker，任何联网设备均可订阅/发布。

---

## 7. 开发优先级与当前建议

**当前最重要的问题：** 树莓派是"单点孤岛"——STM32 数据进来了，但无法稳定输出到 App。

**建议的下一步开发顺序：**
1. **~~代码目录重构~~ ✅ 已完成**（步骤 0.1 已落地，文件已分层，import 已修复）
2. **~~定义统一协议~~ ✅ 已完成**（`core/protocol.py` 已落地，`SensorData` 协议已接入串口数据流）
3. **~~BLE + WiFi + CommService + MQTT 调试通道~~ ✅ 已完成**（经典蓝牙 RFCOMM + WebSocket + MQTT 桥接）
4. **断连缓存补发联调**（`persistence/buffer_queue.py` 已就绪，需主流程联动测试）
5. **安全告警系统**
6. **离线地图 + 导航引擎**

**不要先做/可以后放的功能：**
- 行车记录仪、功率训练课程、云同步、组队骑行、OTA、防盗 —— 这些都属于锦上添花，先把 P0/P1 跑通。

---

## 8. 给 Claude Code 的开发提示

1. **主文件 `main.py` 已瘦身**：`CircleGauge`、`SmallDataBox`、`SerialDebugger` 已分别拆分到 `widgets/` 和 `utils/` 目录。新增功能时应继续按分层目录开发，不要再往 `main.py` 堆代码。

2. **语音模块已高度封装**：`drivers/audio/piper_voice.py` 提供了 `HybridVoicePlayer`，支持离线 Piper 和在线 Edge-TTS 的自动切换。新功能需要语音播报时，优先复用它。

3. **DataContext 是中心数据源**：所有需要向 LLM 提供上下文或向 UI 刷新数据的功能，都应通过 `data_context.py` 读写，不要绕过它直接改 UI。

4. **高德地图是在线的**：当前 `map_widget.py` 依赖网络，户外无网会白屏。任何地图相关的修改都要考虑"离线可用性"这个约束。

5. **树莓派性能有限**：Ollama 已经通过 `num_ctx=512`、`num_thread=4` 做过优化。新增 heavy 计算（如 Whisper ASR、视频编码）要先评估 CPU 占用和延迟。

6. **BLE Server 在 Linux 上的坑**：`bleak` 做 Server 的资料比 Client 少得多，可能需要直接调用 `bluez` D-Bus API 或 `pygattlib`。遇到困难时不要硬磕 bleak，可以考虑用 `btmgmt` / `hciconfig` 做底层配置。

---

## 9. 高频修改点速查

| 需求 | 修改位置 |
|------|---------|
| 新增数据字段显示 | `core/data_context.py` → `main.py` `on_data_received()` → UI 控件 |
| 新增语音播报场景 | 复用 `drivers.audio.piper_voice` 的 `speak()` |
| 新增 AI 回答能力 | 改 `llm/ollama_client.py` 的 system prompt 或 model 参数 |
| 新增 BLE 服务 | 新建 `drivers/ble_server.py`，在 `main.py` 初始化 |
| 新增地图交互 | `widgets/map_widget.py` |
| 新增骑行记录保存 | 新建 `persistence/ride_repository.py` |

---

*最后更新：2026-04-13*
