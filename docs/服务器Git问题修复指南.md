# 服务器 Git 分叉问题修复指南

## 问题描述

当服务器上出现以下错误时:
```
Your branch and 'origin/main' have diverged,
and have 1 and 2 different commits each, respectively.
```

这表示本地分支和远程分支已经分叉,需要合并。

## 快速解决方案

### 方案1: 使用自动化脚本 (推荐)

1. 上传脚本到服务器:
```bash
# 在本地,将脚本上传到服务器
scp scripts/fix_server_git.sh root@your-server:/root/Chenzheng/aws-pricing-assistant/
```

2. 在服务器上执行:
```bash
cd ~/Chenzheng/aws-pricing-assistant
chmod +x fix_server_git.sh
bash fix_server_git.sh
```

### 方案2: 手动执行命令

#### 选项A: 使用 rebase (推荐,保持历史整洁)

```bash
cd ~/Chenzheng/aws-pricing-assistant

# 1. 查看当前状态
git status

# 2. 创建备份分支(可选但推荐)
git branch backup-$(date +%Y%m%d)

# 3. 使用 rebase 合并
git pull --rebase origin main

# 4. 如果有冲突,解决后继续
git add .
git rebase --continue

# 5. 如果想取消 rebase
git rebase --abort
```

#### 选项B: 使用 merge (创建合并提交)

```bash
cd ~/Chenzheng/aws-pricing-assistant

# 直接合并
git pull origin main

# 如果有冲突,解决后提交
git add .
git commit -m "合并远程更新"
```

#### 选项C: 强制使用远程版本 (会丢失本地提交)

⚠️ **警告**: 这会丢失你的本地提交!

```bash
cd ~/Chenzheng/aws-pricing-assistant

# 查看会丢失哪些提交
git log origin/main..HEAD

# 确认后执行
git reset --hard origin/main
```

## 冲突解决步骤

如果在合并过程中出现冲突:

1. **查看冲突文件**:
```bash
git status
```

2. **编辑冲突文件**,找到并解决冲突标记:
```
<<<<<<< HEAD
你的本地更改
=======
远程的更改
>>>>>>> origin/main
```

3. **标记为已解决**:
```bash
git add <冲突文件>
```

4. **继续合并**:
```bash
# 如果使用的是 rebase
git rebase --continue

# 如果使用的是 merge
git commit
```

## 预防措施

为避免将来出现分叉:

1. **拉取前先提交本地更改**:
```bash
git add .
git commit -m "描述你的更改"
git pull --rebase origin main
```

2. **定期同步**:
```bash
# 每天开始工作前
git pull --rebase origin main
```

3. **推送前先拉取**:
```bash
git pull --rebase origin main
git push origin main
```

## 验证修复

修复后验证状态:

```bash
# 检查状态
git status

# 应该显示:
# Your branch is up to date with 'origin/main'.
# nothing to commit, working tree clean

# 查看提交历史
git log --oneline --graph -10
```

## 常见问题

### Q: rebase 和 merge 有什么区别?

**Rebase**: 
- 将你的提交放在远程提交之后
- 保持线性的提交历史
- 推荐用于个人分支

**Merge**: 
- 创建一个新的合并提交
- 保留完整的分支历史
- 适合团队协作

### Q: 如何恢复到修复前的状态?

如果创建了备份分支:
```bash
git checkout backup-20241226
git branch -D main
git checkout -b main
```

### Q: 删除那些意外创建的文件 (=2.5.0, =2.9.0)

```bash
rm =2.5.0 =2.9.0
```

这些文件可能是命令输入错误导致的。

## 联系支持

如果以上方法都无法解决问题,请:
1. 保存当前状态截图
2. 运行 `git log --oneline --graph --all -20 > git-status.txt`
3. 联系技术支持
