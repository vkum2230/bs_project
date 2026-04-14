#!/usr/bin/env python3
"""
导航功能最小测试 - 用于诊断路线规划问题
"""

import sys
import os
os.environ['QT_QPA_PLATFORM'] = 'wayland'

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt

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
        
        # 地图视图
        self.web = QWebEngineView()
        layout.addWidget(self.web, stretch=1)
        
        self.load_test_page()
        
    def log_msg(self, msg):
        self.log.append(msg)
        print(msg)
        
    def load_test_page(self):
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
    <div id="result"></div>
    
    <script>
        var map, driving;
        var currentPos = [121.473701, 31.230416];
        var destPos = [121.490091, 31.238525];
        var logs = [];
        
        function log(msg) {
            var line = new Date().toLocaleTimeString() + ': ' + msg;
            logs.push(line);
            console.log(line);
            document.getElementById('result').innerHTML += line + '<br>';
        }
        
        // 等待 AMap 加载
        function waitAMap(cb) {
            var t = setInterval(function() {
                if (typeof AMap !== 'undefined') {
                    clearInterval(t);
                    cb(true);
                }
            }, 100);
        }
        
        waitAMap(function(ok) {
            if (!ok) { log('AMap加载失败'); return; }
            
            log('✅ AMap 已加载');
            log('  AMap.Map = ' + typeof AMap.Map);
            log('  AMap.Driving = ' + typeof AMap.Driving);
            
            // 初始化地图
            map = new AMap.Map('container', {
                zoom: 13,
                center: currentPos
            });
            log('✅ 地图初始化完成');
            
            // 添加标记
            new AMap.Marker({position: currentPos, map: map, title: '起点'});
            new AMap.Marker({position: destPos, map: map, title: '终点'});
            log('✅ 标记添加完成');
            
            // 初始化 Driving
            try {
                driving = new AMap.Driving({
                    map: map,
                    policy: AMap.DrivingPolicy.LEAST_DISTANCE
                });
                log('✅ Driving 初始化完成');
            } catch (e) {
                log('❌ Driving 初始化失败: ' + e.message);
            }
        });
        
        // 测试函数
        window.testNav = function() {
            if (!driving) { log('❌ Driving 未初始化'); return; }
            
            log('--- 开始路线规划测试 ---');
            log('起点: ' + JSON.stringify(currentPos));
            log('终点: ' + JSON.stringify(destPos));
            
            var start = new AMap.LngLat(currentPos[0], currentPos[1]);
            var end = new AMap.LngLat(destPos[0], destPos[1]);
            
            log('调用 driving.search()...');
            
            driving.search(start, end, function(status, result) {
                log('回调被调用!');
                log('  status = ' + status);
                log('  result 类型 = ' + typeof result);
                
                if (status === 'complete') {
                    log('✅ 路线规划成功');
                    if (result && result.routes && result.routes[0]) {
                        var r = result.routes[0];
                        log('  距离: ' + r.distance + '米');
                        log('  时间: ' + r.time + '秒');
                        log('  步骤: ' + r.steps.length + '个');
                    } else {
                        log('⚠️ 结果格式异常: ' + JSON.stringify(result).substring(0, 200));
                    }
                } else {
                    log('❌ 路线规划失败');
                    log('  status = ' + status);
                    if (result) {
                        log('  result = ' + JSON.stringify(result));
                        if (result.info) log('  info = ' + result.info);
                    }
                }
            });
            
            log('search() 调用完成，等待回调...');
        };
    </script>
</body>
</html>"""
        self.web.setHtml(html)
        
    def run_test(self):
        self.log_msg("运行测试...")
        self.web.page().runJavaScript("testNav()")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = NavTest()
    w.show()
    sys.exit(app.exec_())
