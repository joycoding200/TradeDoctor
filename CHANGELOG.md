# 变更日志

本项目所有重要变更记录在此文件中。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [V1.1.0] — 2026-06-27

### 概述

本版本是一次**深度代码审查与质量加固**，起因是用户报告的「生成 AI 报告后返回分析面板数据丢失」故障。围绕该故障定位根因后，顺藤摸瓜展开全量审查，按用户操作路径（认证→上传→分析→查看→AI 报告→案例库→管理）补全了所有缺失测试，清理了死代码，并追查修复了 3 个此前潜伏的 bug。新增 63 个测试，全量 398 passed / 0 failed。

### 修复的 Bug

#### 1. 分析面板数据丢失（422 ValidationError）—— 本次审查的起点

**现象**：用户在服务器上上传交割单 → 看分析面板正常 → 生成 AI 报告 → 返回分析面板 → 页面报错看不到数据 → 点历史报告再进仍看不到。

**根因**：`get_stats` 端点的两个路径写入的快照不一致：
- 快路径 `StatsResponse(**analysis.stats_snapshot)` 要求 40 个字段（含必填 `positions`/`max_win`/`max_loss`/`consecutive_losses`）
- 慢路径（`analysis.py` 旧 line 449-463）只保存 **12 个字段**的 dict

当 `run_analysis` 的 `compute_all` 在服务器上因 mootdx TCP 异常失败时，快照保持 `None`；首次 `get_stats` 走慢路径返回完整数据（用户看到正常）**+ 用 12 字段不完整快照覆盖**；第二次走快路径 → `StatsResponse(**12字段)` 缺必填字段 → ValidationError → 422 → 前端显示"加载失败"，快照被永久污染。

**修复**：
- `get_stats` 慢路径改为存完整的 `response.model_dump()`（而非手写 12 字段 dict）
- `run_analysis` 的 `except` 块新增 `db.rollback()`（失败后 session 污染是 pre-existing 缺陷，导致后续查询全部 `PendingRollbackError`），且 `aid` 在 try 前捕获（避免在 poisoned session 上访问 `analysis.id` 再次崩溃）
- `link_files_to_analysis` 删除冗余的第二次清空+commit（双重清空无意义）
- `MarketDataCache.store_bars` 的 SQLite 路径原本假设所有 bars 同一 symbol（`symbol = bars[0]["symbol"]`），且不处理 within-batch 重复 → 多 symbol 场景漏存 + mootdx 分页重复触发 UNIQUE 冲突。改为按 `(symbol, date)` 元组去重，与 PostgreSQL 的 `ON CONFLICT DO NOTHING` 语义一致

#### 2. 追加交割单后 date 范围未更新

**根因**：`link_files_to_analysis` 在 `db.add(AnalysisFile(...))` 后调用 `get_raw_file_ids` 查询，但测试环境 `autoflush=False`，查不到未提交的新行 → `date_start/end` 不扩展到新文件的交易日期。

**修复**：查询前显式 `db.flush()`。被新测试 `test_link_files_adds_files_and_invalidates_snapshot` 抓出。

#### 3. 上传去重拒绝重传（409 Conflict）

**现象**：两个测试（`test_reimporting_same_statement_does_not_double_count`、`test_multiple_contributions_add_rows`）长期失败，经 stash 对比确认在干净 master 上也失败。

**根因**：`upload_file` 检测到相同 sha256 内容时返回 **409 拒绝**，而非幂等返回已有文件。用户误传同一交割单（改名重传）会被拒绝，无法继续。

**修复**：检测到重复 hash 时**幂等返回已有 RawFile 的 id**。`import_trades` 本身已做交易去重，`_load_trades` 按 `raw_file_id` 过滤，不会双倍计数。

#### 4. AI 报告与 Insight 面板数据源不一致

**根因**：`report.py` 用 `InsightEngine.analyze`（单主模式：每笔交易只归一个主模式，按 `total_pnl` 原始值排序，无样本量门槛），而 `/insight` 面板用 `analyze_by_category`（多桶：每笔交易归入所有匹配模式，按 `total_pnl * log(count)/log(5)` 加权排序，`best_pattern` 还要 `count>=5` 过滤）。

