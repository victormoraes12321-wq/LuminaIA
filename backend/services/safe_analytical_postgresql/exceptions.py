from __future__ import annotations

from typing import Any, Dict, Optional


class AnalyticalError(Exception):
    def __init__(self, message: str, error_code: str = "ANALYTICAL_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class AnalyticalCatalogError(AnalyticalError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="ANALYTICAL_CATALOG_ERROR", details=details)


class AnalyticalCompilationError(AnalyticalError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="ANALYTICAL_COMPILATION_ERROR", details=details)


class AnalyticalSecurityViolationError(AnalyticalError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="ANALYTICAL_SECURITY_VIOLATION", details=details)


class AnalyticalBudgetExceededError(AnalyticalError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="ANALYTICAL_BUDGET_EXCEEDED", details=details)


class AnalyticalConnectionGuardError(AnalyticalError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="ANALYTICAL_CONNECTION_GUARD_ERROR", details=details)


class AnalyticalExecutionError(AnalyticalError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="ANALYTICAL_EXECUTION_ERROR", details=details)
