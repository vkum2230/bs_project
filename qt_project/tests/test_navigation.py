#!/usr/bin/env python3
"""
导航功能独立测试程序
测试 AMap JS API 路线规划功能
"""

import sys
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, pyqtSlot, QObject, pyqtSignal


class TestHandler(QObject):
    """测试用的JavaScript-Python通信桥"""
    
    log_signal = pyqtSignal(str)
    
    @pyqtSlot(str)
    def log(self, message):
        """接收JavaScript日志"""
        print(f"[JS] {message}")
        self.log_signal.emit(message)


class NavigationTest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("导航功能测试")
        self.setGeometry(100, 100, 1200, 800)
        
        # 配置（使用相同的key）
        self.jsapi_key = "c507e554a5bb6e08b7097fa61164f0e4"
        self.security_key = "8ee0cb41f7666cfd320749d269ab6121"
        
        self.init_ui()
        
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(400)
        
        # 状态显示
        self.status_label = QLabel("状态: 等待加载...")
        left_layout.addWidget(self.status_label)
        
        # 测试按钮
        self.btn_test_amap = QPushButton("1. 测试 AMap 加载")
        self.btn_test_amap.clicked.connect(self.test_amap)
        left_layout.addWidget(self.btn_test_amap)
        
        self.btn_test_nav = QPushButton("2. 测试路线规划")
        self.btn_test_nav.clicked.connect(self.test_navigation)
        left_layout.addWidget(self.btn_test_nav)
        
        self.btn_clear = QPushButton("3. 清除路线")
        self.btn_clear.clicked.connect(self.clear_route)
        left_layout.addWidget(self.btn_clear)
        
        # 日志输出
        left_layout.addWidget(QLabel("日志:"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        left_layout.addWidget(self.log_output)
        
        layout.addWidget(left_panel)
        
        # 右侧地图
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view, stretch=2)
        
        # 加载测试页面
        self.load_test_page()
        
        # 设置JavaScript桥
        self.test_handler = TestHandler()
        self.test_handler.log_signal.connect(self.append_log)
        
        from PyQt5.QtWebChannel import QWebChannel
        channel = QWebChannel()
        channel.registerObject("testHandler", self.test_handler)
        self.web_view.page().setWebChannel(channel)
        
    def append_log(self, message):
        self.log_output.append(message)
        
    def load_test_page(self):
        """加载测试HTML页面"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>导航测试</title>
    <style>
        #container {{ width: 100%; height: 100vh; }}
        .info {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 10px;
            border-radius: 5px;
            z-index: 1000;
            font-family: monospace;
            font-size: 12px;
            max-width: 300px;
        }}
    </style>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <script>
        window._AMapSecurityConfig = {{
            securityJsCode: '{self.security_key}'
        }};
    </script>
    <script src="https://webapi.amap.com/maps?v=2.0&key={self.jsapi_key}&plugin=AMap.Driving,AMap.Scale"></script>
</head>
<body>
    <div id="container"></div>
    <div class="info" id="info">等待加载...</div>
    
    <script>
        var map, driving;
        var currentPos = [121.473701, 31.230416];  // 上海人民广场
        var destPos = [121.4906, 31.2397];  // 上海外滩
        var testHandler = null;
        
        function log(msg) {{
            console.log(msg);
            document.getElementById('info').innerHTML += '<br>' + msg;
            if (testHandler) testHandler.log(msg);
        }}
        
        // 等待 AMap 加载
        function waitForAMap(callback, maxAttempts = 50) {{
            var attempts = 0;
            var check = setInterval(function() {{
                attempts++;
                if (typeof AMap !== 'undefined') {{
                    clearInterval(check);
                    log('✅ AMap 加载成功（尝试' + attempts + '次）');
                    callback(true);
                }} else if (attempts >= maxAttempts) {{
                    clearInterval(check);
                    log('❌ AMap 加载超时');
                    callback(false);
                }}
            }}, 100);
        }}
        
        // 初始化
        document.addEventListener('DOMContentLoaded', function() {{
            // 连接 QWebChannel
            if (typeof qt !== 'undefined') {{
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    testHandler = channel.objects.testHandler;
                    log('✅ QWebChannel 连接成功');
                }});
            }}
            
            waitForAMap(function(success) {{
                if (success) {{
                    initMap();
                }} else {{
                    document.getElementById('info').innerHTML = '❌ AMap 加载失败';
                }}
            }});
        }});
        
        function initMap() {{
            try {{
                map = new AMap.Map('container', {{
                    zoom: 14,
                    center: currentPos
                }});
                
                map.addControl(new AMap.Scale({{position: 'LB'}}));
                
                // 添加起点标记
                new AMap.Marker({{
                    position: currentPos,
                    map: map,
                    title: '起点：人民广场',
                    icon: 'https://webapi.amap.com/theme/v1.3/markers/n/start.png'
                }});
                
                // 添加终点标记
                new AMap.Marker({{
                    position: destPos,
                    map: map,
                    title: '终点：外滩',
                    icon: 'https://webapi.amap.com/theme/v1.3/markers/n/end.png'
                }});
                
                log('✅ 地图初始化完成');
                log('起点: ' + currentPos);
                log('终点: ' + destPos);
                
                // 初始化导航
                initDriving();
                
            }} catch (e) {{
                log('❌ 地图初始化失败: ' + e.message);
            }}
        }}
        
        function initDriving() {{
            try {{
                driving = new AMap.Driving({{
                    map: map,
                    policy: AMap.DrivingPolicy.LEAST_DISTANCE,
                    hideMarkers: false
                }});
                
                driving.on('complete', function(result) {{
                    log('✅ 路线规划完成事件触发');
                    log('结果类型: ' + typeof result);
                    
                    if (result && result.routes && result.routes[0]) {{
                        var route = result.routes[0];
                        log('距离: ' + route.distance + '米');
                        log('时间: ' + Math.ceil(route.time/60) + '分钟');
                        log('步骤数: ' + route.steps.length);
                        
                        // 显示第一条指令
                        if (route.steps[0]) {{
                            var instruction = route.steps[0].instruction.replace(/<[^>]+>/g, '');
                            log('第一条指令: ' + instruction);
                        }}
                    }} else {{
                        log('⚠️ 路线结果为空');
                        log('结果内容: ' + JSON.stringify(result).substring(0, 200));
                    }}
                }});
                
                driving.on('error', function(error) {{
                    log('❌ 路线规划错误事件触发');
                    log('错误类型: ' + typeof error);
                    
                    // 尝试提取错误信息
                    var errorInfo = '';
                    if (error) {{
                        if (error.info) errorInfo = error.info;
                        else if (error.message) errorInfo = error.message;
                        else try {{ errorInfo = JSON.stringify(error); }} catch(e) {{ errorInfo = String(error); }}
                    }}
                    log('错误信息: ' + errorInfo);
                }});
                
                log('✅ Driving 初始化完成');
                
            }} catch (e) {{
                log('❌ Driving 初始化失败: ' + e.message);
            }}
        }}
        
        // 测试函数
        window.testAMap = function() {{
            if (typeof AMap === 'undefined') {{
                log('❌ AMap 未定义');
                return false;
            }}
            log('✅ AMap 已定义');
            log('AMap.Map: ' + (typeof AMap.Map));
            log('AMap.Driving: ' + (typeof AMap.Driving));
            log('AMap.DrivingPolicy: ' + (typeof AMap.DrivingPolicy));
            return true;
        }};
        
        window.testNavigation = function() {{
            if (!driving) {{
                log('❌ Driving 未初始化');
                return;
            }}
            
            log('🗺️ 开始路线规划测试...');
            log('起点: ' + currentPos);
            log('终点: ' + destPos);
            
            try {{
                var startPoint = new AMap.LngLat(currentPos[0], currentPos[1]);
                var endPoint = new AMap.LngLat(destPos[0], destPos[1]);
                
                driving.search(startPoint, endPoint);
                log('✅ search() 调用成功');
            }} catch (e) {{
                log('❌ search() 调用失败: ' + e.message);
            }}
        }};
        
        window.clearRoute = function() {{
            if (driving) {{
                driving.clear();
                log('✅ 路线已清除');
            }}
        }};
    </script>
</body>
</html>"""
        self.web_view.setHtml(html)
        
    def test_amap(self):
        """测试 AMap 加载"""
        self.status_label.setText("状态: 测试 AMap...")
        self.web_view.page().runJavaScript("testAMap()", self.on_amap_test_result)
        
    def on_amap_test_result(self, result):
        if result:
            self.status_label.setText("状态: ✅ AMap 正常")
        else:
            self.status_label.setText("状态: ❌ AMap 异常")
            
    def test_navigation(self):
        """测试路线规划"""
        self.status_label.setText("状态: 测试导航...")
        self.web_view.page().runJavaScript("testNavigation()")
        
    def clear_route(self):
        """清除路线"""
        self.web_view.page().runJavaScript("clearRoute()")


def main():
    import os
    os.environ['QT_QPA_PLATFORM'] = 'wayland'
    
    app = QApplication(sys.argv)
    window = NavigationTest()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
