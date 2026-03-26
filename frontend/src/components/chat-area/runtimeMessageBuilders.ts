'use client';

import type { MessageDiagnostics, SubagentEvent, TripPlanArtifact } from '@/types';
import type { StreamCompletionPayload, StreamMetadata } from '@/services/api';

interface CompletionDiagnosticsArgs {
  artifact: TripPlanArtifact | null;
  completion?: StreamCompletionPayload;
  metadata: StreamMetadata | null;
  subagentEvents: SubagentEvent[];
}

export function buildFinalReasoning(reasoning: string, timestamp?: string): string {
  if (!timestamp) return reasoning;
  return `[Timestamp: ${timestamp}]\n\n${reasoning}`;
}

export function buildCompletionDiagnostics({
  artifact,
  completion,
  metadata,
  subagentEvents,
}: CompletionDiagnosticsArgs): MessageDiagnostics | undefined {
  if (!metadata && !artifact && subagentEvents.length === 0) return undefined;

  return {
    toolsUsed: metadata?.toolsUsed || artifact?.toolsUsed || [],
    verificationPassed: metadata?.verificationPassed ?? artifact?.verification.passed ?? null,
    staleResultCount: metadata?.staleResultCount ?? artifact?.budget.staleResultCount ?? 0,
    fallbackSteps: metadata?.fallbackSteps ?? artifact?.budget.fallbackSteps ?? 0,
    planId: metadata?.planId ?? artifact?.itinerary.planId ?? null,
    executionStats: metadata?.executionStats ?? artifact?.budget.summary,
    artifact,
    subagentEvents,
    runId: completion?.runId || metadata?.runId,
    requestId: completion?.requestId || metadata?.requestId,
    traceId: completion?.traceId || metadata?.traceId,
  };
}

export function buildStoppedDiagnostics({
  artifact,
  subagentEvents,
}: {
  artifact: TripPlanArtifact | null;
  subagentEvents: SubagentEvent[];
}): MessageDiagnostics | undefined {
  if (!artifact && subagentEvents.length === 0) return undefined;
  return { artifact, subagentEvents };
}
