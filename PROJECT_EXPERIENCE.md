# 项目经验教训

## SmartParser 列类型推断陷阱（2026-06-12 修复）

SmartParser 使用基于数值特征（而非列名）的列类型推断。这套机制对常见券商格式有效，但存在以下边界情况：

### Bug 1: 证券代码被选为数量列
- **现象**: 600036 等 6 位数字码被当作成交数量，导致数量=600036（实际应为 1200）
- **原因**: 证券代码是全数字列（QUANTITY=0.4），和成交数量得分相同，排在前面被选中
- **修复**: `qty_col` 和 `price_col` 必须 `exclude` 已识别的 `symbol_col`

### Bug 2: 成交价格被纳入费用汇总
- **现象**: 股价 <100 元的 A 股，成交价格列被当作费用列，12.50 元被加到佣金里
- **原因**: `_classify_column` 给低价列 COMMISSION=0.5（avg<1000 +0.3, avg<100 +0.2），超 0.3 阈值
- **修复**: 费用列筛选增加 `PRICE < COMMISSION` 条件，排除价格主导列

### Bug 3: 序号/编号列被纳入费用
- **现象**: 序号=1 加到佣金中，导致每行佣金多 1 元
- **原因**: 序号列值小（1,2,3...），满足 COMMISSION 数值条件
- **修复**: 费用列按列名排除：`序号`、`编号`、`成交编号`、`委托编号`、`合同编号`、`股东代码`

### Bug 4: 旧券商解析器仍被调用
- **现象**: 删除旧解析器后 `source_type` 仍为 `dfcf`，佣金全为 0
- **原因**: 后端进程未完全终止，旧代码缓存未失效
- **教训**: 代码修改后必须 `taskkill //F //IM python.exe` 确保所有进程重启

## PnL 计算（2026-06-12 修复）

### 费用扣除
- PositionBuilder 的 `_build_for_symbol`（FIFO）和 `_group_for_symbol` 均使用 `(sell_price - buy_price) × qty`，未扣除佣金
- 修复后在 PnL 中扣除买卖双边费用，`pnl_pct` 分母使用含费投资成本

### 多费用列汇总
- A 股有 4 种独立费用：佣金、印花税、过户费、其他杂费
- SmartParser 只取 COMMISSION 评分最高的一列，其余丢失
- 修复为汇总所有 COMMISSION > 0.3 的列

## 测试文件数据一致性问题

- 部分 CSV 中 `清算金额 ≠ 成交金额 ± 费用`，数据生成时有计算误差
- 买卖方向标注错误（如卖出标为买入但有印花税）
- 占位符行（`...,...,...`）导致文件不完整
- 测试前应验证数据内部一致性，而非仅依赖预期值

## 真实券商导出 vs 模拟数据：三层污染（2026-06-19 修复）

真实导出的中信交割单 `20260619 交割单.xls` 一上传就报"无法识别"，而 `testfiles/` 下的模拟数据从未触发。根因：**模拟测试数据是手写的理想化 CSV，和券商程序真实导出的格式分布完全脱节，测试成了自我证明的闭环。**

真实 CITIC 导出与模拟数据的关键差异（每一项都击穿了原代码的隐含假设）：

| 维度 | 模拟数据（测试假设） | 真实 CITIC 导出 | 后果 |
|------|------|------|------|
| 编码 | UTF-8 | GBK | 中文表头乱码，列名匹配失败 |
| 格式 | 真 `.csv` 逗号分隔 | 扩展名 `.xls`，实为 Tab 分隔文本 | `read_excel` 抛异常，`detect` 返回 0 → "无法识别" |
| 单元格 | 裸值 `600519` | 每值裹 `="002471"`（Excel 文本保护公式，保留前导零） | 值正则/日期/`float()` 全失效 → 0 笔成交 |
| 费用列 | 无 / 简单 | `手续费=5.00` 小整数 | 误判为 QUANTITY，佣金**静默漏算** |

### Bug 5: `_read_df` 信任扩展名，不信任内容
- **现象**: `.xls` 文件"无法识别"
- **原因**: `base.py` 按扩展名分发——`.csv` 假设 UTF-8 逗号、`.xls` 假设真 Excel 工作簿。中信导出的是伪装成 `.xls` 的 GBK TSV 文本，`pd.read_excel` 直接 `ValueError`，无 try/except 回退，异常被 `detect` 吞掉返回 0.0
- **教训**: **券商导出的扩展名不可信**。`.xls` 常是 GBK/GB18030 文本（中信、华泰、QMT 等普遍如此），`.csv` 常非 UTF-8。必须"按内容探测格式 + 按字节探测编码"，而非按扩展名分发
- **修复**: `read_excel` 失败即回退文本读取；文本读取做编码探测（utf-8→gb18030→gbk）+ 分隔符探测（tab/逗号/分号/管道）

