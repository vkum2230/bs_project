from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
                             QProgressBar, QStackedWidget)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt


class MapPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)

        # 位置信息卡片
        self.location_card = QLabel("📍 等待定位...")
        self.location_card.setStyleSheet("""
            QLabel {
                color: #4DB8FF;
                background-color: #2A2A2A;
                border-radius: 10px;
                border: 2px solid #4DB8FF;
                padding: 15px;
            }
        """)
        self.location_card.setFont(QFont("Helvetica", 14, QFont.Bold))
        self.location_card.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.location_card)

        # 坐标显示
        coords_layout = QHBoxLayout()
        self.lat_label = QLabel("纬度: --")
        self.lat_label.setStyleSheet("color: #888888; background: transparent;")
        self.lat_label.setFont(QFont("Arial", 11))
        self.lat_label.setAlignment(Qt.AlignCenter)
        
        self.lon_label = QLabel("经度: --")
        self.lon_label.setStyleSheet("color: #888888; background: transparent;")
        self.lon_label.setFont(QFont("Arial", 11))
        self.lon_label.setAlignment(Qt.AlignCenter)
        
        coords_layout.addWidget(self.lat_label)
        coords_layout.addWidget(self.lon_label)
        self.main_layout.addLayout(coords_layout)

        # 地图显示区域（堆叠：加载中/地图/占位符）
        self.map_stack = QStackedWidget()
        self.map_stack.setMinimumHeight(240)
        self.map_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #252525;
                border-radius: 12px;
                border: 2px solid #3A3A3A;
            }
        """)
        
        # 页面1: 下载进度
        self.download_page = QWidget()
        dl_layout = QVBoxLayout(self.download_page)
        dl_layout.setAlignment(Qt.AlignCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4DB8FF;
                border-radius: 8px;
                text-align: center;
                color: white;
                background-color: #2A2A2A;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4DB8FF;
                border-radius: 6px;
            }
        """)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setFixedWidth(250)
        dl_layout.addWidget(self.progress_bar)
        
        self.download_label = QLabel("正在下载地图...")
        self.download_label.setStyleSheet("color: #4DB8FF; background: transparent;")
        self.download_label.setFont(QFont("Helvetica", 12))
        self.download_label.setAlignment(Qt.AlignCenter)
        dl_layout.addWidget(self.download_label)
        
        # 页面2: 地图显示
        self.map_display = QLabel()
        self.map_display.setStyleSheet("""
            QLabel {
                background-color: #252525;
                border-radius: 10px;
            }
        """)
        self.map_display.setAlignment(Qt.AlignCenter)
        self.map_display.setScaledContents(True)
        
        # 页面3: 离线占位符
        self.offline_page = QWidget()
        offline_layout = QVBoxLayout(self.offline_page)
        offline_layout.setAlignment(Qt.AlignCenter)
        
        self.offline_icon = QLabel("🗺️")
        self.offline_icon.setStyleSheet("color: #666666; background: transparent; font-size: 48px;")
        self.offline_icon.setAlignment(Qt.AlignCenter)
        offline_layout.addWidget(self.offline_icon)
        
        self.offline_text = QLabel("简图模式\n(无本地地图)")
        self.offline_text.setStyleSheet("color: #666666; background: transparent;")
        self.offline_text.setFont(QFont("Arial", 14))
        self.offline_text.setAlignment(Qt.AlignCenter)
        offline_layout.addWidget(self.offline_text)
        
        self.map_stack.addWidget(self.download_page)   # index 0
        self.map_stack.addWidget(self.map_display)     # index 1
        self.map_stack.addWidget(self.offline_page)    # index 2
        
        self.main_layout.addWidget(self.map_stack, 1)

        # 缓存状态
        self.cache_label = QLabel("💾 已缓存: 0 个省份")
        self.cache_label.setStyleSheet("color: #555555; background: transparent;")
        self.cache_label.setFont(QFont("Helvetica", 9))
        self.cache_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.cache_label)

    def update_location(self, location_info):
        """更新位置显示"""
        province = location_info.get('province', '未知')
        lat = location_info.get('lat', 0)
        lon = location_info.get('lon', 0)
        
        self.location_card.setText(f"📍 {province}")
        self.lat_label.setText(f"纬度: {lat:.4f}°")
        self.lon_label.setText(f"经度: {lon:.4f}°")
        
        # 根据是否有省份改变颜色
        if province and province != "未知区域":
            self.location_card.setStyleSheet("""
                QLabel {
                    color: #2ecc71;
                    background-color: #2A2A2A;
                    border-radius: 10px;
                    border: 2px solid #2ecc71;
                    padding: 15px;
                }
            """)
        else:
            self.location_card.setStyleSheet("""
                QLabel {
                    color: #e74c3c;
                    background-color: #2A2A2A;
                    border-radius: 10px;
                    border: 2px solid #e74c3c;
                    padding: 15px;
                }
            """)

    def show_download_progress(self, progress):
        """显示下载进度"""
        self.map_stack.setCurrentIndex(0)
        self.progress_bar.setValue(progress)
        self.download_label.setText(f"正在下载地图... {progress}%")

    def load_local_map(self, map_path, province_name):
        """加载本地地图"""
        self.map_stack.setCurrentIndex(1)
        pixmap = QPixmap(map_path)
        if not pixmap.isNull():
            # 缩放适应窗口
            scaled = pixmap.scaled(self.map_stack.width() - 20, 
                                  self.map_stack.height() - 20,
                                  Qt.KeepAspectRatio, 
                                  Qt.SmoothTransformation)
            self.map_display.setPixmap(scaled)
        else:
            self.map_display.setText(f"📍 {province_name}\n(地图加载失败)")

    def show_offline_placeholder(self, province_name):
        """显示离线占位符"""
        self.map_stack.setCurrentIndex(2)
        self.offline_text.setText(f"{province_name}\n(简图模式)")
    
    def update_cache_count(self, count):
        """更新缓存数量显示"""
        self.cache_label.setText(f"💾 已缓存: {count} 个省份")
    
    def resizeEvent(self, event):
        """窗口大小变化时重新缩放地图"""
        super().resizeEvent(event)
        # 如果当前显示的是地图，重新缩放
        if self.map_stack.currentIndex() == 1 and self.map_display.pixmap():
            pixmap = self.map_display.pixmap()
            scaled = pixmap.scaled(self.map_stack.width() - 20,
                                  self.map_stack.height() - 20,
                                  Qt.KeepAspectRatio,
                                  Qt.SmoothTransformation)
            self.map_display.setPixmap(scaled)