'use client';

/**
 * ============================================================
 * LUMINA AI — useDashboardRuntime Hook
 * ============================================================
 * Central orchestration hook for the Dashboard Runtime Engine.
 *
 * Responsibilities:
 * - Fetches the ADE/ECE payload from the backend
 * - Manages loading/error/ready states
 * - Handles Smart Refresh via SSE
 * - Manages cross-filter state
 * - Manages expand/fullscreen state
 *
 * Rule: NO business logic. Only data fetching and UI state.
 * ============================================================
 */

import { useCallback, useReducer, useRef } from 'react';
import type {
  DashboardRuntimePayload,
  DashboardRuntimeState,
  RuntimeStatus,
  FilterValue,
  CrossFilterEvent,
  SSERefreshEvent,
  RuntimeWidget,
} from '@/types/dashboard-runtime';
import { getApiBase } from '@/lib/utils';
import { useSSEEvents } from './useSSEEvents';

// ─────────────────────────────────────────────
// REDUCER
// ─────────────────────────────────────────────

type Action =
  | { type: 'SET_STATUS'; status: RuntimeStatus }
  | { type: 'SET_PAYLOAD'; payload: DashboardRuntimePayload }
  | { type: 'SET_ERROR'; error: string }
  | { type: 'CLEAR_ERROR' }
  | { type: 'EXPAND_COMPONENT'; id: string | null }
  | { type: 'SET_FILTER'; key: string; value: FilterValue }
  | { type: 'CLEAR_FILTER'; key: string }
  | { type: 'CLEAR_ALL_FILTERS' }
  | { type: 'SMART_REFRESH'; widgets: Partial<RuntimeWidget>[] }
  | { type: 'SET_REFRESHED_AT'; at: string };

const initialState: DashboardRuntimeState = {
  status: 'idle',
  payload: null,
  activeBreakpoint: 'desktop',
  expandedComponentId: null,
  activeFilters: {},
  error: null,
  lastRefreshedAt: null,
};

function reducer(
  state: DashboardRuntimeState,
  action: Action,
): DashboardRuntimeState {
  switch (action.type) {
    case 'SET_STATUS':
      return { ...state, status: action.status, error: null };

    case 'SET_PAYLOAD':
      return {
        ...state,
        status: 'ready',
        payload: action.payload,
        error: null,
        lastRefreshedAt: new Date().toISOString(),
      };

    case 'SET_ERROR':
      return { ...state, status: 'error', error: action.error };

    case 'CLEAR_ERROR':
      return { ...state, error: null };

    case 'EXPAND_COMPONENT':
      return { ...state, expandedComponentId: action.id };

    case 'SET_FILTER':
      return {
        ...state,
        activeFilters: { ...state.activeFilters, [action.key]: action.value },
      };

    case 'CLEAR_FILTER': {
      const { [action.key]: _, ...rest } = state.activeFilters;
      return { ...state, activeFilters: rest };
    }

    case 'CLEAR_ALL_FILTERS':
      return { ...state, activeFilters: {} };

    case 'SMART_REFRESH': {
      if (!state.payload) return state;
      const updatedWidgets = state.payload.widgets.map((w) => {
        const update = action.widgets.find((u) => u.id === w.id);
        return update ? { ...w, ...update } : w;
      });
      return {
        ...state,
        status: 'ready',
        payload: { ...state.payload, widgets: updatedWidgets },
        lastRefreshedAt: new Date().toISOString(),
      };
    }

    case 'SET_REFRESHED_AT':
      return { ...state, lastRefreshedAt: action.at };

    default:
      return state;
  }
}

// ─────────────────────────────────────────────
// HOOK
// ─────────────────────────────────────────────

export interface UseDashboardRuntimeOptions {
  token: string | null;
  tenantId: string | null;
  enableSSE?: boolean;
}

