# Release Harness Scorecard

- generated_at: `2026-03-28T07:17:43.879202+00:00`
- status: `warn`
- errors: `0`
- warnings: `2`

## Benchmark

- golden pass rate: `1.0000`
- golden hallucination rate: `0.0000`
- benchmark success rate: `0.6834`
- benchmark fallback steps total: `2`

## Subagents

- expected: `['research', 'planning', 'budget', 'verification']`
- observed: `['planning', 'research', 'verification']`
- healthy / partial / missing / mismatch: `0 / 2 / 1 / 1`

## Delivery

- snapshot: `frontend/tests/features/trip-plan/__snapshots__/travelPlanDeliverySnapshot.test.ts.snap`
- replay modes: `['direct', 'plan', 'react']`
- branding present: `True`

## Skills

- total skills: `7`
- docs covered: `7`
- eval covered: `7`
- selection policy covered: `7`

## Findings

- `warning` `subagents`: subagent scorecard still reports 1 missing subagent(s)
- `warning` `subagents`: subagent scorecard still reports 1 mismatch subagent(s)

