"""Verify the exact locked typed Studio contract, tests, and production build."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "gridlab-studio" / "frontend-typed"


def _run(command: Sequence[str]) -> None:
    print("+", subprocess.list2cmdline(list(command)), flush=True)
    result = subprocess.run(list(command), cwd=FRONTEND, check=False)
    if result.returncode:
        raise RuntimeError(f"frontend command failed with {result.returncode}")


def _output(command: Sequence[str]) -> str:
    result = subprocess.run(
        list(command),
        cwd=FRONTEND,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode:
        raise RuntimeError(result.stdout)
    return result.stdout.strip()


def _check_openapi() -> None:
    sys.path[:0] = [str(ROOT / "gridlab" / "src"), str(ROOT / "gridlab-studio")]
    from backend.app import app

    expected = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    committed = (FRONTEND / "openapi.json").read_text(encoding="utf-8")
    if committed != expected:
        raise RuntimeError(
            "frontend openapi.json is stale; run python tools/export_studio_openapi.py"
        )


def main() -> int:
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
    node = os.environ.get("GRIDLAB_NODE") or shutil.which("node")
    pnpm = os.environ.get("GRIDLAB_PNPM") or shutil.which("pnpm")
    if node is None or pnpm is None:
        raise RuntimeError("Node and pnpm must be on PATH for frontend verification")

    expected_node = package["engines"]["node"]
    expected_pnpm = package["engines"]["pnpm"]
    actual_node = _output([node, "--version"]).removeprefix("v")
    actual_pnpm = _output([pnpm, "--version"])
    if (actual_node, actual_pnpm) != (expected_node, expected_pnpm):
        raise RuntimeError(
            "frontend toolchain mismatch: "
            f"node {actual_node}/pnpm {actual_pnpm}, "
            f"expected node {expected_node}/pnpm {expected_pnpm}"
        )

    _run([pnpm, "install", "--frozen-lockfile"])
    _check_openapi()
    with tempfile.TemporaryDirectory(prefix="gridlab-contract-") as temporary:
        generated = Path(temporary) / "schema.d.ts"
        _run(
            [
                pnpm,
                "exec",
                "openapi-typescript",
                "openapi.json",
                "-o",
                str(generated),
            ]
        )
        committed = FRONTEND / "src" / "api" / "schema.d.ts"
        if generated.read_bytes() != committed.read_bytes():
            raise RuntimeError("generated TypeScript contract is stale")

    for script in ("typecheck", "test", "build", "test:browser"):
        _run([pnpm, "run", script])
    print("typed frontend verification accepted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
