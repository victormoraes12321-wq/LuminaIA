'use client'

export default function GovernedDashboardError({ reset }: { readonly reset: () => void }) {
  return <div className="grid min-h-screen place-items-center p-6"><div role="alert" className="max-w-md rounded-2xl border border-red-500/40 bg-red-500/10 p-6"><h1 className="font-semibold">A interface deste dashboard falhou</h1><p className="mt-2 text-sm">A falha foi isolada. Nenhum dado ou revisão foi alterado.</p><button type="button" onClick={reset} className="mt-4 rounded-lg border px-4 py-2 text-sm">Tentar novamente</button></div></div>
}
