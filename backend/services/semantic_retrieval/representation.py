from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol

from contracts.semantic_retrieval_v2 import (
    PROVIDER_VERSION,
    SemanticDataClassification,
    VectorRepresentationV2,
)
from services.semantic_retrieval.checksums import checksum_for
from services.semantic_retrieval.normalization import NormalizedSemanticText


@dataclass(frozen=True)
class SemanticRepresentationProviderInfo:
    provider_type: str
    version: str
    dimension: int
    normalization: str
    locale: str
    checksum: str
    deterministic: bool
    network_required: bool
    allowed_classifications: tuple[SemanticDataClassification, ...]


class SemanticRepresentationProvider(Protocol):
    def provider_info(self) -> SemanticRepresentationProviderInfo: ...

    def validate_configuration(self) -> None: ...

    def encode_document(
        self,
        normalized: NormalizedSemanticText,
        *,
        aliases: tuple[str, ...],
        domain: str,
        entity_type: str,
        classification: SemanticDataClassification,
    ) -> VectorRepresentationV2: ...

    def encode_query(self, normalized: NormalizedSemanticText) -> VectorRepresentationV2: ...

    @staticmethod
    def similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float: ...

    def deterministic_fingerprint(self) -> str: ...


class DeterministicFeatureEmbeddingProvider:
    """Local feature hashing. This is intentionally not a neural embedding."""

    def __init__(self, *, dimension: int = 256, locale: str = "pt-BR") -> None:
        if dimension < 32 or dimension > 4096:
            raise ValueError("dimension must be between 32 and 4096")
        self.dimension = dimension
        self.locale = locale
        self._allowed = (
            SemanticDataClassification.PUBLIC_BUSINESS_METADATA,
            SemanticDataClassification.TENANT_BUSINESS_METADATA,
            SemanticDataClassification.RESTRICTED_BUSINESS_METADATA,
        )

    def deterministic_fingerprint(self) -> str:
        return checksum_for(
            {
                "provider_type": "DETERMINISTIC_FEATURE_HASH",
                "version": PROVIDER_VERSION,
                "dimension": self.dimension,
                "locale": self.locale,
                "algorithm": "sha256-signed-feature-hashing-l2",
            }
        )

    def provider_info(self) -> SemanticRepresentationProviderInfo:
        return SemanticRepresentationProviderInfo(
            provider_type="DETERMINISTIC_FEATURE_HASH",
            version=PROVIDER_VERSION,
            dimension=self.dimension,
            normalization="L2",
            locale=self.locale,
            checksum=self.deterministic_fingerprint(),
            deterministic=True,
            network_required=False,
            allowed_classifications=self._allowed,
        )

    def validate_configuration(self) -> None:
        info = self.provider_info()
        if info.network_required or not info.deterministic:
            raise ValueError("semantic provider must be deterministic and offline")

    def _encode_features(self, features: tuple[str, ...]) -> VectorRepresentationV2:
        vector = [0.0] * self.dimension
        for feature in features:
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimension
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        rounded = tuple(round(value, 12) for value in vector)
        checksum = checksum_for(
            {
                "provider": PROVIDER_VERSION,
                "dimension": self.dimension,
                "vector": rounded,
            }
        )
        return VectorRepresentationV2(
            dimension=self.dimension,
            vector=rounded,
            checksum=checksum,
        )

    def encode_document(
        self,
        normalized: NormalizedSemanticText,
        *,
        aliases: tuple[str, ...],
        domain: str,
        entity_type: str,
        classification: SemanticDataClassification,
    ) -> VectorRepresentationV2:
        if classification not in self._allowed:
            raise ValueError("classification is not allowed for semantic representation")
        alias_features: list[str] = []
        for alias in aliases:
            from services.semantic_retrieval.normalization import normalize_semantic_text

            alias_normalized = normalize_semantic_text(alias, locale=self.locale)
            alias_features.extend(f"alias:{token}" for token in alias_normalized.significant_tokens)
        features = tuple(
            [f"token:{token}" for token in normalized.significant_tokens]
            + [f"ngram:{item}" for item in normalized.character_ngrams]
            + alias_features
            + [f"domain:{domain.casefold()}", f"type:{entity_type}"]
        )
        return self._encode_features(features)

    def encode_query(self, normalized: NormalizedSemanticText) -> VectorRepresentationV2:
        features = tuple(
            [f"token:{token}" for token in normalized.significant_tokens]
            + [f"ngram:{item}" for item in normalized.character_ngrams]
        )
        return self._encode_features(features)

    @staticmethod
    def similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        if len(left) != len(right):
            raise ValueError("vectors must have the same dimension")
        score = sum(a * b for a, b in zip(left, right, strict=True))
        if abs(score - 1.0) <= 1e-9:
            return 1.0
        return round(max(0.0, min(1.0, score)), 12)
