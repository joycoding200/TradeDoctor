#!/bin/bash
# ============================================================
# TradeDoctor — 本地一键推送+部署脚本
# ============================================================
# ⚠️ 注意：此脚本只 git push + 触发服务器 update.sh，**不做 rsync 同步**，
#    且 update.sh **不 git pull**。服务器代码不会因此更新！
#    → 改了代码请用 local-deploy.sh（rsync 全量同步），而非本脚本。
#    → 本脚本仅适用于：代码已用 local-deploy.sh 同步过，只需重启服务时。
#
# 用法：
#   bash deploy/local-push.sh          # push 并触发服务器更新
#   bash deploy/local-push.sh --no-push # 只触发服务器更新（不 push）
#
# 首次使用前：
#   1. 修改下方 SERVER_USER / SERVER_HOST / PROJECT_PATH
#   2. 确保本地 SSH 免密登录已配置（ssh-copy-id）
# ============================================================
set -euo pipefail

# ============ 配置区（按实际修改） ============
SERVER_USER="root"
SERVER_HOST="你的服务器公网IP"
PROJECT_PATH="/opt/TradeDoctor"
# =============================================

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'
log()  { echo -e "${GREEN}[push]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
err()  { echo -e "${RED}[error]${NC} $1"; }

DO_PUSH=true
if [ "${1:-}" = "--no-push" ]; then
    DO_PUSH=false
fi

# ---- 1. 推送代码到 GitHub ----
if [ "$DO_PUSH" = true ]; then
    log "推送代码到 GitHub..."
    git push origin main || {
        err "git push 失败"
        exit 1
    }
fi

# ---- 2. SSH 触发服务器端更新 ----
log "触发服务器更新..."
log "  → ${SERVER_USER}@${SERVER_HOST}:${PROJECT_PATH}/deploy/update.sh"
echo ""

ssh "${SERVER_USER}@${SERVER_HOST}" "bash ${PROJECT_PATH}/deploy/update.sh"

echo ""
log "推送+部署完成！"
