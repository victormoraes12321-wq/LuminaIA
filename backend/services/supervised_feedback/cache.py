from __future__ import annotations

import time
import uuid
from collections import Counter, OrderedDict
from dataclasses import dataclass

from contracts.supervised_feedback_v2 import TrainingDatasetManifestV2


@dataclass(frozen=True)
class _ManifestEntry:
    expires_at: float
    manifest: TrainingDatasetManifestV2


class FeedbackMetadataCache:
    """Bounded cache for published manifests only; raw feedback is never accepted."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        ttl_seconds: int = 30,
        max_entries: int = 500,
    ) -> None:
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._items: OrderedDict[
            tuple[uuid.UUID, uuid.UUID, int, str], _ManifestEntry
        ] = OrderedDict()
        self._counters: Counter[str] = Counter()

    @staticmethod
    def key(
        *,
        tenant_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        version: int,
        checksum: str,
    ) -> tuple[uuid.UUID, uuid.UUID, int, str]:
        return tenant_id, snapshot_id, version, checksum

    def get_manifest(
        self,
        *,
        tenant_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        version: int,
        checksum: str,
    ) -> TrainingDatasetManifestV2 | None:
        if not self.enabled:
            return None
        key = self.key(
            tenant_id=tenant_id,
            snapshot_id=snapshot_id,
            version=version,
            checksum=checksum,
        )
        entry = self._items.get(key)
        if entry is None or entry.expires_at <= time.monotonic():
            self._items.pop(key, None)
            self._counters["misses"] += 1
            return None
        self._items.move_to_end(key)
        self._counters["hits"] += 1
        return entry.manifest.model_copy(deep=True)

    def put_manifest(
        self,
        *,
        tenant_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        version: int,
        checksum: str,
        manifest: TrainingDatasetManifestV2,
    ) -> None:
        if not self.enabled:
            return
        key = self.key(
            tenant_id=tenant_id,
            snapshot_id=snapshot_id,
            version=version,
            checksum=checksum,
        )
        self._items[key] = _ManifestEntry(
            expires_at=time.monotonic() + self.ttl_seconds,
            manifest=manifest.model_copy(deep=True),
        )
        self._items.move_to_end(key)
        while len(self._items) > self.max_entries:
            self._items.popitem(last=False)

    def invalidate_tenant(self, tenant_id: uuid.UUID) -> None:
        for key in tuple(self._items):
            if key[0] == tenant_id:
                self._items.pop(key, None)
        self._counters["invalidations"] += 1

    def snapshot(self) -> dict[str, int]:
        return {
            "entries": len(self._items),
            "hits": self._counters["hits"],
            "misses": self._counters["misses"],
            "invalidations": self._counters["invalidations"],
        }
