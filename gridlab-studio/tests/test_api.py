"""API smoke + contract tests for gridlab-studio.

Uses FastAPI's TestClient (no live server needed). Data sizes are kept small so
the whole suite runs in a couple of seconds while still exercising every route
and the engine/service serialization path end-to-end.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


# A small, fast, deterministic spec reused across tests.
SMALL_SPEC = {
    "symbol": "TESTUSDT",
    "market_type": "spot",
    "initial_cash": 10_000.0,
    "grid": {"levels": 8, "lower": 90.0, "upper": 110.0, "spacing": "arithmetic", "direction": "neutral"},
    "sizing": {"mode": "fixed_quote", "value": 50.0},
    "data": {"kind": "synthetic", "n": 300, "start_price": 100.0, "seed": 7, "sigma": 0.01, "regime": "range"},
}


def _body(**over):
    spec = {**SMALL_SPEC, **over}
    return {"spec": spec}


# --------------------------------------------------------------------------- meta

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_meta_payload():
    r = client.get("/api/meta")
    assert r.status_code == 200
    data = r.json()
    for key in ("presets", "default_spec", "metric_meta", "headline_metrics", "guide", "enums", "objectives"):
        assert key in data, f"missing meta key {key}"
    assert len(data["presets"]) >= 3
    assert "deflated_sharpe" in data["objectives"]
    # every headline metric must have metadata
    for m in data["headline_metrics"]:
        assert m in data["metric_meta"]


# --------------------------------------------------------------------- grid preview

def test_grid_preview_returns_rungs():
    r = client.post("/api/grid-preview", json=_body())
    assert r.status_code == 200
    g = r.json()
    assert "levels" in g and len(g["levels"]) == 8
    assert g["lower"] < g["center"] < g["upper"]


# ------------------------------------------------------------------------- backtest

def test_backtest_core_payload():
    r = client.post("/api/backtest", json={"spec": SMALL_SPEC, "options": {"include_trades": True}})
    assert r.status_code == 200, r.text
    d = r.json()
    # metrics block
    assert "metrics" in d and "total_return" in d["metrics"]
    # aligned series share one length
    s = d["series"]
    n = len(s["equity"])
    assert n > 0
    for key in ("price", "buy_and_hold", "dca", "drawdown"):
        assert len(s[key]) == n, f"series {key} misaligned"
    # narrative layer
    assert isinstance(d["insights"], list) and d["insights"]
    assert "label" in d["verdict"] and "score" in d["verdict"]
    # benchmarks + trades
    assert "buy_and_hold" in d["benchmarks"] and "dca" in d["benchmarks"]
    assert isinstance(d["trades"], list)


def test_backtest_trade_marker_positions_are_in_range():
    r = client.post("/api/backtest", json={"spec": SMALL_SPEC, "options": {"include_trades": True}})
    d = r.json()
    n = len(d["series"]["equity"])
    for t in d["trades"]:
        assert 0 <= t["exit_x"] <= n - 1, "exit marker x out of downsampled range"
        assert 0 <= t["entry_x"] <= n - 1, "entry marker x out of downsampled range"


def test_backtest_with_report():
    r = client.post("/api/backtest", json={"spec": SMALL_SPEC, "options": {"with_report": True}})
    assert r.status_code == 200
    assert "<html" in r.json()["html_report"].lower()


def test_report_download_is_attachment():
    r = client.post("/api/report", json={"spec": SMALL_SPEC})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "attachment" in r.headers["content-disposition"]
    assert b"<html" in r.content.lower()


def test_backtest_validation_error_is_422():
    bad = {**SMALL_SPEC, "grid": {**SMALL_SPEC["grid"], "levels": 1}}  # below ge=2
    r = client.post("/api/backtest", json={"spec": bad})
    assert r.status_code == 422


# ------------------------------------------------------------------------- research

def test_grid_search_leaderboard_and_heatmap():
    body = {
        "base": SMALL_SPEC,
        "space": {"grid.levels": [6, 8], "sizing.value": [40, 60]},
        "objective": "total_return",
    }
    r = client.post("/api/research/grid-search", json=body)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["n_results"] == 4
    assert d["heatmap"] is not None
    assert len(d["heatmap"]["z"]) == 2 and len(d["heatmap"]["z"][0]) == 2
    # leaderboard sorted by score descending
    scores = [row["score"] for row in d["results"]]
    assert scores == sorted(scores, reverse=True)


def test_walk_forward_folds():
    body = {
        "base": SMALL_SPEC,
        "space": {"grid.levels": [6, 8]},
        "n_splits": 3,
        "objective": "total_return",
    }
    r = client.post("/api/research/walk-forward", json=body)
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["folds"]) == 3
    for f in d["folds"]:
        assert "is_score" in f and "oos_score" in f
    assert "mean_oos_score" in d["summary"]


def test_monte_carlo_distribution():
    body = {"base": SMALL_SPEC, "method": "trades", "n_sims": 300, "seed": 1}
    r = client.post("/api/research/monte-carlo", json=body)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "final_return" in d  # percentile dict (p5/p25/p50/...)
    assert isinstance(d["final_return"], dict) and d["final_return"]
    assert d["histogram"]["counts"], "expected histogram bins"
    assert len(d["histogram"]["centers"]) == len(d["histogram"]["counts"])


# --------------------------------------------------------------------------- spa

def test_spa_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "gridlab" in r.text.lower()
