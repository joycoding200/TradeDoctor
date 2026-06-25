#!/bin/bash
# ============================================================
# TradingJournalAnalyzer — 首次服务器环境安装脚本
# ============================================================
# 在一台全新的阿里云轻量服务器上执行（已有宝塔面板即可）
# 用法：
#   ssh root@你的服务器IP
#   cd /opt
#   git clone https://github.com/joycoding200/TradingJournalAnalyzer.git
#   cd TradingJournalAnalyzer
#   bash deploy/server-setup.sh
#
# 执行前请确认：
#   1. 宝塔面板已安装（nginx 已由宝塔管理）
#   2. 你有 root 权限
#   3. 服务器能访问外网（apt 源）
# ============================================================
set -euo pipefail

G='\033[0;32m'; Y='\033[0;33m'; R='\033[0;31m'; B='\033[0;34m'; N='\033[0m'
log()  { echo -e "${G}[setup]${N} $1"; }
warn() { echo -e "${Y}[warn]${N} $1"; }
err()  { echo -e "${R}[error]${N} $1"; }
step() { echo -e "${B}[${1}]${N} $2"; }

# ============ 配置区 ============
PROJECT_DIR="/opt/TradingJournalAnalyzer"
DB_NAME="tradelens"
DB_USER="tradelens"
PG_VERSION="17"
PYTHON_BIN="python3"
SERVICE_NAME="tja-backend"
# =================================

cd "$PROJECT_DIR"

echo ""
echo "============================================"
echo "  TradingJournalAnalyzer 首次环境安装"
echo "  目标目录: $PROJECT_DIR"
echo "============================================"
echo ""

# ---------- 1. 系统依赖 ----------
step "1/8" "安装系统依赖..."

apt-get update -qq
apt-get install -y -qq \
    "$PYTHON_BIN" "$PYTHON_BIN"-venv "$PYTHON_BIN"-dev \
    build-essential libpq-dev \
    git curl wget rsync > /dev/null 2>&1

log "系统依赖安装完成"

# ---------- 2. PostgreSQL ----------
step "2/8" "安装 PostgreSQL ${PG_VERSION}..."

if command -v psql &>/dev/null && psql --version | grep -q "$PG_VERSION"; then
    log "PostgreSQL ${PG_VERSION} 已安装，跳过"
else
    # 添加 PostgreSQL 官方源（宝塔自带的是 MySQL，需要单独装 PG）
    if ! apt-cache show "postgresql-$PG_VERSION" &>/dev/null; then
        warn "apt 源中没有 PostgreSQL ${PG_VERSION}，添加官方源..."
        sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
        curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg 2>/dev/null
        apt-get update -qq
    fi
    apt-get install -y -qq "postgresql-$PG_VERSION" > /dev/null 2>&1
    log "PostgreSQL ${PG_VERSION} 安装完成"
fi

systemctl enable postgresql >/dev/null 2>&1
systemctl start postgresql >/dev/null 2>&1

# ---------- 3. 创建数据库和用户 ----------
step "3/8" "创建数据库和用户..."

DB_PASS=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 24)

su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'\" | grep -q 1" 2>/dev/null || \
    su - postgres -c "psql -c \"CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';\"" >/dev/null 2>&1

su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'\" | grep -q 1" 2>/dev/null || \
    su - postgres -c "createdb -O ${DB_USER} ${DB_NAME}" >/dev/null 2>&1

# 用户已存在则更新密码
su - postgres -c "psql -c \"ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';\"" >/dev/null 2>&1 || true

log "数据库 ${DB_NAME} 和用户 ${DB_USER} 就绪"
echo "  数据库密码: ${DB_PASS}（请保存，稍后写入 .env）"

# ---------- 4. Python 虚拟环境 + 后端依赖 ----------
step "4/8" "配置 Python 环境..."

cd "$PROJECT_DIR/backend"

if [ ! -d .venv ]; then
    "$PYTHON_BIN" -m venv .venv
    log "虚拟环境已创建"
fi

source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
log "后端依赖安装完成"

# ---------- 5. 生成 .env ----------
step "5/8" "生成生产环境 .env..."

SECRET_KEY=$(openssl rand -hex 32)
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "你的服务器IP")

