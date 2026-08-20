from __future__ import annotations


class EnterpriseKnowledgeError(Exception):
    code = "KNOWLEDGE_ERROR"
    http_status = 400

    def __init__(self, message: str, *, details: dict[str, str | int | bool] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class KnowledgeNotFoundError(EnterpriseKnowledgeError):
    code = "KNOWLEDGE_NOT_FOUND"
    http_status = 404


class KnowledgeAccessDeniedError(EnterpriseKnowledgeError):
    code = "KNOWLEDGE_ACCESS_DENIED"
    http_status = 403


class KnowledgeConflictError(EnterpriseKnowledgeError):
    code = "KNOWLEDGE_VERSION_CONFLICT"
    http_status = 409


class KnowledgeLifecycleError(EnterpriseKnowledgeError):
    code = "KNOWLEDGE_INVALID_LIFECYCLE"
    http_status = 409


class KnowledgeBindingError(EnterpriseKnowledgeError):
    code = "KNOWLEDGE_METRIC_BINDING_CONFLICT"
    http_status = 422


class KnowledgeValidationError(EnterpriseKnowledgeError):
    code = "KNOWLEDGE_VALIDATION_ERROR"
    http_status = 422


class KnowledgeFeatureDisabledError(EnterpriseKnowledgeError):
    code = "KNOWLEDGE_FEATURE_DISABLED"
    http_status = 503
