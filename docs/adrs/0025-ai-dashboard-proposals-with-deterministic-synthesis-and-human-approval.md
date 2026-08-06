# ADR 0025 — Propostas de dashboard com síntese determinística e aprovação humana

Status: Aceito para implementação, rollout bloqueado.

## Contexto

Blueprint V2, backend governado e interface/side chat já definem contrato, persistência e apresentação. Faltava assistência para interpretar um pedido em português sem delegar ao modelo autoridade sobre métrica, período, dados, SQL, permissão ou publicação.

## Decisão

Adotar `lumina.dashboard-ai-assistance/1.0`. O modelo produz somente intenção tipada. Resolução canônica, clarificação, design spec, escolha de template/widget, síntese de Blueprint, compilação de patches, validação, checksums e aplicação são determinísticos. Toda saída persistente é uma proposta versionada e revisável. Aceite humano não aplica; um segundo request aplica somente em DRAFT via Prompt 20.

A migration v23 é aditiva, explícita e excluída de `create_all`. Histórico de versões, evidências, decisões, auditoria e resultados de avaliação é imutável. O frontend é server-guarded e usa o renderer Prompt 21 somente com placeholders estruturais.

## Consequências

O fluxo é auditável, tenant-scoped e fail-closed, mas não há provider real, benchmark produtivo, rollout, treino automático nem publicação automática. A criação manual permanece disponível. Produção permanece `LEGACY_ONLY` até aprovação operacional separada.
