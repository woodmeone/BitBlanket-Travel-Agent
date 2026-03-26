import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { StreamStageEvent } from '@/types';
import { useChatRunState } from '@/components/chat-area/useChatRunState';

describe('useChatRunState', () => {
  it('tracks stage and tool lifecycle', () => {
    const { result } = renderHook(() => useChatRunState());
    const stage: StreamStageEvent = {
      stage: 'planning',
      label: '\u89c4\u5212',
      progress: 0.35,
      subagent: 'planning',
    };

    act(() => {
      result.current.beginRun('PLAN');
      result.current.recordStage(stage);
      result.current.recordToolStart('search');
      result.current.recordToolEnd('search');
    });

    expect(result.current.waitingForResponse).toBe(true);
    expect(result.current.isThinking).toBe(true);
    expect(result.current.stageState).toEqual(stage);
    expect(result.current.stageHistory).toEqual([stage]);
    expect(result.current.currentTool).toBeNull();
    expect(result.current.runtimeLogs).toHaveLength(4);
    expect(result.current.runtimeLogs.at(-1)?.detail).toBe('search');
  });

  it('clears transient state on fail, stop, and reset', () => {
    const { result } = renderHook(() => useChatRunState());

    act(() => {
      result.current.beginRun('REACT');
      result.current.recordToolStart('planner');
      result.current.failRun('boom');
    });

    expect(result.current.error).toBe('boom');
    expect(result.current.waitingForResponse).toBe(false);
    expect(result.current.currentTool).toBeNull();

    act(() => {
      result.current.stopRun();
      result.current.resetRunState();
    });

    expect(result.current.error).toBeNull();
    expect(result.current.waitingForResponse).toBe(false);
    expect(result.current.stageState).toBeNull();
    expect(result.current.runtimeLogs).toEqual([]);
  });
});
