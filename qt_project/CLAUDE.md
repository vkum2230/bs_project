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
| 2 | 自定义圆形仪表盘控件 | `main.py` 内 `CircleGauge` | 完成 |
| 3 | STM32 串口数据采集（JSON 协议） | `main.py` 内 `SerialReader` | 完成 |
| 4 | 高德在线地图（JS API）+ 实时位置标记 | `map_widget.py` | 完成 |
| 5 | 离线省份判断 + 语音播报 | `location_service.py` | 完成 |
| 6 | Piper 本地 TTS + Edge-TTS 在线回退 | `voice_driver/piper_voice.py` | 完成 |
| 7 | 按钮语音交互（GPIO 17）+ LED 状态指示 | `voice_driver/voice_recorder.py` | 完成 |
| 8 | Ollama 本地大模型自动连接/选择/流式输出 | `ollama_client.py` | 完成 |
| 9 | 全局骑行数据上下文管理器 | `data_context.py` | 完成 |
| 10 | 串口日志重定向调试器 | `main.py` 内 `SerialDebugger` | 完成 |

---

## 3. 当前未完成的核心功能（按优先级排序）

### P0 — 通信层（最大缺口，必须先补）
- **BLE GATT Server**：树莓派作为 BLE Peripheral 向 App 广播骑行数据
- **WiFi WebSocket Server**：高速数据通道 + 历史记录批量同步
- **通信调度器**：统一调度 BLE/WiFi，自动切换主通道
- **断连缓存补发**：防止信号中断丢数据

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

## 5. 目标目录结构

当前代码存在所有文件堆在根目录的问题，新功能应按以下结构开发：

```
qt_project/
├── main.py                      # 入口，仅做初始化
├── app.py                       # QApplication + 全局异常处理（可选）
│
├── ui/                          # UI 层
│   ├── ui_main_window.py
│   ├── styles.qss
│   ├── history_page.py          # [待建] 历史记录页
│   └── settings_page.py         # [待建] 设置页
│
├── widgets/                     # 可复用控件
│   ├── map_widget.py            # 现有
│   ├── metric_card.py           # [待建]
│   └── message_bubble.py        # [待建]
│
├── services/                    # 业务服务层 [待建]
│   ├── comm_service.py          # BLE/WiFi 通信调度
│   ├── ride_service.py          # 骑行会话管理
│   ├── alert_service.py         # 安全告警
│   ├── nav_engine.py            # 离线导航
│   └── ai_assistant.py          # AI Agent（升级 ollama_client）
│
├── core/                        # 核心领域层 [待建]
│   ├── data_context.py          # 现有，建议移入
│   ├── protocol.py              # 数据协议定义
│   ├── models.py                # RideRecord, GPSPoint 等数据类
│   └── calculator.py            # 骑行指标计算
│
├── drivers/                     # 硬件驱动层 [部分待建]
│   ├── serial_reader.py         # 从 main.py 拆分
│   ├── ble_server.py            # [待建] BLE GATT Server
│   ├── ble_central.py           # [待建] BLE Central 连外设
│   ├── wifi_server.py           # [待建] WebSocket Server
│   └── audio/                   # 语音子模块
│       ├── voice_recorder.py    # 现有
│       ├── piper_voice.py       # 现有
│       └── asr_whisper.py       # [待建] 本地 ASR
│
├── persistence/                 # 持久化层 [待建]
│   ├── ride_repository.py       # FIT/GPX 读写
│   ├── config_manager.py        # 配置管理
│   ├── buffer_queue.py          # 断连缓存队列
│   └── tile_cache_manager.py    # 离线瓦片管理
│
├── llm/                         # 大模型层 [待建]
│   ├── ollama_client.py         # 现有，建议移入
│   └── prompts.py               # 提示词模板
│
├── scripts/                     # 运维脚本
│   ├── download_tiles.py        # [待建] 瓦片预下载
│   ├── setup_piper.sh
│   └── setup_melotts.sh
│
└── tests/                       # 测试
    ├── test_data_context.py
    ├── test_navigation.py
    └── test_voice_system.py
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

### 树莓派 ↔ App（计划中）
- **BLE 通道**：标准 GATT Characteristic（CSCS/CPS/HRS 兼容 + 自定义 Service 0xFF00）
- **WiFi 通道**：JSON over WebSocket，或可选 Protobuf 压缩
- **文件传输**：FIT / GPX 文件通过 WiFi 批量下发

---

## 7. 开发优先级与当前建议

**当前最重要的问题：** 树莓派是"单点孤岛"——STM32 数据进来了，但无法稳定输出到 App。

**建议的下一步开发顺序：**
1. **代码目录重构**（把 `main.py` 拆成合理的模块结构）
2. **定义统一协议**（`core/protocol.py`）
3. **BLE GATT Server**（让 App 能连上树莓派并收到数据）
4. **WiFi WebSocket Server**（高速通道，传文件用）
5. **通信调度器**（`services/comm_service.py`）
6. **本地 FIT 存储 + 骑行会话管理**
7. **安全告警系统**

**不要先做/可以后放的功能：**
- 行车记录仪、功率训练课程、云同步、组队骑行、OTA、防盗 —— 这些都属于锦上添花，先把 P0/P1 跑通。

---

## 8. 给 Claude Code 的开发提示

1. **主文件 `main.py` 当前非常臃肿**：所有初始化、UI、控件、串口、调试器都在一个文件里。新增功能时应优先拆分到对应目录，不要再往 `main.py` 堆代码。

2. **语音模块已高度封装**：`voice_driver/piper_voice.py` 提供了 `HybridVoicePlayer`，支持离线 Piper 和在线 Edge-TTS 的自动切换。新功能需要语音播报时，优先复用它。

3. **DataContext 是中心数据源**：所有需要向 LLM 提供上下文或向 UI 刷新数据的功能，都应通过 `data_context.py` 读写，不要绕过它直接改 UI。

4. **高德地图是在线的**：当前 `map_widget.py` 依赖网络，户外无网会白屏。任何地图相关的修改都要考虑"离线可用性"这个约束。

5. **树莓派性能有限**：Ollama 已经通过 `num_ctx=512`、`num_thread=4` 做过优化。新增 heavy 计算（如 Whisper ASR、视频编码）要先评估 CPU 占用和延迟。

6. **BLE Server 在 Linux 上的坑**：`bleak` 做 Server 的资料比 Client 少得多，可能需要直接调用 `bluez` D-Bus API 或 `pygattlib`。遇到困难时不要硬磕 bleak，可以考虑用 `btmgmt` / `hciconfig` 做底层配置。

---

## 9. 高频修改点速查

| 需求 | 修改位置 |
|------|---------|
| 新增数据字段显示 | `data_context.py` → `main.py` `on_data_received()` → UI 控件 |
| 新增语音播报场景 | 复用 `voice_driver/piper_voice.py` 的 `speak()` |
| 新增 AI 回答能力 | 改 `ollama_client.py` 的 system prompt 或 model 参数 |
| 新增 BLE 服务 | 新建 `drivers/ble_server.py`，在 `main.py` 初始化 |
| 新增地图交互 | `map_widget.py` |
| 新增骑行记录保存 | 新建 `persistence/ride_repository.py` |

---

*最后更新：2026-04-13*
