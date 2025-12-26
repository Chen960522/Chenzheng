#!/bin/bash

# 云服务器 Git 分叉问题修复脚本
# 使用方法: bash fix_server_git.sh

echo "=========================================="
echo "云服务器 Git 分叉问题修复脚本"
echo "=========================================="
echo ""

# 检查当前目录
if [ ! -d ".git" ]; then
    echo "❌ 错误: 当前目录不是 Git 仓库"
    echo "请先进入项目目录: cd ~/Chenzheng/aws-pricing-assistant"
    exit 1
fi

echo "📍 当前位置: $(pwd)"
echo ""

# 显示当前状态
echo "=== 1. 当前 Git 状态 ==="
git status
echo ""

# 显示分支信息
echo "=== 2. 查看提交历史 ==="
git log --oneline --graph --all -10
echo ""

# 备份当前分支(以防万一)
BACKUP_BRANCH="backup-$(date +%Y%m%d-%H%M%S)"
echo "=== 3. 创建备份分支: $BACKUP_BRANCH ==="
git branch $BACKUP_BRANCH
echo "✅ 备份完成"
echo ""

# 获取远程最新信息
echo "=== 4. 获取远程最新信息 ==="
git fetch origin
echo ""

# 使用 rebase 合并
echo "=== 5. 使用 rebase 方式合并远程更新 ==="
echo "执行: git pull --rebase origin main"
echo ""

git pull --rebase origin main

# 检查结果
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 成功! Git 分叉问题已解决"
    echo "=========================================="
    echo ""
    echo "最新状态:"
    git status
    echo ""
    echo "最近的提交:"
    git log --oneline -5
    echo ""
    echo "备份分支 '$BACKUP_BRANCH' 已创建,如需要可以恢复"
    echo "删除备份: git branch -D $BACKUP_BRANCH"
else
    echo ""
    echo "=========================================="
    echo "⚠️  出现冲突,需要手动解决"
    echo "=========================================="
    echo ""
    echo "冲突的文件:"
    git status
    echo ""
    echo "📝 解决步骤:"
    echo "1. 编辑冲突文件,解决冲突标记 (<<<<<<, ======, >>>>>>)"
    echo "2. 添加已解决的文件: git add <文件名>"
    echo "3. 继续 rebase: git rebase --continue"
    echo ""
    echo "如果想放弃 rebase:"
    echo "  git rebase --abort"
    echo "  git checkout $BACKUP_BRANCH  # 恢复到备份"
    echo ""
fi

echo ""
echo "=========================================="
echo "脚本执行完成"
echo "=========================================="
