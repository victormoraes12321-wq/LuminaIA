from __future__ import annotations

from typing import Any, Dict, Optional


class AIToolException(Exception):
    """Base exception for all AI Tool Registry errors."""

    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.details = details or {}


class AIToolNotFoundException(AIToolException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("AI_TOOL_NOT_FOUND", message, details)


class AIToolAccessDeniedException(AIToolException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("AI_TOOL_ACCESS_DENIED", message, details)


class AIToolTenantMismatchException(AIToolException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("AI_TOOL_TENANT_MISMATCH", message, details)


class AIToolAdapterNotRegisteredException(AIToolException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("AI_TOOL_ADAPTER_NOT_REGISTERED", message, details)


class AIToolInputInvalidException(AIToolException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("AI_TOOL_INPUT_INVALID", message, details)


class AIToolOutputInvalidException(AIToolException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("AI_TOOL_OUTPUT_INVALID", message, details)


class AIToolTimeoutException(AIToolException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("AI_TOOL_TIMEOUT", message, details)


class AIToolRateLimitedException(AIToolException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("AI_TOOL_RATE_LIMITED", message, details)


class AIToolCircuitOpenException(AIToolException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("AI_TOOL_CIRCUIT_OPEN", message, details)


class AIToolDisabledException(AIToolException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("AI_TOOL_DISABLED", message, details)


class AIToolDependencyCycleException(AIToolException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("AI_TOOL_DEPENDENCY_CYCLE", message, details)


class AIToolReservedCapabilityUnavailableException(AIToolException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("AI_TOOL_RESERVED_CAPABILITY_UNAVAILABLE", message, details)
