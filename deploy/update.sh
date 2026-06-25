#!/bin/bash
# ============================================================
# TradingJournalAnalyzer — 服务器端一键更新脚本
# ============================================================
# 在服务器项目目录执行：
#   bash deploy/update.sh                  # 完整更新（含前端构建）
#   bash deploy/update.sh --skip-frontend  # 跳过前端（dist/ 已通过 rsync 上传）
#
# 或从本地通过 SSH 触发：
#   ssh user@host "bash /path/to/deploy/update.sh"
# ============================================================
set -euo pipefail

# ============ 配置区（按你的实际环境修改） ============
SERVICE_NAME="tja-backend"
HEALTH_URL="http://localhost/api/health"
BACKUP_DIR="/opt/backups"
# ==========================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# 颜色
G='\033[0;32m'; Y='\033[0;33m'; R='\033[0;31m'; B='\033[0;34m'; N='\033[0m'
log()  { echo -e "${G}[update]${N} $1"; }
warn() { echo -e "${Y}[warn]${N} $1"; }
err()  { echo -e "${R}[error]${N} $1"; }
step() { echo -e "${B}[${1}]${N} $2"; }

START_TIME=$SECONDS

# 解析参数
SKIP_FRONTEND=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-frontend) SKIP_FRONTEND=true; shift ;;
        *) shift ;;
    esac
done

# ============================================================
# 前置检查：生产环境配置完整性
# ============================================================
step "0/8" "前置检查..."

# 0a. backend/.env 必须存在
if [ ! -f "backend/.env" ]; then
    err "backend/.env 不存在！服务器无法启动。"
    echo "  请从 .env.example 复制并填入生产环境配置："
    echo "  cp backend/.env.example backend/.env && vim backend/.env"
    exit 1
fi
log "  backend/.env 存在"

# 0b. ENV 必须是 production
ENV_VAL=$(grep -E "^ENV=" backend/.env 2>/dev/null | cut -d= -f2 | tr -d '[:space:]' || echo "")
if [ "$ENV_VAL" != "production" ]; then
    warn "  backend/.env 中 ENV 未设为 production（当前: ${ENV_VAL:-未设置}）"
    warn "  生产环境必须设为 ENV=production，否则 SECRET_KEY 校验不生效"
fi

# 0c. uploads/ 目录存在（用户数据，不能丢）
if [ ! -d "backend/uploads" ]; then
    warn "  backend/uploads/ 不存在，首次部署请创建：mkdir -p backend/uploads"
fi

# 0d. 检查 .env.example 是否有 .env 中缺少的新配置项
if [ -f "backend/.env.example" ]; then
    NEW_KEYS=$(comm -23 \
        <(grep -E '^[A-Z_]+=' backend/.env.example | cut -d= -f1 | sort) \
        <(grep -E '^[A-Z_]+=' backend/.env | cut -d= -f1 | sort) \
        2>/dev/null || true)
    if [ -n "$NEW_KEYS" ]; then
        warn "  .env.example 中有 .env 未配置的项（请按需添加到 backend/.env）："
        echo "$NEW_KEYS" | sed 's/^/    /'
    fi
fi
echo ""

# ---- 1. 拉取最新代码 ----
step "1/8" "拉取最新代码..."
git pull --ff-only
echo ""

# ---- 2. 前端构建（可跳过） ----
if [ "$SKIP_FRONTEND" = true ]; then
    step "2/8" "跳过前端构建（dist/ 已通过 rsync 上传）"
    if [ ! -d "frontend/dist" ]; then
        warn "  frontend/dist/ 不存在！请先用 local-deploy.sh 上传前端"
    fi
else
    step "2/8" "构建前端..."
    cd frontend
    if [ -f package-lock.json ]; then
        npm ci --silent 2>/dev/null || npm install --silent
    else
        npm install --silent
    fi
    npm run build
    cd "$PROJECT_DIR"
fi
echo ""

