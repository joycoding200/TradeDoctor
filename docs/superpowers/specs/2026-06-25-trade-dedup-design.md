# 交割单去重设计

**日期**: 2026-06-25
**状态**: 已确认

## 1. 问题

用户多次上传同一份交割单（文件名不同但内容/交易记录相同）或有重叠交易记录的交割单时，系统当前无脑叠加，导致：
- 同一笔交易被重复计数
- 分析指标（胜率、盈亏、PF 等）失真
- 持仓重建产生错误的加仓判定

## 2. 设计决策

| 决策点 | 选择 |
|---|---|
| 去重策略 | 自动跳过 + 统计提示 |
| 去重范围 | 用户级别全局（跨所有分析） |
| 文件级重复 | 硬拦截（阻止上传） |

## 3. 去重架构

两层去重：

### 3.1 文件级（上传时）

- **时机**: `POST /api/upload` 
- **方法**: 计算上传文件内容的 SHA256，存到 `RawFile.content_hash`
- **检查**: 查询该用户是否已有相同 `content_hash` 的 RawFile
- **行为**: 重复 → 返回 HTTP 409，提示"此文件已上传过"
- **边界**: 文件名不同但内容相同 → 能检测；内容稍有差异（空格/换行符差异）→ **不能**检测，走交易级去重兜底

### 3.2 交易级（导入时）

- **时机**: `POST /api/upload/import`
- **唯一键**: `(datetime, symbol, exchange, side, quantity, price)`
  - `commission` 不纳入——同一笔交易不同券商导出时费用可能有微小差异
  - 精确匹配，不做浮点容差——数据来自同一数据源，值应完全一致
- **方法**: 批量查询用户全局现有 Trade 表，提取唯一键集合，内存比对
- **行为**: 
  - 全部重复 → 返回 `{imported_count: 0, skipped_count: N}`
  - 部分重复 → 只写入新交易，返回 `{imported_count: N, skipped_count: M}`
  - 全部新 → 正常写入，`skipped_count: 0`

### 3.3 边界情况

| 场景 | 处理 |
|---|---|
| 用户清空数据后重新上传同一文件 | `clear_trades()` 删除 Trade + RawFile，content_hash 随之删除，允许重新上传 |
| 同一文件被两个用户上传 | `content_hash` 仅在同一 user_id 下检查，不同用户互不干扰 |
| 导入时全部交易都是重复 | 正常返回 `imported_count: 0`，不视为错误 |
| 交易量很大（>10万笔） | 批量查询 + 内存 set，用户级别数据量可控 |

## 4. 实现变更

### 4.1 数据库

```sql
ALTER TABLE raw_files ADD COLUMN content_hash VARCHAR(64);
CREATE INDEX ix_raw_files_user_content_hash ON raw_files (user_id, content_hash);
```

### 4.2 后端

**`backend/app/models/raw_file.py`** — 新增字段：
```python
content_hash = Column(String(64), nullable=True, index=True)
```

**`backend/app/schemas/upload.py`** — 扩展 ImportResponse：
```python
class ImportResponse(BaseModel):
    imported_count: int
    skipped_count: int = 0
```

**`backend/app/api/upload.py`** — 两处修改：

1. `upload_file()`: 计算 SHA256 → 查询已有 → 409 或继续
2. `import_trades()`: 解析后 → 构建唯一键 → 查询全局已有 → 过滤 → 返回计数

### 4.3 前端

**`frontend/src/pages/Upload.tsx`** — `autoProcess()` 中读取 `importTrades()` 返回值，展示 toast：
- `skipped_count > 0` → "已导入 N 笔交易，跳过 M 笔重复记录"
- `imported_count === 0` → 提示"所有交易记录已存在，无需重复导入"

**`frontend/src/components/AddFileModal.tsx`** — 同上

### 4.4 数据库迁移

使用 Alembic 自动生成迁移脚本。

## 5. 测试要点

- [ ] 上传完全相同内容的文件 → 409
- [ ] 上传相同文件名不同内容的文件 → 正常
- [ ] 导入与已有交易完全重复的数据 → imported_count=0
- [ ] 导入部分重复的数据 → 正确计数
- [ ] 导入完全新的数据 → skipped_count=0
- [ ] clear_trades 后可以重新上传之前的文件
- [ ] 不同用户上传相同文件互不干扰