export interface UseDashboardRuntimeResult {
  state: DashboardRuntimeState;
  /** Fetch a new dashboard payload from the backend */
  fetchDashboard(dashboardId: string): Promise<void>;
  /** Trigger a full reload of the current dashboard */
  reloadDashboard(): Promise<void>;
  /** Expand a component to fullscreen (null to collapse) */
  expandComponent(id: string | null): void;
  /** Apply a cross-filter */
  applyFilter(event: CrossFilterEvent): void;
  /** Remove a specific filter */
  clearFilter(key: string): void;
  /** Remove all active filters */
  clearAllFilters(): void;
  /** Whether SSE is connected for Smart Refresh */
  sseConnected: boolean;
}

export function useDashboardRuntime({
  token,
  tenantId,
  enableSSE = true,
}: UseDashboardRuntimeOptions): UseDashboardRuntimeResult {
  const [state, dispatch] = useReducer(reducer, initialState);
  const currentDashboardIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // ─── Fetch ────────────────────────────────

  const fetchDashboard = useCallback(
    async (dashboardId: string) => {
      if (!token || !tenantId) return;

      // Cancel previous request
      if (abortRef.current) {
        abortRef.current.abort();
      }
      const controller = new AbortController();
      abortRef.current = controller;

      currentDashboardIdRef.current = dashboardId;
      dispatch({ type: 'SET_STATUS', status: 'loading' });

      try {
        const base = getApiBase();
        const res = await fetch(
          `${base}/api/v1/dashboard-runtime/${dashboardId}?tenant_id=${tenantId}`,
          {
            credentials: 'include',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            signal: controller.signal,
          },
        );

        if (res.status === 401) {
          dispatch({ type: 'SET_ERROR', error: 'Sessão expirada. Por favor, faça login novamente.' });
          return;
        }

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Erro desconhecido' }));
          dispatch({ type: 'SET_ERROR', error: err.detail ?? 'Erro ao carregar dashboard' });
          return;
        }

        const payload: DashboardRuntimePayload = await res.json();
        dispatch({ type: 'SET_PAYLOAD', payload });
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        dispatch({
          type: 'SET_ERROR',
          error: 'Falha na conexão com o servidor. Verifique sua rede.',
        });
      }
    },
    [token, tenantId],
  );

  const reloadDashboard = useCallback(async () => {
    const id = currentDashboardIdRef.current;
    if (id) await fetchDashboard(id);
  }, [fetchDashboard]);

  // ─── SSE Smart Refresh ────────────────────

  const handleSSERefresh = useCallback((event: SSERefreshEvent) => {
    if (event.event_type === 'data_refresh' && event.widgets) {
      dispatch({ type: 'SMART_REFRESH', widgets: event.widgets });
    } else if (event.event_type === 'layout_refresh') {
      // Full reload needed for layout changes
      if (currentDashboardIdRef.current) {
        fetchDashboard(currentDashboardIdRef.current);
      }
    }
  }, [fetchDashboard]);

  const { connected: sseConnected } = useSSEEvents({
    dashboardId: state.payload?.dashboard_id ?? null,
    tenantId,
    token,
    onRefresh: handleSSERefresh,
    enabled: enableSSE && state.status === 'ready',
  });

  // ─── Interaction Controls ─────────────────

  const expandComponent = useCallback((id: string | null) => {
    dispatch({ type: 'EXPAND_COMPONENT', id });
  }, []);

  const applyFilter = useCallback((event: CrossFilterEvent) => {
    dispatch({ type: 'SET_FILTER', key: event.filterKey, value: event.filterValue });
  }, []);

  const clearFilter = useCallback((key: string) => {
    dispatch({ type: 'CLEAR_FILTER', key });
  }, []);

  const clearAllFilters = useCallback(() => {
    dispatch({ type: 'CLEAR_ALL_FILTERS' });
  }, []);

  return {
    state,
    fetchDashboard,
    reloadDashboard,
    expandComponent,
    applyFilter,
    clearFilter,
    clearAllFilters,
    sseConnected,
  };
}
