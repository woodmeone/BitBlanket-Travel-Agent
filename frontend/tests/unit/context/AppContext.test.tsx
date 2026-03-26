import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';

const sessionClientMock = vi.hoisted(() => ({
  getSessions: vi.fn(),
  getSessionMessages: vi.fn(),
}));

const modelClientMock = vi.hoisted(() => ({
  getAvailableModels: vi.fn(),
  getSessionModel: vi.fn(),
  setSessionModel: vi.fn(),
}));

vi.mock('@/services/api', () => ({
  sessionClient: sessionClientMock,
  modelClient: modelClientMock,
}));

import { AppProvider, useAppContext } from '@/context/AppContext';

function Probe() {
  const { currentSessionId, messages } = useAppContext();
  const firstMessage = messages[0];
  return (
    <div>
      <div data-testid="session-id">{currentSessionId ?? 'none'}</div>
      <div data-testid="message-content">{firstMessage?.content ?? 'empty'}</div>
      <div data-testid="plan-id">{firstMessage?.diagnostics?.artifact?.itinerary.planId ?? 'none'}</div>
    </div>
  );
}

describe('AppProvider session hydration', () => {
  beforeEach(() => {
    window.localStorage.clear();
    sessionClientMock.getSessions.mockReset();
    sessionClientMock.getSessionMessages.mockReset();
    modelClientMock.getAvailableModels.mockReset();
    modelClientMock.getSessionModel.mockReset();
    modelClientMock.setSessionModel.mockReset();
    modelClientMock.getAvailableModels.mockResolvedValue({ success: false, models: [] });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('restores stored session messages and diagnostics after refresh', async () => {
    const now = new Date().toISOString();
    window.localStorage.setItem('moyuan-current-session-id', 'session-1');

    sessionClientMock.getSessions.mockResolvedValue({
      sessions: [{ session_id: 'session-1', message_count: 2, last_active: now, name: 'Saved session' }],
    });
    sessionClientMock.getSessionMessages.mockResolvedValue({
      success: true,
      messages: [
        {
          role: 'assistant',
          content: 'saved answer',
          timestamp: '10:01:00',
          diagnostics: {
            artifact: {
              intent: { name: 'itinerary', entities: {}, detail: {} },
              research: { summary: 'Saved research', evidence: [], destinations: [], sourceTools: [] },
              itinerary: {
                planId: 'plan-restored',
                explanation: 'Restored itinerary',
                steps: [],
                validationStatus: 'pass',
                validationErrors: [],
              },
              budget: { summary: {}, executionBudget: {}, staleResultCount: 0, fallbackSteps: 0 },
              verification: { passed: true, shouldRetry: false, issues: [], refreshTargets: [], summary: 'ok' },
              answer: 'saved answer',
              reasoning: '',
              toolsUsed: [],
              metadata: {},
            },
          },
        },
      ],
    });
    modelClientMock.getSessionModel.mockResolvedValue({
      success: true,
      model_id: 'minimax-m2-5',
    });

    render(
      <AppProvider>
        <Probe />
      </AppProvider>
    );

    await waitFor(() => expect(screen.getByTestId('session-id')).toHaveTextContent('session-1'));
    await waitFor(() => expect(screen.getByTestId('message-content')).toHaveTextContent('saved answer'));
    expect(screen.getByTestId('plan-id')).toHaveTextContent('plan-restored');
    expect(sessionClientMock.getSessionMessages).toHaveBeenCalledWith('session-1');
  });
});
