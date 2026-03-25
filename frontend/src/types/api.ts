/**
 * O2C Graph Intelligence — API Type Definitions  (T14: TypeScript)
 *
 * Shared types for all API → frontend data flows.
 * New files use TypeScript; existing .jsx files remain JS to avoid churn.
 */

// ── Query API  /api/query ────────────────────────────────────────────────────

export interface QueryPlan {
  intent: 'trace_flow' | 'detect_anomaly' | 'status_lookup' | 'analyze' | 'compare_analytics';
  entity_type?: string;
  entity_id?: string;
  metric?: string;
  group_by?: string;
  operation?: string;
  anomaly_sub_type?: string;
  confidence?: number;
  clarification?: string | null;
  filters?: QueryFilter[];
}

export interface QueryFilter {
  field: string;
  op: '>=' | '<=' | '=' | '!=' | '>' | '<';
  value: string | number;
}

export interface QueryVerification {
  status: 'ok' | 'warn' | 'error';
  warnings: string[];
}

export interface QueryResult {
  status: 'success' | 'rejected' | 'blocked' | 'error' | 'clarification';
  answer: string;
  sql?: string;
  results?: Record<string, unknown>[];
  result_columns?: string[];
  row_count?: number;
  total_results?: number;
  trace_id?: string;
  intent?: string;
  plan?: QueryPlan;
  verification?: QueryVerification;
  suggestions?: string[];
  trace_events?: TraceEvent[];
}

// ── Trace Events  /api/query/trace/{id} ─────────────────────────────────────

export interface TraceEvent {
  ts: string;
  trace_id: string;
  stage: string;
  payload: Record<string, unknown>;
}

// ── Dashboard Cards  /api/dashboard ─────────────────────────────────────────

export type CardSeverity = 'warning' | 'critical' | undefined;

export interface DashboardCard {
  id: string;
  label: string;
  value: string | number;
  icon: string;
  detail?: string;
  trend?: number | null;
  severity?: CardSeverity;
}

export interface DashboardResponse {
  cards: DashboardCard[];
}

// ── Graph API  /api/graph ────────────────────────────────────────────────────

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  properties?: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats?: {
    node_count: number;
    edge_count: number;
    table_names: string[];
  };
}

// ── Export Utility  (T9) ─────────────────────────────────────────────────────

export type ExportFormat = 'csv' | 'json';

export interface ExportOptions {
  filename?: string;
  format: ExportFormat;
}
