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
# IMPORTANT: dist 必须是最新源码构建的，否则 rsync 推上去的是旧 dist，
# 浏览器/CDN 拿到的还是旧 JS，导致"代码改了但页面没变化"。
#
# ⚠️ WSL 陷阱：如果 node_modules 是在 Windows 上装的（含 rolldown 等原生
# 二进制），在 WSL 里跑 npm run build 会因跨平台原生绑定崩溃
# (ERR_REQUIRE_ESM / rolldown binding error)。
# → WSL 环境（检测到 /mnt/ 路径）不自动构建，要求用户先在 Windows 上构建。
if [ "$SKIP_BUILD" = false ]; then
    step "1/3" "前端构建检查..."
    cd "$PROJECT_DIR/frontend"

    # 检测是否在 WSL 里跑（项目路径含 /mnt/ 说明 node_modules 是 Windows 装的）
    if [[ "$PROJECT_DIR" == /mnt/* ]]; then
        warn "检测到 WSL 环境（$PROJECT_DIR）。"
        warn "node_modules 是 Windows 安装的，在 WSL 里构建会导致 rolldown 原生绑定崩溃。"
        echo "  请先在 Windows 上构建（PowerShell / Git Bash / cmd）："
        echo "    cd D:\\Dev\\Projects\\TradingJournalAnalyzer\\frontend"
        echo "    npm run build"
        echo "  构建完成后再跑本脚本（dist/ 会自动 rsync 上去）。"
        echo ""
        # 不构建，但要确保 dist 存在 + 校验新鲜度
        if [ ! -d dist ]; then
            err "frontend/dist/ 不存在！请先在 Windows 上执行 npm run build。"
            exit 1
        fi
    else
        # 原生 Linux 环境，可以安全构建
        if ! command -v npm &>/dev/null; then
            err "npm 不在 PATH 中！请在 Windows 上构建后用 --skip-build，或安装 Node.js。"
            exit 1
        fi
        log "执行 npm run build（约 10-30s）..."
        if ! npm run build 2>&1 | tail -8; then
            err "前端构建失败！"
            echo "  可单独运行: cd frontend && npm run build 看完整输出。"
            exit 1
        fi
        if [ ! -d dist ]; then
            err "构建完成但 dist/ 不存在，检查 vite 配置。"
            exit 1
        fi
        log "前端构建完成: frontend/dist/"
    fi
    cd "$PROJECT_DIR"
else
    step "1/3" "跳过前端构建（--skip-build）"
    if [ ! -d "$PROJECT_DIR/frontend/dist" ]; then
        err "frontend/dist/ 不存在！请去掉 --skip-build 或先手动构建。"
        exit 1
    fi
    warn "跳过构建——请确认 dist 是最新源码构建的，否则前端改动不生效。"
fi

# dist 新鲜度校验：如果 src/ 里有比 dist/index.html 更新的 .tsx/.ts，
# 警告（dist 可能是旧的）。不阻断部署，但提醒用户。
if [ -f "$PROJECT_DIR/frontend/dist/index.html" ]; then
    NEWEST_SRC=$(find "$PROJECT_DIR/frontend/src" -name "*.tsx" -o -name "*.ts" 2>/dev/null \
        | xargs stat -c %Y 2>/dev/null | sort -rn | head -1)
    DIST_MTIME=$(stat -c %Y "$PROJECT_DIR/frontend/dist/index.html" 2>/dev/null || echo 0)
    if [ -n "$NEWEST_SRC" ] && [ "$NEWEST_SRC" -gt "$DIST_MTIME" ]; then
        warn "检测到 src/ 有比 dist/ 更新的源码——dist 可能是旧构建！"
        warn "请在 Windows 上重新 npm run build 后再部署，否则前端改动不生效。"
        echo "  （如确认 dist 已是最新，可忽略此警告继续。）"
        echo ""
    fi
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
