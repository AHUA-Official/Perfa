#!/bin/bash
# 代码统计脚本 - 统计真实的项目代码量

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "📊 Perfa 项目代码统计"
echo "========================================="
echo ""

# 排除目录列表
EXCLUDE_DIRS=(
    "__pycache__"
    "venv"
    ".venv"
    "node_modules"
    ".git"
    "*.egg-info"
    "dist"
    "build"
)

# 构建 exclude 参数
EXCLUDE_ARGS=""
for dir in "${EXCLUDE_DIRS[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude-dir=$dir"
done

# 额外排除的文件模式
EXCLUDE_FILES=(
    "*.pyc"
    "*.pyo"
    "*.so"
    "*.dll"
    "*.dylib"
    "*.bak"
    "*.log"
    "*.db"
    "*.sqlite"
)

for file in "${EXCLUDE_FILES[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude-ext=$file"
done

echo "📁 统计目录: src/"
echo "🚫 排除: ${EXCLUDE_DIRS[*]}"
echo ""

# 1. 按语言统计
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📈 按语言统计"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cloc src/ \
    --exclude-dir="${EXCLUDE_DIRS[*]}" \
    --exclude-list-file=<(echo "${EXCLUDE_FILES[*]}" | tr ' ' '\n') \
    --quiet

echo ""

# 2. 按模块统计
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 按模块统计 (Python)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for module in src/*/; do
    module_name=$(basename "$module")
    
    # 跳过排除的目录
    skip=false
    for exclude in "${EXCLUDE_DIRS[@]}"; do
        if [[ "$module_name" == "$exclude" ]]; then
            skip=true
            break
        fi
    done
    
    if $skip; then
        continue
    fi
    
    # 统计该模块的 Python 文件
    py_files=$(find "$module" -name "*.py" -not -path "*/__pycache__/*" -not -path "*/venv/*" | wc -l)
    
    if [[ $py_files -gt 0 ]]; then
        # 统计代码行数
        code_lines=$(find "$module" -name "*.py" -not -path "*/__pycache__/*" -not -path "*/venv/*" \
            -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}')
        
        printf "%-20s %3d 文件, %6d 行代码\n" "$module_name" "$py_files" "$code_lines"
    fi
done

echo ""

# 3. Python 详细统计
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 Python 代码详情"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cloc src/ \
    --include-lang=Python \
    --exclude-dir="${EXCLUDE_DIRS[*]}" \
    --by-file \
    --quiet \
    | head -50

echo ""
echo "========================================="
echo "✅ 统计完成"
echo "========================================="
