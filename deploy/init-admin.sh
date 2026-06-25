#!/bin/bash
# ============================================================
# TradeDoctor — 管理员账户初始化（shell 包装）
# ============================================================
# 用法：
#   bash deploy/init-admin.sh --email admin@example.com --password YourPass123
#   bash deploy/init-admin.sh --email admin@example.com --password NewPass456 --update
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR/backend"

# 激活虚拟环境
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
elif [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    echo "[warn] 未找到虚拟环境，使用系统 Python"
fi

python "$PROJECT_DIR/deploy/init-admin.py" "$@"
