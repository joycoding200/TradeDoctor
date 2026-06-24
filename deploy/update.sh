#!/bin/bash
# ============================================================
# TradingJournalAnalyzer — 服务器端一键更新脚本
# ============================================================
# 在服务器项目目录执行：
#   bash deploy/update.sh
#
# 或从本地通过 SSH 触发：
#   ssh user@host "bash /path/to/deploy/update.sh"
# ============================================================
set -euo pipefail

# ============ 配置区（按你的实际环境修改） ============
SERVICE_NAME="tja-backend"          # systemd service 名
HEALTH_URL="http://localhost/api/health"
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

# ============================================================
# 前置检查：生产环境配置完整性
# ============================================================
step "0/7" "前置检查..."

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
step "1/7" "拉取最新代码..."
# .env 在 .gitignore 中，不会被覆盖
# uploads/ 在 .gitignore 中，不会被覆盖
git pull --ff-only
echo ""

# ---- 2. 前端构建 ----
step "2/7" "构建前端..."
cd frontend

if [ -f package-lock.json ]; then
    npm ci --silent 2>/dev/null || npm install --silent
else
    npm install --silent
fi

npm run build
cd "$PROJECT_DIR"
echo ""

# ---- 3. 后端依赖 ----
step "3/7" "同步后端依赖..."
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

# ---- 4. 数据库迁移 ----
step "4/7" "数据库迁移..."
if command -v alembic &>/dev/null && [ -d "alembic" ]; then
    # 关键：服务器可能用 create_all 建的表，alembic 不知道
    # 检查 alembic_version 表是否存在，不存在则先 stamp
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

    # 现在可以安全地执行迁移
    alembic upgrade head || warn "Alembic 迁移失败，请手动检查：alembic upgrade head"
else
    echo "  跳过（未安装 Alembic 或无迁移目录，依赖应用层 create_all）"
fi
echo ""

# ---- 5. 重启后端 ----
step "5/7" "重启后端服务..."
cd "$PROJECT_DIR"
sudo systemctl restart "$SERVICE_NAME"
echo ""

# ---- 6. 健康检查 ----
step "6/7" "健康检查..."
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
    exit 1
fi

# ---- 7. 输出状态 ----
step "7/7" "部署摘要"
echo ""
log "更新完成！"
echo "  分支:   $(git branch --show-current)"
echo "  提交:   $(git log --oneline -1)"
echo "  耗时:   $((SECONDS - START_TIME))s"
echo ""
echo "  提示："
echo "    查看日志:   journalctl -u $SERVICE_NAME -f"
echo "    管理员账户: bash deploy/init-admin.sh"
echo "    配置检查:   bash deploy/config-check.sh"
