'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { HelpCircle, AlertCircle, Send, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ClarificationPanelProps {
  status: 'AMBIGUOUS' | 'MISSING_INFORMATION' | string;
  ambiguities?: string[];
  missingInformation?: string[];
  perguntaOriginal: string;
  onResolve: (resolucao: string) => void;
  className?: string;
}

export function ClarificationPanel({
  status,
  ambiguities = [],
  missingInformation = [],
  perguntaOriginal,
  onResolve,
  className,
}: ClarificationPanelProps) {
  const [missingData, setMissingData] = useState<Record<string, string>>({});
  const [selectedAmbiguity, setSelectedAmbiguity] = useState<string | null>(null);

  const isAmbiguous = status === 'AMBIGUOUS';
  const isMissingInfo = status === 'MISSING_INFORMATION';

  const handleAmbiguitySelect = (option: string) => {
    setSelectedAmbiguity(option);
    // Envia a resposta imediatamente concatenando com a pergunta original
    const resolvedText = `${perguntaOriginal} (${option})`;
    onResolve(resolvedText);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const resolvedParts = Object.entries(missingData)
      .filter(([_, val]) => val.trim().length > 0)
      .map(([key, val]) => `${key}: ${val}`);

    if (resolvedParts.length === 0) return;

    const resolvedText = `${perguntaOriginal} [Com informações adicionadas: ${resolvedParts.join(', ')}]`;
    onResolve(resolvedText);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        className={cn(
          'w-full max-w-xl max-h-[85vh] overflow-y-auto border bg-zinc-950/95 border-zinc-800/90 rounded-2xl shadow-2xl p-6 relative backdrop-blur-xl',
          className
        )}
      >
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-xl bg-lumina-500/10 border border-lumina-500/20 text-lumina-400 flex-shrink-0">
          {isAmbiguous ? <HelpCircle size={20} /> : <AlertCircle size={20} />}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-white tracking-wide">
            {isAmbiguous
              ? 'Identifiquei ambiguidades nos termos analíticos'
              : 'Informações obrigatórias ausentes para prosseguir'}
          </h4>
          <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
            Sua pergunta: <span className="italic font-medium text-zinc-300">"{perguntaOriginal}"</span>
          </p>

          {/* Seção de Resolução de Ambiguidade */}
          {isAmbiguous && ambiguities.length > 0 && (
            <div className="mt-4">
              <p className="text-[10px] font-bold text-lumina-400 uppercase tracking-widest mb-2.5">
                Escolha uma das opções abaixo para esclarecer:
              </p>
              <div className="flex flex-col gap-2">
                {ambiguities.map((option, index) => (
                  <motion.button
                    key={index}
                    whileHover={{ scale: 1.01, x: 2 }}
                    whileTap={{ scale: 0.99 }}
                    onClick={() => handleAmbiguitySelect(option)}
                    className={cn(
                      'w-full text-left p-3.5 px-4 rounded-xl text-xs font-medium border transition-all cursor-pointer flex items-center justify-between',
                      selectedAmbiguity === option
                        ? 'bg-lumina-500/15 border-lumina-500/40 text-lumina-300'
                        : 'bg-zinc-900/40 border-zinc-800 hover:border-zinc-700/80 text-zinc-300 hover:text-white hover:bg-zinc-900/60'
                    )}
                  >
                    <span>{option}</span>
                    {selectedAmbiguity === option && (
                      <Check size={14} className="text-lumina-400 flex-shrink-0" />
                    )}
                  </motion.button>
                ))}
              </div>
            </div>
          )}

          {/* Seção de Informações Ausentes */}
          {isMissingInfo && missingInformation.length > 0 && (
            <form onSubmit={handleFormSubmit} className="mt-4">
              <p className="text-[10px] font-bold text-lumina-400 uppercase tracking-widest mb-3">
                Por favor, preencha os dados necessários:
              </p>
              <div className="flex flex-col gap-4">
                {missingInformation.map((field, index) => (
                  <div key={index} className="flex flex-col gap-1.5">
                    <label className="text-[11px] font-medium text-zinc-400 capitalize">
                      {field.replace(/_/g, ' ')}
                    </label>
                    <input
                      type="text"
                      required
                      placeholder={`Ex: ${field.includes('periodo') || field.includes('data') ? 'Últimos 30 dias' : 'Insira o valor'}`}
                      value={missingData[field] || ''}
                      onChange={(e) =>
                        setMissingData((prev) => ({ ...prev, [field]: e.target.value }))
                      }
                      className={cn(
                        'w-full bg-zinc-900/40 border border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-white outline-none',
                        'placeholder:text-zinc-500 focus:border-lumina-500/50 transition-all duration-200'
                      )}
                    />
                  </div>
                ))}
                
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  className={cn(
                    'mt-2 w-full py-3 rounded-xl bg-lumina-gradient text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-lumina cursor-pointer'
                  )}
                >
                  <Send size={12} />
                  <span>Submeter Resolução</span>
                </motion.button>
              </div>
            </form>
          )}
        </div>
      </div>
    </motion.div>
    </div>
  );
}
