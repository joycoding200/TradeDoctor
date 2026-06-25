# 交割单去重 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在交割单上传和导入阶段增加两层去重（文件级 SHA256 + 交易级唯一键），自动跳过重复交易并通知用户。

**Architecture:** 两层去重——upload_file() 阶段比对文件内容哈希（硬拦截），import_trades() 阶段比对交易唯一键（自动跳过+计数）。去重范围为用户级别全局。

**Tech Stack:** Python 3.11+ / FastAPI / SQLAlchemy / Alembic / React 18 / TypeScript

## Global Constraints

- 交易唯一键: `(datetime, symbol, exchange, side, quantity, price)`，不含 commission
- 文件哈希: SHA256，仅在同一 user_id 下检查
- 去重范围: 用户级别全局（跨所有分析）
- 文件级重复: HTTP 409 硬拦截
- 交易级重复: 自动跳过 + 返回 skipped_count
- 浮点数精确匹配，不做容差

---

### Task 1: RawFile 模型新增 content_hash 字段

**Files:**
- Modify: `backend/app/models/raw_file.py`

**Interfaces:**
- Produces: `RawFile.content_hash: Column(String(64), nullable=True, index=True)`

- [ ] **Step 1: 添加 content_hash 字段**

在 `RawFile` 类中添加 `content_hash` 列，位于 `file_size` 之后：

```python
# 在 file_size = Column(...) 之后新增：
content_hash = Column(String(64), nullable=True)  # SHA256 hex digest
```

完整修改后的 `RawFile.__tablename__` 体：

```python
class RawFile(Base):
    __tablename__ = "raw_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename = Column(String(500), nullable=False)
    source_type = Column(String(50), nullable=True)
    asset_type = Column(String(20), nullable=True)
    file_path = Column(String(1000), nullable=True)
    file_size = Column(Integer, nullable=True)
    content_hash = Column(String(64), nullable=True)
    uploaded_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
        server_default=sa.func.now()
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/raw_file.py
git commit -m "feat: add content_hash column to RawFile model"
```

---

### Task 2: 数据库迁移 — 添加 content_hash 列和索引

**Files:**
- Create: `backend/alembic/versions/<auto>_add_content_hash_to_raw_files.py`

**Interfaces:**
- Produces: `raw_files.content_hash VARCHAR(64)` 列 + `ix_raw_files_user_content_hash` 索引

- [ ] **Step 1: 用 Alembic 自动生成迁移**

```bash
cd backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate
alembic revision --autogenerate -m "add_content_hash_to_raw_files"
```

- [ ] **Step 2: 验证生成的迁移文件**

检查生成的迁移文件包含：
1. `op.add_column('raw_files', sa.Column('content_hash', sa.String(64), nullable=True))`
2. `op.create_index('ix_raw_files_user_content_hash', 'raw_files', ['user_id', 'content_hash'])`

如果 autogenerate 没有生成复合索引，手动补充到 `upgrade()`：

```python
def upgrade() -> None:
    # 添加 content_hash 列
    op.add_column('raw_files', sa.Column('content_hash', sa.String(length=64), nullable=True))
    # 创建复合索引（去重查询用）
    op.create_index('ix_raw_files_user_content_hash', 'raw_files', ['user_id', 'content_hash'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_raw_files_user_content_hash', table_name='raw_files')
    op.drop_column('raw_files', 'content_hash')
```

- [ ] **Step 3: 应用迁移**

```bash
alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: add content_hash migration for raw_files dedup"
```

---

### Task 3: UploadResponse Schema 扩展

**Files:**
- Modify: `backend/app/schemas/upload.py`

**Interfaces:**
- Produces: `ImportResponse.skipped_count: int = 0`

- [ ] **Step 1: 修改 ImportResponse**

```python
# 在 backend/app/schemas/upload.py 中，将 ImportResponse 改为：
class ImportResponse(BaseModel):
    imported_count: int
    skipped_count: int = 0
```

不要触碰文件中其他 schema 类。