**用户可见影响**：AI 报告可能把 `count=1` 的高盈利模式列为"最佳"，而面板因 `count<5` 过滤掉它，显示另一个模式。

**修复**：`report.py` 改用 `compute_insight`（与面板/`compute_all` 同一数据源），AI 报告与 `/insight` 面板用完全相同的 insight 数据。删除未使用的 `InsightEngine` import。

### 测试补全（新增 63 个测试，6 个文件）

按用户操作路径补全所有零覆盖端点：

| 用户路径 | 测试文件 | 覆盖端点 | 测试数 |
|---|---|---|---|
| 认证 | `test_auth_extra.py` | logout / PUT /me / password-strength | 12 |
| 上传清理 | `test_upload_lifecycle.py` | DELETE /trades（FK-safe 删除） | 4 |
| 分析列表+追加 | `test_analysis_list_and_link.py` | GET /analysis / link-files | 8 |
| 报告查询下载 | `test_report_download.py` | check by-analysis / download .md | 7 |
| 管理 | `test_admin.py` | 全 7 个 admin 端点 | 23 |
| drift 防护 | `test_compute_equivalence.py` | 慢路径 == compute_all | 3 |
| 报告一致性 | `test_report.py`（追加） | report insight == /insight | 2 |
| 快照回归 | `test_analysis.py`（追加） | TestSnapshotRoundTrip | 4 |

**drift 防护网**（`test_compute_equivalence.py`）：清空快照 → GET /stats/insight/whatif（慢路径）→ 与 `compute_all` 直接计算结果比较。这是防止再次出现 422 那类 drift 的核心防护。

> 注：whatif 等价性测试初版用了错误 JSON key（`attribution`/`rule_simulation`，schema 实际是 `items`/`stop_loss`），导致断言恒为空通过——已修复为正确字段名 + 实际值比较。shapley 因蒙特卡洛采样（`random.shuffle` 无种子）有算法随机性，改为容差比较（5% 或 1.0 绝对值）。

### 代码清理（删除死代码）

| 死代码 | 位置 | 处理 |
|---|---|---|
| `pattern_config.py` 整模块（70 行） | `engine/pattern_config.py` | 删除（零引用 + 引用不存在的 `pattern_definition.yaml`，一旦触发 FileNotFoundError） |
| `PatternEngine.detect_cooldowns` | `pattern.py:368-407` | 删除 + 删除 3 个独占测试；不变量测试迁移到 `TestTagCoexistence` |
| `_get_multiplier` | `parsers/__init__.py` | 删除 + 删除独占测试（SmartParser 用自己的 `_get_futures_multiplier_smart`） |
| `BaseParser._column_match_score` | `parsers/base.py:157` | 删除 + 删除独占测试（SmartParser 用自己的 `_classify_column`） |

> `PositionBuilder.build_grouped`（~130 行）仅 golden_runner + 测试用，自身注释承认是"参考实现"——保留（golden_runner 依赖）。

### 记录但未改动的隐患（供未来审查参考）

以下隐患经调查确认，本次未改动（风险/范围考量），已用测试锁住或记录归档：

#### A. get_stats/get_insight/get_whatif 慢路径与 compute.py 重复（~280 行）

`analysis.py` 的三个 GET 慢路径是 `compute.py`（`compute_stats`/`compute_insight`/`compute_whatif`）的手工副本。`get_stats` 副本**已导致过 422 bug**（本次已修）。

- **现状**：当前副本与 engine 行为一致，由 `test_compute_equivalence.py` 锁住。
- **未重构原因**：`compute_all` 用并行 fetcher（`ensure_market_data_parallel` + ThreadPoolExecutor），慢路径用串行 `ensure_market_data`；上轮尝试用 `compute_all` 替换触发 `PendingRollbackError`（daily_bars 重复插入），并发模型变更风险较高。
- **建议**：未来若要消除重复，需先评估并行 fetcher 的 session 安全性，并在 GET 端点包裹 `try/except db.rollback()`（镜像 `run_analysis` 的模式）。

