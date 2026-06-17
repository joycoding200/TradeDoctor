"""Golden test runner — TradeLens Golden Dataset Specification v1 执行引擎。

扫描 golden/<module>/ 下的 CSV + expected.json，跑完整分析流水线，
深度比较 actual vs expected 输出 diff。

用法:
    cd backend
    python -m pytest tests/golden_runner.py -v
    python tests/golden_runner.py
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

# 确保 backend 目录在 Python path 中（独立运行时需要）
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# ---------------------------------------------------------------------------
# golden 目录
# ---------------------------------------------------------------------------
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


# ---------------------------------------------------------------------------
# 序列化工具
# ---------------------------------------------------------------------------

def _serialize(obj: Any) -> Any:
    """将 dataclass / date / datetime 转为 JSON 兼容类型。"""
    if is_dataclass(obj) and not isinstance(obj, type):
        result = {}
        for f in fields(obj):
            result[f.name] = _serialize(getattr(obj, f.name))
        # 别名：quantity → total_quantity
        if "total_quantity" in result:
            result["quantity"] = result["total_quantity"]
        return result
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    if isinstance(obj, float):
        # 保留 6 位小数精度，去掉尾部 0
        v = round(obj, 6)
        if v == int(v):
            return int(v)
        return v
    return obj


# ---------------------------------------------------------------------------
# CSV 解析
# ---------------------------------------------------------------------------

def load_trades(csv_path: Path) -> list[dict]:
    """解析 CSV 为 trade dict 列表。自动识别券商格式和简单格式。"""
    content = csv_path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    lines = content.splitlines()
    if len(lines) < 2:
        return []

    header = lines[0]
    reader = csv.DictReader(lines)

    # 检测 CSV 格式：券商格式有 "成交日期" 列，简单格式有 "datetime" 列
    if "成交日期" in header:
        return _parse_broker_csv(reader)
    return _parse_simple_csv(reader)


def _parse_simple_csv(reader: csv.DictReader) -> list[dict]:
    """解析简单格式: datetime,symbol,side,quantity,price。"""
    trades: list[dict] = []
    for row in reader:
        if not row or not any(v.strip() for v in row.values()):
            continue
        trades.append({
            "symbol": row["symbol"].strip(),
            "side": row["side"].strip().upper(),
            "quantity": float(row["quantity"]),
            "price": float(row["price"]),
            "datetime": row["datetime"].strip(),
            "asset_type": row.get("asset_type", "stock").strip() or "stock",
        })
    return trades


def _parse_broker_csv(reader: csv.DictReader) -> list[dict]:
    """解析券商导出格式: 成交日期,证券代码,操作,成交均价,成交数量,...。

    操作映射: 证券买入→BUY, 证券卖出→SELL
    """
    SIDE_MAP = {
        "证券买入": "BUY",
        "证券卖出": "SELL",
        "买入": "BUY",
        "卖出": "SELL",
        "BUY": "BUY",
        "SELL": "SELL",
    }

    trades: list[dict] = []
    for row in reader:
        if not row or not any(v.strip() for v in row.values()):
            continue

        date_str = row.get("成交日期", "").strip()
        time_str = row.get("成交时间", "").strip()
        datetime_str = f"{date_str}T{time_str}" if time_str else date_str

        side_raw = row.get("操作", "").strip()
        side = SIDE_MAP.get(side_raw, side_raw.upper())

        trades.append({
            "symbol": row.get("证券代码", "").strip(),
            "side": side,
            "quantity": float(row.get("成交数量", 0)),
            "price": float(row.get("成交均价", 0)),
            "datetime": datetime_str,
            "asset_type": "stock",
        })
    return trades


# ---------------------------------------------------------------------------
# 最小化对象，供引擎使用
# ---------------------------------------------------------------------------

class _Trade:
    """兼容引擎接口的轻量 trade 对象。"""
    __slots__ = ("id", "symbol", "asset_type", "datetime", "side", "quantity", "price")

    def __init__(self, id: str, d: dict):
        self.id = id
        self.symbol = d["symbol"]
        self.asset_type = d["asset_type"]
        self.datetime = _parse_datetime(d["datetime"])
        self.side = d["side"]
        self.quantity = d["quantity"]
        self.price = d["price"]


def _parse_datetime(s: str) -> datetime:
    """解析 datetime 字符串，支持 'YYYY-MM-DD' 和 'YYYY-MM-DDTHH:MM:SS' 格式。"""
    s = s.strip()
    if "T" in s:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    return datetime.strptime(s, "%Y-%m-%d")


def _to_trade_objects(trades: list[dict]) -> list:
    return [_Trade(f"t{i}", d) for i, d in enumerate(trades)]


# ---------------------------------------------------------------------------
# Pattern 维度映射
# ---------------------------------------------------------------------------

def _dim_for_pattern(name: str) -> str:
    if name in ("TIGHT_STOP", "TRAILING_STOP", "TIME_EXIT", "LARGE_LOSS_EXIT"):
        return "outcome"
    if name in ("CHASE", "BOTTOM", "BREAKOUT", "PYRAMID", "AVERAGE_DOWN",
                "TURN", "SCALP", "SWING", "POSITION", "FOMO"):
        return "behavior"
    if name in ("BULL_TREND", "BEAR_TREND", "BREAKDOWN"):
        return "market_env"
    if name in ("POSSIBLE_REVENGE", "OVERTRADING", "HOLD_LOSER", "CUT_WINNER", "PSY_FOMO"):
        return "psychology"
    return "behavior"


# ---------------------------------------------------------------------------
# 全流水线执行
# ---------------------------------------------------------------------------

def run_full_pipeline(
    trade_dicts: list[dict], pipeline_opts: dict | None = None
) -> dict[str, Any]:
    """执行完整分析流水线，返回 snapshot dict。

    流水线: trades → positions → patterns → stats → insights → whatif

    pipeline_opts:
        method: "build" (默认 FIFO) 或 "build_grouped" (合并分组)
    """
    from app.engine.position import PositionBuilder
    from app.engine.pattern import PatternEngine
    from app.engine.insight import InsightEngine
    from app.engine.whatif import ProfitAttribution

    opts = pipeline_opts or {}
    method = opts.get("method", "build")

    trades = _to_trade_objects(trade_dicts)
    if method == "build_grouped":
        positions = PositionBuilder.build_grouped(trades)
    else:
        positions = PositionBuilder.build(trades)

    if not positions:
        return {
            "position_count": 0,
            "trades": trade_dicts,
            "patterns": [],
            "patterns_dict": {},
            "primary_patterns": {},
            "positions": [],
            "stats": {
                "total_trades": 0,
                "position_count": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "profit_factor": 0.0,
                "expectancy": 0.0,
                "total_return_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "avg_holding_days": 0.0,
                "max_consecutive_losses": 0,
            },
            "insights": [],
            "whatif": [],
        }

    # --- patterns ---
    patterns_raw: dict[int, list[str]] = {}
    patterns_detail: dict[int, dict[str, str]] = {}  # {idx: {category: name}}
    for i, pos in enumerate(positions):
        try:
            tags = PatternEngine.tag_position(pos, positions, trades=trades)
        except Exception:
            tags = []
        names = [t.pattern_name for t in tags]
        patterns_raw[i] = names
        cat_map: dict[str, str] = {}
        for t in tags:
            dim = _dim_for_pattern(t.pattern_name)
            if dim not in cat_map:
                cat_map[dim] = t.pattern_name
        if cat_map:
            patterns_detail[i] = cat_map

    # --- stats ---
    wins = [p for p in positions if p.pnl > 0]
    losses = [p for p in positions if p.pnl <= 0]
    win_rate = len(wins) / len(positions)
    total_pnl = sum(p.pnl for p in positions)
    gross_profit = sum(p.pnl for p in wins)
    gross_loss = abs(sum(p.pnl for p in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    avg_win_pct = sum(p.pnl_pct for p in wins) / len(wins) if wins else 0.0
    avg_loss_pct = abs(sum(p.pnl_pct for p in losses) / len(losses)) if losses else 0.0
    expectancy = win_rate * avg_win_pct - (1 - win_rate) * avg_loss_pct
    total_invested = sum(p.avg_entry_price * p.total_quantity for p in positions)
    total_return_pct = total_pnl / total_invested if total_invested > 0 else 0.0

    # 最大回撤 (cumulative pnl drawdown)
    max_dd = 0.0
    cum_pnl = 0.0
    peak = 0.0
    for p in sorted(positions, key=lambda x: x.exit_date):
        cum_pnl += p.pnl
        if cum_pnl > peak:
            peak = cum_pnl
        dd = peak - cum_pnl
        if dd > max_dd:
            max_dd = dd

    # 最大连续亏损
    max_consec = 0
    cur_consec = 0
    for p in sorted(positions, key=lambda x: x.exit_date):
        if p.pnl <= 0:
            cur_consec += 1
            max_consec = max(max_consec, cur_consec)
        else:
            cur_consec = 0

    avg_holding = sum(p.holding_days for p in positions) / len(positions)

    pos_count = len(positions)
    stats = {
        "total_trades": pos_count,
        "position_count": pos_count,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(win_rate, 4),
        "total_pnl": round(total_pnl, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else None,
        "expectancy": round(expectancy, 4),
        "total_return_pct": round(total_return_pct, 4),
        "max_drawdown_pct": round(max_dd, 2),
        "avg_holding_days": round(avg_holding, 1),
        "max_consecutive_losses": max_consec,
    }

    # 所有出现的唯一标签名（扁平列表）
    all_pattern_names: set[str] = set()
    for names in patterns_raw.values():
        all_pattern_names.update(names)

    # --- insights ---
    insights = InsightEngine.analyze(positions, patterns_raw)

    # --- whatif ---
    whatif = ProfitAttribution.attribution_analysis(positions, patterns_raw)

    return {
        "position_count": pos_count,
        "trades": trade_dicts,
        "patterns": sorted(all_pattern_names),
        "patterns_dict": {str(k): sorted(v) for k, v in patterns_raw.items()},
        "primary_patterns": {str(k): v for k, v in patterns_detail.items()},
        "positions": _serialize(positions),
        "stats": stats,
        "insights": _serialize(insights),
        "whatif": _serialize(whatif),
    }


# ---------------------------------------------------------------------------
# 深层比较
# ---------------------------------------------------------------------------

def deep_compare(actual: Any, expected: Any, path: str = "") -> list[str]:
    """递归比较 actual vs expected，返回差异列表（空 = 通过）。"""
    errors: list[str] = []

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            errors.append(f"{path}: 期望 dict, 实际 {type(actual).__name__}")
            return errors
        for key, exp_val in expected.items():
            if key not in actual:
                errors.append(f"{path}.{key}: 实际输出中缺少该字段")
            else:
                errors.extend(deep_compare(actual[key], exp_val, f"{path}.{key}"))
    elif isinstance(expected, list):
        if not isinstance(actual, list):
            errors.append(f"{path}: 期望 list, 实际 {type(actual).__name__}")
            return errors
        if len(actual) != len(expected):
            errors.append(
                f"{path}: 列表长度不匹配, 期望 {len(expected)}, 实际 {len(actual)}"
            )
        else:
            try:
                key_fn = lambda x: json.dumps(x, sort_keys=True, default=str)
                act_sorted = sorted(actual, key=key_fn)
                exp_sorted = sorted(expected, key=key_fn)
            except (TypeError, ValueError):
                act_sorted, exp_sorted = actual, expected
            for i, (a, e) in enumerate(zip(act_sorted, exp_sorted)):
                errors.extend(deep_compare(a, e, f"{path}[{i}]"))
    elif isinstance(expected, float):
        if isinstance(actual, (int, float)):
            if abs(actual - expected) > 0.001:
                errors.append(f"{path}: 期望 {expected}, 实际 {actual}")
        else:
            errors.append(f"{path}: 期望数字, 实际 {type(actual).__name__}")
    elif expected is None:
        if actual is not None:
            # None 在比较中表示 "不校验" 或 "可为任意值"，跳过
            pass
    else:
        if actual != expected:
            errors.append(f"{path}: 期望 {expected!r}, 实际 {actual!r}")

    return errors


# ---------------------------------------------------------------------------
# 测试发现
# ---------------------------------------------------------------------------

def discover_tests(golden_dir: Path) -> list[tuple[str, Path, Path]]:
    """扫描 golden/<module>/ 发现全部测试用例。"""
    tests: list[tuple[str, Path, Path]] = []
    for engine_dir in sorted(golden_dir.iterdir()):
        if not engine_dir.is_dir():
            continue
        module_name = engine_dir.name
        for csv_file in sorted(engine_dir.glob("*.csv")):
            expected_file = csv_file.with_suffix(".expected.json")
            if expected_file.exists():
                tests.append((module_name, csv_file, expected_file))
    return tests


# ---------------------------------------------------------------------------
# 单用例执行
# ---------------------------------------------------------------------------

def run_single_test(
    csv_path: Path, expected_path: Path
) -> tuple[bool, list[str], dict]:
    """执行单个 golden 用例。返回 (通过, 错误列表, 实际输出)。"""
    try:
        trade_dicts = load_trades(csv_path)
    except Exception as e:
        return False, [f"CSV 解析失败: {e}"], {}

    expected_raw = expected_path.read_text(encoding="utf-8").strip()
    if not expected_raw:
        return True, ["(expected.json 为空，跳过校验)"], {}

    try:
        expected = json.loads(expected_raw)
    except json.JSONDecodeError as e:
        return False, [f"expected.json 解析失败: {e}"], {}

    # 提取 _pipeline 选项，不参与比较
    pipeline_opts = expected.pop("_pipeline", None)

    try:
        actual = run_full_pipeline(trade_dicts, pipeline_opts)
    except Exception:
        import traceback
        return False, [f"流水线异常:\n{traceback.format_exc()}"], {}

    errors = deep_compare(actual, expected)
    return len(errors) == 0, errors, actual


# ---------------------------------------------------------------------------
# 全量执行
# ---------------------------------------------------------------------------

def run_all(golden_dir: Path | None = None) -> bool:
    """执行全部 golden 测试。返回 True = 全部通过。"""
    if golden_dir is None:
        golden_dir = GOLDEN_DIR

    tests = discover_tests(golden_dir)
    if not tests:
        print("未发现 golden 测试用例。")
        return True

    passed = 0
    failed = 0
    for module_name, csv_path, expected_path in tests:
        test_name = f"[{module_name}] {csv_path.stem}"
        ok, errors, _ = run_single_test(csv_path, expected_path)
        if ok:
            print(f"  PASS  {test_name}")
            passed += 1
        else:
            print(f"  FAIL  {test_name}")
            for err in errors:
                print(f"        {err}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"结果: {passed} 通过, {failed} 失败, {passed + failed} 总计")
    return failed == 0


# ---------------------------------------------------------------------------
# pytest 集成
# ---------------------------------------------------------------------------

def pytest_generate_tests(metafunc):
    """pytest 参数化 — 为每个 golden 用例生成一条测试。"""
    if "module_name" in metafunc.fixturenames:
        cases = discover_tests(GOLDEN_DIR)
        metafunc.parametrize(
            "module_name,csv_path,expected_path",
            cases,
            ids=[f"{m}/{c.stem}" for m, c, _ in cases],
        )


def test_golden(module_name, csv_path, expected_path):
    """pytest 测试函数 — 每个 golden 用例一条。"""
    import pytest
    ok, errors, _ = run_single_test(csv_path, expected_path)
    if not ok:
        pytest.fail("\n".join(errors))


# ---------------------------------------------------------------------------
# 独立运行入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
