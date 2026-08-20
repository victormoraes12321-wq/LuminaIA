'use client';

/**
 * ============================================================
 * LUMINA AI — useSSEEvents Hook
 * ============================================================
 * Listens to Server-Sent Events from the backend for
 * Smart Refresh — updates Runtime Datasets without
 * rebuilding the full dashboard.
 * ============================================================
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { SSERefreshEvent } from '@/types/dashboard-runtime';
import { getApiBase } from '@/lib/utils';

export interface UseSSEEventsOptions {
  dashboardId: string | null;
  tenantId: string | null;
  token: string | null;
  onRefresh: (event: SSERefreshEvent) => void;
  onError?: (error: string) => void;
  enabled?: boolean;
}

export interface UseSSEEventsResult {
  connected: boolean;
  lastEvent: SSERefreshEvent | null;
  reconnect(): void;
}

/**
 * Connects to the backend SSE endpoint for Smart Dashboard Refresh.
 * Automatically reconnects on disconnection with exponential backoff.
 */
export function useSSEEvents({
  dashboardId,
  tenantId,
  token,
  onRefresh,
  onError,
  enabled = true,
}: UseSSEEventsOptions): UseSSEEventsResult {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSERefreshEvent | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectRef = useRef<() => void>(() => undefined);

  const connect = useCallback(() => {
    if (!dashboardId || !tenantId || !token || !enabled) return;

    // Close existing connection
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    const base = getApiBase();
    const url = `${base}/api/v1/dashboard-runtime/sse/${dashboardId}?tenant_id=${tenantId}&token=${encodeURIComponent(token)}`;

    const es = new EventSource(url, { withCredentials: true });
    esRef.current = es;

    es.onopen = () => {
      setConnected(true);
      retryCountRef.current = 0;
    };

    es.addEventListener('data_refresh', (e: MessageEvent) => {
      try {
        const event: SSERefreshEvent = JSON.parse(e.data);
        setLastEvent(event);
        onRefresh(event);
      } catch {
        // Ignore parse errors
      }
    });

    es.addEventListener('layout_refresh', (e: MessageEvent) => {
      try {
        const event: SSERefreshEvent = JSON.parse(e.data);
        setLastEvent(event);
        onRefresh(event);
      } catch {
        // Ignore parse errors
      }
    });

    es.addEventListener('error_event', (e: MessageEvent) => {
      try {
        const event: SSERefreshEvent = JSON.parse(e.data);
        onError?.(event.error ?? 'Unknown SSE error');
      } catch {
        onError?.('SSE parse error');
      }
    });

    es.onerror = () => {
      setConnected(false);
      es.close();
      esRef.current = null;

      // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
      const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30_000);
      retryCountRef.current++;

      retryTimerRef.current = setTimeout(() => connectRef.current(), delay);
    };
  }, [dashboardId, tenantId, token, enabled, onRefresh, onError]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      setConnected(false);
    };
  }, [connect]);

  return {
    connected,
    lastEvent,
    reconnect: connect,
  };
}
