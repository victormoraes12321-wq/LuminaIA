from __future__ import annotations

import copy
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass

from contracts.semantic_retrieval_v2 import SemanticCacheKeyV2, SemanticSearchResultV2


@dataclass
class _CacheEntry:
    expires_at: float
    key: SemanticCacheKeyV2
    value: SemanticSearchResultV2


class SemanticRetrievalCache:
    """Bounded metadata cache. PostgreSQL remains authoritative."""

    def __init__(
        self,
        *,
        enabled: bool,
        ttl_seconds: int = 30,
        maximum_entries: int = 1000,
    ) -> None:
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.maximum_entries = maximum_entries
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()

    def get(self, key: SemanticCacheKeyV2) -> SemanticSearchResultV2 | None:
        if not self.enabled:
            return None
        item = self._entries.get(key.checksum)
        if item is None:
            return None
        if item.expires_at <= time.monotonic():
            self._entries.pop(key.checksum, None)
            return None
        self._entries.move_to_end(key.checksum)
        return copy.deepcopy(item.value)

    def put(self, key: SemanticCacheKeyV2, value: SemanticSearchResultV2) -> None:
        if not self.enabled:
            return
        self._entries[key.checksum] = _CacheEntry(
            expires_at=time.monotonic() + self.ttl_seconds,
            key=key,
            value=copy.deepcopy(value),
        )
        self._entries.move_to_end(key.checksum)
        while len(self._entries) > self.maximum_entries:
            self._entries.popitem(last=False)

    def invalidate(
        self,
        *,
        tenant_id: uuid.UUID,
        index_id: uuid.UUID | None = None,
    ) -> int:
        removed = 0
        for key, item in list(self._entries.items()):
            same_tenant = item.key.tenant_id == tenant_id
            same_index = index_id is None or item.key.index_id == index_id
            if same_tenant and same_index:
                self._entries.pop(key, None)
                removed += 1
        return removed

    def clear(self) -> None:
        self._entries.clear()

    @property
    def size(self) -> int:
        return len(self._entries)
