import { describe, expect, it } from 'vitest';
import { createEmptyTripPlanArtifact, hasArtifactData, mergeTripPlanArtifact } from '@/utils/agentArtifacts';

describe('agentArtifacts', () => {
  it('deep merges artifact patches without dropping previous branches', () => {
    const base = mergeTripPlanArtifact(null, {
      itinerary: { planId: 'plan-1', validationStatus: 'pass' },
      research: { summary: 'initial research' },
    });

    const merged = mergeTripPlanArtifact(base, {
      verification: { passed: true, summary: 'checked' },
      research: { evidence: [{ tool: 'search_cities' }] },
    });

    expect(merged?.itinerary.planId).toBe('plan-1');
    expect(merged?.research.summary).toBe('initial research');
    expect(merged?.research.evidence).toEqual([{ tool: 'search_cities' }]);
    expect(merged?.verification.passed).toBe(true);
  });

  it('detects whether artifact has meaningful data', () => {
    expect(hasArtifactData(createEmptyTripPlanArtifact())).toBe(false);
    expect(
      hasArtifactData(
        mergeTripPlanArtifact(null, {
          itinerary: { planId: 'plan-2' },
        })
      )
    ).toBe(true);
  });
});
