"""Ratchet canonical Python dependency and process-global-state findings."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "architecture-baseline.json"
SOURCE_ROOTS = (
    (ROOT / "gridlab" / "src", ""),
    (ROOT / "gridlab-studio", ""),
)
DOMAIN_PREFIXES = (
    "gridlab.accounting",
    "gridlab.api",
    "gridlab.canonical",
    "gridlab.config",
    "gridlab.core",
    "gridlab.engine",
    "gridlab.execution",
    "gridlab.strategy",
)
STUDIO_PREFIXES = ("backend", "run")
FORBIDDEN_DOMAIN_IMPORTS = {
    "azure",
    "backend",
    "binance",
    "fastapi",
    "httpx",
    "os",
    "pathlib",
    "requests",
    "sqlalchemy",
    "sqlite3",
    "uvicorn",
}
TRADING_STATE_WORDS = {
    "balance",
    "balances",
    "command",
    "commands",
    "inventory",
    "ledger",
    "order",
    "orders",
    "outbox",
    "position",
    "positions",
    "state",
}


def _module_name(path: Path, source_root: Path) -> str:
    relative = path.relative_to(source_root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _sources() -> dict[str, Path]:
    modules: dict[str, Path] = {}
    for source_root, _ in SOURCE_ROOTS:
        for path in source_root.rglob("*.py"):
            if "tests" in path.parts or "__pycache__" in path.parts:
                continue
            module = _module_name(path, source_root)
            if module:
                modules[module] = path
    return modules


def _imports(tree: ast.AST, module: str, *, is_package: bool) -> Iterable[str]:
    package = module.split(".") if is_package else module.split(".")[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                prefix = package[: len(package) - node.level + 1]
                base = ".".join([*prefix, node.module or ""]).strip(".")
            else:
                base = node.module or ""
            if base:
                yield base


def _internal_target(imported: str, modules: set[str]) -> str | None:
    candidate = imported
    while candidate:
        if candidate in modules:
            return candidate
        candidate = candidate.rpartition(".")[0]
    return None


def _cycles(graph: dict[str, set[str]]) -> list[str]:
    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    findings: list[str] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(graph[node]):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])
        if lowlinks[node] != indices[node]:
            return
        component: list[str] = []
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break
        if len(component) > 1:
            findings.append(" -> ".join(sorted(component)))
        elif node in graph[node]:
            findings.append(f"{node} -> {node}")

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return sorted(findings)


def _assigned_names(node: ast.Assign | ast.AnnAssign) -> list[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return [target.id for target in targets if isinstance(target, ast.Name)]


def _is_mutable(value: ast.expr | None) -> bool:
    if isinstance(value, ast.Tuple):
        return any(_is_mutable(element) for element in value.elts)
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
        if value.func.id in {"frozenset", "tuple"}:
            return any(_is_mutable(argument) for argument in value.args) or bool(
                value.keywords
            )
    return isinstance(
        value,
        (
            ast.Call,
            ast.Dict,
            ast.List,
            ast.Set,
            ast.ListComp,
            ast.DictComp,
            ast.SetComp,
        ),
    )


def _mutable_state_assignments(tree: ast.Module, module: str) -> list[str]:
    findings: list[str] = []
    critical_domain = module.startswith(DOMAIN_PREFIXES)
    studio = module.startswith(STUDIO_PREFIXES)
    if not critical_domain and not studio:
        return findings
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or not _is_mutable(
            node.value
        ):
            continue
        for name in _assigned_names(node):
            if name == "__all__":
                continue
            words = {part.lower() for part in name.strip("_").split("_")}
            if critical_domain or words & TRADING_STATE_WORDS:
                findings.append(f"{module}: module-level mutable {name}")
    return findings


def findings() -> dict[str, list[str]]:
    modules = _sources()
    module_names = set(modules)
    graph: dict[str, set[str]] = defaultdict(set)
    forbidden: list[str] = []
    mutable_state: list[str] = []
    for module, path in sorted(modules.items()):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for imported in _imports(tree, module, is_package=path.name == "__init__.py"):
            target = _internal_target(imported, module_names)
            if target and target != module:
                graph[module].add(target)
            root_import = imported.split(".", 1)[0]
            if (
                module.startswith(DOMAIN_PREFIXES)
                and root_import in FORBIDDEN_DOMAIN_IMPORTS
            ):
                forbidden.append(f"{module}: imports {imported}")
            if module.startswith("gridlab") and root_import == "backend":
                forbidden.append(f"{module}: imports {imported}")
        graph.setdefault(module, set())
        mutable_state.extend(_mutable_state_assignments(tree, module))
    return {
        "dependency_cycles": _cycles(graph),
        "forbidden_imports": sorted(set(forbidden)),
        "process_global_mutable_trading_state": sorted(set(mutable_state)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="print current findings as JSON"
    )
    args = parser.parse_args(argv)
    current = findings()
    if args.json:
        print(json.dumps(current, indent=2, sort_keys=True))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))["checks"]
    new_findings = {
        check: sorted(set(values) - set(baseline.get(check, [])))
        for check, values in current.items()
    }
    new_findings = {check: values for check, values in new_findings.items() if values}
    if new_findings:
        print("new architecture findings exceed the frozen baseline:", file=sys.stderr)
        print(json.dumps(new_findings, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    counts = ", ".join(f"{name}={len(values)}" for name, values in current.items())
    print(f"architecture baseline accepted: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
