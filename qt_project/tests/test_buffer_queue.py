#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BufferQueue + CommService 断连补发联调测试

运行方式：
    cd qt_project && python3 -m tests.test_buffer_queue

测试内容：
1. 模拟 BLE/WiFi/MQTT 全断连，验证实时数据进入 BufferQueue
2. 模拟 BLE 恢复连接，验证缓存数据被批量补发
3. 模拟 MQTT/WiFi 恢复连接，验证缓存数据被批量补发
4. 验证 BufferQueue 的滑动窗口限制（max_items / max_age_seconds）
"""

import sys
import time
import json
from unittest.mock import MagicMock

from PyQt5.QtCore import QCoreApplication, QTimer

sys.path.insert(0, "..")

from services.comm_service import CommService
from core.protocol import AppRealtimeData, SensorData, RideSessionState
from persistence.buffer_queue import BufferQueue


def test_buffer_queue_sliding_window():
    """测试 BufferQueue 滑动窗口"""
    print("\n[TEST] BufferQueue 滑动窗口测试")
    bq = BufferQueue(max_items=5, max_age_seconds=60)

    for i in range(10):
        d = AppRealtimeData(speed=float(i), timestamp=time.time())
        bq.push(d)

    assert bq.size() == 5, f"期望 5，实际 {bq.size()}"
    items = bq.drain()
    first_speed = items[0]["speed"]
    assert first_speed == 5.0, f"期望保留最新数据，首个 speed={first_speed}"
    print("  ✓ 滑动窗口正确，超量数据已丢弃最旧条目")


def test_buffer_queue_age_cleanup():
    """测试 BufferQueue 时间过期清理"""
    print("\n[TEST] BufferQueue 过期清理测试")
    bq = BufferQueue(max_items=100, max_age_seconds=0.5)

    d1 = AppRealtimeData(speed=10.0, timestamp=time.time() - 1.0)
    d2 = AppRealtimeData(speed=20.0, timestamp=time.time())
    bq.push(d1)
    bq.push(d2)

    # push 内部会调用 _cleanup，但 d1 的 timestamp 是 1 秒前，max_age=0.5
    # 注意：_cleanup 的 cutoff 是 now - max_age，所以 d1 应该被清理
    assert bq.size() == 1, f"期望 1，实际 {bq.size()}"
    assert bq.peek()[0]["speed"] == 20.0
    print("  ✓ 过期数据已自动清理")


def test_comm_service_buffer_and_flush():
    """测试 CommService 断连缓存 + 重连补发"""
    print("\n[TEST] CommService 断连缓存与补发测试")
    app = QCoreApplication(sys.argv)

    comm = CommService(parent=None, ride_repo=None)

    # Mock BLE / WiFi / MQTT
    comm.ble_server = MagicMock()
    comm.wifi_server = MagicMock()
    comm.mqtt_bridge = MagicMock()

    # 阶段 1：全断连，数据应进入 BufferQueue
    comm.ble_server.has_connected_client.return_value = False
    comm.wifi_server.has_connected_client.return_value = False
    comm.mqtt_bridge._connected = False

    for i in range(5):
        comm.data_buffer.push(SensorData(speed=float(i)))
        comm._push_realtime_data()
        time.sleep(0.05)

    assert comm.buffer_queue.size() == 5, f"期望缓存 5 条，实际 {comm.buffer_queue.size()}"
    print("  ✓ 全断连期间，5 条数据已进入缓存队列")

    # 阶段 2：BLE 恢复，验证补发
    comm.ble_server.has_connected_client.return_value = True
    comm.ble_server.notify.reset_mock()
    comm._push_realtime_data()

    # _try_flush_buffer 会把 5 条数据分 1 个 batch (<=50) 发出
    assert comm.ble_server.notify.called, "BLE notify 应被调用以补发缓存"
    notified_args = comm.ble_server.notify.call_args_list
    # 最后一条 notify 是补发的 batch（前面可能还有当前实时数据）
    last_call = notified_args[-1][0][0]
    payload = json.loads(last_call)
    assert payload.get("event") == "buffer_sync", f"期望 event=buffer_sync，实际 {payload.get('event')}"
    assert len(payload["data"]) == 5, f"期望补发 5 条，实际 {len(payload['data'])}"
    print(f"  ✓ BLE 恢复后，成功补发 {len(payload['data'])} 条缓存数据")

    # 阶段 3：缓存应已被清空
    assert comm.buffer_queue.is_empty(), "补发后缓存队列应为空"
    print("  ✓ 补发完成后，缓存队列已清空")

    # 阶段 4：模拟仅 MQTT 恢复
    comm.ble_server.has_connected_client.return_value = False
    comm.wifi_server.has_connected_client.return_value = False
    comm.mqtt_bridge._connected = True
    comm.mqtt_bridge.publish.reset_mock()

    for i in range(3):
        comm.data_buffer.push(SensorData(speed=float(i + 100)))
        comm._push_realtime_data()

    # MQTT 连着，数据直接 publish，不走缓存
    assert comm.buffer_queue.is_empty(), "有 MQTT 时不应缓存"
    assert comm.mqtt_bridge.publish.called, "MQTT publish 应被调用"
    print("  ✓ MQTT 连接正常时，实时数据直接发送，不进入缓存")

    # 阶段 5：MQTT 断开，数据再次缓存；然后 WiFi 恢复补发
    comm.mqtt_bridge._connected = False
    for i in range(3):
        comm.data_buffer.push(SensorData(speed=float(i + 200)))
        comm._push_realtime_data()

    assert comm.buffer_queue.size() == 3, f"期望缓存 3 条，实际 {comm.buffer_queue.size()}"
    print("  ✓ MQTT 断开后，数据重新进入缓存")

    comm.wifi_server.has_connected_client.return_value = True
    comm.wifi_server.broadcast.reset_mock()
    comm._push_realtime_data()

    wifi_called = comm.wifi_server.broadcast.called
    assert wifi_called, "WiFi broadcast 应被调用以补发缓存"
    last_wifi_call = comm.wifi_server.broadcast.call_args_list[-1][0][0]
    payload = json.loads(last_wifi_call)
    assert payload.get("event") == "buffer_sync"
    assert len(payload["data"]) == 3
    print(f"  ✓ WiFi 恢复后，成功补发 {len(payload['data'])} 条缓存数据")

    print("\n[RESULT] 所有 CommService 缓存补发测试通过 ✓")


if __name__ == "__main__":
    test_buffer_queue_sliding_window()
    test_buffer_queue_age_cleanup()
    test_comm_service_buffer_and_flush()
    print("\n=====================================")
    print("全部测试通过！断连缓存补发逻辑正常。")
    print("=====================================\n")
