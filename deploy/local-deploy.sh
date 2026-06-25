#!/bin/bash
# ============================================================
# TradingJournalAnalyzer — 本地构建 + rsync 部署（推荐）
# ============================================================
# 比 local-push.sh 更快：前端在本地 build，rsync 传到服务器
# 服务器不需要装 Node.js，部署时间从 30-60s 降到 10-20s
#
# 用法：
#   bash deploy/local-deploy.sh              # 默认：build + push + deploy
#   bash deploy/local-deploy.sh --skip-build # 跳过前端构建（dist/ 已是最新）
#   bash deploy/local-deploy.sh --no-push    # 不 git push，只部署当前 dist/
#   bash deploy/local-deploy.sh --branch dev # 部署 dev 分支
# ============================================================
set -euo pipefail

# ============ 配置区（按实际修改） ============
SERVER_USER="root"
SERVER_HOST="你的服务器公网IP"
PROJECT_PATH="/opt/TradingJournalAnalyzer"
# =============================================

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
DO_PUSH=true
BRANCH="main"
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build) SKIP_BUILD=true; shift ;;
        --no-push)    DO_PUSH=false; shift ;;
        --branch)     BRANCH="$2"; shift 2 ;;
        *) err "未知参数: $1"; exit 1 ;;
    esac
done

# ---- 1. 本地构建前端 ----
if [ "$SKIP_BUILD" = false ]; then
    step "1/4" "本地构建前端..."
    cd "$PROJECT_DIR/frontend"

    # 确保依赖安装
    if [ ! -d node_modules ]; then
        log "安装 npm 依赖..."
        npm install
    fi

    # 生产构建（VITE_API_BASE 不设置 → 默认空字符串 → 走相对路径 → nginx 反代）
    log "VITE_API_BASE 不设置，前端走相对路径，依赖 nginx /api 反代"
    npm run build
    cd "$PROJECT_DIR"
    log "前端构建完成: frontend/dist/"
else
    step "1/4" "跳过前端构建"
fi
echo ""

# ---- 2. rsync 前端 dist/ 到服务器 ----
step "2/4" "上传前端到服务器..."
rsync -avz --delete \
    "$PROJECT_DIR/frontend/dist/" \
    "${SERVER_USER}@${SERVER_HOST}:${PROJECT_PATH}/frontend/dist/"
log "前端已上传"
echo ""

# ---- 3. git push ----
if [ "$DO_PUSH" = true ]; then
    step "3/4" "推送代码到 GitHub (${BRANCH})..."
    git push origin "$BRANCH" || { err "git push 失败"; exit 1; }
else
    step "3/4" "跳过 git push"
fi
echo ""

# ---- 4. SSH 触发服务器更新（仅后端） ----
step "4/4" "触发服务器更新..."
ssh "${SERVER_USER}@${SERVER_HOST}" \
    "cd ${PROJECT_PATH} && bash deploy/update.sh --skip-frontend"

ELAPSED=$((SECONDS - START_TIME))
echo ""
log "部署完成！耗时 ${ELAPSED}s"
log "  分支: ${BRANCH}"
log "  前端: 本地构建 + rsync"
log "  后端: git pull + pip install + alembic + restart"