- [ ] **Step 2: 添加用于文件级重复的警告提示**

不需要新增 schema 字段——文件级重复直接返回 HTTP 409，FastAPI 会自动序列化 `detail` 字段。Response 模型不变。

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/upload.py
git commit -m "feat: add skipped_count to ImportResponse schema"
```

---

### Task 4: upload_file() — 文件级 SHA256 去重

**Files:**
- Modify: `backend/app/api/upload.py` — `upload_file()` 函数

**Interfaces:**
- Consumes: `RawFile.content_hash`
- Produces: HTTP 409 on duplicate file content

- [ ] **Step 1: 添加 hashlib import**

在文件顶部 import 区域添加：

```python
import hashlib
```

- [ ] **Step 2: 在 upload_file() 中增加哈希检查**

在 `content = file.file.read(MAX_UPLOAD_BYTES + 1)` 之后、`raw_file = RawFile(...)` 之前，插入哈希计算和检查逻辑：

```python
    # Read with size cap to prevent OOM (read 1 byte more to detect overflow)
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    # 计算内容哈希，检查是否重复上传
    content_hash = hashlib.sha256(content).hexdigest()
    existing = (
        db.query(RawFile)
        .filter(
            RawFile.user_id == current_user.id,
            RawFile.content_hash == content_hash,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"此文件已上传过（文件名：{existing.filename}），请勿重复上传。",
        )

    raw_file = RawFile(
        user_id=current_user.id,
        filename=filename,
        content_hash=content_hash,
    )
```

注意：`RawFile()` 构造函数和 `raw_file.content_hash = content_hash` 都需要。

完整修改后 `upload_file()` 中 RawFile 的创建逻辑：

```python
    raw_file = RawFile(
        user_id=current_user.id,
        filename=filename,
        content_hash=content_hash,
    )
    db.add(raw_file)
    db.flush()
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/upload.py
git commit -m "feat: add SHA256 content hash check on file upload"
```

---

### Task 5: import_trades() — 交易级唯一键去重

**Files:**
- Modify: `backend/app/api/upload.py` — `import_trades()` 函数

**Interfaces:**
- Consumes: `Trade` 表（用户全局已有交易）
- Produces: `ImportResponse(imported_count, skipped_count)`

- [ ] **Step 1: 替换 import_trades() 函数体**

将 `import_trades()` 中解析之后、返回之前的部分改为带去重的版本：

```python
@router.post("/import", response_model=ImportResponse)
def import_trades(
    body: ImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Parse confirmed file and save all trades to the database."""
    raw_file = (
        db.query(RawFile)
        .filter(RawFile.id == body.raw_file_id, RawFile.user_id == current_user.id)
        .first()
    )
    if not raw_file:
        raise HTTPException(status_code=404, detail="Raw file not found")
    if not raw_file.source_type:
        raise HTTPException(
            status_code=400, detail="Source type not set. Confirm format first."
        )

    parser_cls = ParserRegistry.get_parser(raw_file.source_type)
    if not parser_cls:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source type: {raw_file.source_type}",
        )

    content = _read_raw_content(raw_file)
    trades = parser_cls.parse(content, raw_file.filename)

    if not trades:
        return ImportResponse(imported_count=0, skipped_count=0)

    # 构建本次导入交易唯一键集合 (datetime, symbol, exchange, side, qty, price)
    incoming_keys = {
        (
            t.datetime.replace(microsecond=0),
            t.symbol,
            t.exchange,
            t.side,
            t.quantity,
            t.price,
        )
        for t in trades
    }

    # 批量查询用户全局已有交易，构建已有唯一键集合
    existing_rows = (
        db.query(
            Trade.datetime,
            Trade.symbol,
            Trade.exchange,
            Trade.side,
            Trade.quantity,
            Trade.price,
        )
        .filter(
            Trade.user_id == current_user.id,
            Trade.is_deleted.is_(False),
        )
        .all()
    )
    existing_keys = {
        (dt.replace(microsecond=0), sym, ex, side, qty, price)
        for dt, sym, ex, side, qty, price in existing_rows
    }

    # 过滤：只写入新交易
    imported = 0
    skipped = 0
    for t in trades:
        key = (
            t.datetime.replace(microsecond=0),
            t.symbol,
            t.exchange,
            t.side,
            t.quantity,
            t.price,
        )
        if key in existing_keys:
            skipped += 1
            continue
        db.add(
            Trade(
                raw_file_id=raw_file.id,
                user_id=current_user.id,
                asset_type=raw_file.asset_type or parser_cls.asset_type(),
                datetime=t.datetime,
                symbol=t.symbol,
                exchange=t.exchange,
                side=t.side,
                quantity=t.quantity,
                price=t.price,
                commission=t.commission,
                margin=t.margin,
                multiplier=t.multiplier,
            )
        )
        existing_keys.add(key)  # 同文件内去重
        imported += 1

    if imported > 0:
        db.commit()

    return ImportResponse(imported_count=imported, skipped_count=skipped)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/upload.py
git commit -m "feat: add trade-level dedup on import based on unique key"
```

---

### Task 6: 前端 — Upload.tsx 展示去重结果

**Files:**
- Modify: `frontend/src/pages/Upload.tsx`

- [ ] **Step 1: 修改 autoProcess() 中的 importTrades 调用**

将第 32 行 `await importTrades(fileId);` 改为：

```typescript
    setStatusText("正在导入交易记录...");
    const importResult = await importTrades(fileId);
    const { imported_count, skipped_count } = importResult;

    if (skipped_count > 0) {
      toast.addToast(
        "info",
        `已导入 ${imported_count} 笔交易，跳过 ${skipped_count} 笔重复记录`
      );
    }
```

完整修改后的 `autoProcess()` 函数：

```typescript
  const autoProcess = async (fileId: string, sourceType: string, fileName: string) => {
    setStatusText("正在解析交易记录...");
    const confirmed = await confirmFormat(fileId, sourceType);
    const trades = confirmed.trades || [];

    setStatusText("正在导入交易记录...");
    const importResult = await importTrades(fileId);
    const { imported_count, skipped_count } = importResult;

    if (skipped_count > 0) {
      toast.addToast(
        "info",
        `已导入 ${imported_count} 笔交易，跳过 ${skipped_count} 笔重复记录`
      );
    }

    if (attachToAnalysisId) {
      // 如果全部是重复交易 (imported_count === 0)，仍允许添加到分析
      setStatusText("正在添加到分析...");
      await linkFilesToAnalysis(attachToAnalysisId, [fileId]);
      toast.addToast("success", "文件已添加到分析");
      navigate(`/analysis/${attachToAnalysisId}`);
    } else {
      setStatusText("正在运行分析...");
      const dates = trades
        .map((t: any) => t.datetime)
        .filter(Boolean)
        .sort();
      const today = new Date().toISOString().split("T")[0];
      const dateStart = dates[0]?.split("T")[0] || "2020-01-01";
      const dateEnd = dates[dates.length - 1]?.split("T")[0] || today;
      const analysis = await runAnalysis(dateStart, dateEnd, fileId, fileName);
      toast.addToast("success", "分析完成");
      navigate(`/analysis/${analysis.analysis_id}`);
    }
  };
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Upload.tsx
git commit -m "feat: show skipped duplicate count on upload page"
```

---

### Task 7: 前端 — AddFileModal.tsx 展示去重结果

**Files:**
- Modify: `frontend/src/components/AddFileModal.tsx`

- [ ] **Step 1: 修改 processFile() 中的 importTrades 调用**

将第 78 行 `await importTrades(result.raw_file_id);` 改为：

```typescript
      setStatus("正在导入交易记录...");
      const importResult = await importTrades(result.raw_file_id);
      const { imported_count, skipped_count } = importResult;

      if (skipped_count > 0) {
        toast.addToast(
          "info",
          `已导入 ${imported_count} 笔交易，跳过 ${skipped_count} 笔重复记录`
        );
      }
```

完整修改后的 `processFile()` 函数：

```typescript
  const processFile = async (file: File) => {
    setLoading(true);
    try {
      setStatus("正在上传文件...");
      const result = await uploadFile(file);
      const formats = result.detected_formats || [];
      if (formats.length === 0) {
        toast.addToast("warning", "无法识别文件格式");
        setLoading(false);
        return;
      }

      const sourceType = formats[0].source_type;
      setStatus("正在解析交易记录...");
      await confirmFormat(result.raw_file_id, sourceType);

      setStatus("正在导入交易记录...");
      const importResult = await importTrades(result.raw_file_id);
      const { imported_count, skipped_count } = importResult;

      if (skipped_count > 0) {
        toast.addToast(
          "info",
          `已导入 ${imported_count} 笔交易，跳过 ${skipped_count} 笔重复记录`
        );
      }

      setStatus("正在添加到分析...");
      await linkFilesToAnalysis(analysisId, [result.raw_file_id]);

      toast.addToast("success", "文件已添加到分析");
      onSuccess();
      onClose();
    } catch (err) {
      toast.addToast("error", err instanceof Error ? err.message : "添加失败");
      setLoading(false);
    }
  };
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/AddFileModal.tsx
git commit -m "feat: show skipped duplicate count in add-file modal"
```

---

### Task 8: 测试 — 去重逻辑验证

**Files:**
- Modify: `backend/tests/test_api/test_upload.py`

- [ ] **Step 1: 添加文件级去重测试**

在 `TestUploadErrors` 类末尾添加：

```python
    def test_upload_duplicate_file_returns_409(self, client):
        """上传内容完全相同的文件应返回 409"""
        headers = get_auth_header(client)

        # 第一次上传
        r1 = client.post(
            "/api/upload",
            headers=headers,
            files={"file": ("dup.csv", QMT_CSV, "text/csv")},
        )
        assert r1.status_code == 200

        # 第二次上传相同内容（文件名不同）
        r2 = client.post(
            "/api/upload",
            headers=headers,
            files={"file": ("dup_renamed.csv", QMT_CSV, "text/csv")},
        )
        assert r2.status_code == 409
        assert "已上传过" in r2.json()["detail"]
```

- [ ] **Step 2: 添加交易级去重测试**

继续添加：

```python
    def test_import_skips_duplicate_trades(self, client):
        """导入与已有交易重复的数据时，应跳过并返回正确计数"""
        headers = get_auth_header(client)

        # 第一次上传 + 导入
        r1 = client.post(
            "/api/upload",
            headers=headers,
            files={"file": ("batch1.csv", QMT_CSV, "text/csv")},
        )
        fid1 = r1.json()["raw_file_id"]
        client.post(
            "/api/upload/confirm",
            headers=headers,
            json={"raw_file_id": fid1, "source_type": "smart"},
        )
        imp1 = client.post(
            "/api/upload/import",
            headers=headers,
            json={"raw_file_id": fid1},
        )
        assert imp1.json()["imported_count"] == 4
        assert imp1.json()["skipped_count"] == 0

        # 第二次上传完全相同的数据，换文件名
        r2 = client.post(
            "/api/upload",
            headers=headers,
            files={"file": ("batch2.csv", QMT_CSV, "text/csv")},
        )
        # 注意：文件级去重按 content_hash，若内容完全相同则 409
        # 这里测试内容不同（换行差异）但交易记录相同的场景
        # 换一个稍微不同的内容绕过文件级去重
        slightly_different = QMT_CSV + "\n"  # 多一个换行
        r2 = client.post(
            "/api/upload",
            headers=headers,
            files={"file": ("batch2.csv", slightly_different, "text/csv")},
        )
        fid2 = r2.json()["raw_file_id"]
        client.post(
            "/api/upload/confirm",
            headers=headers,
            json={"raw_file_id": fid2, "source_type": "smart"},
        )
        imp2 = client.post(
            "/api/upload/import",
            headers=headers,
            json={"raw_file_id": fid2},
        )
        assert imp2.json()["imported_count"] == 0
        assert imp2.json()["skipped_count"] == 4

    def test_import_partial_duplicate_trades(self, client):
        """部分重复：新交易写入，重复交易跳过"""
        headers = get_auth_header(client)

        # 先导入 4 笔
        r1 = client.post(
            "/api/upload",
            headers=headers,
            files={"file": ("p1.csv", QMT_CSV, "text/csv")},
        )
        fid1 = r1.json()["raw_file_id"]
        client.post(
            "/api/upload/confirm",
            headers=headers,
            json={"raw_file_id": fid1, "source_type": "smart"},
        )
        client.post(
            "/api/upload/import",
            headers=headers,
            json={"raw_file_id": fid1},
        )

        # 再导入含 2 笔新 + 2 笔重复的数据
        mixed_csv = (
            "委托时间,证券代码,证券名称,买卖方向,成交价格,成交数量,手续费\n"
            "2024-01-05 09:30:00,000001,平安银行,买入,10.50,1000,5.00\n"   # 重复
            "2024-01-10 14:00:00,000001,平安银行,卖出,11.00,1000,5.00\n"   # 重复
            "2024-03-01 09:30:00,000002,万科A,买入,15.00,500,2.50\n"       # 新
            "2024-03-05 14:00:00,000002,万科A,卖出,16.00,500,2.50"          # 新
        )
        r2 = client.post(
            "/api/upload",
            headers=headers,
            files={"file": ("p2.csv", mixed_csv, "text/csv")},
        )
        fid2 = r2.json()["raw_file_id"]
        client.post(
            "/api/upload/confirm",
            headers=headers,
            json={"raw_file_id": fid2, "source_type": "smart"},
        )
        imp2 = client.post(
            "/api/upload/import",
            headers=headers,
            json={"raw_file_id": fid2},
        )
        assert imp2.json()["imported_count"] == 2
        assert imp2.json()["skipped_count"] == 2

    def test_different_users_same_file_no_conflict(self, client):
        """不同用户上传相同文件互不干扰"""
        # 用户 A 上传
        headers_a = get_auth_header(client)

        # 注册并获取用户 B 的 token
        resp_b = client.post(
            "/api/auth/register",
            json={"email": "user_b@test.com", "password": "Test1234"},
        )
        token_b = resp_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # A 上传
        r_a = client.post(
            "/api/upload",
            headers=headers_a,
            files={"file": ("shared.csv", QMT_CSV, "text/csv")},
        )
        assert r_a.status_code == 200

        # B 上传相同内容
        r_b = client.post(
            "/api/upload",
            headers=headers_b,
            files={"file": ("shared.csv", QMT_CSV, "text/csv")},
        )
        assert r_b.status_code == 200  # 不同用户，不冲突
```

- [ ] **Step 3: 运行测试验证**

```bash
cd backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pytest tests/test_api/test_upload.py -v
```

期望：所有测试通过，尤其是新增的 4 个去重测试。

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_api/test_upload.py
git commit -m "test: add dedup tests for file hash and trade key dedup"
```

---

### Task 9: 端到端验证

- [ ] **Step 1: 启动后端和前端**

```bash
# 终端 1 — 后端
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2 — 前端
cd frontend
npm run dev
```

- [ ] **Step 2: 手动测试场景**

| 场景 | 预期结果 |
|---|---|
| 上传文件 A → 再次上传文件 A（相同内容） | 409 "此文件已上传过" |
| 上传文件 A → 导入 → 上传内容不同但交易相同的文件 B | toast "跳过 N 笔重复记录" |
| 上传文件 A → 导入 → 清空数据 → 上传文件 A | 200 正常（数据已清） |
| 上传含新+旧交易的文件 | imported=N, skipped=M, 指标只基于新+旧 |

- [ ] **Step 3: 验证前端 toast 提示**

确保 `Upload.tsx` 和 `AddFileModal.tsx` 都正确显示去重提示。

