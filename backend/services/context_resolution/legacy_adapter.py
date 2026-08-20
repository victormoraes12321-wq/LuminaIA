from __future__ import annotations

from typing import Iterable

from services.metadata_catalog.intent_engine import SemanticPatch


class LegacySemanticPatchError(ValueError):
    pass


_ALLOWED_OPERATIONS = {
    "ADD_FILTER",
    "CHANGE_PERIOD",
    "REMOVE_FILTER",
    "ADD_METRIC",
    "CHANGE_LIMIT",
}
_ALLOWED_FIELDS = {
    "Data",
    "Periodo",
    "Filial",
    "Vendedor",
    "Cliente",
    "Produto",
    "Categoria",
    "Estado",
    "Receita",
    "Ticket Medio",
    "Desconto",
}


def validate_legacy_semantic_patches(
    patches: Iterable[SemanticPatch],
) -> list[SemanticPatch]:
    """Fail closed before legacy SemanticPatch reaches a mutable plan."""
    validated: list[SemanticPatch] = []
    for patch in patches:
        operation = patch.operation.upper().strip()
        field = patch.field.strip()
        if operation not in _ALLOWED_OPERATIONS:
            raise LegacySemanticPatchError("unsupported legacy semantic patch operation")
        if operation not in {"CHANGE_PERIOD", "CHANGE_LIMIT"} and field not in _ALLOWED_FIELDS:
            raise LegacySemanticPatchError("legacy semantic patch field is not governed")
        if len(patch.value) > 256:
            raise LegacySemanticPatchError("legacy semantic patch value is too long")
        validated.append(patch.model_copy(update={"operation": operation, "field": field}))
    return validated
