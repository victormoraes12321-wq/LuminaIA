'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  AlertTriangle,
  Cpu,
  Play,
  RefreshCw,
  ShieldAlert,
  Wrench,
} from 'lucide-react'

import { Sidebar } from '@/components/Sidebar'
import { useAuth } from '@/context/AuthContext'
import { getApiBase } from '@/lib/utils'

interface ToolItem {
  tool_id: string
  canonical_name: string
  display_name: string
  domain: string
  tool_type: string
  risk_class: string
  side_effect: string
  created_at: string
}

interface CatalogItem {
  tool_id: string
  canonical_name: string
  display_name: string
  description: string
  version: string
  tool_type: string
  capabilities: string[]
  risk_class: string
  side_effect: string
}

export default function AIToolRegistryAdminPage() {
  const { token, user, loading: authLoading } = useAuth()
  const canAdminister = user?.role === 'ADMIN'

  const [activeTab, setActiveTab] = useState<'catalog' | 'tools' | 'inspector'>('catalog')
  const [catalogItems, setCatalogItems] = useState<CatalogItem[]>([])
  const [adminTools, setAdminTools] = useState<ToolItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [inspectToolId, setInspectToolId] = useState('lumina.temporal.normalize')
  const [inspectArgs, setInspectArgs] = useState('{\n  "expression": "hoje"\n}')
  const [inspectResult, setInspectResult] = useState<string | null>(null)
  const [inspecting, setInspecting] = useState(false)

  const fetchCatalog = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      const res = await fetch(`${getApiBase()}/api/v2/tools/catalog`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!res.ok) throw new Error('Falha ao carregar catálogo de ferramentas')
      const data = await res.json()
      setCatalogItems(data.items || [])
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erro ao carregar catálogo'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [token])

  const fetchAdminTools = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch(`${getApiBase()}/api/v2/admin/tools`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!res.ok) throw new Error('Falha ao carregar registro administrativo de ferramentas')
      const data = await res.json()
      setAdminTools(data.items || [])
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erro ao carregar ferramentas'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    if (!authLoading && canAdminister) {
      void fetchCatalog()
      void fetchAdminTools()
    }
  }, [authLoading, canAdminister, fetchCatalog, fetchAdminTools])

  const runInspector = async () => {
    try {
      setInspecting(true)
      setInspectResult(null)
      let parsed = {}
      try {
        parsed = JSON.parse(inspectArgs)
      } catch {
        throw new Error('Argumentos devem ser um JSON válido')
      }

      const res = await fetch(`${getApiBase()}/api/v2/admin/tools/inspector/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          tool_id: inspectToolId,
          raw_arguments: parsed,
        }),
      })

      const data = await res.json()
      setInspectResult(JSON.stringify(data, null, 2))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erro no teste sintético'
      setInspectResult(JSON.stringify({ error: msg }, null, 2))
    } finally {
      setInspecting(false)
    }
  }

  if (authLoading) {
    return (
      <div className="flex h-screen bg-[#090D16] text-white items-center justify-center">
        <RefreshCw className="animate-spin text-lumina-400" size={32} />
      </div>
    )
  }

  if (!canAdminister) {
    return (
      <div className="flex h-screen bg-[#090D16] text-white">
        <Sidebar />
        <main className="flex-1 p-8 flex items-center justify-center">
          <div className="bg-[#121827] border border-red-500/20 rounded-xl p-6 text-center max-w-md">
            <ShieldAlert className="mx-auto text-red-400 mb-3" size={40} />
            <h2 className="text-xl font-bold mb-2">Acesso Restrito</h2>
            <p className="text-sm text-zinc-400">
              Apenas administradores possuem acesso ao Registro Governado de Ferramentas da IA.
            </p>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-[#090D16] text-white overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-6xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
            <div>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-lumina-500/10 text-lumina-400 border border-lumina-500/20">
                  <Cpu size={24} />
                </div>
                <div>
                  <h1 className="text-2xl font-bold">Registro Governado de Ferramentas da IA</h1>
                  <p className="text-xs text-zinc-400">lumina.ai-tool-registry/1.0 • Fail-Closed Authority</p>
                </div>
              </div>
            </div>
            <button
              onClick={() => { void fetchCatalog(); void fetchAdminTools(); }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold transition"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Atualizar
            </button>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-3 rounded-lg text-xs flex items-center gap-2">
              <AlertTriangle size={16} />
              <span>{error}</span>
            </div>
          )}

          {/* Navigation Tabs */}
          <div className="flex gap-2 border-b border-zinc-800">
            <button
              onClick={() => setActiveTab('catalog')}
              className={`px-4 py-2 text-xs font-semibold border-b-2 transition ${
                activeTab === 'catalog'
                  ? 'border-lumina-400 text-lumina-400'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Catálogo Ativo ({catalogItems.length})
            </button>
            <button
              onClick={() => setActiveTab('tools')}
              className={`px-4 py-2 text-xs font-semibold border-b-2 transition ${
                activeTab === 'tools'
                  ? 'border-lumina-400 text-lumina-400'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Identidades Registradas ({adminTools.length})
            </button>
            <button
              onClick={() => setActiveTab('inspector')}
              className={`px-4 py-2 text-xs font-semibold border-b-2 transition ${
                activeTab === 'inspector'
                  ? 'border-lumina-400 text-lumina-400'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Inspector & Testes Sintéticos
            </button>
          </div>

          {/* Tab 1: Catalog */}
          {activeTab === 'catalog' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {catalogItems.map((item) => (
                <div
                  key={item.tool_id}
                  className="bg-[#121827] border border-zinc-800 hover:border-lumina-500/30 rounded-xl p-5 space-y-3 transition"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-xs text-lumina-400 font-mono font-bold">{item.tool_id}</span>
                      <h3 className="text-base font-semibold text-white mt-0.5">{item.display_name}</h3>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      v{item.version}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 leading-relaxed">{item.description}</p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-zinc-800 text-zinc-300">
                      Risco: {item.risk_class}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-zinc-800 text-zinc-300">
                      Side-effect: {item.side_effect}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Tab 2: Admin Tools */}
          {activeTab === 'tools' && (
            <div className="bg-[#121827] border border-zinc-800 rounded-xl overflow-hidden">
              <table className="w-full text-left text-xs text-zinc-300">
                <thead className="bg-[#182032] text-zinc-400 border-b border-zinc-800 font-semibold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="p-3">Tool ID</th>
                    <th className="p-3">Nome</th>
                    <th className="p-3">Domínio</th>
                    <th className="p-3">Tipo</th>
                    <th className="p-3">Risco</th>
                    <th className="p-3">Side Effect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/50">
                  {adminTools.map((t) => (
                    <tr key={t.tool_id} className="hover:bg-zinc-800/30 transition">
                      <td className="p-3 font-mono text-lumina-400 font-bold">{t.tool_id}</td>
                      <td className="p-3 font-semibold text-white">{t.display_name}</td>
                      <td className="p-3 text-zinc-400">{t.domain}</td>
                      <td className="p-3 text-zinc-400">{t.tool_type}</td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                          {t.risk_class}
                        </span>
                      </td>
                      <td className="p-3 text-zinc-400">{t.side_effect}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Tab 3: Inspector */}
          {activeTab === 'inspector' && (
            <div className="bg-[#121827] border border-zinc-800 rounded-xl p-6 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Wrench size={18} className="text-lumina-400" />
                Inspector e Executor Sintético de Ferramentas
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-400 mb-1">Selecione a Ferramenta:</label>
                  <select
                    value={inspectToolId}
                    onChange={(e) => setInspectToolId(e.target.value)}
                    className="w-full bg-[#090D16] border border-zinc-800 rounded-lg p-2 text-xs font-mono text-white focus:outline-none focus:border-lumina-400"
                  >
                    {catalogItems.map((c) => (
                      <option key={c.tool_id} value={c.tool_id}>
                        {c.tool_id} (v{c.version})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-400 mb-1">Argumentos Raw (JSON):</label>
                  <textarea
                    value={inspectArgs}
                    onChange={(e) => setInspectArgs(e.target.value)}
                    rows={4}
                    className="w-full bg-[#090D16] border border-zinc-800 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-lumina-400"
                  />
                </div>
                <button
                  onClick={() => { void runInspector(); }}
                  disabled={inspecting}
                  className="flex items-center gap-2 px-4 py-2 bg-lumina-500 hover:bg-lumina-400 text-black font-bold text-xs rounded-lg transition disabled:opacity-50"
                >
                  <Play size={14} className={inspecting ? 'animate-spin' : ''} />
                  Executar Teste Sintético
                </button>
              </div>

              {inspectResult && (
                <div className="mt-4 pt-4 border-t border-zinc-800">
                  <h4 className="text-xs font-bold text-zinc-400 mb-2">Resultado do Envelope:</h4>
                  <pre className="bg-[#090D16] p-4 rounded-xl text-xs font-mono text-emerald-400 border border-zinc-800 overflow-x-auto">
                    {inspectResult}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
