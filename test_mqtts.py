import paho.mqtt.client as mqtt
import time
import random
import ssl  # 必须导入 ssl 库处理加密

# --- 1. 配置区（根据你的图片修改） ---
MQTT_BROKER = "q0193f39.ala.dedicated.aliyun.emqxcloud.cn"
MQTT_PORT = 8883  # 加密端口通常是 8883
MQTT_USER = "ghost_pedal"
MQTT_PW = "123456"
MQTT_TOPIC = "rpi5/test/data"

# --- 2. 实例化客户端 ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# --- 3. 设置用户名和密码（关键步骤） ---
client.username_pw_set(MQTT_USER, MQTT_PW)

# --- 4. 设置 SSL/TLS 加密（关键步骤） ---
# 对应图片中的 "SSL/TLS" 开启和 "CA signed server certificate"
# 树莓派系统自带 CA 证书库，通常直接调用 tls_set() 即可
client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print(f"成功连接到阿里云 MQTT 服务器！状态码: {rc}")
    else:
        print(f"连接失败，错误码: {rc}。请检查用户名密码或防火墙设置。")

client.on_connect = on_connect

# --- 5. 开始连接 ---
try:
    print(f"正在通过 SSL 连接到 {MQTT_BROKER}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
    client.loop_start()

    while True:
        test_value = random.uniform(20.0, 30.0)
        message = f"Pi5 SSL Data: {test_value:.2f}"
        
        result = client.publish(MQTT_TOPIC, message, qos=1) # 私有云建议加 qos=1 保证送达
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"已安全发送: {message}")
        
        time.sleep(5)

except KeyboardInterrupt:
    print("程序停止")
    client.loop_stop()
    client.disconnect()
except Exception as e:
    print(f"发生错误: {e}")