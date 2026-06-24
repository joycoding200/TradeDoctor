# TradingJournalAnalyzer 部署更新指南

## 你的环境

- 阿里云 ECS + PostgreSQL 17（裸机安装）
- 前端：npm run build → nginx 托管 dist/ 静态文件
- 后端：systemd service 托管 FastAPI
- Nginx：80 端口统一入口（静态文件 + /api 反代）
- 代码仓库：GitHub

## 文件说明

```
deploy/
├── update.sh          # 服务器端：一键更新（含前置检查、alembic 安全处理）
├── local-push.sh      # 本地：push + SSH 触发 update.sh
├── config-check.sh    # 服务器端：生产配置完整性校验
├── init-admin.sh      # 管理员账户初始化/更新（shell 包装）
├── init-admin.py      # 管理员账户初始化/更新（Python 实现）
├── deploy.yml         # GitHub Actions 自动部署（可选，复制到 .github/workflows/）
└── README.md          # 本文件
```

## 日常更新流程

本地改完代码，一条命令：

```bash
bash deploy/local-push.sh
```

这条命令会：git push → SSH 到服务器 → 前置检查 → git pull → npm run build → pip install → alembic 迁移 → systemctl restart → 健康检查

整个过程 30-60 秒。

## 你已经在服务器上手动配置的（脚本不会碰）

这些配置在服务器上手动做过，update.sh 不会覆盖它们：

### 1. backend/.env — 环境配置

.env 在 .gitignore 中，git pull 不会覆盖。但 update.sh 会在更新前做前置检查：
- 确认 .env 存在
- 确认 ENV=production
- 检查 .env.example 是否有 .env 中缺少的新配置项（只提醒，不修改）

你的 .env 应该包含这些生产环境专属值（与本地开发不同）：

| 配置项 | 开发环境 | 生产环境 |
|--------|----------|----------|
| ENV | development | production |
| DATABASE_URL | postgresql://localhost:5432/tradelens | postgresql://用户名:生产密码@localhost:5432/tradelens |
| SECRET_KEY | dev-only-... | openssl rand -hex 32 生成的 32+ 字符随机串 |
| CORS_ORIGINS | http://localhost:5173 | http://服务器IP 或 http://域名 |
| AI_PROVIDER | openai | deepseek（推荐，国内速度快） |
| DEEPSEEK_API_KEY | （空） | 你的 DeepSeek API Key |

### 2. 管理员账户

你手动在数据库里创建的 admin 用户（is_admin=True）。update.sh 不会动它。

如果需要重新创建或更新密码，用 init-admin 脚本：

```bash
# 创建管理员（首次部署或新服务器）
bash deploy/init-admin.sh --email admin@你的邮箱.com --password 你的密码123

# 更新管理员密码
bash deploy/init-admin.sh --email admin@你的邮箱.com --password 新密码456 --update
```

### 3. 数据库用户和表结构

你手动创建的 PostgreSQL 用户、数据库、表结构。update.sh 的处理逻辑：

- 如果 alembic_version 表不存在（说明之前用 create_all 建表）：
  → 先执行 alembic stamp head（标记当前状态，不执行任何迁移）
  → 再执行 alembic upgrade head（只执行新增的迁移）
- 如果 alembic_version 表已存在：
  → 直接执行 alembic upgrade head

这样不会因为表已存在而报错。

### 4. uploads/ 目录

用户上传的交割单文件存在 backend/uploads/ 下。

- .gitignore 已添加 backend/uploads/，git pull 不会覆盖
- update.sh 前置检查会确认该目录存在

## 首次配置（做一次就行）

### 1. 确认 .gitignore 已修复

之前 .gitignore 把 deploy/ 排除了，导致部署脚本推不到服务器。已修复：
- 移除了 deploy/（部署脚本现在可以 git push 到服务器）
- 添加了 backend/uploads/（保护用户上传数据）

确认服务器上 deploy/ 目录已通过 git pull 获取到：
```bash
ls deploy/
# 应看到: update.sh  local-push.sh  config-check.sh  init-admin.sh  init-admin.py  deploy.yml  README.md
```

