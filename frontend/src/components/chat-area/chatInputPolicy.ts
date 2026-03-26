'use client';

import { buildEnhancedPrompt, type ComparePlanCount } from './shared';

export interface PrepareChatInputOptions {
  budgetUpperLimit: number | null;
  compareModeEnabled: boolean;
  comparePlanCount: ComparePlanCount;
  selectedConstraints: string[];
}

export interface PreparedChatInput {
  displayMessage: string;
  enrichedPrompt: string;
  sessionName: string;
  trimmed: string;
}

export function buildSessionName(displayMessage: string): string {
  return displayMessage.slice(0, 15) + (displayMessage.length > 15 ? '...' : '');
}

export function buildStoppedMessageContent(content: string): string {
  return `${content || '\u5df2\u505c\u6b62\u751f\u6210'}\n\n\u26a0\ufe0f \u5df2\u505c\u6b62\u751f\u6210`;
}

export function prepareChatInput(
  rawInput: string,
  options: PrepareChatInputOptions
): PreparedChatInput | null {
  const trimmed = rawInput.trim();
  if (!trimmed) return null;

  return {
    trimmed,
    displayMessage: trimmed,
    enrichedPrompt: buildEnhancedPrompt(trimmed, options),
    sessionName: buildSessionName(trimmed),
  };
}
