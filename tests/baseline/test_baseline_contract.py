from __future__ import annotations

import json
import ast
import tomllib
from pathlib import Path

from backend.app import app, health
from tools.check_architecture import _imports, _mutable_state_assignments


ROOT = Path(__file__).resolve().parents[2]


def test_canonical_workspace_contract_is_declared_at_repository_root() -> None:
    root_config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert root_config["tool"]["uv"]["workspace"]["members"] == [
        "gridlab",
        "gridlab-studio",
    ]
    assert root_config["tool"]["uv"]["required-version"].startswith("==")
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12.10"
    assert (ROOT / "uv.lock").is_file()


def test_one_product_version_drives_every_visible_surface() -> None:
    expected = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    engine_config = tomllib.loads(
        (ROOT / "gridlab" / "pyproject.toml").read_text(encoding="utf-8")
    )
    studio_config = tomllib.loads(
        (ROOT / "gridlab-studio" / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert expected == "1.0.0"
    assert engine_config["project"]["version"] == expected
    assert studio_config["project"]["version"] == expected

    engine_version = (ROOT / "gridlab" / "src" / "gridlab" / "_version.py").read_text(
        encoding="utf-8"
    )
    assert f'__version__ = "{expected}"' in engine_version
    assert 'version="1.0.0"' not in (
        ROOT / "gridlab-studio" / "backend" / "app.py"
    ).read_text(encoding="utf-8")
    assert app.version == expected
    assert health()["version"] == expected


def test_baseline_has_one_operator_entry_point_and_inspectable_contracts() -> None:
    runner = ROOT / "tools" / "verify_baseline.py"
    catalogue = ROOT / "docs" / "current-normative-values.md"
    report = ROOT / "docs" / "baseline-report.md"
    architecture_baseline = ROOT / "architecture-baseline.json"
    quality_baseline = ROOT / "quality-baseline.json"

    assert runner.is_file()
    assert "python tools/verify_baseline.py" in report.read_text(encoding="utf-8")
    catalogue_text = catalogue.read_text(encoding="utf-8")
    assert "Superseded values (not effective)" in catalogue_text
    for system_life_evidence in (
        "Complete authoritative evidence",
        "Exact promotion datasets and captures",
        "Qualifying Paper, Testnet, and first-live bundles",
        "Critical incidents",
    ):
        assert any(
            line.startswith(f"| {system_life_evidence}")
            and "| **Life of the system** |" in line
            for line in catalogue_text.splitlines()
        )

    baseline = json.loads(architecture_baseline.read_text(encoding="utf-8"))
    assert baseline["schema_version"] == 1
    assert set(baseline["checks"]) == {
        "dependency_cycles",
        "forbidden_imports",
        "process_global_mutable_trading_state",
    }
    quality = json.loads(quality_baseline.read_text(encoding="utf-8"))
    assert set(quality["checks"]) == {"formatting", "lint", "typing", "coverage"}


def test_legacy_repositories_are_named_read_only_and_not_workspace_members() -> None:
    report = (ROOT / "docs" / "baseline-report.md").read_text(encoding="utf-8")
    for legacy_name in ("backtester_old", "grid-backtest-core", "grid-backtest-saas"):
        assert f"`{legacy_name}`" in report
        assert "read-only" in report


def test_architecture_analysis_resolves_package_relative_imports() -> None:
    tree = ast.parse("from .ledger import Ledger")
    assert list(_imports(tree, "gridlab.accounting", is_package=True)) == [
        "gridlab.accounting.ledger"
    ]


def test_architecture_analysis_detects_critical_and_studio_mutable_state() -> None:
    critical = ast.parse("_VENUE_PRESETS = {'BTCUSDT': object()}")
    studio = ast.parse("active_orders = []")
    assert _mutable_state_assignments(critical, "gridlab.execution.rules") == [
        "gridlab.execution.rules: module-level mutable _VENUE_PRESETS"
    ]
    assert _mutable_state_assignments(studio, "backend.runtime") == [
        "backend.runtime: module-level mutable active_orders"
    ]
    final_container = ast.parse("active_orders: Final[list[int]] = []")
    assert _mutable_state_assignments(final_container, "backend.runtime") == [
        "backend.runtime: module-level mutable active_orders"
    ]
    nested_tuple = ast.parse("active_orders = ([],)")
    constructed_tuple = ast.parse("active_orders = tuple([[]])")
    for tree in (nested_tuple, constructed_tuple):
        assert _mutable_state_assignments(tree, "backend.runtime") == [
            "backend.runtime: module-level mutable active_orders"
        ]
