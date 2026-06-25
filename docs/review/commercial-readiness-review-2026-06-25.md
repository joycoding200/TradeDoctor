# TradingJournalAnalyzer 商业化就绪度评估报告

**审查日期**: 2026-06-25
**审查方法**: 4 个专项 agent 并行全量代码审查（安全 / 后端可靠性 / 数据库完整性 / 前端体验）

---

## 总体评价

项目核心业务逻辑扎实，金融计算符合行业标准。当前主要短板集中在**数据库完整性和运行时可观测性**两个维度——缺少外键级联、连接池探活、结构化日志等生产环境必备能力。

---

## 🔴 阻断级（上线前必须修复，共 10 项）

### 1. 真实 API Key 硬编码在 .env 中

**文件**: `backend/.env:6-7`
**问题**: `DEEPSEEK_API_KEY` 为真实有效密钥。屏幕分享、备份脚本、IDE 截图均可泄露。
**修复**: 替换为占位符。

### 2. 文件上传大小限制计算错误

**文件**: `backend/app/api/upload.py:31`
**问题**: `10 * 1024 * 100 ≈ 1MB`，注释写 10MB。
**修复**: 改为 `10 * 1024 * 1024` ✅

### 3. dates.index() 在缺失键上崩溃

**文件**: `backend/app/engine/pattern.py:447`
**问题**: 市场数据未覆盖入场日期时 `ValueError` → 500。
**修复**: 添加 `entry_str in symbol_data` 前置检查。

### 4. 所有外键缺少 ON DELETE CASCADE

**文件**: 全部 `backend/app/models/*.py`
**问题**: 10 个外键中仅 `AnalysisFile` 正确配置。删除用户/文件时外键冲突。
**修复**: 添加 `ondelete="CASCADE"` + Alembic 迁移。

### 5. 连接池缺少 pool_pre_ping=True

**文件**: `backend/app/database.py:10-16`
**问题**: PostgreSQL 空闲断开后返回死连接 → `OperationalError`。
**修复**: 添加 `pool_pre_ping=True`。

### 6. Report.validation_passed schema 与模型不匹配

**文件**: `backend/app/models/report.py:23`
**问题**: Pydantic 定义 `bool`（不可空），DB 列无 `nullable=False`。NULL 值时反序列化崩溃。
**修复**: 模型添加 `nullable=False` + 迁移。

### 7. 没有登出/令牌吊销机制

**文件**: `backend/app/auth/jwt.py` + `backend/app/api/auth.py`
**问题**: JWT 签发后 8 小时内无法失效。
**修复**: 添加 `token_blacklist` 表、`POST /api/auth/logout`、`get_current_user` 黑名单检查。

### 8. Cookie secure=False 写死

**文件**: `backend/app/auth/jwt.py:69`
**问题**: 部署 HTTPS 后不会自动启用 `secure` 标志。
**修复**: 从 `ENV` 环境变量推导，生产环境自动为 `True`。

### 9. Login 页 type="email" 拦截手机号

**文件**: `frontend/src/pages/Login.tsx:52`
**问题**: 浏览器 HTML5 校验要求 `@`，手机号用户发不出请求。
**修复**: 改为 `type="text"`。

### 10. 401 重定向竞态条件

**文件**: `frontend/src/api/client.ts:29-32`
**问题**: `onAuthExpired()` 跳转后 `apiFetch` 继续返回 resp，上层 `resp.json()` 抛未捕获错误。
**修复**: 401 时抛 `AuthExpiredError`。

---

## 🟡 高危（首周，12 项）

| # | 维度 | 问题 | 文件 |
|---|------|------|------|
| 11 | 安全 | JWT HS256 对称算法，密钥泄露 = 任意账户伪造 | `jwt.py` |
| 12 | 安全 | JWT 无 `aud` 声明 | `jwt.py` |
| 13 | 安全 | `secret_key` 弱检测——`"dev-secret-key-change-in-production"` 能通过 | `config.py` |
| 14 | 安全 | AI 报告无输出过滤，LLM 含 `<script>` 时可能 XSS | `report.py` |
| 15 | 安全 | admin login 缺少 `_DUMMY_HASH` 时序防护 | `admin.py` |
| 16 | 后端 | 所有 API 路由零日志 | api/*.py |
| 17 | 后端 | `store_bars` 不处理并发 `IntegrityError` | `market_data.py` |
| 18 | 后端 | 市场数据锁进程级而非跨 worker | `market_fetcher.py` |
| 19 | 数据库 | Alembic 初始迁移外键匿名 | `alembic/versions/` |
| 20 | 数据库 | `trades.raw_file_id` 缺少索引 | `trade.py` |
| 21 | 数据库 | 缺失关键索引（symbol/pattern_name/date_range） | models |
| 22 | 数据库 | `created_at` 等无 `nullable=False` + `server_default` | models |

## 🟢 中低危（首月，23 项）

详见完整审查记录。主要类别：密码修改/重置缺失、IP 限流缺陷、前端无障碍（a11y）、无结构化日志、无请求追踪 ID、枚举列缺 CHECK 约束等。

---

## ✅ 亮点

bcrypt + 时序攻击防护（`_DUMMY_HASH`）、Cookie httpOnly+SameSite、React.lazy 代码分割、React Query 合理缓存、部署脚本链（备份/迁移/回滚/健康检查）、边界场景处理（100% 胜率 → PF=∞、小样本不评价）。
