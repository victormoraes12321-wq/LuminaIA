"""
LuminaAI — Semantic Engine
--------------------------
Normaliza termos informados em linguagem natural, corrigindo
pequenos erros de escrita, plurais/singulares e sinônimos de BI.
"""
from __future__ import annotations

import logging
import unicodedata

from services.semantic_layer import canonicalize_metric_name

logger = logging.getLogger("luminaai.ai.semantic_engine")


class SemanticEngine:
    """
    Higieniza e normaliza ortografia e sinônimos analíticos em linguagem natural.
    """

    def clean_text(self, text: str) -> str:
        """
        Remove acentos, normaliza caixa e retira caracteres indesejados.
        """
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKD", text)
        clean = "".join([c for c in normalized if not unicodedata.combining(c)])
        return clean.strip().lower()

    def resolve_synonyms(self, term: str) -> str:
        """
        Mapeia expressões comuns e sinônimos informais para o termo de negócio padronizado.
        """
        cleaned = self.clean_text(term)

        canonical_metric = canonicalize_metric_name(cleaned)
        if canonical_metric != cleaned:
            return canonical_metric
        
        dictionary = {
            "quem vendeu mais": "ranking de vendedores",
            "top vendedores": "ranking de vendedores",
            "vendedores campeoes": "ranking de vendedores",
            "melhores vendedores": "ranking de vendedores",
            "itens": "produto",
            "sku": "produto",
            "mercadoria": "produto",
            "comprador": "cliente",
            "consumidor": "cliente",
        }
        
        return dictionary.get(cleaned, term)


# Singleton export
semantic_engine = SemanticEngine()
