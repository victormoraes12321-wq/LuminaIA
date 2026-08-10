'use client'

import React from 'react'

interface Props {
  traceId: string
  events: any[]
  onClose: () => void
}

export function TraceSummaryDrawer({ traceId, events, onClose }: Props) {
  return (
    <div className="fixed inset-y-0 right-0 max-w-md w-full bg-slate-900 border-l border-slate-800 p-6 shadow-2xl z-50 overflow-y-auto" data-testid="trace-summary-drawer">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-bold text-slate-100">Trace: {traceId.slice(0, 12)}...</h3>
        <button onClick={onClose} className="text-slate-400 hover:text-white font-bold text-lg" data-testid="close-drawer-btn">
          ✕
        </button>
      </div>

      <div className="space-y-4">
        {events.map((evt, i) => (
          <div key={i} className="p-3 bg-slate-800/60 rounded border border-slate-700 text-xs">
            <div className="font-bold text-blue-300 font-mono">{evt.event_type}</div>
            <div className="text-slate-400 mt-1">Span: {evt.span_id}</div>
            <div className="text-slate-500 mt-1">{evt.timestamp}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
