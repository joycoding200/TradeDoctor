# TradingJournalAnalyzer 部署指南

## 你的环境

- 阿里云轻量应用服务器 + 宝塔面板
- 前端：本地构建 → rsync 上传 → nginx 托管 dist/ 静态文件
- 后端：systemd service 托管 FastAPI（uvicorn）
- Nginx：80 端口统一入口（静态文件 + /api 反代）
- 数据库：PostgreSQL 17
- 代码仓库：GitHub

## 文件说明

```
deploy/
├── server-setup.sh    # 首次安装：一键配好 PG + Python + venv + systemd
├── local-deploy.sh    # 日常部署（推荐）：本地 build + rsync + SSH 触发
├── local-push.sh      # 旧版部署：git push + 服务器 build（保留兼容）
├── update.sh          # 服务器端更新：含备份、迁移、健康检查
├── config-check.sh    # 生产配置校验：6 维检查
├── init-admin.sh      # 管理员账户初始化（shell 包装）
├── init-admin.py      # 管理员账户初始化（Python 实现）
├── nginx-tja.conf     # Nginx 配置模板（或用宝塔面板配置）
├── deploy.yml         # GitHub Actions 自动部署（可选）
└── README.md          # 本文件
```

## 首次部署（从零开始）

### 前提：服务器已有宝塔面板

宝塔面板提供了 nginx，你不需要单独装 nginx。

### 步骤 1：SSH 到服务器，克隆代码并执行首次安装

```bash
ssh root@你的服务器IP

# 克隆项目
cd /opt
git clone https://github.com/joycoding200/TradingJournalAnalyzer.git
cd TradingJournalAnalyzer

# 执行首次安装脚本
bash deploy/server-setup.sh
```

这个脚本会自动完成：
1. 安装系统依赖（Python、编译工具、rsync）
2. 安装 PostgreSQL 17
3. 创建数据库 tradelens 和用户
4. 创建 Python 虚拟环境 + 安装后端依赖
5. 生成 backend/.env（含随机密钥）
6. 初始化数据库表
7. 创建 systemd 服务
8. 启动后端并健康检查

安装完成后，脚本会输出数据库密码和后续步骤提示。

### 步骤 2：配置 .env

```bash
vim /opt/TradingJournalAnalyzer/backend/.env
```

确认以下配置（脚本已自动生成，你只需补填 API Key）：

| 配置项 | 值 | 说明 |
|--------|-----|------|
| DATABASE_URL | postgresql://tradelens:密码@localhost:5432/tradelens | 脚本已生成 |
| SECRET_KEY | 64 字符随机串 | 脚本已生成 |
| ENV | production | 脚本已设置 |
| CORS_ORIGINS | http://服务器IP | 脚本已生成 |
| AI_PROVIDER | deepseek | 脚本已设置 |
| DEEPSEEK_API_KEY | 你的 Key | **需要手动填入** |

填完后重启后端使配置生效：
```bash
systemctl restart tja-backend
```

### 步骤 3：创建管理员账户

```bash
cd /opt/TradingJournalAnalyzer
ADMIN_PASSWORD=你的密码123 bash deploy/init-admin.sh --email admin@你的邮箱.com
```

### 步骤 4：配置 Nginx

**方式 A：宝塔面板（推荐）**

1. 宝塔面板 → 网站 → 添加站点
2. 域名填：你的服务器 IP（或域名）
3. 根目录设为：`/opt/TradingJournalAnalyzer/frontend/dist`
4. 设置 → 反向代理 → 添加：
   - 代理名称：tja-api
   - 目标URL：`http://127.0.0.1:8000`
   - 发送域名：`$host`
5. 设置 → 配置文件，在 location / 下添加：
   ```nginx
   location / {
       try_files $uri $uri/ /index.html;
   }
   ```

**方式 B：手动配置**

```bash
cp deploy/nginx-tja.conf /etc/nginx/conf.d/tja.conf
# 编辑 server_name 和 root 路径
vim /etc/nginx/conf.d/tja.conf
nginx -t && nginx -s reload
```

### 步骤 5：本地构建并上传前端

在你的本地电脑（不是服务器）：

