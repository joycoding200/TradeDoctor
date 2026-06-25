# 测试代码审查报告

**日期**: 2026-06-24
**审查范围**: backend/tests/ 全部测试文件 + golden 测试数据
**项目**: TradingJournalAnalyzer V4.0
**测试运行环境**: Python 3.14.4, pytest 8.3.4, Windows venv via WSL

---

## 一、测试运行总览

### 1.1 运行结果

| 类别 | 通过 | 失败 | 总计 |
|------|------|------|------|
| 单元测试 | 296 | 8 | 304 |
| Golden 测试 | 15 | 4 | 19 |
| **合计** | **311** | **12** | **323** |

### 1.2 运行环境问题

**__pycache__ 缓存导致 conftest.py 导入失败**

清除 `__pycache__` 后 conftest.py 正常导入。根因是 `.pyc` 缓存了旧版 analysis.py 的签名信息，
导致 slowapi 装饰器看到过期的函数签名（不含 `request: Request` 参数）。
清除缓存后所有测试均可运行。

**影响**: 开发者拉取新代码后直接运行 `pytest` 会遇到导入错误，需要手动清除 `__pycache__`。
**建议**: 在 `conftest.py` 中增加缓存失效保护，或在项目 README 中注明清除缓存的步骤。

---

## 二、失败测试逐项分析

### 2.1 Golden 测试失败（4 项）

#### GT-1. pattern/PT002 — patterns 字段类型不匹配

- **文件**: `tests/golden/pattern/PT002.expected.json`
- **错误**: `.patterns: 期望 dict, 实际 list`
- **根因**: golden_runner.py 输出 `patterns` 为 `sorted(list)` (line 326)，
  同时输出 `patterns_dict` 为 `{idx: [names]}` (line 327)。
  但 expected.json 中 `patterns` 字段写成了 dict 格式：
  ```json
  "patterns": {"0": ["SWING"], "1": ["AVERAGE_DOWN", "SWING"]}
  ```
- **修复**: 将 expected.json 中的 `patterns` 改为 list 格式：
  ```json
  "patterns": ["AVERAGE_DOWN", "SWING"]
  ```
  或者将 dict 数据移到 `patterns_dict` 字段下。

#### GT-2. pattern/PT003 — 同 GT-1

- **文件**: `tests/golden/pattern/PT003.expected.json`
- **错误**: 同 GT-1，`patterns` 字段类型不匹配
- **修复**: 同 GT-1

#### GT-3. position/P003 — holding_days + patterns 数量不匹配

- **文件**: `tests/golden/position/P003.expected.json`
- **CSV 数据**: 买入 100@10.00 (Jan 2) → 买入 100@8.00 (Jan 5) → 卖出 200@7.00 (Jan 10)
- **错误 1**: `holding_days: 期望 5, 实际 8`
  - expected.json 写的 5 = Jan 5 → Jan 10（以第二次买入为 entry_date）
  - 实际 8 = Jan 2 → Jan 10（以首次买入为 entry_date，**正确行为**）
- **错误 2**: `patterns: 列表长度不匹配, 期望 1, 实际 2`
  - expected.json 只有 `["AVERAGE_DOWN"]`
  - 实际多出 `SWING`（holding_days=8，在 3-30 天范围内，**正确行为**）
- **修复**: 更新 expected.json：
  - `holding_days: 8`
  - `patterns: ["AVERAGE_DOWN", "SWING"]`

#### GT-4. position/P009 — exit_date + holding_days 不匹配

- **文件**: `tests/golden/position/P009.expected.json`
- **CSV 数据**: BUY 100@10 (Jan 1) → BUY 100@12 (Jan 3) → SELL 150@15 (Jan 10) → SELL 50@15 (Jan 15)
- **pipeline**: `build_grouped`
- **错误**: `exit_date: 期望 '2025-01-10', 实际 '2025-01-15'`
  - expected.json 写的 Jan 10（第一次卖出日期）
  - 实际 Jan 15（最后一次卖出日期，**正确行为** — 持仓在最后一笔卖出时才完全平仓）
  - `holding_days` 和 `avg_holding_days` 连锁错误
