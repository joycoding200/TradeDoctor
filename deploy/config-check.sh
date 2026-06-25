#!/bin/bash
# ============================================================
# TradeDoctor — 生产环境配置校验
# ============================================================
# 在服务器上运行，检查所有生产环境必需的配置是否就位
#   bash deploy/config-check.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

G='\033[0;32m'; Y='\033[0;33m'; R='\033[0;31m'; N='\033[0m'
PASS=0; WARN=0; FAIL=0

ok()   { echo -e "  ${G}[OK]${N} $1"; PASS=$((PASS+1)); }
warn() { echo -e "  ${Y}[WARN]${N} $1"; WARN=$((WARN+1)); }
fail() { echo -e "  ${R}[FAIL]${N} $1"; FAIL=$((FAIL+1)); }

echo "=== TradeDoctor 生产配置校验 ==="
echo ""

# ---- 1. .env 文件 ----
echo "[1/6] 环境配置文件"
if [ -f backend/.env ]; then
    ok "backend/.env 存在"
else
    fail "backend/.env 不存在！从 .env.example 复制并修改"
    echo "      cp backend/.env.example backend/.env"
fi
echo ""

# ---- 2. 关键配置项 ----
echo "[2/6] 关键配置项"
if [ ! -f backend/.env ]; then
    echo "  (跳过，.env 不存在)"
    echo ""
else
    # ENV
    ENV_VAL=$(grep -E "^ENV=" backend/.env 2>/dev/null | cut -d= -f2 | tr -d '[:space:]' || echo "")
    if [ "$ENV_VAL" = "production" ]; then
        ok "ENV=production"
    else
        fail "ENV 应设为 production（当前: ${ENV_VAL:-未设置}）"
    fi

    # SECRET_KEY
    SK_VAL=$(grep -E "^SECRET_KEY=" backend/.env 2>/dev/null | cut -d= -f2- || echo "")
    if [ -z "$SK_VAL" ]; then
        fail "SECRET_KEY 未设置"
    elif [ "$SK_VAL" = "dev-only-change-this-to-a-random-32-char-string" ]; then
        fail "SECRET_KEY 仍是开发默认值，必须修改"
    elif [ ${#SK_VAL} -lt 32 ]; then
        fail "SECRET_KEY 长度不足 32 字符（当前: ${#SK_VAL}）"
    else
        ok "SECRET_KEY 已设置（${#SK_VAL} 字符）"
    fi

    # DATABASE_URL
    DB_VAL=$(grep -E "^DATABASE_URL=" backend/.env 2>/dev/null | cut -d= -f2- || echo "")
    if echo "$DB_VAL" | grep -q "localhost.*tradelens"; then
        warn "DATABASE_URL 可能仍是开发默认值"
    elif [ -z "$DB_VAL" ]; then
        fail "DATABASE_URL 未设置"
    else
        ok "DATABASE_URL 已设置"
    fi

    # CORS_ORIGINS
    CORS_VAL=$(grep -E "^CORS_ORIGINS=" backend/.env 2>/dev/null | cut -d= -f2- || echo "")
    if echo "$CORS_VAL" | grep -q "localhost:5173"; then
        warn "CORS_ORIGINS 仍是 localhost:5173，生产环境应改为服务器域名/IP"
    elif [ -z "$CORS_VAL" ]; then
        fail "CORS_ORIGINS 未设置"
    else
        ok "CORS_ORIGINS=$CORS_VAL"
    fi
fi
echo ""

# ---- 3. AI 配置 ----
echo "[3/6] AI 提供商配置"
if [ ! -f backend/.env ]; then
    echo "  (跳过，.env 不存在)"
    echo ""
else
    AI_PROVIDER=$(grep -E "^AI_PROVIDER=" backend/.env 2>/dev/null | cut -d= -f2 | tr -d '[:space:]' || echo "")
    case "$AI_PROVIDER" in
        openai)
            KEY=$(grep -E "^OPENAI_API_KEY=" backend/.env | cut -d= -f2- || echo "")
            if [ -n "$KEY" ] && [ "$KEY" != "sk-xxx" ]; then ok "OpenAI API Key 已设置"
            else fail "OPENAI_API_KEY 未设置或仍是占位符"; fi
            ;;
        deepseek)
            KEY=$(grep -E "^DEEPSEEK_API_KEY=" backend/.env | cut -d= -f2- || echo "")
            if [ -n "$KEY" ]; then ok "DeepSeek API Key 已设置"
            else fail "DEEPSEEK_API_KEY 未设置"; fi
            ;;
        claude)
            KEY=$(grep -E "^CLAUDE_API_KEY=" backend/.env | cut -d= -f2- || echo "")
            if [ -n "$KEY" ]; then ok "Claude API Key 已设置"
            else fail "CLAUDE_API_KEY 未设置"; fi
            ;;
        openrouter)
            KEY=$(grep -E "^OPENAI_API_KEY=" backend/.env | cut -d= -f2- || echo "")
            if [ -n "$KEY" ]; then ok "OpenRouter API Key 已设置"
            else fail "OPENAI_API_KEY 未设置（OpenRouter 复用此 key）"; fi
            ;;
        *)
            warn "AI_PROVIDER 未设置或值不匹配（当前: ${AI_PROVIDER:-空}）"
            ;;
    esac
