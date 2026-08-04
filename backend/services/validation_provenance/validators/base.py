"""
LuminaAI Governed Validation & Provenance V2 - Base Validator Interface
Version: lumina.validation-provenance/1.0
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from contracts.validation_provenance_v2 import (
    ValidationCheckResultV2,
    ValidationContextV2,
    ValidationIssueV2,
    ValidationSeverity,
    ValidationStage,
    ValidationStatus,
)


class GovernedValidator(ABC):
    """
    Abstract base class for all typed, static validators in the LuminaAI validation pipeline.
    """

    @property
    @abstractmethod
    def validator_id(self) -> str:
        """Unique string ID of the validator, e.g. tenant_isolation.v1"""
        pass

    @property
    @abstractmethod
    def validator_version(self) -> str:
        """Semver string of the validator implementation"""
        pass

    @property
    @abstractmethod
    def target_stage(self) -> ValidationStage:
        """Primary target stage of this validator"""
        pass

    @property
    @abstractmethod
    def default_severity(self) -> ValidationSeverity:
        """Default issue severity if this check fails"""
        pass

    @abstractmethod
    async def validate(
        self,
        context: ValidationContextV2,
        payload: Dict,
        proposed_facts: List[Dict],
        proposed_claims: List[Dict],
        tenant_proof: Optional[Dict] = None,
    ) -> ValidationCheckResultV2:
        """
        Executes deterministic validation logic and returns typed result.
        """
        pass
