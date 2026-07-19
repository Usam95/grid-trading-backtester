"""Check or generate product-version surfaces from the root VERSION file."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"
PACKAGE_PROJECTS = (ROOT / "gridlab" / "pyproject.toml", ROOT / "gridlab-studio" / "pyproject.toml")
GENERATED_MODULE = ROOT / "gridlab" / "src" / "gridlab" / "_version.py"
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def authoritative_version() -> str:
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not SEMVER.fullmatch(version):
        raise ValueError(f"VERSION must contain one semantic version, got {version!r}")
    return version


def _replace_project_version(path: Path, version: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^(version\s*=\s*)"[^"]+"\s*$',
        rf'\1"{version}"',
        text,
        count=1,
    )
    if count != 1:
        raise ValueError(f"expected one project version in {path}")
    path.write_text(updated, encoding="utf-8")


def sync() -> None:
    version = authoritative_version()
    for path in PACKAGE_PROJECTS:
        _replace_project_version(path, version)
    GENERATED_MODULE.write_text(
        '"""Generated product version. The authoritative source is the root VERSION file."""\n\n'
        f'__version__ = "{version}"\n',
        encoding="utf-8",
    )


def check() -> list[str]:
    expected = authoritative_version()
    errors: list[str] = []
    for path in PACKAGE_PROJECTS:
        actual = tomllib.loads(path.read_text(encoding="utf-8"))["project"]["version"]
        if actual != expected:
            errors.append(f"{path.relative_to(ROOT)} reports {actual}; expected {expected}")
    expected_assignment = f'__version__ = "{expected}"'
    if expected_assignment not in GENERATED_MODULE.read_text(encoding="utf-8"):
        errors.append(f"{GENERATED_MODULE.relative_to(ROOT)} is not generated from VERSION")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true", help="regenerate declared version surfaces")
    args = parser.parse_args(argv)
    if args.sync:
        sync()
    errors = check()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"product version: {authoritative_version()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

