from __future__ import annotations

import json
from typing import Any, Dict, List


class AITokenEstimator:
    """
    Deterministic, offline Unicode/pt-BR token estimator.
    Applies a safe character-to-token ratio (approx 3.5 chars per token for pt-BR/JSON)
    plus structured metadata overhead and safety margins.
    """

    @staticmethod
    def estimate_text_tokens(text: str) -> int:
        if not text:
            return 0
        raw_length = len(text)
        # Conservative ratio: 3.2 chars per token for pt-BR
        estimated = int(raw_length / 3.2) + 1
        return max(1, estimated)

    @classmethod
    def estimate_dict_tokens(cls, data: Dict[str, Any]) -> int:
        if not data:
            return 0
        try:
            dumped = json.dumps(data, ensure_ascii=False)
            return cls.estimate_text_tokens(dumped) + 10
        except Exception:
            return 50

    @classmethod
    def estimate_messages_tokens(cls, messages: List[Dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            total += 4  # message wrapper overhead
            total += cls.estimate_text_tokens(role)
            total += cls.estimate_text_tokens(content)
        total += 3  # conversation wrapper
        return total
