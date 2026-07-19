"""Install the locked workspace and verify the frozen canonical baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
import venv
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / ".artifacts"
REPORT_PATH = ARTIFACT_DIR / "baseline-report.json"
BOOTSTRAP_ENV = ROOT / ".tools" / "uv-bootstrap"


def _required_uv_version() -> str:
    required = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["uv"][
        "required-version"
    ]
    if not required.startswith("=="):
        raise RuntimeError("tool.uv.required-version must be an exact == pin")
    return required.removeprefix("==")


def _run(command: Sequence[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", subprocess.list2cmdline(list(command)), flush=True)
    return subprocess.run(
        list(command),
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def _version_of(executable: Path) -> str | None:
    result = _run([str(executable), "--version"], capture=True)
    if result.returncode != 0 or not result.stdout:
        return None
    match = re.search(r"\b(\d+\.\d+\.\d+)\b", result.stdout)
    return match.group(1) if match else None


def _bootstrap_uv(required: str) -> Path:
    candidate_name = "uv.exe" if os.name == "nt" else "uv"
    global_uv = shutil.which("uv")
    if global_uv:
        candidate = Path(global_uv)
        if _version_of(candidate) == required:
            return candidate

    scripts = BOOTSTRAP_ENV / ("Scripts" if os.name == "nt" else "bin")
    candidate = scripts / candidate_name
    if candidate.is_file() and _version_of(candidate) == required:
        return candidate

    print(f"Bootstrapping pinned uv {required} in {BOOTSTRAP_ENV.relative_to(ROOT)}")
    venv.EnvBuilder(with_pip=True, clear=True).create(BOOTSTRAP_ENV)
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    install = _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            f"uv=={required}",
        ]
    )
    if install.returncode != 0 or not candidate.is_file():
        raise RuntimeError(f"could not bootstrap uv {required}")
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _optional_sha256(path: Path) -> str | None:
    return _sha256(path) if path.is_file() else None


def _git_identity() -> dict[str, object]:
    commit = _run(["git", "rev-parse", "HEAD"], capture=True)
    status = _run(["git", "status", "--porcelain=v1"], capture=True)
    return {
        "commit": commit.stdout.strip() if commit.returncode == 0 and commit.stdout else "UNBORN",
        "clean": status.returncode == 0 and not (status.stdout or "").strip(),
        "status": (status.stdout or "").splitlines(),
    }


def _write_report(
    *, uv: Path, steps: list[dict[str, object]], started_at: float, success: bool
) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    freeze = _run([str(uv), "pip", "freeze", "--python", str(ROOT / ".venv")], capture=True)
    report = {
        "schema_version": 1,
        "success": success,
        "generated_unix_seconds": int(time.time()),
        "duration_seconds": round(time.monotonic() - started_at, 3),
        "product_version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "source": _git_identity(),
        "dependencies": {
            "uv_lock_sha256": _optional_sha256(ROOT / "uv.lock"),
            "installed": (freeze.stdout or "").splitlines() if freeze.returncode == 0 else [],
        },
        "interpreters": {
            "python_pin": (ROOT / ".python-version").read_text(encoding="utf-8").strip(),
            "uv": _version_of(uv),
            "platform": sys.platform,
        },
        "steps": steps,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Baseline evidence: {REPORT_PATH.relative_to(ROOT)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    started_at = time.monotonic()
    uv = _bootstrap_uv(_required_uv_version())
    steps: list[dict[str, object]] = []
    commands = [
        [str(uv), "lock", "--check"],
        [str(uv), "sync", "--locked", "--all-packages", "--all-groups", "--no-editable"],
        [str(uv), "run", "--locked", "--no-sync", "python", "tools/version_contract.py"],
        [str(uv), "run", "--locked", "--no-sync", "python", "tools/check_architecture.py"],
        [
            str(uv),
            "run",
            "--locked",
            "--no-sync",
            "python",
            "tools/check_quality_baseline.py",
            "--static",
        ],
        [
            str(uv),
            "run",
            "--locked",
            "--no-sync",
            "python",
            "-m",
            "pytest",
            "--cov=gridlab",
            "--cov=backend",
            "--cov-branch",
            "--cov-report=json:.artifacts/coverage.json",
            "tests/baseline",
            "gridlab/tests",
            "gridlab-studio/tests",
        ],
        [
            str(uv),
            "run",
            "--locked",
            "--no-sync",
            "python",
            "tools/check_quality_baseline.py",
            "--coverage",
        ],
    ]
    success = True
    for command in commands:
        result = _run(command)
        steps.append({"command": command, "exit_code": result.returncode})
        if result.returncode != 0:
            success = False
            break
    _write_report(uv=uv, steps=steps, started_at=started_at, success=success)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
