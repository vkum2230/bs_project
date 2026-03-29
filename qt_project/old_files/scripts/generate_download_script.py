#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成批量下载脚本
帮助你快速创建下载命令
"""

import os
import sys

# 热门骑行城市/区域坐标（西南角, 东北角）
HOT_AREAS = {
    "深圳市区": "113.9,22.5,114.3,22.8",
    "广州市区": "113.2,23.0,113.5,23.2",
    "北京市区": "116.2,39.8,116.6,40.0",
    "上海市区": "121.4,31.1,121.6,31.3",
    "杭州市区": "120.1,30.2,120.3,30.4",
    "成都市区": "104.0,30.6,104.2,30.8",
    "西安市区": "108.9,34.2,109.0,34.3",
    "武汉市区": "114.2,30.5,114.4,30.6",
    "南京市区": "118.7,32.0,118.8,32.1",
    "重庆市区": "106.5,29.5,106.6,29.6",
}

PROVINCES = [
    "北京市", "天津市", "河北省", "山西省", "内蒙古自治区",
    "辽宁省", "吉林省", "黑龙江省", "上海市", "江苏省",
    "浙江省", "安徽省", "福建省", "江西省", "山东省",
    "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区",
    "海南省", "重庆市", "四川省", "贵州省", "云南省",
    "西藏自治区", "陕西省", "甘肃省", "青海省", "宁夏回族自治区",
    "新疆维吾尔自治区", "台湾省", "香港特别行政区", "澳门特别行政区"
]


def print_menu():
    print("=" * 60)
    print("离线地图下载脚本生成器")
    print("=" * 60)
    print()
    print("请选择下载方式:")
    print()
    print("1. 按热门城市下载（推荐，省空间）")
    print("2. 按省份下载（完整，占空间）")
    print("3. 自定义边界框下载")
    print("4. 生成多个城市的批量脚本")
    print()
    print("0. 退出")
    print()


def download_by_city():
    print("\n热门骑行城市列表:")
    print("-" * 40)
    for i, (name, bbox) in enumerate(HOT_AREAS.items(), 1):
        print(f"{i:2d}. {name}")
    print()
    
    choice = input("请输入城市编号（多个用逗号分隔，如 1,3,5）: ").strip()
    zoom = input("请输入 Zoom 层级（默认 14-16）: ").strip() or "14-16"
    
    try:
        indices = [int(x.strip()) for x in choice.split(",")]
        cities = list(HOT_AREAS.items())
        
        print("\n" + "=" * 60)
        print("生成的下载命令:")
        print("=" * 60)
        
        for idx in indices:
            if 1 <= idx <= len(cities):
                name, bbox = cities[idx - 1]
                cmd = f'python3 offline_map_downloader.py --bbox {bbox} --zoom {zoom}'
                print(f"\n# {name}")
                print(cmd)
        
        print("\n" + "=" * 60)
        print("复制以上命令在电脑上运行")
        print("=" * 60)
        
    except ValueError:
        print("输入错误，请使用数字编号")


def download_by_province():
    print("\n省份列表:")
    print("-" * 40)
    for i, province in enumerate(PROVINCES, 1):
        print(f"{i:2d}. {province}")
    print()
    
    choice = input("请输入省份编号（多个用逗号分隔）: ").strip()
    zoom = input("请输入 Zoom 层级（默认 13-15，省级不需要太细）: ").strip() or "13-15"
    
    try:
        indices = [int(x.strip()) for x in choice.split(",")]
        
        print("\n" + "=" * 60)
        print("生成的下载命令:")
        print("=" * 60)
        
        for idx in indices:
            if 1 <= idx <= len(PROVINCES):
                province = PROVINCES[idx - 1]
                cmd = f'python3 offline_map_downloader.py --province "{province}" --zoom {zoom}'
                print(f"\n# {province}")
                print(cmd)
        
        print("\n" + "=" * 60)
        print("注意：省份下载较大，确保有足够存储空间")
        print("=" * 60)
        
    except ValueError:
        print("输入错误，请使用数字编号")


def download_by_bbox():
    print("\n自定义边界框下载")
    print("-" * 40)
    print("提示：在 https://bboxfinder.com 上框选区域获取坐标")
    print("格式：min_lon,min_lat,max_lon,max_lat")
    print()
    
    bbox = input("请输入边界框坐标: ").strip()
    zoom = input("请输入 Zoom 层级（默认 14-16）: ").strip() or "14-16"
    name = input("给这个区域起个名字（用于标识）: ").strip() or "custom_area"
    
    print("\n" + "=" * 60)
    print("生成的下载命令:")
    print("=" * 60)
    print(f"\n# {name}")
    print(f'python3 offline_map_downloader.py --bbox {bbox} --zoom {zoom}')
    print("\n" + "=" * 60)


def generate_batch_script():
    print("\n生成批量下载脚本")
    print("-" * 40)
    
    script_name = input("脚本文件名（默认 download_maps.sh）: ").strip() or "download_maps.sh"
    
    print("\n选择要包含的城市/区域:")
    print("-" * 40)
    
    cities = list(HOT_AREAS.items())
    selected = []
    
    for i, (name, bbox) in enumerate(cities, 1):
        choice = input(f"包含 {name}? (y/n): ").strip().lower()
        if choice == 'y':
            selected.append((name, bbox))
    
    if not selected:
        print("没有选择任何城市")
        return
    
    zoom = input("请输入 Zoom 层级（默认 14-16）: ").strip() or "14-16"
    
    # 生成脚本
    with open(script_name, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("# 自动生成的离线地图下载脚本\n\n")
        f.write("set -e\n\n")
        
        f.write(f'OUTPUT_DIR="${{1:-offline_maps}}"\n')
        f.write(f'ZOOM="{zoom}"\n\n')
        
        f.write('echo "开始下载离线地图..."\n')
        f.write('echo "输出目录: $OUTPUT_DIR"\n')
        f.write('echo "Zoom 层级: $ZOOM"\n\n')
        
        for name, bbox in selected:
            safe_name = name.replace(" ", "_")
            f.write(f'\necho "\\n===== 下载 {name} ====="\n')
            f.write(f'python3 offline_map_downloader.py \\\n')
            f.write(f'    --bbox {bbox} \\\n')
            f.write(f'    --zoom $ZOOM \\\n')
            f.write(f'    --output "$OUTPUT_DIR" \\\n')
            f.write(f'    --delay 0.1 \\\n')
            f.write(f'    --workers 6\n')
        
        f.write('\necho "\\n===== 生成索引 ====="\n')
        f.write('python3 offline_map_downloader.py --index --output "$OUTPUT_DIR"\n')
        f.write('\necho "\\n下载完成！"\n')
    
    os.chmod(script_name, 0o755)
    
    print("\n" + "=" * 60)
    print(f"脚本已生成: {script_name}")
    print("=" * 60)
    print(f"\n使用方法:")
    print(f"  1. 在电脑上有外网访问权限的终端运行:")
    print(f"     ./{script_name}")
    print(f"\n  2. 或指定输出目录:")
    print(f"     ./{script_name} /path/to/output")
    print(f"\n  3. 等待下载完成后，打包传输到树莓派:")
    print(f"     tar -czvf offline_maps.tar.gz offline_maps/")
    print("=" * 60)


def main():
    while True:
        print_menu()
        choice = input("请输入选项: ").strip()
        
        if choice == "1":
            download_by_city()
        elif choice == "2":
            download_by_province()
        elif choice == "3":
            download_by_bbox()
        elif choice == "4":
            generate_batch_script()
        elif choice == "0":
            print("再见！")
            break
        else:
            print("无效选项")
        
        input("\n按 Enter 继续...")
        print()


if __name__ == "__main__":
    main()
