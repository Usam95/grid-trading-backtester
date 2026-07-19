"""Ratchet formatting, lint, typing, and coverage against Ticket 01."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence, TypedDict, cast


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "quality-baseline.json"
COVERAGE_PATH = ROOT / ".artifacts" / "coverage.json"
SOURCES = (
    "gridlab/src",
    "gridlab-studio/backend",
    "gridlab-studio/run.py",
    "tools",
    "tests/baseline",
)


class CoverageScope(TypedDict):
    line_percent: float
    branch_percent: float
    covered_lines: int
    covered_branches: int


class CoverageMeasurement(TypedDict):
    overall: CoverageScope
    packages: dict[str, CoverageScope]


def _package_name(path: str) -> str:
    normalized = path.replace("\\", "/")
    engine_prefix = "gridlab/src/gridlab/"
    studio_prefix = "gridlab-studio/backend/"
    if normalized == "gridlab-studio/run.py":
        return "gridlab-studio.entrypoint"
    if normalized.startswith(studio_prefix):
        return "gridlab-studio.backend"
    if normalized.startswith(engine_prefix):
        relative = normalized.removeprefix(engine_prefix)
        first = relative.split("/", 1)[0]
        return "gridlab" if first.endswith(".py") else f"gridlab.{first}"
    raise ValueError(f"unclassified production coverage path: {path}")


def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _relative(path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.relative_to(ROOT).as_posix()
    return candidate.as_posix()


def static_findings() -> dict[str, list[str]]:
    formatting_result = _run(
        [sys.executable, "-m", "ruff", "format", "--check", *SOURCES]
    )
    formatting = sorted(
        _relative(line.partition(":")[2].strip())
        for line in formatting_result.stdout.splitlines()
        if line.startswith("Would reformat:")
    )

    lint_result = _run(
        [sys.executable, "-m", "ruff", "check", "--output-format", "json", *SOURCES]
    )
    lint_payload = json.loads(lint_result.stdout or "[]")
    lint = sorted(
        {
            f"{_relative(item['filename'])}:{item['location']['row']}:{item['code']}"
            for item in lint_payload
        }
    )

    typing_result = _run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--no-incremental",
            "--explicit-package-bases",
            "--check-untyped-defs",
            "--ignore-missing-imports",
            "--show-error-codes",
            "--no-error-summary",
            *SOURCES,
        ]
    )
    typing_pattern = re.compile(r"^(.*?):(\d+): error: .*?\[([^]]+)]$")
    typing: list[str] = []
    for line in typing_result.stdout.splitlines():
        match = typing_pattern.match(line)
        if match:
            typing.append(
                f"{_relative(match.group(1))}:{match.group(2)}:{match.group(3)}"
            )
    return {"formatting": formatting, "lint": lint, "typing": sorted(set(typing))}


def coverage_measurement() -> CoverageMeasurement:
    report = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    grouped: dict[str, dict[str, int]] = {}
    metrics = ("covered_lines", "num_statements", "covered_branches", "num_branches")
    for path, evidence in report["files"].items():
        package = _package_name(path)
        totals = grouped.setdefault(package, {metric: 0 for metric in metrics})
        summary = evidence["summary"]
        for metric in metrics:
            totals[metric] += int(summary[metric])

    def measurement(totals: dict[str, int]) -> CoverageScope:
        line_rate = 100.0 * totals["covered_lines"] / totals["num_statements"]
        branch_rate = 100.0
        if totals["num_branches"]:
            branch_rate = 100.0 * totals["covered_branches"] / totals["num_branches"]
        return {
            "line_percent": round(line_rate, 4),
            "branch_percent": round(branch_rate, 4),
            "covered_lines": totals["covered_lines"],
            "covered_branches": totals["covered_branches"],
        }

    overall = {metric: int(report["totals"][metric]) for metric in metrics}
    return {
        "overall": measurement(overall),
        "packages": {
            name: measurement(values) for name, values in sorted(grouped.items())
        },
    }


def _check_static(
    current: dict[str, list[str]], baseline: dict[str, object]
) -> list[str]:
    errors: list[str] = []
    for check, findings in current.items():
        allowed = set(cast(list[str], baseline[check]))
        additions = sorted(set(findings) - allowed)
        if additions:
            errors.append(f"new {check} findings: {json.dumps(additions)}")
    return errors


def _check_coverage(
    current: CoverageMeasurement, baseline: dict[str, object]
) -> list[str]:
    expected = cast(dict[str, object], baseline["coverage"])
    errors: list[str] = []

    def compare(scope: str, actual: CoverageScope, floor: CoverageScope) -> None:
        for metric in ("line_percent", "branch_percent"):
            if float(actual[metric]) < float(floor[metric]):
                errors.append(
                    f"{scope} {metric} decreased: {actual[metric]} < {floor[metric]}"
                )

    compare("overall", current["overall"], cast(CoverageScope, expected["overall"]))
    actual_packages = current["packages"]
    expected_packages = cast(dict[str, CoverageScope], expected["packages"])
    if set(actual_packages) != set(expected_packages):
        errors.append(
            "coverage package classification changed: "
            f"{sorted(actual_packages)} != {sorted(expected_packages)}"
        )
    for package in sorted(set(actual_packages) & set(expected_packages)):
        compare(package, actual_packages[package], expected_packages[package])
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--static", action="store_true", help="check formatting, lint, and typing"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="check the generated coverage report"
    )
    parser.add_argument(
        "--measure-static", action="store_true", help="print current static findings"
    )
    parser.add_argument(
        "--measure-coverage", action="store_true", help="print current coverage values"
    )
    args = parser.parse_args(argv)
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    if args.static or args.measure_static:
        current_static = static_findings()
        if args.measure_static:
            print(json.dumps(current_static, indent=2, sort_keys=True))
        if args.static:
            errors.extend(_check_static(current_static, baseline["checks"]))
    if args.coverage or args.measure_coverage:
        current_coverage = coverage_measurement()
        if args.measure_coverage:
            print(json.dumps(current_coverage, indent=2, sort_keys=True))
        if args.coverage:
            errors.extend(_check_coverage(current_coverage, baseline["checks"]))
    if not any(
        (args.static, args.coverage, args.measure_static, args.measure_coverage)
    ):
        parser.error("select at least one check or measurement")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.static:
        print("static quality baseline accepted")
    if args.coverage:
        print("coverage baseline accepted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
