#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据上下文功能
"""

import sys
sys.path.insert(0, '/home/hedya/Desktop/bs_project/qt_project')

from core.data_context import get_data_context, RideData


def test_basic():
    """基础功能测试"""
    print("=" * 50)
    print("数据上下文管理器测试")
    print("=" * 50)
    
    # 获取实例
    ctx = get_data_context()
    
    # 初始状态
    print("\n1. 初始状态:")
    print(ctx.get_context_string())
    
    # 更新数据
    print("\n2. 更新骑行数据...")
    ctx.update_data(
        speed=28.5,
        power=200,
        cadence=90,
        distance=15.6,
        ride_time=1800,  # 30分钟
        slope=3.2,
        temperature=26.5,
        heart_rate=155,
        rear_dist=8.5,
        location="浙江省杭州市"
    )
    
    print("\n3. 更新后状态:")
    print(ctx.get_context_string())
    
    print("\n4. 系统提示词:")
    print("-" * 50)
    print(ctx.get_system_prompt_with_context())
    print("-" * 50)
    
    # 部分数据更新
    print("\n5. 部分更新（只更新速度）:")
    ctx.update_data(speed=32.0)
    print(ctx.get_context_string())
    
    # 获取数据副本
    print("\n6. 获取数据字典:")
    data = ctx.get_data()
    print(data.to_dict())
    
    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)


def test_with_questions():
    """模拟用户提问场景"""
    print("\n\n" + "=" * 50)
    print("模拟用户提问场景")
    print("=" * 50)
    
    ctx = get_data_context()
    
    # 设置一些骑行数据
    ctx.update_data(
        speed=25.0,
        power=180,
        cadence=85,
        distance=42.5,
        ride_time=5400,  # 1.5小时
        heart_rate=165,
        location="江苏省南京市"
    )
    
    context = ctx.get_context_string()
    
    questions = [
        "我现在骑得多快？",
        "我的心率正常吗？",
        "我已经骑了多久了？",
        "我现在在哪里？",
        "我的功率是多少？",
    ]
    
    print("\n当前数据上下文:")
    print(context)
    print()
    
    for q in questions:
        print(f"问: {q}")
        print(f"系统提示词包含数据: {context[:60]}...")
        print()


if __name__ == "__main__":
    test_basic()
    test_with_questions()
