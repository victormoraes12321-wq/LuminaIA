# Guia De Manutencao

## Boas Praticas

- Rodar testes backend e frontend antes de mudancas.
- Preservar contratos de API e tipos TypeScript.
- Nao alterar regra de negocio no frontend.
- Nao permitir IA consultar banco diretamente.
- Criar ADR para mudancas arquiteturais.

## Comandos De Validacao

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run lint
npm run build
npm run test:visual
```

## Atualizacoes

- Atualizar dependencias em janela controlada.
- Rodar `npm audit` e `pip check`.
- Validar import cycles com `scripts/import_cycle_check.py`.

## Monitoramento

Monitorar latencia API, erros 5xx, tempo OpenAI, sync, pool DB, uso CPU/memoria e render frontend.
