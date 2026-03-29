#!/usr/bin/env python3
"""诊断拼音输入法问题"""
import sys
sys.path.insert(0, '/home/hedya/Desktop/bs_project')

def check_python_code():
    """检查Python代码"""
    print("=" * 60)
    print("1. 检查 Python 代码")
    print("=" * 60)
    
    from qt_project.map_widget import PinyinHandler
    from qt_project.smart_pinyin_ime import get_ime
    
    ph = PinyinHandler()
    
    # Test get_candidates
    result = ph.get_candidates('zhong', page=0)
    print(f"✓ PinyinHandler.get_candidates('zhong', 0):")
    print(f"  candidates: {result['candidates']}")
    print(f"  count: {len(result['candidates'])}")
    print(f"  has_more: {result['has_more']}")
    print(f"  page: {result['page']}")
    
    if len(result['candidates']) == 5:
        print("✓ Python端返回正确（5个字符）")
    else:
        print(f"✗ Python端返回错误（{len(result['candidates'])}个字符，应为5个）")
    
    return True

def check_html_generation():
    """检查HTML生成"""
    print()
    print("=" * 60)
    print("2. 检查 HTML/JavaScript 生成")
    print("=" * 60)
    
    from qt_project.map_widget import MapWidget
    from unittest.mock import MagicMock
    
    mock = MagicMock()
    mock.amap_key = 'test_key'
    html = MapWidget.generate_amap_html(mock)
    
    # Check showCandidates function
    start = html.find('function showCandidates')
    end = html.find('function selectCandidate', start)
    js_func = html[start:end]
    
    checks = [
        ('Array.isArray(result)', '处理数组格式'),
        ('result.candidates', '处理对象格式'),
        ('result.has_more', '读取has_more'),
        ('result.page', '读取page'),
        ('currentPage > 0', '检查上一页条件'),
        ('textContent = \'<<\'', '<<按钮'),
        ('textContent = \'>>\'', '>>按钮'),
        ('candidates.forEach', '遍历候选词'),
        ('if (hasMore)', '检查下一页条件'),
    ]
    
    all_ok = True
    for pattern, desc in checks:
        found = pattern in js_func
        status = '✓' if found else '✗'
        print(f"{status} {desc}: {'有' if found else '无'}")
        if not found:
            all_ok = False
    
    # Check for old problematic code
    if 'candidates.slice(0, 8)' in js_func:
        print("✗ 发现旧代码：candidates.slice(0, 8)")
        all_ok = False
    else:
        print("✓ 没有发现旧的slice(0, 8)代码")
    
    # Check else branch
    if 'showCandidates({' in html:
        print("✓ 备用词典调用showCandidates对象格式")
    else:
        print("✗ 备用词典没有正确调用showCandidates")
        all_ok = False
    
    return all_ok

def save_html_for_inspection():
    """保存HTML文件供检查"""
    print()
    print("=" * 60)
    print("3. 保存 HTML 文件供手动检查")
    print("=" * 60)
    
    from qt_project.map_widget import MapWidget
    from unittest.mock import MagicMock
    
    mock = MagicMock()
    mock.amap_key = 'test_key'
    html = MapWidget.generate_amap_html(mock)
    
    output_file = '/tmp/map_widget_debug.html'
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"✓ HTML已保存到: {output_file}")
    print(f"  文件大小: {len(html)} 字节")
    
    # Extract showCandidates function to separate file
    start = html.find('function showCandidates')
    end = html.find('function selectCandidate', start)
    js_func = html[start:end]
    
    js_file = '/tmp/showCandidates.js'
    with open(js_file, 'w') as f:
        f.write(js_func)
    
    print(f"✓ showCandidates函数已保存到: {js_file}")

def main():
    print("拼音输入法诊断工具")
    print("=" * 60)
    
    try:
        check_python_code()
        js_ok = check_html_generation()
        save_html_for_inspection()
        
        print()
        print("=" * 60)
        print("诊断结论")
        print("=" * 60)
        
        if js_ok:
            print("✓ 代码检查通过")
            print()
            print("如果问题仍然存在，可能原因：")
            print("1. 浏览器/QT WebEngine 缓存了旧代码")
            print("   - 尝试清除缓存或重启应用")
            print("2. 运行的是旧版本的Python模块")
            print("   - 尝试删除 __pycache__ 目录")
            print("3. 有其他JavaScript错误阻止了代码执行")
            print("   - 检查浏览器/QT控制台错误信息")
        else:
            print("✗ 代码检查发现问题，请查看上方输出")
            
    except Exception as e:
        print(f"✗ 诊断出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
