from __future__ import annotations

from dataclasses import dataclass

from .models import TemporalLexiconProvider


MONTHS: dict[str, int] = {
    "janeiro": 1,
    "jan": 1,
    "fevereiro": 2,
    "fev": 2,
    "marco": 3,
    "mar": 3,
    "abril": 4,
    "abr": 4,
    "maio": 5,
    "mai": 5,
    "junho": 6,
    "jun": 6,
    "julho": 7,
    "jul": 7,
    "agosto": 8,
    "ago": 8,
    "setembro": 9,
    "set": 9,
    "outubro": 10,
    "out": 10,
    "novembro": 11,
    "nov": 11,
    "dezembro": 12,
    "dez": 12,
}

MONTH_LABELS: dict[int, str] = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Marco",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}

ORDINALS: dict[str, int] = {
    "primeiro": 1,
    "primeira": 1,
    "1o": 1,
    "1a": 1,
    "segundo": 2,
    "segunda": 2,
    "2o": 2,
    "2a": 2,
    "terceiro": 3,
    "terceira": 3,
    "3o": 3,
    "3a": 3,
    "quarto": 4,
    "quarta": 4,
    "4o": 4,
    "4a": 4,
}

RANGE_CONNECTORS = (
    "entre",
    "desde",
    " ate ",
    " a ",
)
COMPARISON_CONNECTORS = (
    "compare",
    "comparar",
    "comparacao entre",
    "versus",
    " vs ",
    "contra",
    "em relacao a",
    "comparado com",
)
CLOSED_MODIFIERS = ("fechado", "fechados", "completo", "completos", "encerrado", "encerrados")
FISCAL_TERMS = ("fiscal", "exercicio fiscal", "fy")
ACCUMULATED_ALIASES = {
    "mtd": "MONTH_TO_DATE",
    "mes ate hoje": "MONTH_TO_DATE",
    "acumulado no mes": "MONTH_TO_DATE",
    "ytd": "YEAR_TO_DATE",
    "ano ate hoje": "YEAR_TO_DATE",
    "acumulado no ano": "YEAR_TO_DATE",
    "qtd": "QUARTER_TO_DATE",
    "trimestre ate hoje": "QUARTER_TO_DATE",
    "acumulado no trimestre": "QUARTER_TO_DATE",
    "acumulado no semestre": "SEMESTER_TO_DATE",
    "semestre ate hoje": "SEMESTER_TO_DATE",
}


@dataclass(frozen=True)
class BuiltinPtBrLexiconProvider(TemporalLexiconProvider):
    def aliases(self) -> dict[str, str]:
        return {
            "mes passado": "PREVIOUS_MONTH",
            "mes anterior": "PREVIOUS_MONTH",
            "ultimo mes": "PREVIOUS_MONTH",
            "ano passado": "PREVIOUS_YEAR",
            "ano anterior": "PREVIOUS_YEAR",
            "ultima semana": "PREVIOUS_WEEK",
            "semana passada": "PREVIOUS_WEEK",
            "semana anterior": "PREVIOUS_WEEK",
            "ultimo trimestre": "PREVIOUS_QUARTER",
            "trimestre anterior": "PREVIOUS_QUARTER",
            "semestre anterior": "PREVIOUS_SEMESTER",
            "hoje": "TODAY",
            "ontem": "YESTERDAY",
            "anteontem": "DAY_BEFORE_YESTERDAY",
            "amanha": "TOMORROW",
        }


def merged_aliases(
    providers: tuple[TemporalLexiconProvider, ...] | None = None,
) -> dict[str, str]:
    aliases = BuiltinPtBrLexiconProvider().aliases()
    for provider in providers or ():
        aliases.update(provider.aliases())
    return aliases
