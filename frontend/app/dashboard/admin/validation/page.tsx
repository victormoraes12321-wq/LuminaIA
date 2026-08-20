import React from 'react';
import { ValidationInspector } from '@/components/validation/ValidationInspector';

export const metadata = {
  title: 'Validação & Proveniência | LuminaAI Admin',
  description: 'Painel Administrativo de Validação Analítica Consolidada e Proveniência V2',
};

export default function AdminValidationPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold text-slate-100">Administração de Validação e Proveniência</h1>
        <p className="text-sm text-slate-400">
          Governança determinística de 18 estágios, fatos analíticos com precisão Decimal, suporte a claims e grafos de proveniência.
        </p>
      </div>

      <ValidationInspector />
    </main>
  );
}