#### B. get_insight / get_whatif 慢路径不写快照

与 `get_stats`（写快照）和 `run_analysis`（写全部三个快照）不同，`get_insight`/`get_whatif` 的慢路径**不持久化快照** → 每次请求重复全量计算。这是性能问题，非正确性问题。

#### C. get_whatif 的 rule_type guard 是死代码

`get_whatif` 用 `if rule_type == "stop_loss":` guard 止损模拟（`analysis.py`），而 `compute_whatif` 无此 guard。但前端**从不传非默认值**，且即使传了，`analyze_rule` 也只处理 `stop_loss`。当前行为一致，guard 无害，保留以防前端未来扩展。

#### D. MAE/MFE 的 lookback 范围差异（理论性）

慢路径的 `ensure_market_data` 返回 120 天 lookback 扩展的 market_data，`compute_all` 的 `get_market_data` 用原始窗口。但 `compute_mae_mfe` 的 position 窗口过滤（`entry_date <= bar_date <= exit_date`）恰好掩盖了差异——当前不触发。若未来 position 的 `entry_date` 早于 `analysis.date_start`，两边会 diverge。

#### E. report.py 的内联 stats 计算（B2，未处理）

`report.py` 的 `_build_analysis_data` + `generate_report` 内联重算了 profit_factor/max_drawdown/consecutive_losses/MAE/MFE/expectancy 等（~200 行），与 `compute.py` 重复。本次仅统一了 insight 数据源（问题 4），stats 计算仍重复。建议未来复用 `compute_all` 的 stats 结果。

#### F. 三个近似的 raw-file 读取器

`upload.py:_read_raw_content`、`admin.py:_read_raw_file_bytes`、`case_library.py:_read_and_decode_raw_file` 三个读取器逻辑近似，建议未来合并到 `common.py`。

### 变更文件清单

```
修改:
  backend/app/api/analysis.py        # get_stats 完整快照 + run_analysis rollback + link_files flush
  backend/app/api/report.py          # analyze → compute_insight 统一数据源
  backend/app/api/upload.py          # 去重 409 → 幂等返回
  backend/app/engine/market_data.py  # store_bars (symbol,date) 去重
  backend/app/engine/pattern.py     # 删除 detect_cooldowns
  backend/app/parsers/__init__.py   # 删除 _get_multiplier
  backend/app/parsers/base.py       # 删除 _column_match_score
  backend/tests/test_api/test_analysis.py       # +TestSnapshotRoundTrip
  backend/tests/test_api/test_report.py         # +TestReportInsightConsistency
  backend/tests/test_api/test_upload.py         # 更新去重测试断言
  backend/tests/test_engine/test_pattern.py     # 迁移 detect_cooldowns 测试
  backend/tests/test_parsers/test_helpers.py    # 删除 _get_multiplier 测试
  backend/tests/test_parsers/test_registry.py  # 删除 _column_match_score 测试
删除:
  backend/app/engine/pattern_config.py
新增:
  backend/tests/test_api/test_auth_extra.py
  backend/tests/test_api/test_upload_lifecycle.py
  backend/tests/test_api/test_analysis_list_and_link.py
  backend/tests/test_api/test_report_download.py
  backend/tests/test_api/test_admin.py
  backend/tests/test_engine/test_compute_equivalence.py
```

---

## [V1.0.0] — 2026-06-26

### 首个正式版本

经过 6 个月的迭代开发（V0.1.1 → V0.5.0），TradeDoctor 达到 v1.0 里程碑。本版本具备完整的「交割单上传 → 持仓重建 → 行为标签 → 盈亏归因 → AI 诊断报告」分析链路，并提供匿名案例库贡献的数据闭环。

### 核心能力

