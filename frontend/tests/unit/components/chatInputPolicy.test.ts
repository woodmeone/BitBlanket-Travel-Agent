import { describe, expect, it } from 'vitest';
import {
  buildSessionName,
  buildStoppedMessageContent,
  prepareChatInput,
} from '@/components/chat-area/chatInputPolicy';

describe('chatInputPolicy', () => {
  it('returns null for blank input', () => {
    expect(
      prepareChatInput('   ', {
        selectedConstraints: [],
        budgetUpperLimit: null,
        compareModeEnabled: false,
        comparePlanCount: 2,
      })
    ).toBeNull();
  });

  it('builds enriched prompt and session bootstrap fields', () => {
    const result = prepareChatInput('\u4e0a\u6d77\u5468\u672b\u4e24\u65e5\u6e38  ', {
      selectedConstraints: ['\u4eb2\u5b50'],
      budgetUpperLimit: 2800,
      compareModeEnabled: true,
      comparePlanCount: 3,
    });

    expect(result).not.toBeNull();
    expect(result?.displayMessage).toBe('\u4e0a\u6d77\u5468\u672b\u4e24\u65e5\u6e38');
    expect(result?.enrichedPrompt).toContain('\u4e0a\u6d77\u5468\u672b\u4e24\u65e5\u6e38');
    expect(result?.enrichedPrompt).toContain('2800');
    expect(result?.sessionName).toBe(buildSessionName('\u4e0a\u6d77\u5468\u672b\u4e24\u65e5\u6e38'));
  });

  it('builds stopped message content with fallback text', () => {
    expect(buildStoppedMessageContent('partial answer')).toContain('partial answer');
    expect(buildStoppedMessageContent('')).toContain('\u5df2\u505c\u6b62\u751f\u6210');
  });
});
