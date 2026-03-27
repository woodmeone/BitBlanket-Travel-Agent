import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const modelClientMock = vi.hoisted(() => ({
  getAvailableModels: vi.fn(),
  setSessionModel: vi.fn(),
}));

vi.mock('@/services/api', () => ({
  modelClient: modelClientMock,
}));

import { DEFAULT_MODELS, resolveBootstrapModelId, useModelBootstrapState } from '@/context/useModelBootstrapState';

describe('useModelBootstrapState helpers', () => {
  it('keeps the preferred model when it is still available', () => {
    expect(resolveBootstrapModelId(DEFAULT_MODELS, 'minimax-m2-5')).toBe('minimax-m2-5');
  });

  it('falls back to the first available model when preferred model is missing', () => {
    expect(
      resolveBootstrapModelId(
        [
          {
            model_id: 'minimax-m2-7',
            name: 'MiniMax M2.7',
            provider: 'anthropic',
            model: 'MiniMax-M2.7',
          },
        ],
        'missing-model'
      )
    ).toBe('minimax-m2-7');
  });
});

describe('useModelBootstrapState', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    modelClientMock.getAvailableModels.mockReset();
    modelClientMock.setSessionModel.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('bootstraps available models and keeps the recovered model selection', async () => {
    modelClientMock.getAvailableModels.mockResolvedValue({
      success: true,
      models: [
        {
          model_id: 'minimax-m2-5',
          name: 'MiniMax M2.5',
          provider: 'anthropic',
          model: 'MiniMax-M2.5',
        },
        {
          model_id: 'minimax-m2-7',
          name: 'MiniMax M2.7',
          provider: 'anthropic',
          model: 'MiniMax-M2.7',
        },
      ],
    });

    const { result } = renderHook(() => useModelBootstrapState({ currentSessionId: null }));

    await act(async () => {
      result.current.recoverModelId('minimax-m2-7');
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(modelClientMock.getAvailableModels).toHaveBeenCalledTimes(1);
    expect(result.current.currentModelId).toBe('minimax-m2-7');
    expect(result.current.availableModels).toHaveLength(2);
  });

  it('persists the selected model to the current session', async () => {
    modelClientMock.getAvailableModels.mockResolvedValue({
      success: false,
      models: [],
    });
    modelClientMock.setSessionModel.mockResolvedValue({
      success: true,
      model_id: 'minimax-m2-7',
    });

    const { result } = renderHook(() => useModelBootstrapState({ currentSessionId: 'session-1' }));

    await act(async () => {
      await result.current.setCurrentModelId('minimax-m2-7');
    });

    expect(result.current.currentModelId).toBe('minimax-m2-7');
    expect(modelClientMock.setSessionModel).toHaveBeenCalledWith('session-1', 'minimax-m2-7');
  });

  it('rethrows session model sync failures so the UI can surface them', async () => {
    modelClientMock.getAvailableModels.mockResolvedValue({
      success: false,
      models: [],
    });
    modelClientMock.setSessionModel.mockRejectedValue(new Error('sync failed'));

    const { result } = renderHook(() => useModelBootstrapState({ currentSessionId: 'session-1' }));

    await act(async () => {
      await expect(result.current.setCurrentModelId('minimax-m2-7')).rejects.toThrow('sync failed');
    });
  });
});
