'use client';

import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
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

function cleanPerguntaOriginal(pergunta: string): string {
  if (!pergunta) return '';
  return pergunta.replace(/\s*\([^)]*\)/g, '').replace(/\s*\[Instruções:[^\]]*\]/g, '').trim();
}

export function ClarificationPanel({
  status,
  ambiguities = [],
  missingInformation = [],
  perguntaOriginal,
  onResolve,
  className,
}: ClarificationPanelProps) {
  const [mounted, setMounted] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [missingData, setMissingData] = useState<Record<string, string>>({});
  const [selectedAmbiguity, setSelectedAmbiguity] = useState<string | null>(null);
  const [customInstructions, setCustomInstructions] = useState<string>('');

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => setMounted(true));
    return () => window.cancelAnimationFrame(frame);
  }, []);

  const isAmbiguous = status === 'AMBIGUOUS';
  const isMissingInfo = status === 'MISSING_INFORMATION';

  const handleAmbiguitySelect = (option: string) => {
    setSelectedAmbiguity(option);
    setIsClosing(true);
    const baseQuestion = cleanPerguntaOriginal(perguntaOriginal);
    const extra = customInstructions.trim() ? ` [Instruções: ${customInstructions.trim()}]` : '';
    const resolvedText = `${baseQuestion} em ${option}${extra}`;
    onResolve(resolvedText);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const resolvedParts = Object.entries(missingData)
      .filter(([_, val]) => val.trim().length > 0)
      .map(([key, val]) => `${key}: ${val}`);

    if (resolvedParts.length === 0) return;

    setIsClosing(true);
    const extra = customInstructions.trim() ? ` [Instruções: ${customInstructions.trim()}]` : '';
    const resolvedText = `${perguntaOriginal} [Com informações adicionadas: ${resolvedParts.join(', ')}]${extra}`;
    onResolve(resolvedText);
  };

  if (!mounted || isClosing || typeof document === 'undefined') return null;

  const modalNode = (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-lg p-4 animate-in fade-in duration-200">
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
            Sua pergunta: <span className="italic font-medium text-zinc-300">&quot;{perguntaOriginal}&quot;</span>
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

              {/* Seção de Instruções Personalizadas Opcionais */}
              <div className="mt-4 pt-3 border-t border-zinc-900/80">
                <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block mb-1.5">
                  Instruções Personalizadas (Opcional):
                </label>
                <input
                  type="text"
                  placeholder="Ex: Ordenar por maior valor, destacar top 5, etc."
                  value={customInstructions}
                  onChange={(e) => setCustomInstructions(e.target.value)}
                  className="w-full bg-zinc-900/60 border border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-white outline-none placeholder:text-zinc-600 focus:border-lumina-500/60 transition-all duration-200"
                />
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

  return createPortal(modalNode, document.body);
}