```bash
cd frontend
npm install
npm run build
rsync -avz --delete dist/ root@你的服务器IP:/opt/TradingJournalAnalyzer/frontend/dist/
```

### 步骤 6：验证

```bash
# 服务器上
curl http://localhost/api/health
# 应返回 {"status":"ok"}

# 浏览器打开
http://你的服务器IP/
```

---

## 日常更新流程

### 方式 1：本地构建 + rsync（推荐，最快）

本地改完代码，一条命令：

```bash
bash deploy/local-deploy.sh
```

流程：本地 npm run build → rsync dist/ 到服务器 → git push → SSH 触发 update.sh

特点：服务器不需要 Node.js，10-20 秒完成。

可选参数：
```bash
bash deploy/local-deploy.sh --skip-build  # dist/ 已是最新，跳过构建
bash deploy/local-deploy.sh --no-push     # 不 push，只部署当前 dist/
bash deploy/local-deploy.sh --branch dev  # 部署 dev 分支
```

首次使用前，编辑 `deploy/local-deploy.sh` 修改顶部变量：
```bash
SERVER_USER="root"
SERVER_HOST="47.xxx.xxx.xxx"
PROJECT_PATH="/opt/TradingJournalAnalyzer"
```

### 方式 2：服务器端构建（旧版，兼容保留）

```bash
bash deploy/local-push.sh
```

流程：git push → SSH → 服务器 npm build → pip install → alembic → restart

特点：服务器需要 Node.js，30-60 秒完成。

### 方式 3：手动 SSH

```bash
git push origin main
ssh root@服务器IP
cd /opt/TradingJournalAnalyzer
bash deploy/update.sh --skip-frontend  # 前端已通过 rsync 上传
```

### 方式 4：GitHub Actions 全自动

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

---

## 服务器上脚本不会碰的配置

这些配置在服务器上手动做过，脚本不会覆盖：

### 1. backend/.env

.env 在 .gitignore 中，git pull 不会覆盖。update.sh 会在更新前做前置检查。

### 2. 管理员账户

手动创建的 admin 用户。如需重置密码：
```bash
bash deploy/init-admin.sh --email admin@你的邮箱.com --password 新密码456 --update
```

### 3. uploads/ 目录

用户上传的交割单文件，.gitignore 已排除。

---

## 可选操作

### 配置校验

```bash
bash deploy/config-check.sh
```

检查 6 个维度：.env、关键配置项、AI 配置、数据库连接、管理员账户、systemd 服务。

### 回滚

```bash
cd /opt/TradingJournalAnalyzer
git log --oneline -5
git reset --hard HEAD~1

# 如需回滚迁移
cd backend && source .venv/bin/activate
alembic downgrade -1

sudo systemctl restart tja-backend
```

### 数据库备份

update.sh 已自动在每次迁移前备份到 `/opt/backups/`，保留最近 7 个。

手动备份：
```bash
pg_dump -U postgres tradelens > backup_$(date +%Y%m%d).sql
```

自动备份（crontab -e）：
```
0 2 * * * pg_dump -U postgres tradelens > /opt/backups/tradelens_$(date +\%Y\%m\%d).sql
```

### HTTPS 配置

**方式 A：宝塔面板（推荐）**

宝塔面板 → 网站 → 你的站点 → SSL → Let's Encrypt → 申请

**方式 B：手动**

```bash
systemctl stop nginx
certbot certonly --standalone -d your-domain.com
# 修改 nginx 配置添加 443 server 块
# 修改 backend/.env 中 CORS_ORIGINS 为 https://your-domain.com
systemctl start nginx
```

注意：配了 HTTPS 后，backend/app/auth/jwt.py 中的 `secure=False` 应改为 `secure=True`。

---

## SSH 免密配置

```bash
# 本地生成密钥（已有则跳过）
ssh-keygen -t ed25519

# 推送到服务器
ssh-copy-id root@你的服务器IP
```

## 防火墙

宝塔面板 → 安全 → 放行端口：
- 80（HTTP）
- 443（HTTPS，如配了 SSL）
- 22（SSH）

**不要**放行 8000 端口（后端只通过 nginx 反代访问）。