### 2. 配置本地推送脚本

编辑 deploy/local-push.sh，修改顶部三个变量：

```bash
SERVER_USER="root"
SERVER_HOST="47.xxx.xxx.xxx"           # 阿里云公网 IP
PROJECT_PATH="/opt/TradingJournalAnalyzer"  # 服务器上项目路径
```

### 3. 配置服务器端更新脚本

SSH 到服务器，编辑 deploy/update.sh，确认顶部变量：

```bash
SERVICE_NAME="tja-backend"     # 你的 systemd service 名
HEALTH_URL="http://localhost/api/health"
```

不确定 service 名：
```bash
systemctl list-units --type=service | grep -i trad
# 或
ls /etc/systemd/system/*.service
```

### 4. SSH 免密配置

```bash
# 本地生成密钥（已有则跳过）
ssh-keygen -t ed25519

# 推送到服务器
ssh-copy-id root@你的服务器IP
```

### 5. sudo 免密（如果不是 root 用户）

```bash
sudo visudo
# 末尾添加：
#   你的用户名 ALL=(ALL) NOPASSWD: /bin/systemctl restart tja-backend
```

## 运行配置校验

部署前或出问题时，在服务器上运行：

```bash
bash deploy/config-check.sh
```

检查 6 个维度：
1. backend/.env 是否存在
2. ENV / SECRET_KEY / DATABASE_URL / CORS_ORIGINS 是否正确
3. AI 提供商和 API Key 是否配置
4. 数据库连接是否正常
5. 管理员账户是否存在
6. systemd 服务是否运行

## 三种更新方式

### 方式 1：本地一键（日常推荐）

```bash
bash deploy/local-push.sh
```

### 方式 2：手动 SSH

```bash
git push origin main
ssh root@服务器IP
cd /opt/TradingJournalAnalyzer
bash deploy/update.sh
```

### 方式 3：GitHub Actions 全自动

1. GitHub 仓库 Settings → Secrets → Actions，添加：
   - SSH_HOST：服务器 IP
   - SSH_USER：SSH 用户名
   - SSH_KEY：SSH 私钥全文
   - PROJECT_PATH：服务器项目路径

2. 复制 workflow 文件：
```bash
mkdir -p .github/workflows
cp deploy/deploy.yml .github/workflows/deploy.yml
```

3. push 到 main 分支自动触发

## 可选操作

### 只更新后端（跳过前端构建）

```bash
ssh root@服务器IP
cd /opt/TradingJournalAnalyzer
git pull
cd backend && source .venv/bin/activate
pip install -r requirements.txt --quiet
alembic upgrade head 2>/dev/null
sudo systemctl restart tja-backend
curl -sf http://localhost/api/health
```

### 回滚

```bash
cd /opt/TradingJournalAnalyzer
git log --oneline -5
git reset --hard HEAD~1

cd frontend && npm run build && cd ..
cd backend && source .venv/bin/activate
# 如需回滚迁移：alembic downgrade -1
sudo systemctl restart tja-backend
```

### 数据库备份

```bash
# 手动备份
pg_dump -U postgres tradelens > backup_$(date +%Y%m%d).sql

# 自动备份（crontab -e）
0 2 * * * pg_dump -U postgres tradelens > /opt/backups/tradelens_$(date +\%Y\%m\%d).sql
```

### HTTPS 配置

如果有域名，建议配 HTTPS：

```bash
# 停止 nginx 释放 80 端口
systemctl stop nginx

# 申请证书
certbot certonly --standalone -d your-domain.com

# 修改 nginx 配置添加 443 server 块
# 修改 backend/.env 中 CORS_ORIGINS 为 https://your-domain.com

# 证书自动续期（crontab -e）
0 3 * * 1 certbot renew --quiet && systemctl reload nginx
```

注意：配了 HTTPS 后，backend/app/auth/jwt.py 中的 `secure=False` 应改为 `secure=True`。
