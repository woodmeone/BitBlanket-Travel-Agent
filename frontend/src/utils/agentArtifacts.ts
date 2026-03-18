import type { ArtifactPatch, TripPlanArtifact } from '@/types';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function cloneValue<T>(value: T): T {
  if (Array.isArray(value)) return value.map((item) => cloneValue(item)) as T;
  if (isRecord(value)) {
    const next: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value)) next[key] = cloneValue(item);
    return next as T;
  }
  return value;
}

function mergeRecord(
  target: Record<string, unknown>,
  patch: Record<string, unknown>
): Record<string, unknown> {
  const merged: Record<string, unknown> = { ...target };
  for (const [key, value] of Object.entries(patch)) {
    const current = merged[key];
    if (isRecord(current) && isRecord(value)) {
      merged[key] = mergeRecord(current, value);
      continue;
    }
    merged[key] = cloneValue(value);
  }
  return merged;
}

export function createEmptyTripPlanArtifact(): TripPlanArtifact {
  return {
    intent: {
      name: 'general',
      confidence: null,
      entities: {},
      detail: {},
    },
    research: {
      summary: '',
      evidence: [],
      destinations: [],
      sourceTools: [],
    },
    itinerary: {
      planId: null,
      explanation: '',
      steps: [],
      validationStatus: 'pass',
      validationErrors: [],
    },
    budget: {
      summary: {},
      executionBudget: {},
      staleResultCount: 0,
      fallbackSteps: 0,
    },
    verification: {
      passed: null,
      shouldRetry: false,
      issues: [],
      refreshTargets: [],
      summary: '',
    },
    answer: '',
    reasoning: '',
    toolsUsed: [],
    metadata: {},
  };
}

export function mergeTripPlanArtifact(
  baseArtifact: TripPlanArtifact | null | undefined,
  patch: ArtifactPatch | TripPlanArtifact | null | undefined
): TripPlanArtifact | null {
  if (!patch) return baseArtifact ?? null;

  const nextBase = baseArtifact ? cloneValue(baseArtifact) : createEmptyTripPlanArtifact();
  return mergeRecord(
    nextBase as unknown as Record<string, unknown>,
    patch as unknown as Record<string, unknown>
  ) as unknown as TripPlanArtifact;
}

export function hasArtifactData(artifact: TripPlanArtifact | null | undefined): boolean {
  if (!artifact) return false;

  return Boolean(
    artifact.answer ||
      artifact.reasoning ||
      artifact.toolsUsed.length > 0 ||
      artifact.research.summary ||
      artifact.research.evidence.length > 0 ||
      artifact.itinerary.planId ||
      artifact.itinerary.steps.length > 0 ||
      artifact.verification.summary ||
      artifact.verification.passed !== null &&
        artifact.verification.passed !== undefined
  );
}