### Bug 6: 值分类器对 `="..."` 外壳零容忍
- **现象**: 文件能读进来，但 `parse` 返回 0 笔
- **原因**: SmartParser 的值推断（股票代码 `^\d{6}$`、日期 `^\d{4}[-/]\d{1,2}`、`float(v)`）都假设值是裸的；真实值是 `="002471"`，所有列 DATE/STOCK_SYMBOL/PRICE/QUANTITY 全 0 分
- **教训**: `="..."` 是 Excel 文本保护公式，券商为保留前导零代码刻意加的——真实导出常态，模拟数据绝不会出现。**值分类器必须先清洗外壳**
- **修复**: `base.py` 新增 `_strip_formula_strings`，用 `^="(.*)"$` 正则统一剥离，所有列无差别应用（不依赖 dtype，因 `dtype=str` 下列是 StringDtype 而非 object）

### Bug 7: 费用列 QUANTITY 守卫误杀小整数手续费
- **现象**: 成交识别成功，但佣金偏低（5 元券商手续费没计入 PnL）
- **原因**: `comm_cols` 的 `QUANTITY < 0.45` 守卫本意排除序号/编号列，但 `手续费=5.00` 这种小整数被打上 QUANTITY 0.6 分被误杀。比"无法识别"更危险——不报错，只静默算错盈亏
- **修复**: 对**名称含费用关键词**（费/佣/税）的列豁免 QUANTITY 守卫；ID 类列仍由名称黑名单排除
- **教训**: 启发式数值守卫要和列名语义交叉验证，不能只看数值分布

### 根因教训：测试数据分布 ≠ 生产数据分布
- `testfiles/` 的模拟数据是**按解析器当前能力反向定制**的——能过什么就生成什么，于是测试自证闭环，真实数据一来立刻穿帮
- 必须用**真实脱敏交割单**做夹具，覆盖三层污染（编码、伪装格式、`="..."` 外壳）
- 新增 `tests/test_parsers/test_citic_xls.py` 固化真实 CITIC 特征为回归测试
- 遗留脱节：`testfiles/` 目录已不存在（CLAUDE.md 仍引用）；`tests/test_api/test_upload.py` 仍断言已删除的 `qmt` 格式——均为"模拟时代"残留，待清理

## V4.0 P0 冲刺：净值曲线 + 股票维度盈亏 + AI Prompt 扩充（2026-06-23）

### 经验 1：净值曲线数据采集复用 max_dd 循环

- `get_stats()` 中计算最大回撤时已遍历 `sorted_positions` 累计 PnL，净值曲线数据点（`EquityPoint`）可在同一循环中收集，无需二次遍历
- 起点必须为 `{首笔 exit_date, 0.0, 0.0}`，后续逐笔累加 position.pnl
- `cum_pnl_pct` 基于初始资金计算，非交易收益率
- 前端 `EquityCurve.tsx` 用 Recharts `AreaChart`，颜色由最终 cum_pnl 正负决定（盈利绿/亏损红），`ReferenceLine y=0` 标记零线

### 经验 2：股票维度盈亏使用 valid_positions 口径

- `symbol_summary` 必须只统计 `cost_known=True` 的有效持仓，与 KPI 口径一致
- 按 `symbol` 分组后计算 `trade_count`、`win_count`、`win_rate`、`total_pnl`、`avg_holding_days`
- 前端 `SymbolSummaryTable.tsx` 默认按 `total_pnl` 降序排列，支持点击列头排序

### 经验 3：AI Prompt 扩充的数据流

- `report.py` 的 `_build_analysis_data()` 原本只接收 positions/market_data/insight/whatif，V4.0 新增 `stats_data` 参数
- 风险指标从 `StatsResponse` 字段直接采集，不经 AI 猜测，确保数值准确
- `build_user_prompt()` 新增「风险指标」和「关键交易」两个板块
- Validator（`validator.py`）对 PF、max_drawdown_pct、consecutive_losses 执行软校验（±1% 容忍度），不匹配仅记录 warning 不阻断报告生成
- 测试覆盖：`test_prompt.py` 新增 4 个测试，`test_validator.py` 新增 6 个测试

### 经验 4：WSL 环境下的 CRLF/LF 行尾问题

- Claude Code 在 WSL 环境中执行会导致 Windows 文件被转为 LF，与 git 仓库的 CRLF 产生大面积 diff
- 解决方案：添加 `.gitattributes`（`* text=auto eol=lf`），统一行尾为 LF
- `git rm --cached -r . && git add .` 可批量归一化行尾，但会产生大量 diff，需在功能提交前单独处理

## 错误诊断流程

1. 先本地跑 SmartParser 验证列类型推断和佣金
2. 手工计算 1-2 笔 PnL 作基准
3. 与程序结果逐笔比对
4. 最后通过 UI 端到端验证
