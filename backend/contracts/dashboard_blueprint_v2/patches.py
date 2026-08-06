"""Strict visual and semantic patch proposals. Runtime mutation is intentionally absent."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field, JsonValue, model_validator

from .identity import CANONICAL_ID_PATTERN, StrictDashboardModel


class DashboardPatchOperationKindV2(str, Enum):
    ADD = "ADD"
    REPLACE = "REPLACE"
    REMOVE = "REMOVE"
    MOVE = "MOVE"


class DashboardPatchOperationV2(StrictDashboardModel):
    operation: DashboardPatchOperationKindV2
    path: str = Field(min_length=2, max_length=240, pattern=r"^/[a-z0-9_./:-]+$")
    value: JsonValue | None = None
    from_path: str | None = Field(
        default=None, min_length=2, max_length=240, pattern=r"^/[a-z0-9_./:-]+$"
    )

    @model_validator(mode="after")
    def validate_operation(self) -> "DashboardPatchOperationV2":
        if self.operation in {DashboardPatchOperationKindV2.ADD, DashboardPatchOperationKindV2.REPLACE}:
            if self.value is None:
                raise ValueError("ADD and REPLACE patch operations require a value")
        elif self.value is not None:
            raise ValueError("REMOVE and MOVE do not accept value")
        if self.operation is DashboardPatchOperationKindV2.MOVE and self.from_path is None:
            raise ValueError("MOVE patch operation requires from_path")
        if self.operation is not DashboardPatchOperationKindV2.MOVE and self.from_path is not None:
            raise ValueError("from_path is valid only for MOVE")
        return self


class DashboardVisualPatchV2(StrictDashboardModel):
    patch_type: Literal["VISUAL"] = "VISUAL"
    blueprint_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    base_blueprint_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    base_semantic_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    base_visual_revision: int = Field(ge=1)
    target_visual_revision: int = Field(ge=2)
    operations: tuple[DashboardPatchOperationV2, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_revision(self) -> "DashboardVisualPatchV2":
        if self.target_visual_revision <= self.base_visual_revision:
            raise ValueError("visual patch must advance visual revision")
        return self


class DashboardSemanticPatchV2(StrictDashboardModel):
    patch_type: Literal["SEMANTIC"] = "SEMANTIC"
    blueprint_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    base_blueprint_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    base_semantic_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    base_semantic_revision: int = Field(ge=1)
    target_semantic_revision: int = Field(ge=2)
    requires_revalidation: Literal[True] = True
    operations: tuple[DashboardPatchOperationV2, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_revision(self) -> "DashboardSemanticPatchV2":
        if self.target_semantic_revision <= self.base_semantic_revision:
            raise ValueError("semantic patch must advance semantic revision")
        return self

