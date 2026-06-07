#!/bin/bash
# 小满 + nomos 项目 GitHub 多仓库智能同步脚本
# - private (xiaoman.git): 双向同步，全量内容
# - public (xiaoman-public.git): 单向发布，仅源码
# - private (nomos.git): 双向同步，全量内容
# - private (nomos-references.git): 双向同步，全量内容

set -e

PRIVATE_DIR="/Users/zhongqiwei/projects/xiaoman"
PUBLIC_DIR="/Users/zhongqiwei/projects/xiaoman-public"
NOMOS_DIR="/Users/zhongqiwei/projects/nomos"
NOMOS_REF_DIR="/Users/zhongqiwei/projects/nomos-references"
LOG_FILE="$PRIVATE_DIR/tools/sync.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ==================== Private 仓库通用同步 ====================
# 参数1: 仓库本地目录
# 参数2: 仓库显示名称
sync_private_repo() {
    local repo_dir="$1"
    local repo_name="$2"

    cd "$repo_dir"
    log "=== [$repo_name] 开始同步 ==="

    # 检查当前分支（优先 main，回退 master）
    local branch="main"
    if ! git show-ref --verify --quiet refs/heads/main; then
        if git show-ref --verify --quiet refs/heads/master; then
            branch="master"
        else
            log "[$repo_name] 未找到 main/master 分支，跳过"
            return 1
        fi
    fi

    # fetch 远程
    if ! git fetch origin "$branch" 2>/dev/null; then
        log "[$repo_name] 无法连接 GitHub，跳过"
        return 1
    fi

    # 暂存本地未提交更改
    local had_changes=false
    if ! git diff --quiet || ! git diff --cached --quiet; then
        had_changes=true
        git add -A
        git stash push -m "auto-stash-$(date +%Y%m%d-%H%M%S)" || true
    fi

    local local_commit=$(git rev-parse "$branch")
    local remote_commit=$(git rev-parse "origin/$branch")
    local base_commit=$(git merge-base "$branch" "origin/$branch")

    if [ "$local_commit" = "$remote_commit" ]; then
        log "[$repo_name] 已同步，无需操作"
    elif [ "$local_commit" = "$base_commit" ]; then
        log "[$repo_name] 远程领先，执行 pull"
        git pull origin "$branch" --no-rebase
        log "[$repo_name] pull 完成"
    elif [ "$remote_commit" = "$base_commit" ]; then
        log "[$repo_name] 本地领先，执行 push"
        git push origin "$branch"
        log "[$repo_name] push 完成"
    else
        log "[$repo_name] 本地与远程分叉，尝试自动合并"
        if git merge "origin/$branch" --no-edit; then
            git push origin "$branch"
            log "[$repo_name] 合并并推送完成"
        else
            log "[$repo_name] 合并冲突！已中止，需要手动处理"
            git merge --abort 2>/dev/null || true
            if [ "$had_changes" = true ]; then
                git stash pop 2>/dev/null || true
            fi
            return 1
        fi
    fi

    # 恢复暂存并提交新的本地更改
    if [ "$had_changes" = true ]; then
        git stash pop 2>/dev/null || true
        git add -A
        if ! git diff --cached --quiet; then
            git commit -m "auto: daily backup $(date +%Y-%m-%d_%H:%M)"
            git push origin "$branch"
            log "[$repo_name] 本地更改已提交并推送"
        fi
    fi
}

# ==================== Public 仓库同步 ====================
sync_public() {
    log "=== [PUBLIC] 开始同步 xiaoman-public.git ==="

    # 如果 public 目录不存在或不是 git 仓库，先 clone
    if [ ! -d "$PUBLIC_DIR/.git" ]; then
        log "[PUBLIC] 本地目录为空，正在 clone..."
        rm -rf "$PUBLIC_DIR"
        if ! git clone "$PUBLIC_URL" "$PUBLIC_DIR"; then
            log "[PUBLIC] clone 失败，跳过"
            return 1
        fi
    fi

    cd "$PUBLIC_DIR"

    # 先 pull 最新（处理云端可能有的更新）
    if ! git pull origin main 2>/dev/null; then
        log "[PUBLIC] 无法 pull，跳过"
        return 1
    fi

    # 从 private 同步源码（排除数据、文档、依赖等非公开内容）
    rsync -av --delete \
        --exclude='.git/' \
        --exclude='node_modules/' \
        --exclude='dist/' \
        --exclude='build/' \
        --exclude='data/' \
        --exclude='data_*/' \
        --exclude='__pycache__/' \
        "$PRIVATE_DIR/backend/" "$PUBLIC_DIR/backend/"

    rsync -av --delete \
        --exclude='.git/' \
        --exclude='data/' \
        --exclude='data_*/' \
        --exclude='node_modules/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.env*' \
        "$PRIVATE_DIR/backend-py/" "$PUBLIC_DIR/backend-py/"

    rsync -av --delete \
        --exclude='.git/' \
        --exclude='node_modules/' \
        --exclude='dist/' \
        --exclude='build/' \
        --exclude='data/' \
        --exclude='data_*/' \
        --exclude='.vite/' \
        "$PRIVATE_DIR/web/" "$PUBLIC_DIR/web/"

    rsync -av --delete \
        --exclude='.git/' \
        --exclude='sync.log' \
        "$PRIVATE_DIR/tools/" "$PUBLIC_DIR/tools/"

    cp "$PRIVATE_DIR/docker-compose.yml" "$PUBLIC_DIR/"
    cp "$PRIVATE_DIR/start-web.bat" "$PUBLIC_DIR/"

    # 同步 README 和 .gitignore（如果存在）
    [ -f "$PRIVATE_DIR/README.md" ] && cp "$PRIVATE_DIR/README.md" "$PUBLIC_DIR/"
    [ -f "$PRIVATE_DIR/.gitignore" ] && cp "$PRIVATE_DIR/.gitignore" "$PUBLIC_DIR/"

    # 提交并推送
    git add -A
    if git diff --cached --quiet; then
        log "[PUBLIC] 无变更需要推送"
    else
        git commit -m "auto: sync public source $(date +%Y-%m-%d_%H:%M)"
        git push origin main
        log "[PUBLIC] 已推送源码更新"
    fi
}

# ==================== 主流程 ====================
log "========== 小满 + nomos 多仓库同步开始 =========="
sync_private_repo "$PRIVATE_DIR" "xiaoman-private"
sync_public
sync_private_repo "$NOMOS_DIR" "nomos"
sync_private_repo "$NOMOS_REF_DIR" "nomos-references"
log "========== 同步结束 =========="
