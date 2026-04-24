#!/bin/bash
# 清理项目缓存和临时文件

set -e

PROJECT_DIR="/home/hedya/Desktop/bs_project/qt_project"
DRY_RUN=0
CLEAN_LOGS=0
CLEAN_BUILD_CACHE=0

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -n, --dry-run       预览模式，不实际删除"
    echo "  -l, --logs          同时清理日志文件"
    echo "  -b, --build-cache   同时清理构建缓存 (autom4te, config.log)"
    echo "  -a, --all           清理所有（含日志和构建缓存）"
    echo "  -h, --help          显示帮助"
    echo ""
    echo "默认只清理 Python __pycache__ 和 .pyc 文件。"
    exit 0
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--dry-run) DRY_RUN=1 ; shift ;;
        -l|--logs) CLEAN_LOGS=1 ; shift ;;
        -b|--build-cache) CLEAN_BUILD_CACHE=1 ; shift ;;
        -a|--all) CLEAN_LOGS=1; CLEAN_BUILD_CACHE=1 ; shift ;;
        -h|--help) usage ;;
        *) echo "未知选项: $1"; usage ;;
    esac
done

cd "$PROJECT_DIR"

TOTAL_SIZE=0
deleted_count=0

# 记录要删除的文件/目录
declare -a to_delete=()

# 1. Python __pycache__
while IFS= read -r -d '' dir; do
    to_delete+=("$dir")
done < <(find . -type d -name "__pycache__" -print0 2>/dev/null)

# 2. .pyc 文件
while IFS= read -r -d '' file; do
    to_delete+=("$file")
done < <(find . -type f -name "*.pyc" -print0 2>/dev/null)

# 3. .pyo 文件
while IFS= read -r -d '' file; do
    to_delete+=("$file")
done < <(find . -type f -name "*.pyo" -print0 2>/dev/null)

# 4. 日志文件
if [[ $CLEAN_LOGS -eq 1 ]]; then
    while IFS= read -r -d '' file; do
        to_delete+=("$file")
    done < <(find . -type f \( -name "*.log" -o -name "nohup.out" \) -print0 2>/dev/null)
fi

# 5. 构建缓存
if [[ $CLEAN_BUILD_CACHE -eq 1 ]]; then
    while IFS= read -r -d '' dir; do
        to_delete+=("$dir")
    done < <(find . -type d -name "autom4te.cache" -print0 2>/dev/null)

    while IFS= read -r -d '' file; do
        to_delete+=("$file")
    done < <(find . -type f -name "config.log" -print0 2>/dev/null)
fi

# 6. 其他常见缓存
while IFS= read -r -d '' dir; do
    to_delete+=("$dir")
done < <(find . -type d \( -name ".mypy_cache" -o -name ".pytest_cache" -o -name ".ruff_cache" \) -print0 2>/dev/null)

# 计算总大小
for item in "${to_delete[@]}"; do
    if [[ -e "$item" ]]; then
        size=$(du -sb "$item" 2>/dev/null | cut -f1)
        TOTAL_SIZE=$((TOTAL_SIZE + size))
    fi
done

size_human=$(du -sh /dev/null 2>/dev/null | sed 's|/dev/null||' || true)
if command -v numfmt >/dev/null 2>&1; then
    size_human=$(numfmt --to=iec-i --suffix=B "$TOTAL_SIZE" 2>/dev/null || echo "${TOTAL_SIZE}B")
else
    size_human="${TOTAL_SIZE} bytes"
fi

# 预览或执行
echo "========================================"
echo "  SmartRide 缓存清理脚本"
echo "========================================"
echo ""
echo "项目目录: $PROJECT_DIR"
echo "待清理项: ${#to_delete[@]} 个"
echo "占用空间: $size_human"
echo ""

if [[ ${#to_delete[@]} -eq 0 ]]; then
    echo "✅ 未发现可清理的缓存文件。"
    exit 0
fi

if [[ $DRY_RUN -eq 1 ]]; then
    echo "🔍 [预览模式] 以下文件/目录将被删除："
    echo ""
    for item in "${to_delete[@]}"; do
        echo "  - $item"
    done
    echo ""
    echo "使用 --all 实际执行清理。"
    exit 0
fi

# 确认删除
echo "⚠️  确认删除以上 ${#to_delete[@]} 项？无法恢复。"
read -r -p "输入 y 确认: " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "已取消。"
    exit 0
fi

echo ""
echo "正在清理..."

for item in "${to_delete[@]}"; do
    if [[ -e "$item" ]]; then
        rm -rf "$item"
        echo "  🗑️  已删除: $item"
        ((deleted_count++)) || true
    fi
done

echo ""
echo "========================================"
echo "✅ 清理完成！释放了 $size_human"
echo "   删除项: $deleted_count"
echo "========================================"
