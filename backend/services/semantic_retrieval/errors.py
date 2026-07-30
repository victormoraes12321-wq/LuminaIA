from __future__ import annotations


class SemanticRetrievalError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


ERROR_STATUS: dict[str, int] = {
    "SEMANTIC_INDEX_NOT_FOUND": 404,
    "SEMANTIC_INDEX_ACCESS_DENIED": 403,
    "SEMANTIC_INDEX_TENANT_MISMATCH": 404,
    "SEMANTIC_INDEX_VERSION_CONFLICT": 409,
    "SEMANTIC_INDEX_BUILD_FAILED": 422,
    "SEMANTIC_INDEX_NOT_READY": 409,
    "SEMANTIC_INDEX_STALE": 409,
    "SEMANTIC_INDEX_IMMUTABLE": 409,
    "SEMANTIC_PROVIDER_UNAVAILABLE": 503,
    "SEMANTIC_PROVIDER_CONFIGURATION_INVALID": 422,
    "SEMANTIC_QUERY_INVALID": 422,
    "SEMANTIC_QUERY_TOO_LARGE": 413,
    "SEMANTIC_CANDIDATE_NOT_FOUND": 404,
    "SEMANTIC_CANDIDATE_FORBIDDEN": 403,
    "SEMANTIC_AMBIGUOUS": 409,
    "SEMANTIC_UNRESOLVED": 422,
    "ENTITY_TYPE_INCOMPATIBLE": 422,
    "ENTITY_REFERENCE_INVALID": 422,
    "ENTITY_REFERENCE_DEPRECATED": 409,
    "ENTITY_RESOLUTION_FORBIDDEN": 403,
    "ENTITY_CLARIFICATION_EXPIRED": 410,
    "ENTITY_CLARIFICATION_INVALID_OPTION": 422,
    "SEMANTIC_SOURCE_STALE": 409,
    "SEMANTIC_CONTENT_FORBIDDEN": 422,
}


def semantic_error(code: str, message: str) -> SemanticRetrievalError:
    return SemanticRetrievalError(code, message, status_code=ERROR_STATUS.get(code, 422))
