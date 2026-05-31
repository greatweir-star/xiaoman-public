#!/bin/bash
# 小满项目 GitHub 双仓库智能同步脚本
# - private (xiaoman.git): 双向同步，全量内容
# - public (xiaoman-public.git): 单向发布，仅源码

set -e

PRIVATE_DIR="/Users/zhongqiwei/projects/xiaoman"
PUBLIC_DIR="/Users/zhongqiwei/projects/xiaoman-public"
PRIVATE_URL="https://github.com/greatweir-star/xiaoman.git"
PUBLIC_URL="https://github.com/greatweir-star/xiaoman-public.git"
LOG_FILE="$PRIVATE_DIR/tools/sync.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ==================== Private 仓库同步 ====================
sync_private() {
    cd "$PRIVATE_DIR"
    log "=== [PRIVATE] 开始同步 xiaoman.git ==="

    # fetch 远程
    if ! git fetch origin main 2>/dev/null; then
        log "[PRIVATE] 无法连接 GitHub，跳过"
        return 1
    fi

    # 暂存本地未提交更改
    local had_changes=false
    if ! git diff --quiet || ! git diff --cached --quiet; then
        had_changes=true
        git add -A
        git stash push -m "auto-stash-$(date +%Y%m%d-%H%M%S)" || true
    fi

    local local_commit=$(git rev-parse main)
    local remote_commit=$(git rev-parse origin/main)
    local base_commit=$(git merge-base main origin/main)

    if [ "$local_commit" = "$remote_commit" ]; then
        log "[PRIVATE] 已同步，无需操作"
    elif [ "$local_commit" = "$base_commit" ]; then
        log "[PRIVATE] 远程领先，执行 pull"
        git pull origin main --no-rebase
        log "[PRIVATE] pull 完成"
    elif [ "$remote_commit" = "$base_commit" ]; then
        log "[PRIVATE] 本地领先，执行 push"
        git push origin main
        log "[PRIVATE] push 完成"
    else
        log "[PRIVATE] 本地与远程分叉，尝试自动合并"
        if git merge origin/main --no-edit; then
            git push origin main
            log "[PRIVATE] 合并并推送完成"
        else
            log "[PRIVATE] 合并冲突！已中止，需要手动处理"
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
            git push origin main
            log "[PRIVATE] 本地更改已提交并推送"
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

    # 从 private 同步源码（排除数据、文档等非公开内容）
    rsync -av --delete \
        --exclude='.git/' \
        --exclude='data/' \
        --exclude='data_*/' \
        --exclude='__pycache__/' \
        "$PRIVATE_DIR/backend/" "$PUBLIC_DIR/backend/"

    rsync -av --delete \
        --exclude='.git/' \
        --exclude='data/' \
        --exclude='node_modules/' \
        --exclude='__pycache__/' \
        "$PRIVATE_DIR/backend-py/" "$PUBLIC_DIR/backend-py/"

    rsync -av --delete \
        --exclude='.git/' \
        --exclude='node_modules/' \
        --exclude='dist/' \
        --exclude='build/' \
        "$PRIVATE_DIR/web/" "$PUBLIC_DIR/web/"

    rsync -av --delete \
        --exclude='.git/' \
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
log "========== 小满双仓库同步开始 =========="
sync_private
sync_public
log "========== 同步结束 =========="
