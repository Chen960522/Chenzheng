#!/bin/bash

# 快速修复 Git 分叉 - 简化版
# 使用方法: bash quick_fix_git.sh

echo "🔧 快速修复 Git 分叉问题..."
echo ""

# 方案1: 使用 rebase (推荐)
echo "方案1: 使用 rebase 合并 (推荐)"
echo "命令: git pull --rebase origin main"
echo ""

# 方案2: 使用 merge
echo "方案2: 使用 merge 合并"
echo "命令: git pull origin main"
echo ""

# 方案3: 强制覆盖本地(慎用)
echo "方案3: 强制使用远程版本 (会丢失本地提交)"
echo "命令: git reset --hard origin/main"
echo ""

read -p "请选择方案 (1/2/3): " choice

case $choice in
    1)
        echo ""
        echo "执行 rebase..."
        git pull --rebase origin main
        ;;
    2)
        echo ""
        echo "执行 merge..."
        git pull origin main
        ;;
    3)
        echo ""
        read -p "⚠️  警告: 这会丢失本地提交! 确认吗? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            echo "执行强制重置..."
            git reset --hard origin/main
        else
            echo "已取消"
        fi
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
echo "当前状态:"
git status
