import { describe, expect, it } from 'vitest';
import { normalizePersistedMessages } from '@/utils/sessionMessages';

describe('normalizePersistedMessages', () => {
  it('keeps assistant diagnostics for artifact-backed sessions', () => {
    const messages = normalizePersistedMessages([
      {
        role: 'assistant',
        content: 'saved answer',
        timestamp: '10:00:00',
        diagnostics: {
          planId: 'plan-321',
          artifact: {
            intent: { name: 'itinerary', entities: {}, detail: {} },
            research: { summary: 'Saved research', evidence: [], destinations: [], sourceTools: [] },
            itinerary: { planId: 'plan-321', explanation: '', steps: [], validationStatus: 'pass', validationErrors: [] },
            budget: { summary: {}, executionBudget: {}, staleResultCount: 0, fallbackSteps: 0 },
            verification: { passed: true, shouldRetry: false, issues: [], refreshTargets: [], summary: 'ok' },
            answer: 'saved answer',
            reasoning: '',
            toolsUsed: [],
            metadata: {},
          },
          subagentEvents: [{ subagent: 'planning', status: 'completed', timestamp: '10:00:01' }],
        },
      },
    ]);

    expect(messages).toHaveLength(1);
    expect(messages[0].diagnostics?.planId).toBe('plan-321');
    expect(messages[0].diagnostics?.artifact?.itinerary.planId).toBe('plan-321');
    expect(messages[0].diagnostics?.subagentEvents?.[0]?.subagent).toBe('planning');
  });
});
