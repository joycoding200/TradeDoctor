#!/bin/bash
# ============================================================
# TradeDoctor — 本地构建 + rsync 全量代码部署
# ============================================================
# 用法：
#   bash deploy/local-deploy.sh                 # 完整流程
#   bash deploy/local-deploy.sh --skip-build    # 跳过 npm build
#   bash deploy/local-deploy.sh --dry-run       # 只显示 rsync 影响不实际执行
#
# 工作流程：
#   1. 本地构建前端 → 2. rsync 整个项目（含源码+dist）到服务器
#   → 3. SSH 触发服务器端更新（pip install + 备份 + alembic + 重启 + 健康检查）
# ============================================================
set -euo pipefail

# ============ 配置区 ============
SERVER_USER="root"
SERVER_HOST="47.109.159.232"
PROJECT_PATH="/opt/TradeDoctor"
# ================================

G='\033[0;32m'; Y='\033[0;33m'; R='\033[0;31m'; B='\033[0;34m'; N='\033[0m'
log()  { echo -e "${G}[deploy]${N} $1"; }
warn() { echo -e "${Y}[warn]${N} $1"; }
err()  { echo -e "${R}[error]${N} $1"; }
step() { echo -e "${B}[${1}]${N} $2"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
START_TIME=$SECONDS

# 解析参数
SKIP_BUILD=false
DRY_RUN=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build) SKIP_BUILD=true; shift ;;
        --dry-run)    DRY_RUN=true; shift ;;
        *) err "未知参数: $1"; exit 1 ;;
    esac
done

# ---- 1. 本地构建前端 ----
# IMPORTANT: 必须每次部署前重新构建。否则 rsync 推上去的是旧 dist，
# 浏览器/CDN 拿到的还是旧 JS，导致"代码改了但页面没变化"。
# 之前的版本只检查 dist 是否存在，不主动构建——这是最常见的"前端改动不生效"根因。
if [ "$SKIP_BUILD" = false ]; then
    step "1/3" "本地构建前端..."
    cd "$PROJECT_DIR/frontend"

    # 检测 npm 是否可用
    if ! command -v npm &>/dev/null; then
        err "npm 不在 PATH 中！"
        echo "  请在 Windows 上（Git Bash / PowerShell）执行本脚本，确保 npm 可用。"
        echo "  或先手动构建：cd frontend && npm run build，再用 --skip-build 部署。"
        exit 1
    fi

    # 源码比 dist 新时，npm run build 必然产出新 hash 文件名
    log "执行 npm run build（约 10-30s）..."
    if ! npm run build 2>&1 | tail -8; then
        err "前端构建失败！请检查 TypeScript 错误。"
        echo "  可单独运行: cd frontend && npm run build 看完整输出。"
        exit 1
    fi

    if [ ! -d dist ]; then
        err "构建完成但 dist/ 不存在，检查 vite 配置。"
        exit 1
    fi
    cd "$PROJECT_DIR"
    log "前端构建完成: frontend/dist/"
else
    step "1/3" "跳过前端构建（--skip-build）"
    # 即便跳过构建，也要确保 dist 存在
    if [ ! -d "$PROJECT_DIR/frontend/dist" ]; then
        err "frontend/dist/ 不存在！请去掉 --skip-build 或先手动构建。"
        exit 1
    fi
    warn "跳过构建——请确认 dist 是最新源码构建的，否则前端改动不生效。"
fi
echo ""

# ---- 2. rsync 整个项目到服务器 ----
step "2/3" "同步代码到服务器..."
SSH_TARGET="${SERVER_USER}@${SERVER_HOST}:${PROJECT_PATH}/"

RSYNC_EXCLUDES=(
    --exclude='.git'
    --exclude='__pycache__'
    --exclude='*.pyc'
    --exclude='*.pyo'
    --exclude='frontend/node_modules'
    --exclude='backend/.venv'
    --exclude='backend/venv'
    --exclude='backend/uploads'      # 用户数据，不过期
    --exclude='.env'                 # 生产环境配置，不覆盖
    --exclude='.claude'
)

if [ "$DRY_RUN" = true ]; then
    log "DRY RUN — 仅列出会被同步的文件："
    rsync -avz --delete --dry-run \
        "${RSYNC_EXCLUDES[@]}" \
        "$PROJECT_DIR/" \
        "$SSH_TARGET" \
        | grep -v '/$' | head -50
    echo "    ..."
    log "DRY RUN 完成，未实际传输"
    exit 0
fi

rsync -avz --delete \
    "${RSYNC_EXCLUDES[@]}" \
    "$PROJECT_DIR/" \
    "$SSH_TARGET"

log "代码同步完成"

# 检查服务器端 deploy/update.sh 是否存在
if ssh "${SERVER_USER}@${SERVER_HOST}" "test -f ${PROJECT_PATH}/deploy/update.sh"; then
    log "服务器端 update.sh 存在"
else
    err "服务器上找不到 ${PROJECT_PATH}/deploy/update.sh！"
    echo "  请先手动在服务器上创建项目目录并上传初始代码"
    exit 1
fi
echo ""

# ---- 3. SSH 触发服务器端更新 ----
step "3/3" "触发服务器端更新..."
ssh "${SERVER_USER}@${SERVER_HOST}" \
    "bash ${PROJECT_PATH}/deploy/update.sh"

ELAPSED=$((SECONDS - START_TIME))
echo ""
log "部署完成！耗时 ${ELAPSED}s"
log "  前端构建: $([ "$SKIP_BUILD" = true ] && echo '跳过' || echo '已构建')"
log "  代码同步: rsync 全量（排除 node_modules/.venv/uploads/.env/.git）"
log "  服务端:   pip install + 备份 + alembic + 重启 + 健康检查"
