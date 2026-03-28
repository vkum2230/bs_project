# 地图 API 更新说明

## 架构变更

之前使用前端 JavaScript API (AutoComplete, PlaceSearch, Geocoder)
现在改为使用 Python 后端调用 WebService API

```
┌─────────────────────────────────────────┐
│  JavaScript 前端                        │
│  - QWebChannel 调用后端                 │
│  - 显示地图和 UI                         │
└──────────────┬──────────────────────────┘
               │ QWebChannel
┌──────────────▼──────────────────────────┐
│  Python 后端 (AMapAPIHandler)           │
│  - geocode_regeo()  逆地理编码          │
│  - input_tips()     输入提示            │
│  - place_search()   地点搜索            │
└──────────────┬──────────────────────────┘
               │ HTTP Request
┌──────────────▼──────────────────────────┐
│  高德地图 WebService API                │
│  - /v3/geocode/regeo                    │
│  - /v3/assistant/inputtips              │
│  - /v3/place/text                       │
└─────────────────────────────────────────┘
```

## 新增后端类

### AMapAPIHandler(QObject)

提供三个方法供 JavaScript 调用：

1. **geocode_regeo(location)**
   - 参数: location ("lng,lat" 格式)
   - 返回: JSON 字符串
   - 功能: 根据经纬度获取地址

2. **input_tips(keywords, city)**
   - 参数: keywords (关键词), city (城市)
   - 返回: JSON 字符串
   - 功能: 输入提示，返回匹配的地点列表

3. **place_search(keywords, city)**
   - 参数: keywords (关键词), city (城市)
   - 返回: JSON 字符串
   - 功能: 地点搜索

## QWebChannel 连接

```javascript
// JavaScript 端
var amapAPI = null;
document.addEventListener("DOMContentLoaded", function() {
    new QWebChannel(qt.webChannelTransport, function(channel) {
        amapAPI = channel.objects.amapAPI;
    });
});

// 调用后端方法
amapAPI.geocode_regeo("116.397,39.909", function(result) {
    var data = JSON.parse(result);
    console.log(data.regeocode.formatted_address);
});
```

## 使用方式

### 1. 点击地图获取地址
1. 点击地图任意位置
2. JavaScript 获取经纬度
3. 调用 `amapAPI.geocode_regeo()`
4. Python 后端请求高德 API
5. 返回地址信息显示在界面上

### 2. 输入提示
1. 在搜索框输入关键词
2. 调用 `amapAPI.input_tips()`
3. 显示匹配的地点列表
4. 点击选择后标注到地图

### 3. 开始导航
1. 设置目的地（点击地图或搜索）
2. 调用 `amapAPI.place_search()` 获取精确坐标
3. 规划路线并开始导航

## 调试方法

查看控制台输出：
- `[AMapAPI] 逆地理编码请求: 116.397,39.909`
- `[AMapAPI] 逆地理编码响应: {...}`
- `[AMapAPI] 输入提示请求: 天安门`

## 测试步骤

```bash
cd qt_project
python3 main.py
```

1. 打开程序后，等待地图加载
2. 查看控制台是否有 `QWebChannel 已连接` 日志
3. 点击地图任意位置，查看是否显示地址
4. 打开键盘，输入关键词，查看是否有候选列表

## 常见问题

1. **QWebChannel 未连接**
   - 检查是否正确加载 `qwebchannel.js`
   - 检查是否正确注册 `amapAPI` 对象

2. **API 返回错误**
   - 检查 `amap_key` 是否有效
   - 检查网络连接
   - 查看控制台错误信息

3. **中文乱码**
   - WebService API 返回 UTF-8 编码
   - Python 后端正确解码
   - JavaScript 正确解析 JSON
