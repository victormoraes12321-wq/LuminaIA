from __future__ import annotations

import json

import pytest

from main import app
from services.semantic_retrieval.checksums import checksum_for


pytestmark = pytest.mark.no_database


def test_semantic_openapi_is_deterministic_and_exposes_versioned_routes() -> None:
    first = app.openapi()
    app.openapi_schema = None
    second = app.openapi()
    assert checksum_for(first) == checksum_for(second)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    paths = second["paths"]
    operation_count = sum(
        method.lower()
        in {"get", "post", "put", "patch", "delete", "options", "head"}
        for operations in paths.values()
        for method in operations
    )
    semantic_paths = {
        path: operations
        for path, operations in paths.items()
        if path.startswith("/api/v2/semantic")
    }
    semantic_operation_count = sum(
        method.lower()
        in {"get", "post", "put", "patch", "delete", "options", "head"}
        for operations in semantic_paths.values()
        for method in operations
    )
    assert len(paths) == 170
    assert operation_count == 195
    assert len(semantic_paths) == 21
    assert semantic_operation_count == 22
    required = {
        "/api/v2/semantic/capabilities",
        "/api/v2/semantic/search",
        "/api/v2/semantic/resolve",
        "/api/v2/semantic/entities/resolve",
        "/api/v2/semantic/candidates/{document_id}",
        "/api/v2/semantic/clarifications/{clarification_id}/resolve",
        "/api/v2/semantic/admin/indexes",
        "/api/v2/semantic/admin/indexes/{index_id}/build",
        "/api/v2/semantic/admin/indexes/{index_id}/publish",
        "/api/v2/semantic/admin/indexes/{index_id}/rollback",
        "/api/v2/semantic/admin/indexes/{index_id}/stale-sources",
        "/api/v2/semantic/admin/indexes/{index_id}/evaluations",
    }
    assert required.issubset(paths)

    search_schema = paths["/api/v2/semantic/search"]["post"]
    assert search_schema["requestBody"]["required"] is True
    assert "200" in search_schema["responses"]
    assert "422" in search_schema["responses"]
