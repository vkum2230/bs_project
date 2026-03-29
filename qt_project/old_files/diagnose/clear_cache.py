#!/usr/bin/env python3
"""清除缓存脚本"""
import os
import shutil
import glob

def clear_python_cache():
    """清除Python缓存"""
    print("清除 Python 缓存...")
    cache_dirs = glob.glob('qt_project/__pycache__')
    for d in cache_dirs:
        shutil.rmtree(d)
        print(f"  已删除: {d}")
    
    # Also remove .pyc files
    pyc_files = glob.glob('qt_project/**/*.pyc', recursive=True)
    for f in pyc_files:
        os.remove(f)
        print(f"  已删除: {f}")
    
    print("✓ Python缓存已清除")

def clear_qt_webengine_cache():
    """提示用户清除QT WebEngine缓存"""
    print()
    print("QT WebEngine 缓存位置：")
    
    # Common Qt WebEngine cache locations
    home = os.path.expanduser('~')
    cache_paths = [
        f"{home}/.cache/QtWebEngine",
        f"{home}/.local/share/QtWebEngine",
        "/tmp/.QtWebEngine",
    ]
    
    for path in cache_paths:
        if os.path.exists(path):
            print(f"  找到: {path}")
            response = input(f"  是否删除? (y/n): ")
            if response.lower() == 'y':
                shutil.rmtree(path)
                print(f"    已删除")

def main():
    print("=" * 60)
    print("清除缓存工具")
    print("=" * 60)
    
    clear_python_cache()
    
    print()
    print("=" * 60)
    print("其他需要手动清除的缓存：")
    print("=" * 60)
    print()
    print("1. Python缓存已自动清除")
    print()
    print("2. 如果应用正在运行，请完全关闭后重新启动")
    print()
    print("3. 如果问题仍然存在，在启动应用时设置环境变量：")
    print("   export QTWEBENGINE_REMOTE_DEBUGGING=9222")
    print("   然后使用Chrome访问 chrome://inspect 查看调试信息")
    print()
    print("4. 临时禁用缓存（测试用）：")
    print("   在 map_widget.py 的 init_ui() 方法中添加：")
    print("   settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, False)")
    print()

if __name__ == "__main__":
    main()
