#!/usr/bin/env python3
"""测试智能拼音输入法"""
import sys
sys.path.insert(0, '/home/hedya/Desktop/bs_project')

from qt_project.map_widget import PinyinHandler

def test_pinyin_ime():
    print("=" * 50)
    print("智能拼音输入法测试")
    print("=" * 50)
    
    handler = PinyinHandler()
    
    test_cases = [
        ("zhong", "中文字"),
        ("zhongg", "中国 (前缀匹配)"),
        ("beijing", "北京 (词组)"),
        ("tian", "天/天津/天安门"),
        ("tiananmen", "天安门 (词组)"),
        ("a", "啊/阿/安/岸/按/案/暗"),
        ("shanghai", "上海 (词组)"),
        ("xxx", "无匹配"),
    ]
    
    print("\n测试基本查询（第1页）:")
    print("-" * 50)
    for pinyin, desc in test_cases:
        result = handler.get_candidates(pinyin, page=0)
        candidates = result.get('candidates', [])
        has_more = result.get('has_more', False)
        total = result.get('total', 0)
        
        more_str = ">>" if has_more else ""
        print(f"{pinyin:12} ({desc}):")
        print(f"  候选: {candidates} {more_str}")
        print(f"  总计: {total}个")
        
        # 如果有更多，测试第2页
        if has_more:
            result2 = handler.get_candidates(pinyin, page=1)
            candidates2 = result2.get('candidates', [])
            print(f"  第2页: {candidates2}")
        print()
    
    print("=" * 50)
    print("测试完成!")

if __name__ == "__main__":
    test_pinyin_ime()
