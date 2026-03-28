# 高德地图 Key 更新说明

## Key 配置

现在使用两个不同的 Key：

| Key 类型 | 值 | 用途 |
|---------|-----|------|
| Web 端 Key | `bc9998864f9d289e0913acb4c0554c2e` | 前端地图显示（JS API） |
| WebService Key | `8b657a470f4b69e82bf81f72b3a2b3c0` | 后端 API 调用（逆地理编码、输入提示） |

## 代码结构

```
main.py
├── amap_key_web     = Web 端 Key（地图显示）
└── amap_key_service = WebService Key（后端 API）

map_widget.py
├── amap_key_web      → 前端 HTML 地图
└── amap_key_service  → AMapAPIHandler 后端
```

## API 功能测试

使用新的 WebService Key 测试：

✓ 逆地理编码 - 根据经纬度获取地址
✓ 输入提示 - 根据关键词获取地点建议
✓ 地点搜索 - 搜索具体地点

## 使用方式

### 1. 点击地图获取地址
```
1. 点击地图任意位置
2. 后端调用逆地理编码 API
3. 显示地址信息
```

### 2. 输入提示
```
1. 打开键盘输入关键词
2. 后端调用输入提示 API
3. 显示候选地点列表
4. 点击选择标注到地图
```

### 3. 开始导航
```
1. 设置目的地（点击地图或搜索）
2. 点击导航按钮
3. 后端搜索精确坐标
4. 规划路线
```

## 运行测试

```bash
cd qt_project
python3 main.py
```

现在输入提示和地理逆编码功能应该可以正常工作了！