if [ ! -f .env ]; then
    cat > .env << ENVEOF
# ===== 数据库 =====
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}

# ===== JWT 认证 =====
SECRET_KEY=${SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480

# ===== AI 配置 =====
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=请填入你的DeepSeek_API_Key
DEEPSEEK_MODEL=deepseek-chat

# ===== 跨域 (CORS) =====
CORS_ORIGINS=http://${SERVER_IP}

# ===== 环境标识 =====
ENV=production
ENVEOF
    log ".env 已生成"
    warn "请编辑 backend/.env 填入 DEEPSEEK_API_KEY"
else
    log ".env 已存在，跳过（如需重新生成请先备份再删除）"
fi

mkdir -p uploads
log "uploads/ 目录已创建"

# ---------- 6. 数据库初始化 ----------
step "6/8" "初始化数据库表..."

# 用 create_all 建表（main.py lifespan 会自动执行，这里手动触发一次）
python -c "
import sys; sys.path.insert(0, '.')
from app.database import engine, Base
import app.models  # noqa
Base.metadata.create_all(bind=engine)
print('表创建完成')
" 2>/dev/null || warn "create_all 执行失败，请手动检查"

# 标记 alembic 版本（后续迁移用）
if [ -d "alembic" ] && command -v alembic &>/dev/null; then
    alembic stamp head 2>/dev/null && log "alembic 版本已标记" || warn "alembic stamp 失败（可后续手动处理）"
fi
log "数据库表初始化完成"

# ---------- 7. systemd 服务 ----------
step "7/8" "创建 systemd 服务..."

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [ -f "$SERVICE_FILE" ]; then
    log "systemd 服务已存在，跳过创建"
else
    cat > "$SERVICE_FILE" << SVCEOF
[Unit]
Description=TradingJournalAnalyzer Backend
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}/backend
ExecStart=${PROJECT_DIR}/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5
Environment=PATH=${PROJECT_DIR}/backend/.venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
SVCEOF
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME" >/dev/null 2>&1
    log "systemd 服务已创建: ${SERVICE_NAME}"
fi

systemctl restart "$SERVICE_NAME" 2>/dev/null || warn "服务启动失败，请检查 .env 配置"

sleep 3
if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
    log "后端服务已启动！健康检查通过"
else
    warn "后端服务可能未就绪，请检查:"
    echo "  systemctl status ${SERVICE_NAME}"
    echo "  journalctl -u ${SERVICE_NAME} -n 20"
fi

# ---------- 8. 完成提示 ----------
step "8/8" "完成"

echo ""
echo "============================================"
echo "  首次安装完成！"
echo "============================================"
echo ""
echo "  接下来你需要做的："
echo ""
echo "  1. 编辑后端配置："
echo "     vim ${PROJECT_DIR}/backend/.env"
echo "     → 填入 DEEPSEEK_API_KEY"
echo ""
echo "  2. 创建管理员账户："
echo "     cd ${PROJECT_DIR}"
echo "     ADMIN_PASSWORD=你的密码 bash deploy/init-admin.sh --email admin@你的邮箱.com"
echo ""
echo "  3. 配置 nginx（通过宝塔面板或手动）："
echo "     方式A - 宝塔面板："
echo "       → 网站 → 添加站点 → 域名填 ${SERVER_IP}"
echo "       → 设置 → 反向代理 → 添加：/api → http://127.0.0.1:8000"
echo "       → 设置 → 网站目录 → 设为 ${PROJECT_DIR}/frontend/dist"
echo "     方式B - 手动配置："
echo "       cp deploy/nginx-tja.conf /etc/nginx/conf.d/tja.conf"
echo "       nginx -t && nginx -s reload"
echo ""
echo "  4. 构建并上传前端（在本地电脑执行）："
echo "     cd frontend && npm run build"
echo "     rsync -avz --delete dist/ root@${SERVER_IP}:${PROJECT_DIR}/frontend/dist/"
echo ""
echo "  5. 重启服务使 .env 生效："
echo "     systemctl restart ${SERVICE_NAME}"
echo ""
echo "  6. 访问测试："
echo "     curl http://${SERVER_IP}/api/health  → 后端"
echo "     浏览器打开 http://${SERVER_IP}/       → 前端"
echo ""