- **SmartParser 自动解析**：基于数据值推断列类型，支持 6+ 券商格式，GBK 编码容错、伪 `.xls` 回退、`="..."` 外壳剥离
- **FIFO 持仓重建**：前序持仓 `cost_known` 标记，软删除 `is_deleted` 支持
- **4 维行为标签体系**：市场环境 / 交易行为 / 交易结果 / 心理推测，每持仓每维最多一个标签
- **Insight Engine**：PF、Expectancy(R)、Shapley 归因、Primary Pattern 识别
- **What-If 止损回测**：持仓期间日线 low 判断盘中触发，因子贡献分析
- **MAE/MFE 风险分析**：持仓期间最大浮亏/浮盈，止盈效率 `profit_capture_ratio`
- **AI 诊断报告**：自然语言报告，Prompt 携带 10+ 风险指标 + 关键交易摘要
- **净值曲线 + 股票盈亏表**：按持仓退出日累计，按个股汇总
- **匿名案例贡献**：用户主动同意的匿名交割单收集，consent_log 审计追踪确保合规

### V1.0 新增（自 V0.5.0 以来）

- **交割单去重**：SHA256 内容哈希 + 交易唯一键双重去重，防止重复导入
- **ConsentLog 合规审计**：用户同意/拒绝决策不可变记录，满足《个人信息保护法》合规证明需求
- **Landing 页内联认证**：注册/登录无需跳转页面
- **UI 全面优化**：设计令牌体系、焦点陷阱、ESC 关闭、Tailwind 迁移、性能优化
- **部署完善**：rsync 全量同步、server-setup.sh 首次安装、跨平台重启脚本

## [V0.4.0] — 2026-06-23

### 新增

- **净值曲线图**（Equity Curve）
  - 后端：`StatsResponse` 新增 `equity_curve: list[EquityPoint]` 字段
  - `EquityPoint = {date, cum_pnl, cum_pnl_pct}`，按持仓退出日期累计盈亏
  - 前端：新建 `EquityCurve.tsx`，使用 Recharts AreaChart 渲染
  - 盈利区域绿色半透明，亏损区域红色半透明，y=0 参考线
  - 放在统计概览页核心结果卡片上方

- **股票维度盈亏表**（Symbol Summary）
  - 后端：`StatsResponse` 新增 `symbol_summary: list[SymbolSummaryItem]` 字段
  - `SymbolSummaryItem = {symbol, trade_count, win_count, win_rate, total_pnl, avg_holding_days, first_trade_date, last_trade_date}`
  - 按个股汇总，仅统计 `cost_known=True` 的有效持仓（与 KPI 口径一致）
  - 前端：新建 `SymbolSummaryTable.tsx`，可排序表格，5 列
  - 默认按总盈亏降序，放在核心结果下方、进阶分析上方

- **AI Prompt 扩充**
  - `build_user_prompt()` 新增「风险指标」板块：profit_factor、expectancy、max_drawdown、max_drawdown_pct、consecutive_losses、avg_mae、avg_mfe、profit_capture_ratio、total_return_pct（共 10 项）
  - 新增「关键交易」板块：盈利 TOP3 + 亏损 TOP3
  - `_build_analysis_data()` 新增 `stats_data` 参数，从 StatsResponse 直接采集风险指标
  - Validator 新增 PF / max_drawdown_pct / consecutive_losses 软校验（±1% 容忍度）

- **测试**：`test_prompt.py` 新增 4 个测试，`test_validator.py` 新增 6 个测试（共 30 passed, 0 failed）

- **基础设施**：`.gitattributes`（统一行尾为 LF）、`vite.config.ts` 新增 `/api` proxy

### 变更

- `frontend/src/api/client.ts` BASE_URL 从 `http://localhost:8000` 改为 `""`（配合 vite proxy）
- `StatsCards.tsx` 集成 EquityCurve 和 SymbolSummaryTable 组件

---

## [V0.5.0] — 2026-06-25

### 新增

- **匿名案例贡献**：用户可提交匿名交割单用于产品改进，`entry_count` 修复，注册提示优化
- **设计令牌体系**：建立 CSS 变量基础，ToastContext / Layout / 认证 / 上传 / 分析面板全站组件迁移
- **ConfirmDialog** 焦点陷阱 / ESC 关闭 / 滚动锁定，提升无障碍体验
- **跨平台重启脚本** `restart.ps1`：PowerShell 原生实现，健康检查绕过代理，支持 Windows/Linux/macOS