# ---- 3. 后端依赖 ----
step "3/8" "同步后端依赖..."
cd backend
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
elif [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    warn "未找到虚拟环境，使用系统 Python"
fi
pip install -r requirements.txt --quiet 2>&1 | tail -5
echo ""

# ---- 4. 迁移前数据库备份 ----
step "4/8" "数据库备份..."
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="${BACKUP_DIR}/tradelens_$(date +%Y%m%d_%H%M%S).sql"
DB_URL=$(grep -E "^DATABASE_URL=" .env 2>/dev/null | cut -d= -f2- || echo "")
if [ -n "$DB_URL" ] && command -v pg_dump &>/dev/null; then
    if pg_dump "$DB_URL" > "$BACKUP_FILE" 2>/dev/null; then
        FILESIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log "  备份完成: ${BACKUP_FILE} (${FILESIZE})"
        # 保留最近 7 个备份
        ls -t "${BACKUP_DIR}"/tradelens_*.sql 2>/dev/null | tail -n +8 | xargs rm -f 2>/dev/null || true
    else
        warn "  数据库备份失败（非致命，继续部署）"
    fi
else
    warn "  跳过备份（pg_dump 不可用或 DATABASE_URL 未设置）"
fi
echo ""

# ---- 5. 数据库迁移 ----
step "5/8" "数据库迁移..."
if command -v alembic &>/dev/null && [ -d "alembic" ]; then
    ALEMBIC_STAMPED=$(python -c "
from app.config import settings
from sqlalchemy import create_engine, inspect
engine = create_engine(settings.database_url)
insp = inspect(engine)
print('yes' if 'alembic_version' in insp.get_table_names() else 'no')
" 2>/dev/null || echo "unknown")

    if [ "$ALEMBIC_STAMPED" = "no" ]; then
        log "  alembic_version 表不存在 — 服务器之前用 create_all 建表"
        log "  执行 alembic stamp head（标记当前状态，不执行迁移）..."
        alembic stamp head
    fi
    alembic upgrade head || warn "Alembic 迁移失败，请手动检查：alembic upgrade head"
else
    echo "  跳过（未安装 Alembic 或无迁移目录，依赖应用层 create_all）"
fi
echo ""

# ---- 6. 重启后端 ----
step "6/8" "重启后端服务..."
cd "$PROJECT_DIR"
sudo systemctl restart "$SERVICE_NAME"
echo ""

# ---- 7. 健康检查 ----
step "7/8" "健康检查..."
READY=false
for i in $(seq 1 20); do
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        ELAPSED=$((SECONDS - START_TIME))
        log "服务就绪！耗时 ${ELAPSED}s"
        READY=true
        break
    fi
    printf "."
    sleep 1
done
echo ""

if [ "$READY" = false ]; then
    err "服务未在 20 秒内就绪，排查命令："
    echo "  systemctl status $SERVICE_NAME"
    echo "  journalctl -u $SERVICE_NAME -n 50"
    echo ""
    warn "如需回滚到上一个版本："
    echo "  cd $PROJECT_DIR && git log --oneline -5"
    echo "  git reset --hard HEAD~1"
    echo "  systemctl restart $SERVICE_NAME"
    echo "  如需回滚迁移: cd backend && alembic downgrade -1"
    exit 1
fi

# ---- 8. 输出状态 ----
step "8/8" "部署摘要"
echo ""
log "更新完成！"
echo "  分支:   $(git branch --show-current)"
echo "  提交:   $(git log --oneline -1)"
echo "  耗时:   $((SECONDS - START_TIME))s"
echo "  备份:   ${BACKUP_FILE:-无}"
echo ""
echo "  提示："
echo "    查看日志:   journalctl -u $SERVICE_NAME -f"
echo "    管理员账户: bash deploy/init-admin.sh"
echo "    配置检查:   bash deploy/config-check.sh"
echo "    回滚:       git reset --hard HEAD~1 && systemctl restart $SERVICE_NAME"
