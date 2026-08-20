from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemporalRule:
    rule_id: str
    description: str


RULES: dict[str, TemporalRule] = {
    rule.rule_id: rule
    for rule in (
        TemporalRule("PTBR.ABSOLUTE.DATE", "Data civil absoluta."),
        TemporalRule("PTBR.ABSOLUTE.MONTH", "Mes civil absoluto."),
        TemporalRule("PTBR.ABSOLUTE.YEAR", "Ano civil absoluto."),
        TemporalRule("PTBR.CALENDAR.QUARTER", "Trimestre civil."),
        TemporalRule("PTBR.CALENDAR.SEMESTER", "Semestre civil."),
        TemporalRule("PTBR.CALENDAR.WEEK", "Semana civil ou ISO."),
        TemporalRule("PTBR.CALENDAR.FORTNIGHT", "Quinzena civil."),
        TemporalRule("PTBR.RELATIVE.DAY", "Dia relativo."),
        TemporalRule("PTBR.RELATIVE.PERIOD", "Periodo civil relativo."),
        TemporalRule("PTBR.ROLLING.WINDOW", "Janela movel."),
        TemporalRule("PTBR.CLOSED.WINDOW", "Sequencia de periodos encerrados."),
        TemporalRule("PTBR.ACCUMULATED", "Periodo acumulado ate a referencia."),
        TemporalRule("PTBR.FISCAL.YEAR", "Ano fiscal configurado."),
        TemporalRule("PTBR.FISCAL.QUARTER", "Trimestre fiscal configurado."),
        TemporalRule("PTBR.RELATION.RANGE", "Intervalo temporal continuo."),
        TemporalRule("PTBR.RELATION.LIST", "Lista ordenada de periodos."),
        TemporalRule("PTBR.RELATION.COMPARISON", "Operandos temporais comparativos."),
        TemporalRule("PTBR.INFERENCE.YEAR", "Ano inferido por politica explicita."),
        TemporalRule("PTBR.AMBIGUOUS", "Expressao temporal materialmente ambigua."),
    )
}


def ensure_known_rule(rule_id: str) -> str:
    if rule_id not in RULES:
        raise ValueError(f"Unknown temporal rule ID: {rule_id}")
    return rule_id