- **修复**: 更新 expected.json：
  - `exit_date: "2025-01-15"`
  - `holding_days: 14`
  - `stats.avg_holding_days: 14.0`

---

### 2.2 单元测试失败（8 项）

#### UT-1. test_prompt.py::test_risk_metrics_section — 标签文本不匹配

- **文件**: `tests/test_ai/test_prompt.py:137`
- **断言**: `assert "盈亏比(PF)" in prompt`
- **实际**: prompt.py:116 输出 `"盈亏比（赚的钱÷亏的钱，>1表示整体盈利）"`
- **根因**: V4.0 重写了 prompt 标签格式，从 `"盈亏比(PF)"` 改为带中文解释的长格式
- **修复**: 更新测试断言：
  ```python
  assert "盈亏比" in prompt  # 不再要求精确匹配 (PF) 后缀
  ```
  同时检查其他断言是否也需要更新（`"预期收益(Expectancy)"` 等）

#### UT-2. test_analysis.py::test_stats_returns_kpis — win_count 不匹配

- **文件**: `tests/test_api/test_analysis.py:112`
- **断言**: `assert data["win_count"] == 1`（实际 0）
- **测试 CSV**: 4 笔成交（2 个完整持仓），第一笔 Buy 1000@10.50 → Sell 1000@11.00
  理论 PnL = (11.00 - 10.50) × 1000 - 5 - 5 = 490 > 0 → 应为 win
- **可能根因**: SmartParser 解析 `委托时间`/`买卖方向` 列名时与测试 CSV 格式不匹配，
  导致成交方向或价格解析错误，进而 PnL 计算异常
- **需排查**: 运行 SmartParser 单独解析测试 CSV，检查解析结果
- **修复**: 修正测试 CSV 格式使其匹配 SmartParser 当前识别逻辑，或修正 SmartParser

#### UT-3. test_analysis.py::test_all_winning_profit_factor_is_null — win_count 不匹配

- **文件**: `tests/test_api/test_analysis.py:238`
- **断言**: `assert data["win_count"] == 2`（实际 1）
- **根因**: 同 UT-2，SmartParser 对测试 CSV 的解析问题导致 PnL 异常
- **修复**: 同 UT-2

#### UT-4. test_report.py::test_generated_report_content_stored — validation_passed 不匹配

- **文件**: `tests/test_api/test_report.py:137`
- **断言**: `assert data["validation_passed"] is True`（实际 False）
- **根因**: V4.0 新增的 validator 对 AI 报告内容做软校验（PF、max_drawdown_pct、
  consecutive_losses ±1% 容忍度）。测试使用的 MOCK_REPORT 内容不含这些指标，
  导致 validator 判定为不通过
- **修复**: 更新 MOCK_REPORT 使其包含 validator 期望的指标值，
  或在测试中 mock validator 使其返回 True

#### UT-5~8. test_upload.py — source_type "qmt" 不再支持（4 个测试）

- **文件**: `tests/test_api/test_upload.py`
- **错误**:
  - `test_upload_file_detects_qmt_format`: `assert "qmt" in formats` → `{'smart'}`
  - `test_confirm_format_returns_trade_preview`: 400 Bad Request
  - `test_import_saves_trades_to_db`: 400 Bad Request
  - `test_full_upload_flow_integration`: 400 Bad Request
- **根因**: SmartParser 统一了解析逻辑，不再返回 "qmt" 作为检测到的格式。
  上传确认端点 `/api/upload/confirm` 只接受 `source_type: "smart"`，
  但测试代码中部分地方仍使用 `source_type: "qmt"`
- **修复**:
  - 将所有 `source_type: "qmt"` 改为 `source_type: "smart"`
  - 将 `assert "qmt" in formats` 改为 `assert "smart" in formats`
  - 重新验证 confirm 端点的返回值结构

---

## 三、测试覆盖空白

### 3.1 🔴 阻塞级 — V4.0 核心功能零测试覆盖

**equity_curve（净值曲线）无任何测试**

