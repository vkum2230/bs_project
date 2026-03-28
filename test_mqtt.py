import paho.mqtt.client as mqtt
import time
import random

# --- 配置区 ---
MQTT_BROKER = "broker.emqx.io"  # 公共测试服务器
MQTT_PORT = 1883
MQTT_TOPIC = "rpi5/test/data"   # 你自定义的主题

# --- 实例化客户端 ---
# 注意：paho-mqtt 2.0+ 版本需要指定 CallbackAPIVersion
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("已成功连接到 MQTT 服务器!")
    else:
        print(f"连接失败，返回码: {rc}")

client.on_connect = on_connect

# --- 开始连接 ---
try:
    print(f"正在连接到 {MQTT_BROKER}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
    # 启动网络循环（在后台运行，处理重连等）
    client.loop_start()

    while True:
        # 模拟生成一些数据（比如传感器数值）
        test_value = random.uniform(20.0, 30.0)
        message = f"Hello from Pi 5! Temp: {test_value:.2f}"
        
        # 发送消息
        result = client.publish(MQTT_TOPIC, message)
        
        # 检查是否发送成功
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"发送成功: [{MQTT_TOPIC}] {message}")
        else:
            print("消息发送失败")

        time.sleep(5)  # 每 5 秒发送一次

except KeyboardInterrupt:
    print("程序停止")
    client.loop_stop()
    client.disconnect()