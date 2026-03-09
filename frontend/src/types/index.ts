export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  reasoning?: string;
  diagnostics?: MessageDiagnostics;
}

export interface MessageDiagnostics {
  toolsUsed?: string[];
  verificationPassed?: boolean | null;
  staleResultCount?: number;
  fallbackSteps?: number;
  planId?: string | null;
  executionStats?: Record<string, unknown>;
}

export interface PlanPreviewStep {
  id?: string;
  title?: string;
  description?: string;
  tool?: string;
  [key: string]: unknown;
}

export interface PlanPreview {
  planId?: string | null;
  intent?: string | null;
  explanation?: string | null;
  validationStatus?: string | null;
  validationErrors?: string[];
  steps: PlanPreviewStep[];
}

export interface StreamStageEvent {
  stage?: string;
  label?: string;
  progress?: number | null;
}

export interface SessionInfo {
  session_id: string;
  message_count: number;
  last_active: string;
  name?: string;
  model_id?: string;
}

export interface AppConfig {
  apiBase: string;
}

export type ChatMode = 'direct' | 'react' | 'plan';

export interface ChatRequest {
  message: string;
  session_id: string;
  mode?: ChatMode;
}

export interface ChatResponse {
  success: boolean;
  response?: string;
  error?: string;
  session_id?: string;
}

export interface ModelInfo {
  model_id: string;
  name: string;
  provider: string;
  model: string;
}

export interface AvailableModelsResponse {
  success: boolean;
  models: ModelInfo[];
}

export interface SetModelRequest {
  model_id: string;
}

export interface SetModelResponse {
  success: boolean;
  message?: string;
  model_id: string;
}

export interface GetSessionModelResponse {
  success: boolean;
  model_id: string;
}

export interface CityAttraction {
  name: string;
  type: string;
  duration: string;
  ticket: number;
}

export interface CitySummary {
  id: string;
  name: string;
  region: string;
  tags: string[];
}

export interface CityDetail extends CitySummary {
  description: string;
  attractions: CityAttraction[];
  avg_budget_per_day: number;
  best_seasons: string[];
}

export interface CityListResponse {
  cities: CitySummary[];
}

export interface RegionListResponse {
  regions: string[];
}

export interface TagListResponse {
  tags: string[];
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  services: Record<string, string>;
}

export interface LLMHealthResponse {
  status: 'ok' | 'not initialized';
  llm_adapter: boolean;
  tools_count: number;
  memory_enabled: boolean;
}

export interface ToolsHealthResponse {
  status: 'ok' | 'not initialized';
  initialized: boolean;
  configured_tools_count: number;
  circuit_open_count: number;
  slo: Record<string, unknown>;
  intent_aggregate: Record<string, Record<string, unknown>>;
  window_minutes: number;
  diagnostics: Record<string, unknown>;
}

export interface ToolIntentsHealthResponse {
  status: 'ok' | 'not initialized';
  window_minutes: number;
  total_requests: number;
  intent_aggregate: Record<string, Record<string, unknown>>;
}
