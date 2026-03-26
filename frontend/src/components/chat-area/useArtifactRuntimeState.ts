'use client';

import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import { useRef, useState } from 'react';
import type { ArtifactPatch, PlanPreview, SubagentEvent, TripPlanArtifact } from '@/types';
import { mergeTripPlanArtifact } from '@/utils/agentArtifacts';
import { MAX_SUBAGENT_EVENTS, nowLabel } from './shared';

interface ArtifactRuntimeState {
  activeSubagent: string | null;
  artifactRef: MutableRefObject<TripPlanArtifact | null>;
  artifactState: TripPlanArtifact | null;
  planPreview: PlanPreview | null;
  subagentEvents: SubagentEvent[];
  subagentEventsRef: MutableRefObject<SubagentEvent[]>;
  applyArtifactPatch: (patch: ArtifactPatch | TripPlanArtifact | null | undefined) => void;
  recordSubagentEvent: (event: SubagentEvent) => void;
  resetArtifactRuntimeState: () => void;
  setPlanPreview: Dispatch<SetStateAction<PlanPreview | null>>;
}

export function useArtifactRuntimeState(): ArtifactRuntimeState {
  const [artifactState, setArtifactState] = useState<TripPlanArtifact | null>(null);
  const [subagentEvents, setSubagentEvents] = useState<SubagentEvent[]>([]);
  const [activeSubagent, setActiveSubagent] = useState<string | null>(null);
  const [planPreview, setPlanPreview] = useState<PlanPreview | null>(null);

  const artifactRef = useRef<TripPlanArtifact | null>(null);
  const subagentEventsRef = useRef<SubagentEvent[]>([]);
  const subagentEventKeyRef = useRef(0);

  const applyArtifactPatch = (patch: ArtifactPatch | TripPlanArtifact | null | undefined) => {
    const merged = mergeTripPlanArtifact(artifactRef.current, patch);
    artifactRef.current = merged;
    setArtifactState(merged);
  };

  const recordSubagentEvent = (event: SubagentEvent) => {
    subagentEventKeyRef.current += 1;
    const stamped: SubagentEvent = {
      ...event,
      timestamp: event.timestamp || nowLabel(),
      clientKey: event.clientKey || `subagent-event-${Date.now()}-${subagentEventKeyRef.current}`,
    };
    const nextEvents = [...subagentEventsRef.current.slice(-MAX_SUBAGENT_EVENTS + 1), stamped];
    subagentEventsRef.current = nextEvents;
    setSubagentEvents(nextEvents);
    if (event.status) {
      setActiveSubagent((current) => (current === event.subagent ? null : current));
      return;
    }
    setActiveSubagent(event.subagent);
  };

  const resetArtifactRuntimeState = () => {
    artifactRef.current = null;
    subagentEventsRef.current = [];
    subagentEventKeyRef.current = 0;
    setArtifactState(null);
    setSubagentEvents([]);
    setActiveSubagent(null);
    setPlanPreview(null);
  };

  return {
    activeSubagent,
    artifactRef,
    artifactState,
    planPreview,
    subagentEvents,
    subagentEventsRef,
    applyArtifactPatch,
    recordSubagentEvent,
    resetArtifactRuntimeState,
    setPlanPreview,
  };
}
