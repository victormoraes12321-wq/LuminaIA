# LuminaAI Frontend

Frontend Next.js responsavel por autenticacao de tela, chat, renderizacao de respostas, Dashboard Runtime, Dashboard Studio, componentes visuais, Trust Center e paginas administrativas.

## Stack

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS
- Framer Motion
- ECharts/Recharts
- Playwright

## Estrutura

- `app/`: rotas Next.js.
- `components/`: UI, charts, chat, runtime e Dashboard Studio.
- `hooks/`: queries, runtime, SSE e performance.
- `engines/`: grid, responsividade, layout e performance client-side.
- `types/`: contratos TypeScript.
- `lib/`: helpers, adapter runtime e exportacao.
- `proxy.ts`: protecao de rotas com JWT/cookie.

## Rodar Localmente

```powershell
cd frontend
npm install
npm run dev
```

## Validar

```powershell
npm run lint
npm run build
npm run test:visual
npm run test:load
```

## Contratos

O frontend consome `QueryResponse` e `DashboardRuntimePayload`. Ele nao calcula regra de negocio; apenas renderiza payloads entregues pelo backend.
