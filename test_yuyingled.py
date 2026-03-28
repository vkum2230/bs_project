import spidev
import time
import os

# 1. 尝试通过系统强制拉高 GPIO 5 (电源使能)
os.system("pinctrl set 5 op dh")

spi = spidev.SpiDev()
try:
    # 树莓派 5 的 SPI0 总线
    spi.open(0, 1)
    
    # 尝试更慢的速度，确保芯片能跟上
    spi.max_speed_hz = 500000 
    
    # 尝试改变 SPI 模式
    # Mode 0 是默认，如果不行尝试 Mode 3 (spi.mode = 3)
    spi.mode = 1 

    print("开始测试：所有灯设为红色...")
    
    # 亮度 0xE0 + 5 (先用低亮度测试，防止电流过大)
    br = 0xE0 + 5
    
    # 完整的 APA102 协议包
    # 起始 (4字节0) + 3个灯 (亮度, B, G, R) + 结束 (4字节1)
    # 这里演示红色：R=255, G=0, B=0
    data = [
        0x00, 0x00, 0x00, 0x00,  # Start
        br, 0x00, 0x00, 0xFF,    # LED 1 (BGR)
        br, 0x00, 0x00, 0xFF,    # LED 2
        br, 0x00, 0x00, 0xFF,    # LED 3
        0xFF, 0xFF, 0xFF, 0xFF   # End
    ]
    
    spi.xfer2(data)
    print("指令已发送，请观察灯光。")
    time.sleep(5)

    # 尝试另一种颜色（绿色）
    print("切换为绿色...")
    data_green = [
        0x00, 0x00, 0x00, 0x00,
        br, 0x00, 0xFF, 0x00,
        br, 0x00, 0xFF, 0x00,
        br, 0x00, 0xFF, 0x00,
        0xFF, 0xFF, 0xFF, 0xFF
    ]
    spi.xfer2(data_green)
    time.sleep(5)

finally:
    # 关灯
    spi.xfer2([0x00]*4 + [0xE0,0,0,0]*3 + [0xFF]*4)
    spi.close()