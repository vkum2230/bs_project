import pygame
import random
import time
import subprocess
import threading
import os
import spidev

# --- 1. 硬件配置 (SPI灯光) ---
spi = spidev.SpiDev()
try:
    spi.open(0, 1)  # 之前测试成功的 spidev0.1
    spi.max_speed_hz = 1000000
except:
    print("警告: SPI灯光初始化失败，请检查引脚配置")

def set_led_color(r, g, b):
    """设置ReSpeaker 2-Mics的3颗灯颜色"""
    try:
        brightness = 0xE0 + 10 # 亮度等级 10
        # 起始帧 + 3颗灯(亮度, B, G, R) + 结束帧
        data = [0x00, 0x00, 0x00, 0x00]
        for _ in range(3):
            data.extend([brightness, b, g, r])
        data.extend([0xFF, 0xFF, 0xFF, 0xFF])
        spi.xfer2(data)
    except:
        pass

# --- 2. 语音配置 (管道模式) ---
VOICE_COOLDOWN = 6  # 语音间隔时间，防止复读
last_voice_time = 0

def speak_now(text):
    """调用测试成功的命令行播放语音"""
    global last_voice_time
    if time.time() - last_voice_time > VOICE_COOLDOWN:
        def run_cmd():
            # 使用你测试成功的指令格式
            cmd = f"espeak-ng -v zh '{text}' --stdout | aplay -D plughw:seeed2micvoicec"
            subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL)
            
        threading.Thread(target=run_cmd, daemon=True).start()
        last_voice_time = time.time()

# --- 3. 界面配置 ---
WIDTH, HEIGHT = 640, 480
BAR_WIDTH, BAR_HEIGHT = 450, 60
BAR_X, BAR_Y = (WIDTH - BAR_WIDTH) // 2, 220

# 颜色定义
COLOR_BG = (20, 20, 20)
COLOR_YELLOW = (255, 215, 0)
COLOR_GREEN = (0, 255, 127)
COLOR_RED = (255, 69, 0)
COLOR_GRAY = (60, 60, 60)

# --- 初始化 Pygame ---
os.environ["XDG_RUNTIME_DIR"] = "/tmp/runtime-root"
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ReSpeaker 智能功率助手")

# 字体加载 (优先加载文泉驿微米黑，没有则用系统默认)
try:
    font_main = pygame.font.Font("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 32)
    font_sub = pygame.font.Font("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 18)
except:
    font_main = pygame.font.SysFont("Arial", 32)
    font_sub = pygame.font.SysFont("Arial", 18)

# --- 主循环 ---
running = True
current_power = 0
target_power = 50
clock = pygame.time.Clock()

print("程序启动！请观察屏幕和ReSpeaker灯光...")

try:
    while running:
        screen.fill(COLOR_BG)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 1. 模拟功率数据 (每隔一段时间变动一次目标)
        if random.random() < 0.05:
            target_power = random.randint(10, 95)
        # 让功率条平滑滑动
        current_power += (target_power - current_power) * 0.1

        # 2. 判断区间、更新灯光、触发语音
        if current_power < 40:
            # 黄色区间
            bar_color = COLOR_YELLOW
            set_led_color(255, 200, 0) # 灯光变黄
            status_text = "功率过低"
        elif current_power < 80:
            # 绿色区间 (完美)
            bar_color = COLOR_GREEN
            set_led_color(0, 255, 0)   # 灯光变绿
            status_text = "完美！保持住"
            speak_now("当前功率完美，保持这个踏频")
        else:
            # 红色区间 (过载)
            bar_color = COLOR_RED
            set_led_color(255, 0, 0)   # 灯光变红
            status_text = "注意！请放松"
            speak_now("功率即将超出区间，请稍微放松")

        # 3. 绘制 UI 界面
        # 绘制标题
        title = font_main.render("实时训练功率监控", True, (255, 255, 255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))

        # 绘制进度条背景框
        pygame.draw.rect(screen, COLOR_GRAY, (BAR_X, BAR_Y, BAR_WIDTH, BAR_HEIGHT), 3, border_radius=10)
        
        # 绘制进度条填充
        fill_width = int((current_power / 100) * (BAR_WIDTH - 10))
        if fill_width > 5:
            pygame.draw.rect(screen, bar_color, (BAR_X + 5, BAR_Y + 5, fill_width, BAR_HEIGHT - 10), border_radius=5)

        # 绘制数值百分比
        power_val = font_main.render(f"{int(current_power)}%", True, bar_color)
        screen.blit(power_val, (WIDTH//2 - power_val.get_width()//2, BAR_Y - 60))

        # 绘制状态提示
        status_display = font_sub.render(status_text, True, (200, 200, 200))
        screen.blit(status_display, (WIDTH//2 - status_display.get_width()//2, BAR_Y + 80))

        pygame.display.flip()
        clock.tick(30) # 限制30帧，节省树莓派CPU

finally:
    # 退出前关闭灯光和资源
    set_led_color(0, 0, 0)
    spi.close()
    pygame.quit()