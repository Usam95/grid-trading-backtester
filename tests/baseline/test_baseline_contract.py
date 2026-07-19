from __future__ import annotations

import json
import tomllib
from pathlib import Path

from backend.app import app, health


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
    engine_config = tomllib.loads((ROOT / "gridlab" / "pyproject.toml").read_text(encoding="utf-8"))
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

    assert runner.is_file()
    assert "python tools/verify_baseline.py" in report.read_text(encoding="utf-8")
    assert "Superseded values (not effective)" in catalogue.read_text(encoding="utf-8")

    baseline = json.loads(architecture_baseline.read_text(encoding="utf-8"))
    assert baseline["schema_version"] == 1
    assert set(baseline["checks"]) == {
        "dependency_cycles",
        "forbidden_imports",
        "process_global_mutable_trading_state",
    }


def test_legacy_repositories_are_named_read_only_and_not_workspace_members() -> None:
    report = (ROOT / "docs" / "baseline-report.md").read_text(encoding="utf-8")
    for legacy_name in ("backtester_old", "grid-backtest-core", "grid-backtest-saas"):
        assert f"`{legacy_name}`" in report
        assert "read-only" in report
