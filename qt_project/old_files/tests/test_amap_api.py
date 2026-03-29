#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试高德地图 WebService API
"""

import urllib.request
import urllib.parse
import json

# 你的高德地图 Key
AMAP_KEY = "bc9998864f9d289e0913acb4c0554c2e"

def test_geocode_regeo():
    """测试逆地理编码"""
    print("=" * 60)
    print("测试逆地理编码")
    print("=" * 60)
    
    # 天安门坐标
    location = "116.397428,39.90923"
    
    url = "https://restapi.amap.com/v3/geocode/regeo"
    params = {
        'key': AMAP_KEY,
        'location': location,
        'extensions': 'all',
        'output': 'json'
    }
    
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    print(f"请求 URL: {full_url}")
    
    try:
        with urllib.request.urlopen(full_url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"\n状态: {data.get('status')}")
            print(f"信息: {data.get('info')}")
            
            if data.get('status') == '1' and data.get('regeocode'):
                regeo = data['regeocode']
                print(f"\n格式化地址: {regeo.get('formatted_address')}")
                
                comp = regeo.get('addressComponent', {})
                print(f"省份: {comp.get('province')}")
                print(f"城市: {comp.get('city')}")
                print(f"区县: {comp.get('district')}")
                print(f"街道: {comp.get('street')}")
                print(f"门牌号: {comp.get('streetNumber')}")
                return True
            else:
                print(f"请求失败: {data}")
                return False
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_input_tips():
    """测试输入提示"""
    print("\n" + "=" * 60)
    print("测试输入提示")
    print("=" * 60)
    
    keywords = "天安门"
    
    url = "https://restapi.amap.com/v3/assistant/inputtips"
    params = {
        'key': AMAP_KEY,
        'keywords': keywords,
        'city': '北京',
        'datatype': 'all',
        'output': 'json'
    }
    
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    print(f"请求 URL: {full_url}")
    
    try:
        with urllib.request.urlopen(full_url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"\n状态: {data.get('status')}")
            print(f"信息: {data.get('info')}")
            
            if data.get('status') == '1' and data.get('tips'):
                tips = data['tips']
                print(f"\n找到 {len(tips)} 个结果:")
                for i, tip in enumerate(tips[:5], 1):
                    print(f"{i}. {tip.get('name')} - {tip.get('district', '')}")
                return True
            else:
                print(f"请求失败: {data}")
                return False
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_place_search():
    """测试地点搜索"""
    print("\n" + "=" * 60)
    print("测试地点搜索")
    print("=" * 60)
    
    keywords = "故宫博物院"
    
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        'key': AMAP_KEY,
        'keywords': keywords,
        'city': '北京',
        'extensions': 'all',
        'offset': 5,
        'page': 1,
        'output': 'json'
    }
    
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    print(f"请求 URL: {full_url}")
    
    try:
        with urllib.request.urlopen(full_url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"\n状态: {data.get('status')}")
            print(f"信息: {data.get('info')}")
            
            if data.get('status') == '1' and data.get('pois'):
                pois = data['pois']
                print(f"\n找到 {len(pois)} 个结果:")
                for i, poi in enumerate(pois[:3], 1):
                    print(f"{i}. {poi.get('name')}")
                    print(f"   地址: {poi.get('address')}")
                    print(f"   坐标: {poi.get('location')}")
                return True
            else:
                print(f"请求失败: {data}")
                return False
    except Exception as e:
        print(f"错误: {e}")
        return False

if __name__ == "__main__":
    print("高德地图 WebService API 测试")
    print(f"使用 Key: {AMAP_KEY}")
    
    results = []
    results.append(("逆地理编码", test_geocode_regeo()))
    results.append(("输入提示", test_input_tips()))
    results.append(("地点搜索", test_place_search()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    if all(r for _, r in results):
        print("\n✓ 所有测试通过，可以运行主程序")
    else:
        print("\n✗ 部分测试失败，请检查 Key 和网络")
