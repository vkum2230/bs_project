#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试 - 直接调用后端 API
"""

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit
from PyQt5.QtCore import Qt, pyqtSignal, QObject, pyqtSlot
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
import urllib.request
import urllib.parse
import json


class TestAPIHandler(QObject):
    """测试 API Handler"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.amap_key = "8b657a470f4b69e82bf81f72b3a2b3c0"
    
    @pyqtSlot(str, result=str)
    def test_regeo(self, location):
        """测试逆地理编码"""
        try:
            url = f"https://restapi.amap.com/v3/geocode/regeo"
            params = {
                'key': self.amap_key,
                'location': location,
                'extensions': 'all',
                'output': 'json'
            }
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            
            print(f"[TestAPI] 请求: {full_url}")
            
            with urllib.request.urlopen(full_url, timeout=5) as response:
                data = response.read().decode('utf-8')
                print(f"[TestAPI] 响应: {data[:200]}")
                return data
        except Exception as e:
            print(f"[TestAPI] 错误: {e}")
            return json.dumps({'status': '0', 'info': str(e)})


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("API 测试")
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # 日志显示
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        
        # 测试按钮
        btn = QPushButton("测试逆地理编码 (116.397,39.909)")
        btn.clicked.connect(self.test_api)
        layout.addWidget(btn)
        
        # WebView
        self.web_view = QWebEngineView()
        self.web_view.setHtml(self.get_html())
        layout.addWidget(self.web_view)
        
        # 设置 QWebChannel
        self.channel = QWebChannel()
        self.handler = TestAPIHandler()
        self.channel.registerObject('testAPI', self.handler)
        self.web_view.page().setWebChannel(self.channel)
        
        self.log.append("QWebChannel 已初始化")
        self.log.append("testAPI 已注册")
    
    def test_api(self):
        """直接测试 API"""
        self.log.append("\n直接调用 Python API...")
        result = self.handler.test_regeo("116.397428,39.90923")
        self.log.append(f"结果: {result[:200]}")
    
    def get_html(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
</head>
<body>
    <h3>WebChannel 测试</h3>
    <button onclick="testJS()">点击测试 JS 调用</button>
    <div id="result"></div>
    
    <script>
        var testAPI = null;
        
        // 初始化 QWebChannel
        document.addEventListener("DOMContentLoaded", function() {
            if (typeof qt !== 'undefined') {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    testAPI = channel.objects.testAPI;
                    document.getElementById('result').innerHTML = 'QWebChannel 连接成功!';
                    console.log('QWebChannel 连接成功');
                });
            } else {
                document.getElementById('result').innerHTML = 'qt 未定义';
            }
        });
        
        function testJS() {
            if (!testAPI) {
                document.getElementById('result').innerHTML = 'API 未连接';
                return;
            }
            
            document.getElementById('result').innerHTML = '请求中...';
            testAPI.test_regeo("116.397428,39.90923", function(result) {
                var data = JSON.parse(result);
                if (data.status === '1') {
                    document.getElementById('result').innerHTML = 
                        '成功: ' + data.regeocode.formatted_address;
                } else {
                    document.getElementById('result').innerHTML = '失败: ' + data.info;
                }
            });
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = TestWindow()
    w.show()
    sys.exit(app.exec_())
