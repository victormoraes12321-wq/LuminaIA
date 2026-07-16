from __future__ import annotations

import ast
import os
import re
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def ascii_text(value: str) -> str:
    value = value.replace("\u2192", "->").replace("\u2014", "-").replace("\u2013", "-")
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(ascii_text(content).strip() + "\n", encoding="utf-8")


def list_py_modules(base: str) -> list[tuple[str, list[str], list[str]]]:
    rows: list[tuple[str, list[str], list[str]]] = []
    for file in sorted((ROOT / base).rglob("*.py")):
        if any(part in {"__pycache__", ".venv"} for part in file.parts):
            continue
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"))
        except Exception:
            continue
        classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
        funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        rows.append((file.relative_to(ROOT).as_posix(), classes, funcs))
    return rows


def list_frontend_files(base: str) -> list[str]:
    rows: list[str] = []
    for file in sorted((ROOT / base).rglob("*")):
        if not file.is_file():
            continue
        if any(part in {"node_modules", ".next", "playwright-report", "test-results"} for part in file.parts):
            continue
        if file.suffix.lower() in {".ts", ".tsx", ".css", ".mjs", ".json"}:
            rows.append(file.relative_to(ROOT).as_posix())
    return rows


def parse_tables() -> list[str]:
    sql_path = ROOT / "backend/database/init.sql"
    if not sql_path.exists():
        return []
    sql = sql_path.read_text(encoding="utf-8", errors="ignore")
    tables = re.findall(r"CREATE TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([a-zA-Z0-9_\.]+)", sql, flags=re.I)
    return sorted(set(tables))


def generate_api_reference() -> None:
    os.chdir(ROOT / "backend")
    sys.path.insert(0, str(ROOT / "backend"))
    from main import app  # type: ignore

    schema = app.openapi()
    os.chdir(ROOT)

    lines = [
        "# API Reference - LuminaAI",
        "",
        "Fonte: gerado a partir do schema OpenAPI exposto por `backend/main.py`.",
        "",
        "Observacoes:",
        "",
        "- A autenticacao principal usa JWT emitido pelo backend e enviado por cookie HttpOnly e/ou Bearer token conforme fluxo atual.",
        "- Rotas sob `/api/v1/api/v1/query` existem por compatibilidade com clientes antigos que duplicavam o prefixo no `base_url`.",
        "- Campos exatos de payload/resposta seguem os DTOs em `backend/schemas` e o schema OpenAPI.",
        "",
        "| Metodo | Endpoint | Tag | Objetivo | Autenticacao |",
        "| --- | --- | --- | --- | --- |",
    ]

    for path, ops in sorted(schema.get("paths", {}).items()):
        for method, op in sorted(ops.items()):
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            tags = ", ".join(op.get("tags") or [])
            summary = op.get("summary") or op.get("operationId") or ""
            security = "JWT/Depends" if path.startswith("/api/v1") and not path.startswith("/api/v1/auth/login") else "Publica ou sessao"
            lines.append(f"| `{method.upper()}` | `{path}` | {tags} | {summary} | {security} |")

    lines += ["", "## Detalhamento Por Endpoint", ""]
    for path, ops in sorted(schema.get("paths", {}).items()):
        for method, op in sorted(ops.items()):
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            lines.append(f"### `{method.upper()} {path}`")
            lines.append("")
            lines.append(f"- Nome: `{op.get('operationId', '')}`")
            lines.append(f"- Objetivo: {op.get('summary') or 'Nao informado no schema.'}")
            lines.append(f"- Tags: {', '.join(op.get('tags') or []) or 'Sem tag'}")
            params = op.get("parameters") or []
            if params:
                lines.append("- Parametros:")
                for param in params:
                    req = "obrigatorio" if param.get("required") else "opcional"
                    lines.append(f"  - `{param.get('name')}` em `{param.get('in')}` ({req})")
            else:
                lines.append("- Parametros: nenhum parametro explicito no schema.")
            body = op.get("requestBody")
            if body:
                refs: list[str] = []
                for media in (body.get("content") or {}).values():
                    schema_obj = media.get("schema") or {}
                    ref = schema_obj.get("$ref") or schema_obj.get("type")
                    if ref:
                        refs.append(ref.split("/")[-1])
                lines.append(f"- Payload: {', '.join(sorted(set(refs))) or 'definido inline no OpenAPI'}")
            else:
                lines.append("- Payload: sem corpo de requisicao.")
            responses = ", ".join(sorted((op.get("responses") or {}).keys()))
            lines.append(f"- Codigos HTTP documentados: {responses}")
            lines.append("- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.")
            lines.append("- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.")
            lines.append("")

    write("docs/api-reference.md", "\n".join(lines))


def generate_source_inventory() -> None:
    lines = ["# Inventario De Codigo", "", "Fonte: varredura local de arquivos Python/TypeScript relevantes.", ""]
    for base in ["backend/models", "backend/schemas", "backend/routers", "backend/services"]:
        lines.append(f"## {base}")
        lines.append("")
        lines.append("| Arquivo | Classes | Funcoes |")
        lines.append("| --- | --- | --- |")
        for file, classes, funcs in list_py_modules(base):
            lines.append(f"| `{file}` | {', '.join(classes) or '-'} | {', '.join(funcs[:12]) or '-'} |")
        lines.append("")

    for base in ["frontend/app", "frontend/components", "frontend/hooks", "frontend/engines", "frontend/lib", "frontend/types"]:
        lines.append(f"## {base}")
        lines.append("")
        for file in list_frontend_files(base):
            lines.append(f"- `{file}`")
        lines.append("")

    lines.append("## Tabelas Detectadas Em `backend/database/init.sql`")
    lines.append("")
    for table in parse_tables():
        lines.append(f"- `{table}`")
    lines.append("")

    write("docs/source-inventory.md", "\n".join(lines))


if __name__ == "__main__":
    generate_api_reference()
    generate_source_inventory()
    print("Generated docs/api-reference.md and docs/source-inventory.md")
