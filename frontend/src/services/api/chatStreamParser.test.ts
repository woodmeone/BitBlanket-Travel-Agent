import { describe, expect, it, vi } from 'vitest';
import { CHAT_STREAM_EVENT_TYPES } from '@/types';
import { handleChatStreamLine } from './chatStreamParser';
import { SSEConnectionStatus, type StreamCallbacks } from './chatStreamTypes';

function createCallbacks(): StreamCallbacks {
  return {
    onChunk: vi.fn(),
    onReasoning: vi.fn(),
    onReasoningStart: vi.fn(),
    onReasoningEnd: vi.fn(),
    onReasoningTimestamp: vi.fn(),
    onAnswerStart: vi.fn(),
    onMetadata: vi.fn(),
    onError: vi.fn(),
    onComplete: vi.fn(),
    onSessionId: vi.fn(),
    onStage: vi.fn(),
    onPlanPreview: vi.fn(),
    onSubagentStart: vi.fn(),
    onSubagentEnd: vi.fn(),
    onArtifactPatch: vi.fn(),
    onToolStart: vi.fn(),
    onToolEnd: vi.fn(),
    onConnectionChange: vi.fn(),
  };
}

describe('handleChatStreamLine', () => {
  it('normalizes plan preview payloads', () => {
    const callbacks = createCallbacks();
    const lifecycle = {
      finalizeRequest: vi.fn(),
      setConnectionStatus: vi.fn(),
    };

    const terminal = handleChatStreamLine(
      `data: ${JSON.stringify({
        type: CHAT_STREAM_EVENT_TYPES.PLAN_PREVIEW,
        plan_id: 'plan-1',
        intent: 'weekend',
        explanation: 'fit',
        validation_status: 'ok',
        validation_errors: [{ code: 'TOOL_NOT_REGISTERED', step_id: 's1' }],
        steps: [{ title: 'step-1' }],
        artifact: { title: 'artifact' },
        artifact_patch: { title: 'patch' },
        subagent: 'planner',
        skills: ['planning'],
      })}`,
      callbacks,
      lifecycle
    );

    expect(terminal).toBe(false);
    expect(callbacks.onPlanPreview).toHaveBeenCalledWith({
      planId: 'plan-1',
      intent: 'weekend',
      explanation: 'fit',
      validationStatus: 'ok',
      validationErrors: [{ code: 'TOOL_NOT_REGISTERED', step_id: 's1' }],
      steps: [{ title: 'step-1' }],
      artifact: { title: 'artifact' },
      artifactPatch: { title: 'patch' },
      subagent: 'planner',
      skills: ['planning'],
    });
    expect(lifecycle.finalizeRequest).not.toHaveBeenCalled();
  });

  it('treats done as a terminal event', () => {
    const callbacks = createCallbacks();
    const lifecycle = {
      finalizeRequest: vi.fn(),
      setConnectionStatus: vi.fn(),
    };

    const terminal = handleChatStreamLine(
      `data: ${JSON.stringify({
        type: CHAT_STREAM_EVENT_TYPES.DONE,
        artifact: { title: 'trip' },
        run_id: 'run-1',
        request_id: 'req-1',
        trace_id: 'trace-1',
        execution_receipt: {
          session_id: 'session-1',
          run_id: 'run-1',
          subagent_order: ['planning'],
          segments: [{ subagent: 'planning', sequence: 1, tool_names: ['plan_itinerary'] }],
        },
      })}`,
      callbacks,
      lifecycle
    );

    expect(terminal).toBe(true);
    expect(lifecycle.setConnectionStatus).toHaveBeenCalledWith(SSEConnectionStatus.IDLE);
    expect(lifecycle.finalizeRequest).toHaveBeenCalledTimes(1);
    expect(callbacks.onComplete).toHaveBeenCalledWith({
      artifact: { title: 'trip' },
      runId: 'run-1',
      requestId: 'req-1',
      traceId: 'trace-1',
      executionReceipt: {
        session_id: 'session-1',
        run_id: 'run-1',
        subagent_order: ['planning'],
        segments: [{ subagent: 'planning', sequence: 1, tool_names: ['plan_itinerary'] }],
      },
    });
  });

  it('normalizes metadata payloads with execution receipt', () => {
    const callbacks = createCallbacks();
    const lifecycle = {
      finalizeRequest: vi.fn(),
      setConnectionStatus: vi.fn(),
    };

    const terminal = handleChatStreamLine(
      `data: ${JSON.stringify({
        type: CHAT_STREAM_EVENT_TYPES.METADATA,
        run_id: 'run-1',
        total_steps: 2,
        tools_used: ['search_cities'],
        has_reasoning: true,
        reasoning_length: 10,
        answer_length: 20,
        execution_stats: {},
        verification_passed: true,
        stale_result_count: 0,
        fallback_steps: 0,
        artifact: { title: 'trip' },
        execution_receipt: {
          session_id: 'session-1',
          run_id: 'run-1',
          subagent_order: ['research'],
          tools_used: ['search_cities'],
          segments: [{ subagent: 'research', sequence: 1, tools_used: ['search_cities'] }],
        },
      })}`,
      callbacks,
      lifecycle
    );

    expect(terminal).toBe(false);
    expect(callbacks.onMetadata).toHaveBeenCalledWith(
      expect.objectContaining({
        runId: 'run-1',
        executionReceipt: {
          session_id: 'session-1',
          run_id: 'run-1',
          subagent_order: ['research'],
          tools_used: ['search_cities'],
          segments: [{ subagent: 'research', sequence: 1, tools_used: ['search_cities'] }],
        },
      })
    );
  });

  it('treats error payloads as terminal failures', () => {
    const callbacks = createCallbacks();
    const lifecycle = {
      finalizeRequest: vi.fn(),
      setConnectionStatus: vi.fn(),
    };

    const terminal = handleChatStreamLine(
      `data: ${JSON.stringify({
        type: CHAT_STREAM_EVENT_TYPES.ERROR,
        content: 'boom',
      })}`,
      callbacks,
      lifecycle
    );

    expect(terminal).toBe(true);
    expect(lifecycle.setConnectionStatus).toHaveBeenCalledWith(SSEConnectionStatus.ERROR);
    expect(lifecycle.finalizeRequest).toHaveBeenCalledTimes(1);
    expect(callbacks.onError).toHaveBeenCalledWith('boom');
  });
});
