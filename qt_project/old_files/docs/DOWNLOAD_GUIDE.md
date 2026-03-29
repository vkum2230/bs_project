# 离线地图下载指南

由于网络限制，建议在能访问外网的电脑上下载瓦片，再传输到树莓派使用。

## 📋 步骤一：在电脑上下载

### 1. 准备环境
```bash
# 确保你的电脑能访问外网（国内网络通常可以）
ping tile.openstreetmap.org

# 克隆项目（或复制下载工具）
git clone <你的项目仓库>
cd qt_project

# 安装依赖（如果还没有）
pip install requests pillow shapely
```

### 2. 下载瓦片

#### 方式 A：按省份下载（推荐）
```bash
# 下载整个省份的地图（适合经常在该省骑行）
python3 offline_map_downloader.py --province 广东省 --zoom 14-16

# 查看所有可用省份
python3 offline_map_downloader.py --list-provinces
```

#### 方式 B：按城市/区域下载（省空间）
```bash
# 下载特定区域（经纬度边界框）
python3 offline_map_downloader.py --bbox 113.2,22.5,114.5,23.5 --zoom 14-16

# bbox 格式：min_lon,min_lat,max_lon,max_lat
# 可通过 https://bboxfinder.com 获取
```

#### 方式 C：下载常用骑行路线周边
```bash
# 下载路线沿途的区域（需要知道起止点坐标）
python3 offline_map_downloader.py --bbox 113.9,22.5,114.1,22.7 --zoom 14-16
```

### 3. Zoom 层级说明

| 层级 | 用途 | 文件大小估算 |
|------|------|-------------|
| 12 | 城市概览 | ~10MB/城市 |
| 14 | 区域导航 | ~100MB/城市 |
| 15 | 街道级 | ~400MB/城市 |
| 16 | 详细骑行 | ~1.5GB/城市 |

**推荐**：`14-16` 层级，兼顾导航精度和存储空间。

---

## 📦 步骤二：打包传输

### 1. 打包
```bash
cd qt_project

# 打包离线地图目录
tar -czvf offline_maps.tar.gz offline_maps/

# 查看大小
ls -lh offline_maps.tar.gz
```

### 2. 传输到树莓派

#### 方式 A：使用 scp（推荐）
```bash
# 通过 SSH 传输
scp offline_maps.tar.gz pi@raspberrypi.local:/home/pi/

# 如果不知道 IP，可以用路由器后台查看
# 或用 nmap 扫描局域网
nmap -sn 192.168.1.0/24
```

#### 方式 B：使用 U 盘
```bash
# 复制到 U 盘
cp offline_maps.tar.gz /media/your_usb/

# 在树莓派上挂载 U 盘后复制
sudo mount /dev/sda1 /mnt
cp /mnt/offline_maps.tar.gz /home/pi/qt_project/
```

#### 方式 C：使用网盘/云存储
- 上传到百度网盘/阿里云盘
- 在树莓派上下载

---

## 🎯 步骤三：在树莓派上解压使用

### 1. 解压
```bash
ssh pi@raspberrypi.local
cd /home/pi/qt_project

# 解压
tar -xzvf offline_maps.tar.gz

# 验证
ls -la offline_maps/
find offline_maps -name "*.png" | wc -l
```

### 2. 运行主程序
```bash
cd /home/pi/qt_project
python3 main.py
```

---

## 📊 存储空间估算

### 按区域大小
| 区域类型 | Zoom 14-16 | 预估大小 |
|---------|-----------|---------|
| 单个城市（如深圳） | 14-16 | ~500MB |
| 单个省份（如广东） | 14-16 | ~5-10GB |
| 骑行路线（100km） | 14-16 | ~200MB |

### 树莓派存储建议
- **SD 卡 32GB**：可存 2-3 个省份
- **SD 卡 64GB**：可存 5-6 个省份
- **外接 USB 硬盘**：无限制

---

## 🔧 常见问题

### Q1: 下载太慢怎么办？
```bash
# 增加并发数（默认4）
python3 offline_map_downloader.py --province 广东省 --zoom 14-16 --workers 8

# 减少延迟（默认0.2秒）
python3 offline_map_downloader.py --province 广东省 --zoom 14-16 --delay 0.05
```

### Q2: 如何只下载特定路线？
```bash
# 使用较小的边界框
# 在 https://bboxfinder.com 上框选你的骑行路线
# 复制左下和右上角的坐标作为 bbox 参数
```

### Q3: 瓦片下载失败怎么办？
```bash
# 会自动重试3次，失败记录在 failed_tiles.json
# 稍后重新运行下载命令，已下载的会跳过
python3 offline_map_downloader.py --province 广东省 --zoom 14-16
```

### Q4: 如何更新瓦片？
```bash
# OpenStreetMap 瓦片不定期更新
# 删除旧瓦片重新下载
rm -rf offline_maps/<省份hash>/
python3 offline_map_downloader.py --province 广东省 --zoom 14-16
```

---

## 🗺️ 获取边界框的方法

### 方法 1：bboxfinder.com（推荐）
1. 打开 https://bboxfinder.com
2. 在地图上框选区域
3. 复制 "Box" 后的坐标
4. 格式：`min_lon,min_lat,max_lon,max_lat`

### 方法 2：Leaflet 地图点击获取
在骑行码表地图页面上，可以添加点击获取坐标功能（需要修改代码）。

### 方法 3：根据已知坐标估算
```python
# 深圳大概范围
min_lon, min_lat = 113.7, 22.4  # 西南角
max_lon, max_lat = 114.6, 22.9  # 东北角
```

---

## ✅ 验证下载成功

在树莓派上运行：
```bash
cd /home/pi/qt_project

# 生成索引
python3 offline_map_downloader.py --index

# 查看索引
cat offline_maps/index.json

# 检查瓦片数量
find offline_maps -name "*.png" | wc -l
```

---

## 📞 需要帮助？

如果下载或传输过程中遇到问题，请检查：
1. 电脑能否访问 `https://tile.openstreetmap.org`
2. 树莓派和电脑是否在同一个网络
3. 树莓派 SD 卡剩余空间是否足够
