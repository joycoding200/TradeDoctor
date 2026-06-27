"""Drift-guard tests: the get_stats/get_insight/get_whatif slow paths in
analysis.py are hand-maintained copies of compute.compute_stats /
compute_insight / compute_whatif. The get_stats copy already drifted once and
caused the 422 snapshot bug (fixed). These tests lock the behavior so any
future divergence between the API slow path and the engine is caught immediately.

Approach: force the slow path (null the snapshots), call the endpoint, then
call compute_all directly on the same analysis and assert the two agree on the
key business fields.
"""

import pytest

from app.engine.compute import compute_all
from app.models.analysis import Analysis

QMT_CSV = (
    "委托时间,证券代码,证券名称,买卖方向,成交价格,成交数量,手续费\n"
    "2024-01-05 09:30:00,000001,平安银行,买入,10.50,1000,5.00\n"
    "2024-01-10 14:00:00,000001,平安银行,卖出,11.00,1000,5.00\n"
    "2024-02-01 09:30:00,600001,包钢股份,买入,5.00,2000,3.00\n"
    "2024-02-05 14:00:00,600001,包钢股份,卖出,4.50,2000,3.00"
)

TEST_PASSWORD = "secret123"


def _register(client, email):
    resp = client.post(
        "/api/auth/register", json={"email": email, "password": TEST_PASSWORD}
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _import(client, headers):
    r = client.post(
        "/api/upload", headers=headers, files={"file": ("t.csv", QMT_CSV, "text/csv")}
    )
    fid = r.json()["raw_file_id"]
    client.post(
        "/api/upload/confirm",
        headers=headers,
        json={"raw_file_id": fid, "source_type": "smart"},
    )
    client.post(
        "/api/upload/import", headers=headers, json={"raw_file_id": fid}
    )
    return fid


def _run(client, headers, fid):
    return client.post(
        "/api/analysis/run",
        headers=headers,
        json={
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
            "raw_file_id": fid,
        },
    ).json()["analysis_id"]


@pytest.fixture
def setup_analysis(client, db_session):
    headers = _register(client, "equiv@test.com")
    client.cookies.clear()
    fid = _import(client, headers)
    aid = _run(client, headers, fid)
    return headers, aid, fid


def _null_snapshots(db_session, aid):
    """Force the slow path on the next GET (simulate compute_all having failed
    at creation time, the exact scenario that triggered the original 422 bug)."""
    db_session.rollback()
    analysis = db_session.query(Analysis).filter_by(id=aid).first()
    assert analysis is not None
    analysis.stats_snapshot = None
    analysis.insight_snapshot = None
    analysis.whatif_snapshot = None
    db_session.commit()


def _load_analysis_and_trades(db_session, aid):
    """Reload the analysis + its trades fresh from the DB."""
    db_session.rollback()
    analysis = db_session.query(Analysis).filter_by(id=aid).first()
    from app.api.common import load_trades

    trades = load_trades(analysis, analysis.user_id, db_session)
    return analysis, trades


# Stats fields that must agree between the API slow path and compute_all.
_STATS_FIELDS = [
    "total_trades",
    "total_positions",
    "win_count",
    "loss_count",
    "win_rate",
    "total_pnl",
    "max_win",
    "max_loss",
    "consecutive_losses",
    "profit_factor",
    "max_drawdown",
    "max_drawdown_pct",
    "total_return_pct",
    "expectancy",
]


class TestStatsEquivalence:
    def test_get_stats_slow_path_equals_compute_all(self, client, db_session, setup_analysis):
        """GET /stats slow-path output must match compute_all on key fields."""
        headers, aid, fid = setup_analysis
        _null_snapshots(db_session, aid)

        resp = client.get(f"/api/analysis/{aid}/stats", headers=headers)
        assert resp.status_code == 200, resp.text
        api_stats = resp.json()

        analysis, trades = _load_analysis_and_trades(db_session, aid)
        engine_stats, _, _ = compute_all(analysis, trades, db_session)
        engine_dump = engine_stats.model_dump(mode="json")

        for field in _STATS_FIELDS:
            assert api_stats[field] == engine_dump[field], (
                f"stats drift on '{field}': API={api_stats[field]!r} "
                f"engine={engine_dump[field]!r}"
            )
        # positions count and symbol_summary count must also agree
        assert len(api_stats["positions"]) == len(engine_dump["positions"])
        assert len(api_stats["symbol_summary"]) == len(engine_dump["symbol_summary"])


class TestInsightEquivalence:
    def test_get_insight_slow_path_equals_compute_all(
        self, client, db_session, setup_analysis
    ):
        headers, aid, fid = setup_analysis
        _null_snapshots(db_session, aid)

        resp = client.get(f"/api/analysis/{aid}/insight", headers=headers)
        assert resp.status_code == 200, resp.text
        api_insight = resp.json()

        analysis, trades = _load_analysis_and_trades(db_session, aid)
        _, engine_insight, _ = compute_all(analysis, trades, db_session)
        engine_dump = engine_insight.model_dump(mode="json")

        # Best/worst pattern + baseline expectancy must agree
        assert api_insight.get("best_pattern") == engine_dump.get("best_pattern")
        assert api_insight.get("worst_pattern") == engine_dump.get("worst_pattern")
        assert api_insight.get("baseline_expectancy") == engine_dump.get(
            "baseline_expectancy"
        )
        # Same number of pattern items reported
        assert len(api_insight.get("patterns", [])) == len(
            engine_dump.get("patterns", [])
        )


class TestWhatIfEquivalence:
    def test_get_whatif_slow_path_equals_compute_all(
        self, client, db_session, setup_analysis
    ):
        headers, aid, fid = setup_analysis
        _null_snapshots(db_session, aid)

        resp = client.get(f"/api/analysis/{aid}/whatif", headers=headers)
        assert resp.status_code == 200, resp.text
        api_whatif = resp.json()

        analysis, trades = _load_analysis_and_trades(db_session, aid)
        _, _, engine_whatif = compute_all(analysis, trades, db_session)
        engine_dump = engine_whatif.model_dump(mode="json")

        # WhatIfResponse schema fields are `items` (attribution), `stop_loss`
        # (rule simulation), `shapley`. Earlier this test used wrong keys
        # ("attribution"/"rule_simulation") which silently returned [] and made
        # every assertion a no-op — the drift guard was not actually guarding.
        # Compare real values, not just lengths.
        assert len(api_whatif["items"]) == len(engine_dump["items"]), (
            f"whatif items count drift: API={len(api_whatif['items'])} "
            f"engine={len(engine_dump['items'])}"
        )
        for api_item, eng_item in zip(api_whatif["items"], engine_dump["items"]):
            assert api_item["removed_pattern"] == eng_item["removed_pattern"]
            assert api_item["delta"] == eng_item["delta"]
            assert api_item["contribution_pct"] == eng_item["contribution_pct"]

        # stop_loss is a single object (or None); compare its key fields if present
        api_sl = api_whatif["stop_loss"]
        eng_sl = engine_dump["stop_loss"]
        assert (api_sl is None) == (eng_sl is None), (
            f"stop_loss presence drift: API={'None' if api_sl is None else 'set'} "
            f"engine={'None' if eng_sl is None else 'set'}"
        )
        if api_sl is not None:
            assert api_sl["rule"] == eng_sl["rule"]
            assert api_sl["original_return"] == eng_sl["original_return"]
            assert api_sl["what_if_return"] == eng_sl["what_if_return"]
            assert api_sl["delta"] == eng_sl["delta"]
            assert api_sl["affected_positions"] == eng_sl["affected_positions"]

        # Shapley uses Monte Carlo sampling (random.shuffle, no seed), so the
        # two calls produce slightly different values for the same input — this
        # is algorithmic variance, not drift. Assert they agree on the set of
        # patterns and on each value within a sampling tolerance.
        assert len(api_whatif["shapley"]) == len(engine_dump["shapley"])
        api_sh = {s["pattern_name"]: s["shapley_value"] for s in api_whatif["shapley"]}
        eng_sh = {s["pattern_name"]: s["shapley_value"] for s in engine_dump["shapley"]}
        assert set(api_sh) == set(eng_sh), "shapley pattern set drift"
        for pat in api_sh:
            a, e = api_sh[pat], eng_sh[pat]
            # Tolerance: 5% of the larger magnitude, or 1.0 absolute (handles
            # near-zero values). Monte Carlo with 5000 samples is stable to
            # well within this.
            tol = max(abs(a), abs(e)) * 0.05 + 1.0
            assert abs(a - e) <= tol, (
                f"shapley value drift beyond sampling tolerance for '{pat}': "
                f"API={a} engine={e} tol={tol}"
            )
