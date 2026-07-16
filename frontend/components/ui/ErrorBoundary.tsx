'use client'

import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }
      return (
        <div className="flex flex-col items-center justify-center p-6 text-center border border-dashed border-red-500/20 bg-red-500/5 rounded-xl min-h-[200px] gap-3">
          <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center text-red-500">
            <AlertTriangle size={20} />
          </div>
          <div>
            <h4 className="text-xs font-bold text-red-400">Falha ao processar os dados</h4>
            <p className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-1 max-w-[240px] leading-relaxed">
              Ocorreu um erro ao renderizar o gráfico. A estrutura de dados retornada pelo banco de dados pode estar malformada ou incompatível.
            </p>
          </div>
          <button
            onClick={this.handleReset}
            className="flex items-center gap-1.5 text-[10px] font-semibold py-1.5 px-3 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <RefreshCw size={10} />
            <span>Tentar Novamente</span>
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
