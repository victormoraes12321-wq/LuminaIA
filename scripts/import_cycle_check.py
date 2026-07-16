"""Runtime import cycle detector for the backend package.

Ignores imports guarded by TYPE_CHECKING because they do not affect runtime
initialization. Exits non-zero when a real strongly connected import component
is found.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "backend"
IGNORED_PARTS = {".venv", "__pycache__", ".pytest_cache"}


def module_name(path: Path) -> str:
    return ".".join(path.relative_to(ROOT).with_suffix("").parts)


modules = {
    module_name(path): path
    for path in ROOT.rglob("*.py")
    if not any(part in IGNORED_PARTS for part in path.parts)
}
edges: dict[str, set[str]] = {name: set() for name in modules}


class ImportVisitor(ast.NodeVisitor):
    def __init__(self, current_module: str):
        self.current_module = current_module
        self.type_checking_depth = 0

    def visit_If(self, node: ast.If) -> None:
        is_type_checking = isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING"
        if is_type_checking:
            self.type_checking_depth += 1
            for child in node.body:
                self.visit(child)
            self.type_checking_depth -= 1
            for child in node.orelse:
                self.visit(child)
            return
        self.generic_visit(node)

    def _add(self, target: str) -> None:
        if self.type_checking_depth:
            return
        if target in modules:
            edges[self.current_module].add(target)
            return
        parts = target.split(".")
        while parts:
            candidate = ".".join(parts)
            if candidate in modules:
                edges[self.current_module].add(candidate)
                return
            parts.pop()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._add(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not node.module:
            return
        target = node.module
        if node.level:
            base = self.current_module.split(".")[: -node.level]
            target = ".".join(base + ([node.module] if node.module else []))
        self._add(target)
        for alias in node.names:
            self._add(f"{target}.{alias.name}")


for name, path in modules.items():
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = path.read_text(encoding="latin-1")
    ImportVisitor(name).visit(ast.parse(source))

index: dict[str, int] = {}
lowlink: dict[str, int] = {}
stack: list[str] = []
on_stack: set[str] = set()
components: list[list[str]] = []


def strongconnect(node: str) -> None:
    index[node] = lowlink[node] = len(index)
    stack.append(node)
    on_stack.add(node)

    for neighbor in edges[node]:
        if neighbor not in index:
            strongconnect(neighbor)
            lowlink[node] = min(lowlink[node], lowlink[neighbor])
        elif neighbor in on_stack:
            lowlink[node] = min(lowlink[node], index[neighbor])

    if lowlink[node] == index[node]:
        component: list[str] = []
        while True:
            current = stack.pop()
            on_stack.remove(current)
            component.append(current)
            if current == node:
                break
        if len(component) > 1:
            components.append(sorted(component))


for node in modules:
    if node not in index:
        strongconnect(node)

print(f"runtime_cycles={len(components)}")
for component in sorted(components, key=lambda item: (-len(item), item[0])):
    print(" | ".join(component))

raise SystemExit(1 if components else 0)
