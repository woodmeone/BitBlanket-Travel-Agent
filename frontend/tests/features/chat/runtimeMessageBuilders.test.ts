import { describe, expect, it } from 'vitest';
import {
  buildCompletionDiagnostics,
  buildFinalReasoning,
  buildStoppedDiagnostics,
} from '@/components/chat-area/runtimeMessageBuilders';

describe('runtimeMessageBuilders', () => {
  it('builds timestamped reasoning content', () => {
    expect(buildFinalReasoning('推理正文', '10:30:00')).toBe('[Timestamp: 10:30:00]\n\n推理正文');
    expect(buildFinalReasoning('推理正文')).toBe('推理正文');
  });

  it('prefers runtime metadata but falls back to artifact fields for diagnostics', () => {
    const diagnostics = buildCompletionDiagnostics({
      artifact: {
        intent: { name: '周末游', entities: {}, detail: {} },
        research: { summary: '', evidence: [], destinations: ['杭州'], sourceTools: ['search'] },
        itinerary: {
          planId: 'artifact-plan',
          explanation: '先确定城市再排路线',
          steps: [],
          validationStatus: 'ok',
          validationErrors: [],
        },
        budget: {
          summary: { level: 'balanced' },
          executionBudget: { currency: 'CNY', totalEstimate: 1200 },
          staleResultCount: 3,
          fallbackSteps: 2,
        },
        verification: { passed: false, shouldRetry: false, issues: [], refreshTargets: [], summary: '' },
        answer: 'answer',
        reasoning: 'reasoning',
        toolsUsed: ['artifact-tool'],
        metadata: {},
      },
      completion: { runId: 'done-run', requestId: 'done-request', traceId: 'done-trace' },
      metadata: {
        sessionId: 'session-runtime',
        totalSteps: 5,
        toolsUsed: ['runtime-tool'],
        hasReasoning: true,
        reasoningLength: 10,
        answerLength: 20,
        verificationPassed: true,
        staleResultCount: 1,
        fallbackSteps: 0,
        planId: 'runtime-plan',
        executionStats: { latencyMs: 1200 },
        runId: 'runtime-run',
        requestId: 'runtime-request',
        traceId: 'runtime-trace',
      },
      sessionId: 'session-fallback',
      subagentEvents: [{ subagent: 'planner', status: 'completed' }],
    });

    expect(diagnostics).toMatchObject({
      sessionId: 'session-runtime',
      toolsUsed: ['runtime-tool'],
      verificationPassed: true,
      staleResultCount: 1,
      fallbackSteps: 0,
      planId: 'runtime-plan',
      executionStats: { latencyMs: 1200 },
      runId: 'done-run',
      requestId: 'done-request',
      traceId: 'done-trace',
    });
    expect(diagnostics?.subagentEvents).toHaveLength(1);
  });

  it('returns minimal stopped diagnostics only when runtime artifacts exist', () => {
    expect(buildStoppedDiagnostics({ artifact: null, subagentEvents: [] })).toBeUndefined();
    expect(
      buildStoppedDiagnostics({
        artifact: null,
        sessionId: 'session-stopped',
        subagentEvents: [{ subagent: 'verifier', status: 'stopped' }],
      })
    ).toEqual({
      sessionId: 'session-stopped',
      artifact: null,
      subagentEvents: [{ subagent: 'verifier', status: 'stopped' }],
    });
  });
});