### 变更

- **项目改名**：TradingJournalAnalyzer → TradeDoctor
- **部署流程重构**：服务器不再 git pull，改用本地 rsync 全量同步代码；新增 `server-setup.sh` 首次安装脚本 + nginx 配置模板
- **交割单存储**：文件从数据库 BLOB 迁移到磁盘存储，`.gitignore` 排除 `uploads/`
- **归因分析重构**：BREAKOUT 从 behavior 归位到 market_env（与 BREAKDOWN 对称），S14 区分 PnL 量级分桶与 outcome 行为标签，散户体验优化
- 统一后端端口为 8000，同步 vite proxy 和 restart 脚本
- `.env.example` 环境变量模板，`config.py` 绝对路径加载 `.env`
- `requirements.txt` 补全缺失依赖（pandas、slowapi、PyYAML）
- 前端标题与 SEO 描述更新，移除未使用的 WhatIfChart 组件

### 修复

- 修复 12 项高危缺陷（#11-#22）：手机号注册/上传报错、用户错误提示统一等
- 代码审查修复：3 阻塞 + 11 建议 + 8 小改进
- 密码改用环境变量传递，pin ssh-action SHA 防供应链攻击

---

## [V0.3.1] — 2026-06-22

### 修复

- 第三轮代码审查：8 阻塞 + 10 建议 + 4 小改进全量修复
- 前端 UI/UX 全面优化

---

## [V0.2.5] — 2026-06-20

### 新增

- `max_drawdown_pct`：最大回撤百分比（行业标准，对照 TradesViz/Edgewonk）
- `total_return_pct`：总收益率百分比
- `avg_win_pct` / `avg_loss_pct`：平均盈亏百分比

### 变更

- `is_small_sample` 字段：交易笔数 <5 时标记小样本，前端显示「样本不足」不评价

---

## [V0.2.3] — 2026-06-19

### 修复

- 真实券商导出适配（三层污染修复）：
  - GBK 编码探测（utf-8 → gb18030 → gbk）
  - 伪 `.xls` 文本格式回退（`read_excel` 失败后自动切换文本读取 + 分隔符探测）
  - `="..."` 外壳剥离（`_strip_formula_strings`）
  - 费用列 QUANTITY 守卫误杀修复（名称含费用关键词的列豁免）
- 新增 `tests/test_parsers/test_citic_xls.py` 固化真实 CITIC 特征为回归测试

---

## [V0.1.3] — 2026-06-15

### 新增

- **Expectancy（R-multiple）**：基于 pnl_pct 的预期收益，对照 TradesViz 标准
- **Shapley 归因**：公平归因各行为标签对总盈亏的贡献
- `baseline_expectancy` 字段用于标签对比

---

## [V0.1.2] — 2026-06-12

### 新增

- **MAE/MFE 风险分析**：持仓期间最大不利变动（浮亏）和最大有利变动（浮盈）
- `profit_capture_ratio`：止盈效率（浮盈兑现率）
- `mae_winners` / `mae_losers`：分盈亏组的 MAE 均值

### 修复

- PnL 计算扣除买卖双边费用
- 多费用列汇总（佣金、印花税、过户费、其他杂费）
- SmartParser 列类型推断修复（证券代码误选为数量列、价格列误判为费用列）

---

## [V0.1.1] — 2026-06-10

### 新增

- **4 维行为标签体系**：市场环境 / 交易行为 / 交易结果 / 心理推测
- **SmartParser**：基于数据值推断列类型，零配置自动识别券商格式
- **FIFO 持仓重建**：前序持仓标记（`cost_known`），软删除支持（`is_deleted`）
- **What-If 止损回测**：使用持仓期间日线 low 判断盘中触发
- JWT 认证（邮箱/手机号注册，密码强度校验）
- 支持多文件上传和历史分析记录
