from __future__ import annotations

import time
import uuid
from collections import Counter
from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha256

from contracts.enterprise_knowledge_v2 import KnowledgeResolutionResultV2


@dataclass(frozen=True)
class _CacheEntry:
    expires_at: float
    value: KnowledgeResolutionResultV2


class EnterpriseKnowledgeCache:
    """Small bounded process cache; keys never cross tenant or published checksum."""

    def __init__(self, *, enabled: bool, ttl_seconds: int = 60, max_entries: int = 1000) -> None:
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._query_keys: dict[str, str] = {}
        self._counters: Counter[str] = Counter()

    @staticmethod
    def key(
        *,
        tenant_id: uuid.UUID,
        locale: str,
        normalized_query: str,
        publication_epoch: str,
    ) -> str:
        return f"{tenant_id}:{locale}:{publication_epoch}:{normalized_query}"

    def get(self, key: str) -> KnowledgeResolutionResultV2 | None:
        if not self.enabled:
            return None
        entry = self._entries.get(key)
        if entry is None:
            self._counters["misses"] += 1
            return None
        if entry.expires_at <= time.monotonic():
            self._entries.pop(key, None)
            for query_key, entry_key in tuple(self._query_keys.items()):
                if entry_key == key:
                    self._query_keys.pop(query_key, None)
            self._counters["misses"] += 1
            return None
        self._entries.move_to_end(key)
        self._counters["hits"] += 1
        return entry.value.model_copy(deep=True)

    def set(self, key: str, value: KnowledgeResolutionResultV2) -> None:
        if not self.enabled:
            return
        self._entries[key] = _CacheEntry(
            expires_at=time.monotonic() + self.ttl_seconds,
            value=value.model_copy(deep=True),
        )
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            evicted_key, _ = self._entries.popitem(last=False)
            for query_key, entry_key in tuple(self._query_keys.items()):
                if entry_key == evicted_key:
                    self._query_keys.pop(query_key, None)

    @staticmethod
    def query_key(
        *,
        tenant_id: uuid.UUID,
        locale: str,
        normalized_query: str,
        effective_at: str,
    ) -> str:
        return f"{tenant_id}:{locale}:{effective_at}:{normalized_query}"

    def get_resolution(
        self,
        *,
        tenant_id: uuid.UUID,
        locale: str,
        normalized_query: str,
        effective_at: str,
    ) -> KnowledgeResolutionResultV2 | None:
        if not self.enabled:
            return None
        query_key = self.query_key(
            tenant_id=tenant_id,
            locale=locale,
            normalized_query=normalized_query,
            effective_at=effective_at,
        )
        entry_key = self._query_keys.get(query_key)
        if entry_key is None:
            self._counters["misses"] += 1
            return None
        return self.get(entry_key)

    def set_resolution(
        self,
        *,
        tenant_id: uuid.UUID,
        locale: str,
        normalized_query: str,
        effective_at: str,
        value: KnowledgeResolutionResultV2,
    ) -> None:
        if not self.enabled:
            return
        publication_fingerprint = sha256(
            "|".join(candidate.checksum for candidate in value.candidates).encode("ascii")
        ).hexdigest()
        entry_key = self.key(
            tenant_id=tenant_id,
            locale=locale,
            normalized_query=normalized_query,
            publication_epoch=publication_fingerprint,
        )
        query_key = self.query_key(
            tenant_id=tenant_id,
            locale=locale,
            normalized_query=normalized_query,
            effective_at=effective_at,
        )
        self.set(entry_key, value)
        self._query_keys[query_key] = entry_key

    def invalidate_tenant(self, tenant_id: uuid.UUID) -> None:
        prefix = f"{tenant_id}:"
        for key in tuple(self._entries):
            if key.startswith(prefix):
                self._entries.pop(key, None)
        for key in tuple(self._query_keys):
            if key.startswith(prefix):
                self._query_keys.pop(key, None)
        self._counters["invalidations"] += 1

    def clear(self) -> None:
        self._entries.clear()
        self._query_keys.clear()

    def snapshot(self) -> dict[str, int]:
        return {
            "entries": len(self._entries),
            "query_keys": len(self._query_keys),
            "hits": self._counters["hits"],
            "misses": self._counters["misses"],
            "invalidations": self._counters["invalidations"],
        }
