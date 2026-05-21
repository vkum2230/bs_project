#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BLE GATT 服务器（替代 RFCOMM/SPP）— xinjia.txt 协议

树莓派5 依赖：
    sudo apt install bluez python3-dbus python3-gi
    # 开启 experimental:
    # sudo systemctl edit bluetooth
    # ExecStart=/usr/lib/bluetooth/bluetoothd --experimental
"""

import dbus
import dbus.service
import dbus.mainloop.glib
import gc
import json
import queue
import time
import threading
from typing import Optional, Callable
from PyQt5.QtCore import QThread, pyqtSignal

DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"

BLUEZ_SERVICE_NAME = "org.bluez"
ADAPTER_IFACE = "org.bluez.Adapter1"
DEVICE_IFACE = "org.bluez.Device1"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
GATT_SERVICE_IFACE = "org.bluez.GattService1"
GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"
LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
LE_ADVERTISEMENT_IFACE = "org.bluez.LEAdvertisement1"

SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID = "0000ff03-0000-1000-8000-00805f9b34fb"

DBUS_BASE_PATH = "/org/smride/app0"

# ==============================================================================
# 调试工具
# ==============================================================================

def _dump_dbus_value(v, indent=0):
    """递归打印 dbus 数据结构"""
    prefix = "  " * indent
    if isinstance(v, dbus.Dictionary):
        print(f"{prefix}{{")
        for k, val in v.items():
            print(f"{prefix}  {k!r}:")
            _dump_dbus_value(val, indent + 2)
        print(f"{prefix}}}")
    elif isinstance(v, dbus.Array):
        print(f"{prefix}[Array len={len(v)}]")
        for i, val in enumerate(v):
            _dump_dbus_value(val, indent + 1)
    elif isinstance(v, dbus.Boolean):
        print(f"{prefix}Boolean({bool(v)})")
    elif isinstance(v, dbus.String):
        print(f"{prefix}String({str(v)!r})")
    elif isinstance(v, dbus.ObjectPath):
        print(f"{prefix}ObjectPath({str(v)!r})")
    elif isinstance(v, dbus.Byte):
        print(f"{prefix}Byte({int(v)})")
    else:
        print(f"{prefix}{type(v).__name__}({v!r})")


# ==============================================================================
# Notify Characteristic
# ==============================================================================

class NotifyCharacteristic(dbus.service.Object):
    """Notify 特征"""

    def __init__(self, bus, index, service, on_subscribe: Callable):
        self.path = service.path + "/char" + str(index)
        self.bus = bus
        self.service = service
        self.notifying = False
        self._on_subscribe = on_subscribe
        print(f"[BleGatt-DEBUG] NotifyChar 初始化: path={self.path}")
        dbus.service.Object.__init__(self, bus, self.path)
        # 显式导出 GATT Characteristic 接口
        self._gatt_iface = dbus.Interface(self, GATT_CHRC_IFACE)
        print(f"[BleGatt-DEBUG] NotifyChar dbus 注册完成: {self.path}")

    def get_properties(self):
        props = dbus.Dictionary({
            GATT_CHRC_IFACE: dbus.Dictionary({
                "Service": dbus.ObjectPath(self.service.path),
                "UUID": dbus.String(NOTIFY_CHAR_UUID),
                "Flags": dbus.Array(["notify"], signature="s"),
                "Descriptors": dbus.Array([], signature="o"),
            }, signature="sv"),
        }, signature="sa{sv}")
        return props

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        print(f"[BleGatt-DEBUG] GetAll 被调用: path={self.path}, interface={interface}")
        if interface != GATT_CHRC_IFACE:
            raise dbus.exceptions.DBusException(
                "org.bluez.Error.InvalidArguments", "Invalid interface"
            )
        result = self.get_properties()[GATT_CHRC_IFACE]
        print(f"[BleGatt-DEBUG] GetAll 返回: {dict(result)}")
        return result

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print(f"[BleGatt-DEBUG] StartNotify 被调用! path={self.path}")
        if self.notifying:
            print("[BleGatt-DEBUG] StartNotify: 已经在订阅中，忽略")
            return
        self.notifying = True
        print(f"[BleGatt] App 已订阅 Notify ({NOTIFY_CHAR_UUID})")
        if self._on_subscribe:
            self._on_subscribe(True)

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print(f"[BleGatt-DEBUG] StopNotify 被调用! path={self.path}")
        if not self.notifying:
            return
        self.notifying = False
        print(f"[BleGatt] App 已取消订阅 Notify ({NOTIFY_CHAR_UUID})")
        if self._on_subscribe:
            self._on_subscribe(False)

    def send_notify(self, value: bytes) -> bool:
        if not self.notifying:
            print(f"[BleGatt-DEBUG] send_notify 跳过: notifying=False")
            return False
        print(f"[BleGatt-DEBUG] send_notify: len={len(value)}, notifying={self.notifying}")
        try:
            MTU_SAFE = 180
            if len(value) <= MTU_SAFE:
                self._emit_notify(value)
                print(f"[BleGatt-DEBUG] send_notify: 单包发送成功, {len(value)} bytes")
            else:
                payload_per_packet = MTU_SAFE - 2
                total = (len(value) + payload_per_packet - 1) // payload_per_packet
                print(f"[BleGatt-DEBUG] send_notify: 分包发送, total={total}, len={len(value)}")
                for seq in range(total):
                    start = seq * payload_per_packet
                    end = min(start + payload_per_packet, len(value))
                    chunk = bytes([seq + 1, total]) + value[start:end]
                    self._emit_notify(chunk)
                    time.sleep(0.01)
                print(f"[BleGatt-DEBUG] send_notify: 分包发送完成")
            return True
        except Exception as e:
            print(f"[BleGatt] Notify 发送失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _emit_notify(self, value: bytes):
        print(f"[BleGatt-DEBUG] _emit_notify: 发送 {len(value)} bytes")
        payload = dbus.Array([dbus.Byte(b) for b in value], signature="y")
        try:
            self.PropertiesChanged(
                GATT_CHRC_IFACE,
                dbus.Dictionary({"Value": payload}, signature="sv"),
                dbus.Array([], signature="s"),
            )
            print("[BleGatt-DEBUG] PropertiesChanged 信号已发送")
        except Exception as e:
            print(f"[BleGatt-DEBUG] PropertiesChanged 发送失败: {e}")
            import traceback
            traceback.print_exc()

    @dbus.service.signal(DBUS_PROP_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


# ==============================================================================
# Write Characteristic
# ==============================================================================

class WriteCharacteristic(dbus.service.Object):
    """Write 特征"""

    def __init__(self, bus, index, service, on_command):
        self.path = service.path + "/char" + str(index)
        self.bus = bus
        self.service = service
        self.on_command = on_command
        # JSON 累积缓冲区
        self._json_buffer = b""
        print(f"[BleGatt-DEBUG] WriteChar 初始化: path={self.path}")
        dbus.service.Object.__init__(self, bus, self.path)

        # 显式导出 GATT Characteristic 接口
        self._gatt_iface = dbus.Interface(self, GATT_CHRC_IFACE)
        print(f"[BleGatt-DEBUG] WriteChar dbus 注册完成: {self.path}, gatt_iface={self._gatt_iface}")

    def get_properties(self):
        return dbus.Dictionary({
            GATT_CHRC_IFACE: dbus.Dictionary({
                "Service": dbus.ObjectPath(self.service.path),
                "UUID": dbus.String(WRITE_CHAR_UUID),
                "Flags": dbus.Array(["write", "write-without-response"], signature="s"),
                "Descriptors": dbus.Array([], signature="o"),
            }, signature="sv"),
        }, signature="sa{sv}")

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        print(f"[BleGatt-DEBUG] GetAll 被调用: path={self.path}, interface={interface}")
        if interface != GATT_CHRC_IFACE:
            raise dbus.exceptions.DBusException(
                "org.bluez.Error.InvalidArguments", "Invalid interface"
            )
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="aya{sv}", out_signature="")
    def WriteValue(self, value, options):
        """处理 App 发来的写入请求（JSON 累积 + \n 分隔模式）"""
        data = bytes(value)
        print(f"[BleGatt-DEBUG] WriteValue 被调用! path={self.path}, len={len(data)}, hex={data.hex()[:40]}...")

        # 如果数据以 '{' 开头，重置缓冲区（新消息开始）
        if data and data[0] == 123:  # '{' ASCII
            print(f"[BleGatt-DEBUG] 新消息开始，重置缓冲区")
            self._json_buffer = b""

        # 累积数据
        self._json_buffer += data
        text = self._json_buffer.decode("utf-8", errors="ignore")
        print(f"[BleGatt-DEBUG] 累积后 buffer_len={len(self._json_buffer)}, text={text[:80]}")

        # 检查是否有完整的消息（以 \n 结尾）
        if "\n" in text:
            lines = text.split("\n")
            for i, line in enumerate(lines[:-1]):  # 处理所有完整行
                if line.strip():
                    print(f"[BleGatt-DEBUG] 完整消息: {line}")
                    self._process_line(line.strip())
            # 保留最后一行（可能不完整）
            self._json_buffer = lines[-1].encode("utf-8")
            print(f"[BleGatt-DEBUG] 保留不完整数据: {lines[-1][:50]}")

    def _process_line(self, line: str):
        """处理一行完整的 JSON 消息"""
        if not line:
            return

        try:
            msg = json.loads(line)
            print(f"[BleGatt-DEBUG] JSON 解析成功: {msg}")

            # 检查是否是 App 的封包格式 {"deviceId":"...","chunkCount":N,"text":"..."}
            chunk_count = msg.get("chunkCount")
            text_content = msg.get("text", "")

            if chunk_count is not None and text_content:
                # 封包格式，text_content 才是真正的命令 JSON
                print(f"[BleGatt-DEBUG] App 封包: chunkCount={chunk_count}, text={text_content[:100]}")
                try:
                    inner_cmd = json.loads(text_content.strip())
                    print(f"[BleGatt-DEBUG] 内部命令: {inner_cmd}")
                    if self.on_command:
                        cmd_text = json.dumps(inner_cmd, ensure_ascii=False)
                        print(f"[BleGatt-DEBUG] 发送命令: {cmd_text}")
                        self.on_command(cmd_text)
                except json.JSONDecodeError as e:
                    print(f"[BleGatt-DEBUG] 封包内 JSON 解析失败: {e}")
            else:
                # 直接 JSON 命令
                if self.on_command:
                    cmd_text = json.dumps(msg, ensure_ascii=False)
                    print(f"[BleGatt-DEBUG] 发送命令: {cmd_text}")
                    self.on_command(cmd_text)

        except json.JSONDecodeError as e:
            print(f"[BleGatt-DEBUG] JSON 解析失败: {e}, 原文: {line[:100]}")
        except Exception as e:
            print(f"[BleGatt-DEBUG] 处理异常: {e}")
            import traceback
            traceback.print_exc()


# ==============================================================================
# Service
# ==============================================================================

class SmartRideService(dbus.service.Object):
    def __init__(self, bus, index, on_command, on_subscribe):
        self.path = DBUS_BASE_PATH + "/service" + str(index)
        self.bus = bus
        print(f"[BleGatt-DEBUG] Service 初始化: path={self.path}")
        dbus.service.Object.__init__(self, bus, self.path)
        print(f"[BleGatt-DEBUG] Service dbus 注册完成: {self.path}")

        self.notify_char = NotifyCharacteristic(bus, 0, self, on_subscribe)
        self.write_char = WriteCharacteristic(bus, 1, self, on_command)
        self.chars = [self.notify_char, self.write_char]

    def get_properties(self):
        props = dbus.Dictionary({
            GATT_SERVICE_IFACE: dbus.Dictionary({
                "UUID": dbus.String(SERVICE_UUID),
                "Primary": dbus.Boolean(True),
                "Characteristics": dbus.Array(
                    [c.get_path() for c in self.chars], signature="o"
                ),
            }, signature="sv"),
        }, signature="sa{sv}")
        return props

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        print(f"[BleGatt-DEBUG] Service GetAll: path={self.path}, interface={interface}")
        if interface != GATT_SERVICE_IFACE:
            raise dbus.exceptions.DBusException(
                "org.bluez.Error.InvalidArguments", "Invalid interface"
            )
        return self.get_properties()[GATT_SERVICE_IFACE]


# ==============================================================================
# Application
# ==============================================================================

class Application(dbus.service.Object):
    def __init__(self, bus, on_command, on_subscribe):
        self.path = DBUS_BASE_PATH
        self.bus = bus
        print(f"[BleGatt-DEBUG] Application 初始化: path={self.path}")
        dbus.service.Object.__init__(self, bus, self.path)
        print(f"[BleGatt-DEBUG] Application dbus 注册完成: {self.path}")
        self.service = SmartRideService(bus, 0, on_command, on_subscribe)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        print(f"[BleGatt-DEBUG] ====== GetManagedObjects 被 bluez 调用 ======")
        response = dbus.Dictionary({}, signature="oa{sa{sv}}")
        response[dbus.ObjectPath(self.service.get_path())] = self.service.get_properties()
        for chrc in self.service.chars:
            response[dbus.ObjectPath(chrc.get_path())] = chrc.get_properties()

        print(f"[BleGatt-DEBUG] GetManagedObjects 返回 {len(response)} 个对象:")
        for path, ifaces in response.items():
            print(f"[BleGatt-DEBUG]   path={path}")
            for iface, props in ifaces.items():
                print(f"[BleGatt-DEBUG]     iface={iface}")
                for k, v in props.items():
                    print(f"[BleGatt-DEBUG]       {k}={v}")
        print(f"[BleGatt-DEBUG] ====== GetManagedObjects 结束 ======")
        return response


# ==============================================================================
# Advertisement
# ==============================================================================

class Advertisement(dbus.service.Object):
    def __init__(self, bus, index, device_name="SMART-RIDE"):
        self.path = DBUS_BASE_PATH + "/advertisement" + str(index)
        self.bus = bus
        print(f"[BleGatt-DEBUG] Advertisement 初始化: path={self.path}")
        dbus.service.Object.__init__(self, bus, self.path)
        print(f"[BleGatt-DEBUG] Advertisement dbus 注册完成: {self.path}")
        self.device_name = device_name

    def get_properties(self):
        return dbus.Dictionary({
            LE_ADVERTISEMENT_IFACE: dbus.Dictionary({
                "Type": dbus.String("peripheral"),
                "ServiceUUIDs": dbus.Array([dbus.String(SERVICE_UUID)], signature="s"),
                "LocalName": dbus.String(self.device_name),
                "IncludeTxPower": dbus.Boolean(True),
            }, signature="sv"),
        }, signature="sa{sv}")

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        print(f"[BleGatt-DEBUG] Advertisement GetAll: interface={interface}")
        if interface != LE_ADVERTISEMENT_IFACE:
            raise dbus.exceptions.DBusException(
                "org.bluez.Error.InvalidArguments", "Invalid interface"
            )
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE)
    def Release(self):
        print("[BleGatt] 广播已释放")


# ==============================================================================
# 主类
# ==============================================================================

class BleGattServer(QThread):
    client_connected = pyqtSignal(str)
    client_disconnected = pyqtSignal()
    command_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    advertising_started = pyqtSignal()
    advertising_stopped = pyqtSignal()

    def __init__(self, device_name: str = "SMART-RIDE", **_ignored):
        super().__init__()
        self.device_name = device_name
        self._running = False
        self._advertising = False
        self._send_queue = queue.Queue()
        self._lock = threading.Lock()
        self._client_addr: Optional[str] = None
        self._notify_subscribed = False

        self._bus: Optional[dbus.SystemBus] = None
        self._app: Optional[Application] = None
        self._adv: Optional[Advertisement] = None
        self._adapter_path = "/org/bluez/hci0"
        self._main_loop = None

    def start_advertising(self):
        # 如果线程还在运行（前一次没完全结束），先等它结束
        if self.isRunning():
            print("[BleGatt-DEBUG] 检测到线程还在运行，先停止并等待...")
            self._running = False
            if self._main_loop:
                try:
                    self._main_loop.quit()
                except Exception:
                    pass
            if not self.wait(2000):
                print("[BleGatt-DEBUG] 等待线程结束超时，强制终止")
                return

        if self._advertising:
            return

        # 如果前一次的对象引用还在，手动清理（防止 __del__ 竞争）
        if self._app or self._adv or self._bus:
            print("[BleGatt-DEBUG] 发现残留 dbus 对象，执行清理...")
            self._unregister()

        # 强制垃圾回收，确保旧对象的 __del__ 在创建新对象之前执行
        gc.collect()

        # 给 bluez 一点时间清理内部状态
        time.sleep(0.5)

        # 清理所有状态，为全新启动做准备
        self._advertising = True
        self._running = True
        self._send_queue = queue.Queue()
        self._client_addr = None
        self._notify_subscribed = False
        self._last_connected = None  # 重置连接状态检测
        self._last_subscribed = False  # 重置订阅状态检测
        self._main_loop = None
        self._bus = None
        self._app = None
        self._adv = None

        self.start()
        self.advertising_started.emit()
        print("[BleGatt] BLE 广播已启动")

    def stop_advertising(self):
        self._advertising = False
        self._running = False
        if self._main_loop:
            try:
                self._main_loop.quit()
            except Exception:
                pass
        # 等待线程结束（run() 的 finally 会调用 _unregister）
        if self.isRunning():
            if not self.wait(2000):
                print("[BleGatt-DEBUG] 等待线程结束超时")
        self.advertising_stopped.emit()
        print("[BleGatt] BLE 广播已停止")

    def notify(self, payload: bytes or str):
        has_client = self.has_connected_client()
        print(f"[BleGatt-DEBUG] notify() 被调用, has_client={has_client}, queue_size={self._send_queue.qsize()}")
        if has_client:
            self._send_queue.put(payload)

    def has_connected_client(self) -> bool:
        with self._lock:
            print(f"[BleGatt-DEBUG] has_connected_client 检查:")
            print(f"  - _app exists: {self._app is not None}")
            print(f"  - _app.service exists: {self._app.service if self._app else 'N/A'}")
            if self._app and self._app.service:
                print(f"  - notify_char exists: {self._app.service.notify_char is not None}")
                print(f"  - notifying: {self._app.service.notify_char.notifying}")
            print(f"  - _client_addr: {self._client_addr}")
            if not self._app or not self._app.service:
                print(f"  - 返回 False: app 或 service 不存在")
                return False
            notifying = self._app.service.notify_char.notifying
            has_addr = self._client_addr is not None
            result = notifying and has_addr
            print(f"  - notifying={notifying}, has_addr={has_addr}, result={result}")
            return result

    def stop(self):
        self._running = False
        self._advertising = False
        if self._main_loop:
            try:
                self._main_loop.quit()
            except Exception:
                pass
        if self.isRunning():
            if not self.wait(2000):
                print("[BleGatt-DEBUG] stop() 等待线程结束超时")
        self._unregister()
        print("[BleGatt] BLE 服务已停止")

    def run(self):
        print("[BleGatt-DEBUG] run() 线程启动")
        try:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self._bus = dbus.SystemBus()
            print(f"[BleGatt-DEBUG] SystemBus 获取成功")

            # 检查 bluez 版本和 experimental 支持
            try:
                om = dbus.Interface(
                    self._bus.get_object(BLUEZ_SERVICE_NAME, "/"),
                    DBUS_OM_IFACE,
                )
                objs = om.GetManagedObjects()
                has_gatt_mgr = any(GATT_MANAGER_IFACE in ifaces for ifaces in objs.values())
                has_adv_mgr = any(LE_ADVERTISING_MANAGER_IFACE in ifaces for ifaces in objs.values())
                print(f"[BleGatt-DEBUG] bluez GattManager1 可用: {has_gatt_mgr}")
                print(f"[BleGatt-DEBUG] bluez LEAdvertisingManager1 可用: {has_adv_mgr}")
            except Exception as e:
                print(f"[BleGatt-DEBUG] 检查 bluez 能力失败: {e}")

            # 确保 hci0 已启用
            try:
                adapter_obj = self._bus.get_object(BLUEZ_SERVICE_NAME, self._adapter_path)
                adapter_props = dbus.Interface(adapter_obj, DBUS_PROP_IFACE)
                powered = bool(adapter_props.Get(ADAPTER_IFACE, "Powered"))
                print(f"[BleGatt-DEBUG] hci0 Powered: {powered}")
                if not powered:
                    adapter_props.Set(ADAPTER_IFACE, "Powered", dbus.Boolean(True))
                    print("[BleGatt-DEBUG] 已重新启用 hci0")
            except Exception as e:
                print(f"[BleGatt-DEBUG] 检查 hci0 状态失败: {e}")

            # 检查是否有残留的广播实例
            try:
                adapter_obj = self._bus.get_object(BLUEZ_SERVICE_NAME, self._adapter_path)
                ad_props = dbus.Interface(adapter_obj, DBUS_PROP_IFACE)
                active = int(ad_props.Get(LE_ADVERTISING_MANAGER_IFACE, "ActiveInstances"))
                supported = int(ad_props.Get(LE_ADVERTISING_MANAGER_IFACE, "SupportedInstances"))
                print(f"[BleGatt-DEBUG] 广播实例: 活跃={active}, 支持={supported}")
            except Exception as e:
                print(f"[BleGatt-DEBUG] 检查广播状态失败: {e}")

            self._app = Application(self._bus, self._on_command, self._on_notify_subscribe)
            self._adv = Advertisement(self._bus, 0, self.device_name)

            # 注册 GATT Application
            print(f"[BleGatt-DEBUG] 准备注册 GATT Application: {self._app.get_path()}")
            adapter = dbus.Interface(
                self._bus.get_object(BLUEZ_SERVICE_NAME, self._adapter_path),
                GATT_MANAGER_IFACE,
            )
            adapter.RegisterApplication(
                self._app.get_path(),
                {},
                reply_handler=self._gatt_registered,
                error_handler=self._dbus_error,
            )
            print(f"[BleGatt-DEBUG] RegisterApplication 已调用，等待回调...")

            # 注册广播
            print(f"[BleGatt-DEBUG] 准备注册广播: {self._adv.get_path()}")
            ad_manager = dbus.Interface(
                self._bus.get_object(BLUEZ_SERVICE_NAME, self._adapter_path),
                LE_ADVERTISING_MANAGER_IFACE,
            )
            ad_manager.RegisterAdvertisement(
                self._adv.get_path(),
                {},
                reply_handler=self._adv_registered,
                error_handler=self._dbus_error,
            )
            print(f"[BleGatt-DEBUG] RegisterAdvertisement 已调用，等待回调...")

            self._run_glib_loop()

        except Exception as e:
            err_msg = f"[BleGatt] 服务异常: {e}"
            print(err_msg)
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(err_msg)
        finally:
            self._unregister()

    def _run_glib_loop(self):
        try:
            from gi.repository import GLib
        except ImportError:
            print("[BleGatt] 警告: python3-gi 未安装，使用简化轮询模式")
            self._run_polling_loop()
            return

        print("[BleGatt-DEBUG] 启动 GLib 主循环")
        self._main_loop = GLib.MainLoop()
        self._send_source = GLib.timeout_add(50, self._glib_send_callback)
        self._conn_source = GLib.timeout_add(500, self._glib_check_connection)

        try:
            self._main_loop.run()
        except Exception as e:
            print(f"[BleGatt] GLib 主循环异常: {e}")
        finally:
            if hasattr(self, '_send_source'):
                GLib.source_remove(self._send_source)
            if hasattr(self, '_conn_source'):
                GLib.source_remove(self._conn_source)

    def _run_polling_loop(self):
        print("[BleGatt-DEBUG] 启动纯轮询模式")
        last_subscribed = False

        while self._running:
            subscribed = self._app.service.notify_char.notifying if self._app else False

            if subscribed and not last_subscribed:
                # StartNotify 被调用说明 App 已连接
                print("[BleGatt] App 已订阅 Notify，发送握手帧")
                self._send_raw(b'{"isConnect":"OK"}\r\n')
            elif not subscribed and last_subscribed:
                print("[BleGatt] App 取消订阅 Notify")
                self._client_addr = None
                self._notify_subscribed = False
                self.client_disconnected.emit()

            last_subscribed = subscribed

            if subscribed and self._app:
                self._drain_send_queue()

            time.sleep(0.05)

    def _glib_send_callback(self):
        if not self._running:
            return False
        if self._app and self._app.service.notify_char.notifying and self._client_addr:
            self._drain_send_queue()
        return True

    def _glib_check_connection(self):
        if not self._running:
            return False

        try:
            # 直接使用 notifying 状态作为连接依据
            # StartNotify 被调用 → notifying=True → 连接建立
            # StopNotify 被调用 → notifying=False → 连接断开
            subscribed = self._app.service.notify_char.notifying if self._app else False

            # 只在状态变化时打印日志
            last_subs = getattr(self, '_last_subscribed', None)
            if subscribed != last_subs:
                print(f"[BleGatt-DEBUG] 订阅状态变化: subscribed={subscribed}")

            # 订阅时（从False变为True），发送握手帧
            if subscribed and last_subs is not True and self._client_addr:
                print("[BleGatt] App 已订阅 Notify，发送握手帧")
                self._send_raw(b'{"isConnect":"OK"}\r\n')

            self._last_subscribed = subscribed
        except Exception as e:
            print(f"[BleGatt-DEBUG] _glib_check_connection 异常: {e}")
        return True

    def _drain_send_queue(self):
        sent_count = 0
        try:
            while True:
                payload = self._send_queue.get_nowait()
                if isinstance(payload, str):
                    payload = payload.encode("utf-8")
                if payload.startswith(b"{") and not payload.endswith(b"\r\n"):
                    payload += b"\r\n"
                ok = self._app.service.notify_char.send_notify(payload)
                if ok:
                    sent_count += 1
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[BleGatt] 发送异常: {e}")
        if sent_count > 0:
            print(f"[BleGatt-DEBUG] _drain_send_queue: 发送了 {sent_count} 条消息")

    def _check_connection(self) -> tuple:
        """
        检查是否连接到我们的 GATT 服务器

        BlueZ 中，设备连接时会出现在 managed_objects 中
        我们需要检查是否有设备连接到我们的 GATT 服务
        """
        try:
            if not self._app:
                return False, ""

            om = dbus.Interface(
                self._bus.get_object(BLUEZ_SERVICE_NAME, "/"),
                DBUS_OM_IFACE,
            )
            objects = om.GetManagedObjects()

            print(f"[BleGatt-DEBUG] _check_connection: 检查 {len(objects)} 个对象")

            for path, interfaces in objects.items():
                if DEVICE_IFACE not in interfaces:
                    continue

                props = interfaces[DEVICE_IFACE]
                connected = props.get("Connected", False)

                if not connected:
                    continue

                addr = str(props.get("Address", ""))

                # 方法1：检查设备的 Services 属性（BlueZ 5.60+）
                services = props.get("Services", [])
                if services:
                    print(f"[BleGatt-DEBUG] _check_connection: 设备 {addr} 的 Services: {services}")

                # 方法2：检查设备的 UUIDs 属性
                uuids = props.get("UUIDs", [])
                if isinstance(uuids, dbus.Array):
                    uuids = [str(u) for u in uuids]
                print(f"[BleGatt-DEBUG] _check_connection: 设备 {addr} 已连接, UUIDs: {uuids[:5] if uuids else 'None'}")

                # 检查是否连接到我们的 GATT 服务
                our_service = SERVICE_UUID.upper()
                our_service_short = our_service.replace("-", "")[:8].upper()

                # 检查 UUIDs
                is_our_device = False
                for uuid in uuids:
                    uuid_upper = uuid.upper()
                    if our_service in uuid_upper or our_service_short in uuid_upper.replace("-", ""):
                        is_our_device = True
                        break

                # 检查 Services (BlueZ 5.60+)
                if not is_our_device and services:
                    for svc in services:
                        svc_str = str(svc).upper()
                        if our_service in svc_str or our_service_short in svc_str.replace("-", ""):
                            is_our_device = True
                            break

                if is_our_device:
                    print(f"[BleGatt-DEBUG] _check_connection: 找到连接到我们 GATT 服务的设备: {addr}")
                    return True, addr
                else:
                    print(f"[BleGatt-DEBUG] _check_connection: 发现其他已连接设备: {addr}")

            return False, ""
        except Exception as e:
            print(f"[BleGatt-DEBUG] _check_connection 异常: {e}")
            import traceback
            traceback.print_exc()
            return False, ""

    def _on_notify_subscribe(self, subscribed: bool):
        if subscribed:
            print("[BleGatt] Notify 订阅状态: 已订阅，触发 client_connected 信号")
            # StartNotify 被调用说明 App 已连接，直接通过此回调触发连接信号
            # 不再依赖 _check_connection() 的 UUID 检测（BlueZ 不暴露 FF00 服务 UUID）
            if self._client_addr is None:
                self._client_addr = "app-device"
            # 立即发送握手帧，不经过 notify() 队列（确保时序正确）
            print(f"[BleGatt] 立即发送握手帧...")
            self._send_raw(b'{"deviceId":"1"}\r\n')
            self.client_connected.emit(self._client_addr)
        else:
            print("[BleGatt] Notify 订阅状态: 已取消")
            if self._client_addr:
                self._client_addr = None
                self._notify_subscribed = False
                self.client_disconnected.emit()

    def _on_command(self, text: str):
        print(f"[BleGatt-DEBUG] command_received: {text[:200]}")
        self.command_received.emit(text)

    def _send_raw(self, payload: bytes):
        print(f"[BleGatt-DEBUG] _send_raw: {payload[:100]}")
        if self._app and self._app.service.notify_char.notifying:
            ok = self._app.service.notify_char.send_notify(payload)
            print(f"[BleGatt-DEBUG] _send_raw 结果: {ok}")
        else:
            print(f"[BleGatt-DEBUG] _send_raw 跳过: app={self._app is not None}, notifying={self._app.service.notify_char.notifying if self._app else 'N/A'}")

    def _gatt_registered(self):
        print("[BleGatt] GATT Application 注册成功")

    def _adv_registered(self):
        print(f"[BleGatt] BLE 广播注册成功，设备名: {self.device_name}")

    def _dbus_error(self, e):
        err_msg = f"[BleGatt] dbus 错误: {e}"
        print(err_msg)
        import traceback
        traceback.print_exc()
        self.error_occurred.emit(err_msg)

    def _unregister(self):
        adv_path = self._adv.get_path() if self._adv else None
        app_path = self._app.get_path() if self._app else None

        # 1. 先从 bluez 注销（bluez 需要先取消引用这些对象）
        try:
            if self._bus and adv_path:
                ad_manager = dbus.Interface(
                    self._bus.get_object(BLUEZ_SERVICE_NAME, self._adapter_path),
                    LE_ADVERTISING_MANAGER_IFACE,
                )
                ad_manager.UnregisterAdvertisement(adv_path)
                print("[BleGatt] 广播已从 bluez 注销")
        except Exception as e:
            print(f"[BleGatt] 广播 bluez 注销失败: {e}")

        try:
            if self._bus and app_path:
                adapter = dbus.Interface(
                    self._bus.get_object(BLUEZ_SERVICE_NAME, self._adapter_path),
                    GATT_MANAGER_IFACE,
                )
                adapter.UnregisterApplication(app_path)
                print("[BleGatt] GATT Application 已从 bluez 注销")
        except Exception as e:
            print(f"[BleGatt] GATT Application bluez 注销失败: {e}")

        # 2. 再从 dbus 连接中显式注销所有对象（由内到外）
        # 关键：防止旧对象被垃圾回收时 __del__ 再次调用 remove_from_connection()
        # 如果 __del__ 在新对象创建后执行，会错误地注销新对象！

        # 先注销所有 Characteristic
        try:
            if self._app and self._app.service:
                for chrc in self._app.service.chars:
                    try:
                        chrc.remove_from_connection()
                        chrc._object_path = "/__removed__"
                    except Exception as e:
                        print(f"[BleGatt] Characteristic dbus 注销失败: {e}")
        except Exception as e:
            print(f"[BleGatt] Characteristics 注销失败: {e}")

        # 注销 Service
        try:
            if self._app and self._app.service:
                self._app.service.remove_from_connection()
                self._app.service._object_path = "/__removed__"
                print("[BleGatt] Service 已从 dbus 注销")
        except Exception as e:
            print(f"[BleGatt] Service dbus 注销失败: {e}")

        # 注销 Advertisement
        try:
            if self._adv:
                self._adv.remove_from_connection()
                self._adv._object_path = "/__removed__"
                print("[BleGatt] Advertisement 已从 dbus 注销")
        except Exception as e:
            print(f"[BleGatt] Advertisement dbus 注销失败: {e}")

        # 最后注销 Application
        try:
            if self._app:
                self._app.remove_from_connection()
                self._app._object_path = "/__removed__"
                print("[BleGatt] Application 已从 dbus 注销")
        except Exception as e:
            print(f"[BleGatt] Application dbus 注销失败: {e}")

        self._bus = None
        self._app = None
        self._adv = None


if __name__ == "__main__":
    import sys
    from PyQt5.QtCore import QCoreApplication

    app = QCoreApplication(sys.argv)
    server = BleGattServer(device_name="SMART-RIDE")
    server.client_connected.connect(lambda addr: print(f"信号: 连接 {addr}"))
    server.client_disconnected.connect(lambda: print("信号: 断开"))
    server.command_received.connect(lambda cmd: print(f"信号: 命令 {cmd}"))
    server.start_advertising()
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        server.stop()
