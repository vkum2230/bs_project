import sys
import socket
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QSpacerItem, QSizePolicy
from PyQt5.QtCore import QTimer, QDateTime, Qt
from PyQt5.QtGui import QFont, QPixmap

# --- 关键：导入你写的串口处理类 ---
from serial_handler import SerialReader

class BikeComputerPro(QWidget):
    def __init__(self):
        super().__init__()

        # 1. 路径处理
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.wifi_on_path = os.path.join(self.base_path, "TuBiao/wifi_on.png")
        self.wifi_off_path = os.path.join(self.base_path, "TuBiao/wifi_off.png")

        # 2. 窗口基础设置
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen()
        self.setStyleSheet("background-color: #FFFFFF;") 
        self.setCursor(Qt.BlankCursor)

        # 3. 主布局
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- 第一部分：状态栏 ---
        self.status_bar = QWidget()
        self.status_bar.setFixedHeight(50) 
        self.status_layout = QHBoxLayout(self.status_bar)
        self.status_layout.setContentsMargins(30, 5, 30, 0) 
        self.status_layout.setSpacing(0)

        # [左侧区域]：数据显示界面 + 竖线
        self.left_container = QWidget()
        self.left_layout = QHBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(12)
        self.left_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.page_title = QLabel("数据显示界面")
        self.page_title.setStyleSheet("color: #2980b9;") # 淡蓝色
        self.page_title.setFont(QFont("Helvetica", 14, QFont.Medium))
        
        self.v_line = QFrame()
        self.v_line.setFixedWidth(2)
        self.v_line.setFixedHeight(20)
        self.v_line.setStyleSheet("background-color: #D0D0D0; border: none;")

        self.left_layout.addWidget(self.page_title)
        self.left_layout.addWidget(self.v_line)

        # [中间区域]：SMART RIDE
        self.center_container = QWidget()
        self.center_layout = QHBoxLayout(self.center_container)
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.center_layout.setAlignment(Qt.AlignCenter)

        self.title_label = QLabel("SMART RIDE")
        self.title_label.setStyleSheet("color: #AAAAAA;") 
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.center_layout.addWidget(self.title_label)

        # [右侧区域]：保持你的 WiFi 和 时间 逻辑
        self.right_container = QWidget()
        self.right_layout = QHBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.wifi_icon_label = QLabel()
        self.wifi_icon_label.setFixedSize(60, 30) 
        self.wifi_icon_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.wifi_icon_label.setStyleSheet("margin-right: 15px;") # 保持你的15px间距

        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: #000000;")
        self.time_label.setFont(QFont("Arial", 22, QFont.Bold))

        self.right_layout.addWidget(self.wifi_icon_label)
        self.right_layout.addWidget(self.time_label)

        # 状态栏按 1:1:1 分布
        self.status_layout.addWidget(self.left_container, 1)
        self.status_layout.addWidget(self.center_container, 1)
        self.status_layout.addWidget(self.right_container, 1)

        # --- 第二部分：黑色分割线 ---
        self.line = QFrame()
        self.line.setFrameShape(QFrame.HLine)
        self.line.setLineWidth(1) 
        self.line.setStyleSheet("color: #000000;")

        # --- 第三部分：下方数据显示大区 ---
        self.data_area = QWidget()
        self.data_layout = QVBoxLayout(self.data_area)
        self.data_layout.setAlignment(Qt.AlignCenter)

        # 温度显示大字
        self.temp_label = QLabel("等待数据...")
        self.temp_label.setStyleSheet("color: #333333;")
        self.temp_label.setFont(QFont("Arial", 60, QFont.Bold))
        self.data_layout.addWidget(self.temp_label)

        self.main_layout.addWidget(self.status_bar)
        self.main_layout.addWidget(self.line)
        self.main_layout.addWidget(self.data_area, 1)
        self.setLayout(self.main_layout)

        # 4. 初始化定时器 (刷新时间/WiFi)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_info)
        self.timer.start(1000) 
        self.wifi_counter = 0

        # 5. 初始化并启动串口线程
        self.serial_worker = SerialReader(port='/dev/ttyAMA2')
        # 核心：将串口信号连接到 UI 处理函数
        self.serial_worker.data_received.connect(self.on_data_received)
        self.serial_worker.start()

        self.update_info()

    def on_data_received(self, data):
        """处理从串口传过来的字典数据"""
        if "temperature" in data:
            val = data["temperature"]
            self.temp_label.setText(f"{val} ℃")
            # 颜色逻辑：根据数值变化颜色
            if float(val) > 30:
                self.temp_label.setStyleSheet("color: #e74c3c;") # 红色
            else:
                self.temp_label.setStyleSheet("color: #2ecc71;") # 绿色

    def check_wifi(self):
        try:
            socket.setdefaulttimeout(0.5)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        except:
            return False

    def update_info(self):
        current_time = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.time_label.setText(current_time)

        if self.wifi_counter % 5 == 0:
            image_path = self.wifi_on_path if self.check_wifi() else self.wifi_off_path
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(self.wifi_icon_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.wifi_icon_label.setPixmap(scaled_pixmap)
        self.wifi_counter += 1

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.serial_worker.stop() # 退出前停止线程
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setOverrideCursor(Qt.BlankCursor)
    window = BikeComputerPro()
    window.show()
    sys.exit(app.exec_())