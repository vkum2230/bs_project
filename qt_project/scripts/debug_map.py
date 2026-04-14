#!/usr/bin/env python3
"""地图调试工具 - 检查密钥配置和生成测试页面"""

import os

def check_keys():
    """检查密钥配置"""
    print("="*60)
    print("高德地图密钥配置检查")
    print("="*60)
    
    # 从 main.py 读取配置
    main_py = open('main.py').read()
    
    # 提取密钥
    import re
    web_key = re.search(r'amap_key\s*=\s*"([^"]+)"', main_py)
    jsapi_key = re.search(r'amap_jsapi_key\s*=\s*"([^"]+)"', main_py)
    security_key = re.search(r'amap_security_key\s*=\s*"([^"]+)"', main_py)
    
    print("\n配置信息:")
    if web_key:
        print(f"  Web服务 Key: {web_key.group(1)[:10]}...")
    if jsapi_key:
        print(f"  JS API Key:  {jsapi_key.group(1)[:10]}...")
    if security_key:
        print(f"  安全密钥:    {security_key.group(1)[:10]}...")
    
    print("\n检查建议:")
    print("  1. 确保 JS API Key 已启用 'JS API' 服务")
    print("  2. 确保 Web服务 Key 已启用 'Web服务 API' 服务")
    print("  3. 安全密钥已在 JS API Key 的安全配置中添加")
    print("  4. 白名单设置: 如果限制域名，需要添加 'file://' 或 '*'")
    print()

def generate_test_page():
    """生成测试页面"""
    
    # 从 main.py 读取配置
    main_py = open('main.py').read()
    import re
    jsapi_key = re.search(r'amap_jsapi_key\s*=\s*"([^"]+)"', main_py)
    security_key = re.search(r'amap_security_key\s*=\s*"([^"]+)"', main_py)
    
    if not jsapi_key or not security_key:
        print("错误: 无法读取密钥配置")
        return
    
    jsapi = jsapi_key.group(1)
    security = security_key.group(1)
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>高德地图密钥测试</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        #container {{ width: 100%; height: 400px; border: 1px solid #ccc; }}
        .info {{ margin: 10px 0; padding: 10px; background: #f0f0f0; }}
        .success {{ color: green; }}
        .error {{ color: red; }}
    </style>
</head>
<body>
    <h1>高德地图密钥测试</h1>
    
    <div class="info">
        <p><strong>JS API Key:</strong> {jsapi[:15]}...</p>
        <p><strong>安全密钥:</strong> {security[:15]}...</p>
    </div>
    
    <div id="status">正在加载地图...</div>
    <div id="container"></div>
    
    <script>
        window._AMapSecurityConfig = {{
            securityJsCode: '{security}'
        }};
    </script>
    <script src="https://webapi.amap.com/maps?v=2.0&key={jsapi}&plugin=AMap.Driving,AMap.Scale"></script>
    <script>
        function testMap() {{
            var statusDiv = document.getElementById('status');
            
            // 检查 AMap 是否加载
            if (typeof AMap === 'undefined') {{
                statusDiv.innerHTML = '<p class="error">❌ AMap 未加载！</p>' +
                    '<p>可能原因：</p>' +
                    '<ul>' +
                    '<li>JS API Key 错误</li>' +
                    '<li>安全密钥错误</li>' +
                    '<li>Key 未启用 JS API 服务</li>' +
                    '<li>白名单限制（当前域名不在白名单中）</li>' +
                    '</ul>';
                return;
            }}
            
            statusDiv.innerHTML = '<p class="success">✅ AMap 加载成功！</p>';
            
            try {{
                var map = new AMap.Map('container', {{
                    zoom: 14,
                    center: [116.407428, 39.904207]  // 北京天安门
                }});
                
                map.addControl(new AMap.Scale({{position: 'LB'}}));
                
                statusDiv.innerHTML += '<p class="success">✅ 地图初始化成功！</p>' +
                    '<p>如果看到上面的地图，说明密钥配置正确。</p>';
                    
            }} catch (e) {{
                statusDiv.innerHTML += '<p class="error">❌ 地图初始化失败: ' + e.message + '</p>';
            }}
        }}
        
        // 等待 2 秒后测试
        setTimeout(testMap, 2000);
    </script>
</body>
</html>'''
    
    test_file = '/tmp/amap_key_test.html'
    with open(test_file, 'w') as f:
        f.write(html)
    
    print(f"测试页面已生成: {test_file}")
    print()
    print("请在有图形界面的浏览器中打开此文件测试")
    print("如果地图能正常显示，说明密钥配置正确")
    print()
    print("命令行测试方法:")
    print(f"  firefox {test_file}")
    print(f"  chromium {test_file}")
    print()

if __name__ == "__main__":
    check_keys()
    generate_test_page()
