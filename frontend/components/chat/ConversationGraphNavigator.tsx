'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { GitCommit, GitBranch, ArrowLeftRight, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ConversationGraph } from '@/types/dashboard-runtime';

interface ConversationGraphNavigatorProps {
  graph: ConversationGraph;
  onBacktrack: (nodeId: string) => void;
  className?: string;
}

export function ConversationGraphNavigator({
  graph,
  onBacktrack,
  className,
}: ConversationGraphNavigatorProps) {
  const nodesArray = Object.values(graph.nodes);
  if (nodesArray.length === 0) return null;

  // Encontra todos os nós raiz (aqueles que não têm parent_id ou o pai não existe no grafo)
  const rootNodes = nodesArray.filter(
    (n) => !n.parent_id || !graph.nodes[n.parent_id]
  );

  const renderTree = (nodeId: string, depth: number = 0): React.ReactNode => {
    const node = graph.nodes[nodeId];
    if (!node) return null;

    const isActive = graph.current_node_id === nodeId;
    const hasBranch = node.children_ids.length > 1;

    return (
      <div key={nodeId} className="relative flex flex-col">
        {/* Conector visual da linha do tempo/árvore */}
        {depth > 0 && (
          <div
            className="absolute left-[-16px] top-0 bottom-1/2 w-4 border-l-2 border-b-2 border-zinc-800 rounded-bl-lg"
            style={{ left: `calc(${depth * 16}px - 12px)` }}
          />
        )}

        <div
          style={{ paddingLeft: depth * 16 }}
          className="group relative flex items-start gap-3 py-2"
        >
          {/* Ícone de Estado/Nó */}
          <div className="relative mt-1">
            <motion.button
              whileHover={{ scale: 1.15 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => onBacktrack(nodeId)}
              className={cn(
                'w-6 h-6 rounded-full border flex items-center justify-center transition-all duration-200 cursor-pointer shadow-sm',
                isActive
                  ? 'bg-lumina-500 border-lumina-400 text-white shadow-lumina-sm scale-110'
                  : 'bg-zinc-900 border-zinc-800 text-zinc-400 group-hover:border-zinc-700 group-hover:text-white'
              )}
            >
              {hasBranch ? (
                <GitBranch size={11} className={isActive ? 'text-white' : 'text-lumina-400'} />
              ) : (
                <GitCommit size={11} />
              )}
            </motion.button>
          </div>

          {/* Conteúdo Textual do Nó */}
          <div className="flex-1 min-w-0">
            <button
              onClick={() => onBacktrack(nodeId)}
              className={cn(
                'w-full text-left font-medium text-xs leading-snug rounded-lg transition-all p-2 pr-3 border flex flex-col gap-1 cursor-pointer',
                isActive
                  ? 'bg-lumina-500/10 border-lumina-500/30 text-white font-semibold'
                  : 'bg-zinc-900/40 border-transparent hover:bg-zinc-900/80 hover:border-zinc-800 text-zinc-400 hover:text-zinc-200'
              )}
            >
              <span className="line-clamp-2 break-words">"{node.user_query}"</span>
              <div className="flex items-center gap-2 mt-0.5">
                <span
                  className={cn(
                    'text-[9px] uppercase tracking-wider font-bold rounded-md px-1.5 py-0.5',
                    isActive
                      ? 'bg-lumina-500/20 text-lumina-400 border border-lumina-500/30'
                      : 'bg-zinc-950 text-zinc-500 border border-zinc-900'
                  )}
                >
                  {node.dashboard_state.chart_type}
                </span>
                {isActive && (
                  <span className="text-[9px] text-teal-400 font-bold flex items-center gap-0.5 animate-pulse">
                    ● Ativo
                  </span>
                )}
              </div>
            </button>
          </div>
        </div>

        {/* Renderiza filhos recursivamente */}
        {node.children_ids.length > 0 && (
          <div className="relative flex flex-col">
            {/* Linha vertical conectora contínua */}
            <div
              className="absolute top-4 bottom-4 w-0.5 bg-zinc-800/80"
              style={{ left: `calc(${(depth + 1) * 16}px - 10px)` }}
            />
            {node.children_ids.map((childId) => renderTree(childId, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      className={cn(
        'w-full flex flex-col bg-zinc-950/60 dark:bg-zinc-950/80 border border-zinc-850 dark:border-zinc-900/60 rounded-2xl p-4 shadow-lg',
        className
      )}
    >
      <div className="flex items-center gap-2 border-b border-zinc-900 pb-3 mb-3">
        <ArrowLeftRight size={14} className="text-lumina-400" />
        <span className="text-xs font-bold text-white tracking-wide uppercase">
          Árvore de Decisão & Grafo
        </span>
      </div>

      <div className="max-h-[350px] overflow-y-auto pr-1 space-y-3 scrollbar-thin">
        {rootNodes.map((rootNode) => renderTree(rootNode.node_id, 0))}
      </div>

      <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-zinc-900 text-[10px] text-zinc-500 select-none">
        <Clock size={11} />
        <span>Clique em qualquer pergunta anterior para fazer backtracking de estado.</span>
      </div>
    </div>
  );
}
