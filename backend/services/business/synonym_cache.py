"""Shared business synonym cache.

This module is intentionally dependency-free so Semantic Layer and Business
Layer can share synonym state without importing each other.
"""

_SYNONYM_CACHE: dict[str, str] = {}
_SYNONYM_CACHE_TENANT: str | None = None