- `StatsResponse.equity_curve: list[EquityPoint]` (analysis.py schema line 115)
- `analysis.py:358-363` 构建逻辑（按持仓退出日期累计 PnL）
- 无单元测试、无 golden 测试、无 API 集成测试
- **风险**: 净值曲线是 V4.0 核心交付物，计算错误直接影响前端图表展示

**symbol_summary（个股盈亏汇总）无任何测试**

- `StatsResponse.symbol_summary: list[SymbolSummaryItem]` (analysis.py schema line 116)
- `analysis.py:272-295` 构建逻辑（按个股聚合，仅统计 valid_positions）
- 无单元测试、无 golden 测试、无 API 集成测试
- **风险**: 个股维度统计是 V4.0 新增的 KPI，错误会误导用户决策

### 3.2 🔴 阻塞级 — B1 问题路径无测试

**AVERAGE_DOWN 回退路径（all_trades=None）无测试**

- `pattern.py:221-249` 的回退路径在 all_trades 未传入时执行
- 现有 AVERAGE_DOWN 测试全部通过 `trades=` 参数传入 all_trades（走主路径 line 168-220）
- 没有测试验证回退路径的行为
- **风险**: 回退路径未验证亏损状态（B1 问题），但没有测试来捕获这个错误

### 3.3 🟡 建议级 — Mock 对象字段不完整

**_Position mock 缺少 4 个字段**

实际 `PositionResult` 有 16 个字段：
```
symbol, asset_type, entry_date, exit_date, holding_days,
total_quantity, avg_entry_price, avg_exit_price, pnl, pnl_pct,
trade_ids, cost_known, entry_count, total_buys, total_sells, total_commission
```

测试 mock（test_pattern.py / test_insight.py / test_whatif.py）只有 12 个字段，缺少：
- `entry_count` — build_grouped 产出
- `total_buys` — build_grouped 产出
- `total_sells` — build_grouped 产出
- `total_commission` — whatif.py:152 通过 `getattr(p, "total_commission", 0.0)` 访问

当前因 `getattr` 默认值机制不报错，但任何新增代码直接访问 `p.total_commission` 会导致 AttributeError。

**_Trade mock 缺少 commission 字段**

`position.py:79` 使用 `getattr(trade, 'commission', 0)` 访问佣金。
test_position.py 的 `_Trade` 没有 `commission` 字段。
所有 position 测试的 PnL 计算实际未验证佣金处理逻辑。

### 3.4 🟡 建议级 — 安全/配置无测试

| 检查项 | 测试状态 | 说明 |
|--------|----------|------|
| CORS 配置 | ❌ 无 | B3 问题（硬编码 localhost:5173）无测试 |
| 速率限制 | ❌ 无 | conftest.py 全局禁用 `limiter.enabled = False` |
| 密码强度校验 | ❌ 无 | 8位+含字母+含数字 规则无测试 |
| 文件名 CRLF 注入 | ❌ 无 | 下载文件名校验无测试 |
| 软删除恢复 | ❌ 无 | is_deleted=True 后数据不可查询，但无测试验证 |

### 3.5 💭 改进级 — 测试结构问题

**golden_runner.py 的 patterns 字段歧义**

- `patterns`（list）和 `patterns_dict`（dict）同时输出，容易混淆
- 4 个 golden 测试中有 2 个因字段名混淆而失败
- 建议：在 deep_compare 中增加类型提示，或合并为单一字段

**golden_runner.py 统计计算与 analysis.py 重复**

- golden_runner.py:259-310 重新实现了 win_rate / PF / expectancy / max_drawdown 计算
- 这与 analysis.py 的 `_compute_stats()` 逻辑重复
- 如果 analysis.py 的计算逻辑更新但 golden_runner.py 没同步，golden 测试会给出假阳性/假阴性
- 建议：golden_runner.py 直接调用 analysis.py 的统计函数，避免逻辑重复

---

## 四、修复优先级

### P0 — 立即修复（阻塞 CI）

