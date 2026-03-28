#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地图调试版本 - 用于诊断触摸和旋转问题
"""

import sys
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage

class DebugWebPage(QWebEnginePage):
    """自定义WebPage以捕获JavaScript控制台消息"""
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[JS Console {level}] {message} (line {lineNumber})")

class MapDebugWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("地图调试 - 触摸和旋转测试")
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        self.web_view = QWebEngineView()
        self.web_view.setAttribute(Qt.WA_AcceptTouchEvents, True)
        
        # 使用自定义页面以捕获控制台
        self.web_page = DebugWebPage(self.web_view)
        self.web_view.setPage(self.web_page)
        
        # 启用设置
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.TouchIconsEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        
        # 加载测试HTML
        html_content = self.generate_test_html()
        self.web_view.setHtml(html_content)
        
        layout.addWidget(self.web_view)
        
        print("=" * 60)
        print("地图调试窗口已打开")
        print("=" * 60)
        print("\n请观察上方输出的 JavaScript 控制台消息")
        print("尝试以下操作：")
        print("1. 点击右上角的 + - 按钮（应该看到 zoom 日志）")
        print("2. 点击 ← → 旋转按钮（应该看到 rotation 日志）")
        print("3. 在地图上双指触摸（应该看到 touch 日志）")
        print("\n如果看到红色错误信息，请记录下来")
    
    def generate_test_html(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>地图调试</title>
    <style>
        body { margin: 0; padding: 0; overflow: hidden; }
        #container { width: 100%; height: 100vh; touch-action: none; }
        #debug-info {
            position: fixed;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.9);
            color: #0f0;
            padding: 10px;
            font-family: monospace;
            font-size: 12px;
            z-index: 9999;
            max-width: 350px;
            max-height: 200px;
            overflow-y: auto;
            border: 2px solid #0f0;
        }
        .map-controls {
            position: absolute;
            top: 75px;
            right: 10px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            z-index: 1000;
        }
        .btn-control {
            width: 50px;
            height: 50px;
            border-radius: 8px;
            background: rgba(0,0,0,0.8);
            border: 2px solid #0f0;
            color: #0f0;
            font-size: 24px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div id="debug-info">等待初始化...</div>
    <div id="container"></div>
    
    <div class="map-controls">
        <button class="btn-control" onclick="testZoomIn()">+</button>
        <button class="btn-control" onclick="testZoomOut()">-</button>
        <button class="btn-control" onclick="testRotateLeft()">←</button>
        <button class="btn-control" onclick="testRotateRight()">→</button>
        <button class="btn-control" onclick="testReset()">↑</button>
        <button class="btn-control" onclick="testInfo()">?</button>
    </div>
    
    <script>
        window._AMapSecurityConfig = {
            securityJsCode: '2355cb366c87c99e9733d5266db19854'
        };
    </script>
    <script src="https://webapi.amap.com/maps?v=2.0&key=bc9998864f9d289e0913acb4c0554c2e"></script>
    <script>
        var map;
        var debugInfo = document.getElementById('debug-info');
        var logs = [];
        
        function log(msg) {
            var time = new Date().toLocaleTimeString();
            var line = '[' + time + '] ' + msg;
            logs.push(line);
            if (logs.length > 20) logs.shift();
            debugInfo.innerHTML = logs.join('<br>');
            console.log(line);
        }
        
        // 初始化地图
        try {
            log('开始初始化地图...');
            
            map = new AMap.Map('container', {
                zoom: 16,
                center: [114.057868, 22.543099],
                viewMode: '2D',
                dragEnable: true,
                zoomEnable: true,
                rotateEnable: true,
                pitchEnable: false
            });
            
            log('地图初始化成功');
            log('当前缩放: ' + map.getZoom());
            log('当前旋转: ' + (map.getRotation() || 0));
            log('地图版本: ' + (AMap?.version || 'unknown'));
            
        } catch(e) {
            log('ERROR: 地图初始化失败: ' + e.message);
        }
        
        // 测试按钮功能
        window.testZoomIn = function() {
            try {
                var z = map.getZoom();
                log('放大前: ' + z);
                map.setZoom(z + 1);
                log('放大后: ' + map.getZoom());
            } catch(e) {
                log('ERROR 放大: ' + e.message);
            }
        };
        
        window.testZoomOut = function() {
            try {
                var z = map.getZoom();
                log('缩小前: ' + z);
                map.setZoom(z - 1);
                log('缩小后: ' + map.getZoom());
            } catch(e) {
                log('ERROR 缩小: ' + e.message);
            }
        };
        
        window.testRotateLeft = function() {
            try {
                var r = map.getRotation() || 0;
                log('旋转前: ' + r);
                var newR = r - 15;
                map.setRotation(newR);
                log('旋转后: ' + (map.getRotation() || 0));
            } catch(e) {
                log('ERROR 左旋: ' + e.message);
            }
        };
        
        window.testRotateRight = function() {
            try {
                var r = map.getRotation() || 0;
                log('旋转前: ' + r);
                var newR = r + 15;
                map.setRotation(newR);
                log('旋转后: ' + (map.getRotation() || 0));
            } catch(e) {
                log('ERROR 右旋: ' + e.message);
            }
        };
        
        window.testReset = function() {
            try {
                map.setRotation(0);
                log('已重置正北');
            } catch(e) {
                log('ERROR 重置: ' + e.message);
            }
        };
        
        window.testInfo = function() {
            try {
                log('=== 地图信息 ===');
                log('缩放: ' + map.getZoom());
                log('旋转: ' + (map.getRotation() || 0));
                log('中心: ' + map.getCenter());
                log('是否有旋转方法: ' + (typeof map.setRotation === 'function'));
            } catch(e) {
                log('ERROR 信息: ' + e.message);
            }
        };
        
        // 监听事件
        map.on('zoomchange', function() {
            log('EVENT 缩放变化: ' + map.getZoom());
        });
        
        map.on('rotatechange', function() {
            log('EVENT 旋转变化: ' + (map.getRotation() || 0));
        });
        
        // 触摸事件测试
        var container = document.getElementById('container');
        container.addEventListener('touchstart', function(e) {
            log('TOUCH start: ' + e.touches.length + '点');
        }, {passive: false});
        
        container.addEventListener('touchmove', function(e) {
            if (e.touches.length === 2) {
                log('TOUCH move: 双指');
            }
        }, {passive: false});
        
        container.addEventListener('touchend', function(e) {
            log('TOUCH end');
        }, {passive: false});
        
        // 定期检查
        setInterval(function() {
            log('状态: 缩放=' + map.getZoom().toFixed(1) + ' 旋转=' + (map.getRotation() || 0));
        }, 5000);
        
        log('初始化完成，等待操作...');
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    window = MapDebugWidget()
    window.show()
    sys.exit(app.exec_())
