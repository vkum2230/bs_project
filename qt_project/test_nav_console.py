#!/usr/bin/env python3
"""
导航测试 - 捕获JavaScript控制台输出
"""

import sys
import os
os.environ['QT_QPA_PLATFORM'] = 'wayland'

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import Qt, pyqtSlot, QObject
from PyQt5.QtWebChannel import QWebChannel

class ConsoleHandler(QObject):
    @pyqtSlot(str)
    def log(self, message):
        print(f"[JS Console] {message}")

class WebPage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        levels = {0: "INFO", 1: "WARNING", 2: "ERROR"}
        level_str = levels.get(level, "DEBUG")
        print(f"[{level_str}] {message}")

class NavTest(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("导航诊断测试")
        self.resize(1000, 700)
        
        layout = QVBoxLayout(self)
        
        # 日志输出
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(200)
        layout.addWidget(self.log)
        
        # 测试按钮
        btn_test = QPushButton("开始测试路线规划")
        btn_test.clicked.connect(self.run_test)
        layout.addWidget(btn_test)
        
        # 地图视图 - 使用自定义Page来捕获控制台
        self.web = QWebEngineView()
        self.page = WebPage(self.web)
        self.web.setPage(self.page)
        layout.addWidget(self.web, stretch=1)
        
        self.load_test_page()
        
    def log_msg(self, msg):
        self.log.append(msg)
        print(msg)
        
    def load_test_page(self):
        # 使用直接传递坐标的方式测试
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>导航测试</title>
    <style>
        #container { width: 100%; height: 400px; }
        body { font-family: monospace; margin: 10px; }
    </style>
    <script>
        window._AMapSecurityConfig = {
            securityJsCode: '8ee0cb41f7666cfd320749d269ab6121'
        };
    </script>
    <script src="https://webapi.amap.com/maps?v=2.0&key=c507e554a5bb6e08b7097fa61164f0e4&plugin=AMap.Driving,AMap.Scale"></script>
</head>
<body>
    <h3>高德地图路线规划测试</h3>
    <div id="container"></div>
    
    <script>
        var map, driving;
        // 上海人民广场 -> 上海外滩
        var currentPos = [121.473701, 31.230416];
        var destPos = [121.490091, 31.238525];
        
        function waitAMap(cb) {
            var count = 0;
            var t = setInterval(function() {
                count++;
                if (typeof AMap !== 'undefined') {
                    clearInterval(t);
                    console.log('AMap loaded after ' + count + ' checks');
                    cb(true);
                } else if (count > 50) {
                    clearInterval(t);
                    console.error('AMap load timeout');
                    cb(false);
                }
            }, 100);
        }
        
        waitAMap(function(ok) {
            if (!ok) return;
            
            console.log('AMap types: Map=' + typeof AMap.Map + ', Driving=' + typeof AMap.Driving);
            
            map = new AMap.Map('container', {
                zoom: 14,
                center: currentPos
            });
            
            new AMap.Marker({position: currentPos, map: map, title: '起点'});
            new AMap.Marker({position: destPos, map: map, title: '终点'});
            
            console.log('Map initialized');
            
            try {
                driving = new AMap.Driving({
                    map: map,
                    policy: AMap.DrivingPolicy.LEAST_DISTANCE
                });
                console.log('Driving initialized');
            } catch (e) {
                console.error('Driving init failed: ' + e.message);
            }
        });
        
        window.testNav = function() {
            console.log('--- Test Navigation ---');
            console.log('Start: ' + JSON.stringify(currentPos));
            console.log('End: ' + JSON.stringify(destPos));
            
            if (!driving) {
                console.error('Driving not initialized');
                return;
            }
            
            var start = new AMap.LngLat(currentPos[0], currentPos[1]);
            var end = new AMap.LngLat(destPos[0], destPos[1]);
            
            console.log('Calling driving.search()...');
            
            driving.search(start, end, function(status, result) {
                console.log('Callback received!');
                console.log('  status: ' + status);
                console.log('  result type: ' + typeof result);
                
                if (status === 'complete') {
                    console.log('Route planning SUCCESS');
                    if (result && result.routes && result.routes[0]) {
                        var r = result.routes[0];
                        console.log('  Distance: ' + r.distance + 'm');
                        console.log('  Time: ' + r.time + 's');
                        console.log('  Steps: ' + r.steps.length);
                    }
                } else {
                    console.error('Route planning FAILED');
                    console.error('  status: ' + status);
                    if (result) {
                        console.error('  result: ' + JSON.stringify(result));
                    }
                }
            });
            
            console.log('search() called');
        };
    </script>
</body>
</html>"""
        self.web.setHtml(html)
        
    def run_test(self):
        print("\n=== Starting Navigation Test ===")
        self.page.runJavaScript("testNav()")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = NavTest()
    w.show()
    sys.exit(app.exec_())