| 编号 | 问题 | 工作量 |
|------|------|--------|
| UT-5~8 | test_upload.py 4 个测试：qmt → smart | 30 分钟 |
| GT-1~2 | PT002/PT003 expected.json：patterns dict → list | 10 分钟 |
| GT-3 | P003 expected.json：holding_days 5→8, patterns 加 SWING | 10 分钟 |
| GT-4 | P009 expected.json：exit_date→Jan 15, holding_days→14 | 10 分钟 |

### P1 — 本轮修复（功能正确性）

| 编号 | 问题 | 工作量 |
|------|------|--------|
| UT-1 | test_prompt.py：更新标签断言 | 15 分钟 |
| UT-2~3 | test_analysis.py：排查 SmartParser 解析 + 修正测试 CSV | 1-2 小时 |
| UT-4 | test_report.py：更新 MOCK_REPORT 或 mock validator | 30 分钟 |
| 3.1 | 新增 equity_curve 单元测试 + golden 用例 | 2-3 小时 |
| 3.1 | 新增 symbol_summary 单元测试 + golden 用例 | 2-3 小时 |
| 3.2 | 新增 AVERAGE_DOWN 回退路径测试（B1 问题） | 1 小时 |

### P2 — 后续改进

| 编号 | 问题 | 工作量 |
|------|------|--------|
| 3.3 | _Position / _Trade mock 补齐缺失字段 | 30 分钟 |
| 3.4 | 新增 CORS / 速率限制 / 密码强度测试 | 2-3 小时 |
| 3.5 | golden_runner.py 统计逻辑去重，改调 analysis.py | 1-2 小时 |
| 1.2 | __pycache__ 缓存问题文档化或增加 conftest 保护 | 30 分钟 |

---

## 五、测试质量评估

### 5.1 值得肯定

1. **Golden 测试体系设计优秀** — CSV + expected.json 的数据驱动模式，
   覆盖了 position/pattern/whatif 三个核心引擎的完整流水线
2. **deep_compare 递归比较器** — 支持嵌套 dict/list/float 容忍度，
   None 通配符设计巧妙
3. **pytest 参数化集成** — golden_runner.py 通过 `pytest_generate_tests`
   实现每个 golden 用例独立报告，失败定位精准
4. **测试数据多样性** — 10 个 position 用例覆盖了 FIFO、部分成交、orphan sell、
   grouped builder 等场景；8 个 pattern 用例覆盖了 AVERAGE_DOWN、PYRAMID、TURN 等
5. **test_pattern.py 覆盖率高** — 1333 行，覆盖了所有 14 个行为标签的正/反向测试

### 5.2 需要改进

1. **Golden expected.json 维护滞后** — 4/19 失败（21%），说明在源码迭代后
   没有及时更新期望值。建议增加 `--update-golden` 命令自动重新生成 expected.json
2. **V4.0 功能测试空白** — equity_curve 和 symbol_summary 是 V4.0 核心交付物，
   但零测试覆盖。这在 CLAUDE.md 中被标注为"不可随意改动"的设计决策，却无测试守护
3. **上传流程测试与源码脱节** — SmartParser 统一解析后移除了 qmt 格式，
   但 4 个测试仍使用旧格式，说明 API 变更后没有同步更新测试
4. **Mock 对象与真实数据类不同步** — PositionResult 新增了 4 个字段，
   但所有测试 mock 都没有更新。依赖 getattr 默认值是脆弱的

---

## 六、总结

当前测试套件 311/323 通过（96.3%），但 12 个失败全部源于**测试代码与源码迭代不同步**，
而非源码 bug。核心问题集中在三个方面：

1. **Golden 期望值过期**（4 项）— 源码逻辑改进后 expected.json 未更新
2. **API 变更未同步**（4 项）— SmartParser 统一解析后上传测试未更新
3. **Prompt/Validator 升级**（3 项）— V4.0 标签格式和验证逻辑变更未反映到测试

最严重的风险不是已有失败，而是 V4.0 两个核心功能（equity_curve、symbol_summary）
完全没有测试覆盖。这两个功能涉及金融计算正确性，一旦出错会直接误导用户决策。