fi
echo ""

# ---- 4. 数据库连接 ----
echo "[4/6] 数据库连接"
if command -v psql &>/dev/null; then
    if [ -n "${DB_VAL:-}" ]; then
        # 尝试用 DATABASE_URL 连接
        if psql "$DB_VAL" -c "SELECT 1" > /dev/null 2>&1; then
            ok "数据库连接正常"
        else
            fail "数据库连接失败，检查 DATABASE_URL 和 PostgreSQL 服务"
        fi
    fi
else
    warn "psql 未安装，跳过数据库连接测试"
fi

# 检查关键表是否存在
if command -v psql &>/dev/null && [ -n "${DB_VAL:-}" ]; then
    TABLE_COUNT=$(psql "$DB_VAL" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null | tr -d '[:space:]' || echo "0")
    if [ "$TABLE_COUNT" -gt 5 ]; then
        ok "数据库表已创建（$TABLE_COUNT 张表）"
    else
        warn "数据库表数量偏少（$TABLE_COUNT），可能未正确初始化"
    fi
fi
echo ""

# ---- 5. Admin 账户 ----
echo "[5/6] 管理员账户"
if command -v psql &>/dev/null && [ -n "${DB_VAL:-}" ]; then
    ADMIN_COUNT=$(psql "$DB_VAL" -t -c "SELECT count(*) FROM users WHERE is_admin = true" 2>/dev/null | tr -d '[:space:]' || echo "0")
    if [ "$ADMIN_COUNT" -gt 0 ]; then
        ok "管理员账户存在（$ADMIN_COUNT 个）"
    else
        fail "未找到管理员账户！运行: bash deploy/init-admin.sh"
    fi
else
    warn "无法检查管理员账户（psql 不可用或 DATABASE_URL 未设置）"
fi
echo ""

# ---- 6. systemd 服务 ----
echo "[6/6] systemd 服务状态"
SERVICE_NAME="${SERVICE_NAME:-tja-backend}"
if systemctl is-active "$SERVICE_NAME" &>/dev/null; then
    ok "$SERVICE_NAME 服务运行中"
elif systemctl is-enabled "$SERVICE_NAME" &>/dev/null; then
    warn "$SERVICE_NAME 已启用但未运行"
else
    fail "$SERVICE_NAME 服务未配置或不存在"
    echo "       检查: systemctl status $SERVICE_NAME"
    echo "       配置: ls /etc/systemd/system/*.service"
fi
echo ""

# ---- 汇总 ----
echo "================================"
echo "  通过: $PASS  警告: $WARN  失败: $FAIL"
echo "================================"
if [ "$FAIL" -gt 0 ]; then
    echo -e "${R}有 $FAIL 项未通过，请修复后再部署${N}"
    exit 1
else
    echo -e "${G}所有必需项已通过${N}"
    [ "$WARN" -gt 0 ] && echo -e "${Y}有 $WARN 项警告，建议检查${N}"
fi
