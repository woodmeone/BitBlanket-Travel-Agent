import type { SubagentEvent } from '@/types';

export function buildSubagentEventKey(event: SubagentEvent, index = 0): string {
  if (event.clientKey) return event.clientKey;

  return [
    event.subagent || 'unknown',
    event.sequence ?? 'na',
    event.timestamp ?? 'na',
    event.status ?? event.trigger ?? 'started',
    event.summary ?? event.description ?? 'no-summary',
    event.skills?.join('|') || 'no-skills',
    index,
  ].join('::');
}
