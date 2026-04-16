#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史记录页面（方案 A - 简洁列表 + 详情面板）

职责：
- 展示历史骑行记录列表
- 选中记录后显示详情统计
- 支持"查看轨迹"和"删除记录"
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QFrame, QMessageBox, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from persistence.ride_repository import RideRepository


def _format_moving_time(seconds: float) -> str:
    """将秒数格式化为 hh:mm:ss"""
    t = int(seconds)
    h = t // 3600
    m = (t % 3600) // 60
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class _RideItemWidget(QFrame):
    """列表中的单条记录卡片"""

    def __init__(self, meta: Dict[str, Any], selected: bool = False, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self._set_selected(selected)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(16)

        # 日期列
        start_ts = meta.get("start_time", 0)
        dt = datetime.fromtimestamp(start_ts) if start_ts else datetime.now()
        date_str = dt.strftime("%m-%d")
        time_str = dt.strftime("%H:%M")

        date_layout = QVBoxLayout()
        date_layout.setSpacing(2)
        date_layout.setAlignment(Qt.AlignCenter)

        date_lbl = QLabel(date_str)
        date_lbl.setAlignment(Qt.AlignCenter)
        date_lbl.setStyleSheet("color: #AAAAAA; background: transparent;")
        date_lbl.setFont(QFont("Arial", 11))

        time_lbl = QLabel(time_str)
        time_lbl.setAlignment(Qt.AlignCenter)
        time_lbl.setStyleSheet("color: #FFFFFF; background: transparent;")
        time_lbl.setFont(QFont("Arial", 14, QFont.Bold))

        date_layout.addWidget(date_lbl)
        date_layout.addWidget(time_lbl)
        layout.addLayout(date_layout)

        # 分隔线
        line = QFrame()
        line.setFixedWidth(1)
        line.setStyleSheet("background-color: #555555;")
        layout.addWidget(line)

        # 统计数据
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        stats_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        dist = meta.get("total_distance", 0.0)
        dist_str = f"{dist:.2f} km" if dist >= 1.0 else f"{int(dist * 1000)} m"

        avg_speed = meta.get("avg_speed", 0.0)
        speed_str = f"{avg_speed:.1f} km/h"

        moving_time = _format_moving_time(meta.get("moving_time", 0))

        def _make_stat(value, label):
            vl = QVBoxLayout()
            vl.setSpacing(2)
            vl.setAlignment(Qt.AlignCenter)
            v = QLabel(str(value))
            v.setStyleSheet("color: #FFFFFF; background: transparent;")
            v.setFont(QFont("Arial", 13, QFont.Bold))
            v.setAlignment(Qt.AlignCenter)
            l = QLabel(label)
            l.setStyleSheet("color: #888888; background: transparent;")
            l.setFont(QFont("Helvetica", 9))
            l.setAlignment(Qt.AlignCenter)
            vl.addWidget(v)
            vl.addWidget(l)
            return vl

        stats_layout.addLayout(_make_stat(dist_str, "距离"))
        stats_layout.addLayout(_make_stat(moving_time, "时长"))
        stats_layout.addLayout(_make_stat(speed_str, "均速"))
        layout.addLayout(stats_layout)

        layout.addStretch(1)

        # 右侧箭头
        arrow = QLabel(">")
        arrow.setStyleSheet("color: #666666; background: transparent;")
        arrow.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(arrow)

    def _set_selected(self, selected: bool):
        color = "#3A3A4A" if selected else "#2E2E3A"
        self.setStyleSheet(f"""
            _RideItemWidget {{
                background-color: {color};
                border-radius: 10px;
            }}
        """)


class HistoryPage(QWidget):
    """历史骑行记录列表页"""

    ride_selected = pyqtSignal(str, list)  # ride_id, track_points

    def __init__(self, ride_repo: Optional[RideRepository] = None, parent=None):
        super().__init__(parent)
        self.ride_repo = ride_repo

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # 标题栏
        header = QHBoxLayout()
        header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        title = QLabel("📜 历史记录")
        title.setStyleSheet("color: #FFFFFF; background: transparent;")
        title.setFont(QFont("Helvetica", 14, QFont.Bold))
        header.addWidget(title)

        header.addStretch(1)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedSize(60, 28)
        self.refresh_btn.setStyleSheet(
            "QPushButton { background-color: #4DB8FF; color: #FFFFFF; border-radius: 6px; font-size: 12px; }"
            "QPushButton:pressed { background-color: #3A9BD6; }"
        )
        self.refresh_btn.clicked.connect(self.refresh_list)
        header.addWidget(self.refresh_btn)

        layout.addLayout(header)

        # 列表
        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(0)
        self.list_widget.setSpacing(8)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: transparent;
            }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

        # 空状态提示
        self.empty_label = QLabel("暂无骑行记录\n开始你的第一次骑行吧！")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #666666; background: transparent;")
        self.empty_label.setFont(QFont("Helvetica", 12))
        layout.addWidget(self.empty_label)

        # 详情面板（默认隐藏）
        self.detail_panel = QFrame()
        self.detail_panel.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border-radius: 12px;
                border: 1px solid #3A3A4A;
            }
        """)
        detail_layout = QVBoxLayout(self.detail_panel)
        detail_layout.setContentsMargins(12, 10, 12, 10)
        detail_layout.setSpacing(10)

        detail_title = QLabel("📊 骑行详情")
        detail_title.setStyleSheet("color: #4DB8FF; background: transparent;")
        detail_title.setFont(QFont("Helvetica", 12, QFont.Bold))
        detail_layout.addWidget(detail_title)

        # 统计网格
        stats_grid = QGridLayout()
        stats_grid.setSpacing(8)
        stats_grid.setHorizontalSpacing(20)

        self._detail_labels: Dict[str, QLabel] = {}

        def _add_detail(row, col, key, title):
            vl = QVBoxLayout()
            vl.setSpacing(2)
            val = QLabel("--")
            val.setStyleSheet("color: #FFFFFF; background: transparent;")
            val.setFont(QFont("Arial", 12, QFont.Bold))
            lbl = QLabel(title)
            lbl.setStyleSheet("color: #888888; background: transparent;")
            lbl.setFont(QFont("Helvetica", 9))
            vl.addWidget(val)
            vl.addWidget(lbl)
            stats_grid.addLayout(vl, row, col)
            self._detail_labels[key] = val

        _add_detail(0, 0, "start_time", "开始时间")
        _add_detail(0, 1, "total_distance", "骑行距离")
        _add_detail(0, 2, "total_time", "总时长")
        _add_detail(0, 3, "moving_time", "移动时长")

        _add_detail(1, 0, "avg_speed", "平均速度")
        _add_detail(1, 1, "max_speed", "最大速度")
        _add_detail(1, 2, "avg_power", "平均功率")
        _add_detail(1, 3, "max_power", "最大功率")

        _add_detail(2, 0, "avg_hr", "平均心率")
        _add_detail(2, 1, "max_hr", "最大心率")
        _add_detail(2, 2, "total_elevation_gain", "累计爬升")
        _add_detail(2, 3, "calories", "消耗热量")

        detail_layout.addLayout(stats_grid)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch(1)

        self.view_map_btn = QPushButton("🗺️ 查看轨迹")
        self.view_map_btn.setFixedSize(100, 32)
        self.view_map_btn.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: #FFFFFF; border-radius: 6px; font-size: 12px; }"
            "QPushButton:pressed { background-color: #27ae60; }"
        )
        self.view_map_btn.clicked.connect(self._on_view_map_clicked)
        btn_layout.addWidget(self.view_map_btn)

        self.delete_btn = QPushButton("🗑️ 删除记录")
        self.delete_btn.setFixedSize(100, 32)
        self.delete_btn.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: #FFFFFF; border-radius: 6px; font-size: 12px; }"
            "QPushButton:pressed { background-color: #c0392b; }"
        )
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch(1)
        detail_layout.addLayout(btn_layout)

        self.detail_panel.hide()
        layout.addWidget(self.detail_panel)

        self._ride_metas: List[Dict[str, Any]] = []
        self._selected_index: int = -1
        self._current_ride_id: str = ""
        self._current_track_points: List[Dict[str, Any]] = []
        self.refresh_list()

    def refresh_list(self):
        """重新加载骑行记录列表"""
        self.list_widget.clear()
        self._ride_metas = []
        self._selected_index = -1
        self.detail_panel.hide()

        if self.ride_repo is None:
            self.empty_label.setText(" RideRepository 未初始化")
            self.empty_label.show()
            return

        rides = self.ride_repo.list_rides(limit=50)
        if not rides:
            self.empty_label.setText("暂无骑行记录\n开始你的第一次骑行吧！")
            self.empty_label.show()
            return

        self.empty_label.hide()
        for meta in rides:
            self._ride_metas.append(meta)
            item = QListWidgetItem()
            widget = _RideItemWidget(meta, selected=False)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

    def _on_item_clicked(self, item: QListWidgetItem):
        index = self.list_widget.row(item)
        if index < 0 or index >= len(self._ride_metas):
            return

        # 更新选中高亮
        self._selected_index = index
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            w = self.list_widget.itemWidget(it)
            if isinstance(w, _RideItemWidget):
                w._set_selected(i == index)

        meta = self._ride_metas[index]
        ride_id = meta.get("id", "")
        if not ride_id or not self.ride_repo:
            return

        # 读取完整数据（包含 track_points）
        full = self.ride_repo.get_ride(ride_id)
        if full is None:
            return

        self._current_ride_id = ride_id
        self._current_track_points = full.get("track_points", [])
        self._update_detail_panel(full)
        self.detail_panel.show()

    def _update_detail_panel(self, meta: Dict[str, Any]):
        """用元数据更新详情面板"""
        start_ts = meta.get("start_time", 0)
        dt = datetime.fromtimestamp(start_ts) if start_ts else None
        self._detail_labels["start_time"].setText(dt.strftime("%H:%M") if dt else "--")

        dist = meta.get("total_distance", 0.0)
        self._detail_labels["total_distance"].setText(
            f"{dist:.2f} km" if dist >= 1.0 else f"{int(dist * 1000)} m"
        )

        self._detail_labels["total_time"].setText(
            _format_moving_time(meta.get("total_time", 0))
        )
        self._detail_labels["moving_time"].setText(
            _format_moving_time(meta.get("moving_time", 0))
        )

        self._detail_labels["avg_speed"].setText(f"{meta.get('avg_speed', 0.0):.1f} km/h")
        self._detail_labels["max_speed"].setText(f"{meta.get('max_speed', 0.0):.1f} km/h")
        self._detail_labels["avg_power"].setText(f"{meta.get('avg_power', 0.0):.0f} W")
        self._detail_labels["max_power"].setText(f"{meta.get('max_power', 0.0):.0f} W")
        self._detail_labels["avg_hr"].setText(f"{meta.get('avg_hr', 0.0):.0f} bpm")
        self._detail_labels["max_hr"].setText(f"{meta.get('max_hr', 0.0):.0f} bpm")
        self._detail_labels["total_elevation_gain"].setText(f"{meta.get('total_elevation_gain', 0.0):.1f} m")
        self._detail_labels["calories"].setText(f"{meta.get('calories', 0.0):.0f} kcal")

    def _on_view_map_clicked(self):
        if self._current_ride_id and self._current_track_points:
            self.ride_selected.emit(self._current_ride_id, self._current_track_points)

    def _on_delete_clicked(self):
        if not self._current_ride_id or not self.ride_repo:
            return

        reply = QMessageBox.question(
            self,
            "删除记录",
            f"确定要删除骑行记录 {self._current_ride_id} 吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success = self.ride_repo.delete_ride(self._current_ride_id)
            if success:
                self._current_ride_id = ""
                self._current_track_points = []
                self.refresh_list()
            else:
                QMessageBox.warning(self, "删除失败", "无法删除该记录，请检查文件权限。")


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    repo = RideRepository(base_dir="/tmp/test_rides")
    page = HistoryPage(ride_repo=repo)
    page.ride_selected.connect(lambda rid, pts: print(f"查看轨迹: {rid}, 点数: {len(pts)}"))
    page.setWindowTitle("HistoryPage Test")
    page.resize(480, 700)
    page.show()
    sys.exit(app.exec_())
