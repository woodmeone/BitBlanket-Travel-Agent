import type {
  ArtifactPatch,
  ExecutionReceipt,
  PlanPreview,
  StreamStageEvent,
  SubagentEvent,
  TripPlanArtifact,
} from '@/types';

export enum SSEConnectionStatus {
  IDLE = 'idle',
  CONNECTING = 'connecting',
  STREAMING = 'streaming',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
  DISCONNECTED = 'disconnected',
}

export interface StreamMetadata {
  sessionId?: string;
  totalSteps: number;
  toolsUsed: string[];
  hasReasoning: boolean;
  reasoningLength: number;
  answerLength: number;
  verificationPassed: boolean | null;
  staleResultCount: number;
  fallbackSteps: number;
  planId?: string | null;
  executionStats?: Record<string, unknown>;
  runId?: string;
  requestId?: string;
  traceId?: string;
  artifact?: TripPlanArtifact | null;
  executionReceipt?: ExecutionReceipt | null;
}

export interface StreamCompletionPayload {
  artifact?: TripPlanArtifact | null;
  sessionId?: string;
  runId?: string;
  requestId?: string;
  traceId?: string;
  executionReceipt?: ExecutionReceipt | null;
}

export interface StreamCallbacks {
  onSessionId?: (sessionId: string) => void;
  onStage?: (stage: StreamStageEvent) => void;
  onPlanPreview?: (preview: PlanPreview) => void;
  onSubagentStart?: (event: SubagentEvent) => void;
  onSubagentEnd?: (event: SubagentEvent) => void;
  onArtifactPatch?: (subagent: string, patch: ArtifactPatch) => void;
  onChunk: (content: string) => void;
  onReasoning: (content: string) => void;
  onReasoningStart: () => void;
  onReasoningEnd: () => void;
  onReasoningTimestamp: (timestamp: string) => void;
  onAnswerStart: () => void;
  onToolStart?: (toolName: string) => void;
  onToolEnd?: (toolName: string, result: string) => void;
  onMetadata: (data: StreamMetadata) => void;
  onError: (error: string) => void;
  onComplete: (payload?: StreamCompletionPayload) => void;
  onStop?: () => boolean;
  onConnectionChange?: (status: SSEConnectionStatus) => void;
}
