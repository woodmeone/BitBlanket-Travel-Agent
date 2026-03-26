'use client';

import { useEffect, useMemo, useState } from 'react';
import { artifactClient } from '@/services/api';
import type { ArtifactHistoryEntry, SubagentEvent, TripPlanArtifact } from '@/types';
import { logger } from '@/utils/logger';
import type { PlanVariant } from '@/utils/travelPlan';
import { buildArtifactCompareVariant } from './shared';

interface UseArtifactHistoryCompareOptions {
  artifact?: TripPlanArtifact | null;
  content: string;
  runId?: string | null;
  sessionId?: string | null;
  subagentEvents?: SubagentEvent[];
}

interface UseArtifactHistoryCompareResult {
  loading: boolean;
  variants: PlanVariant[];
}

function buildVariantIdentity(variant: PlanVariant): string {
  return variant.runId || variant.artifact?.itinerary.planId || variant.messageTimestamp || variant.id;
}

function buildHistoryVariant(entry: ArtifactHistoryEntry, fallbackContent: string): PlanVariant | null {
  return buildArtifactCompareVariant(entry.artifact, {
    id: entry.run_id || `artifact-history-${entry.message_index}`,
    messageTimestamp: entry.message_timestamp,
    runId: entry.run_id,
    source: 'artifact-history',
    fallbackContent,
    fallbackTitle: `历史方案 ${entry.message_index + 1}`,
  });
}

export function useArtifactHistoryCompare({
  artifact = null,
  content,
  runId = null,
  sessionId = null,
  subagentEvents = [],
}: UseArtifactHistoryCompareOptions): UseArtifactHistoryCompareResult {
  const [entries, setEntries] = useState<ArtifactHistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    if (!sessionId) {
      setEntries([]);
      setLoading(false);
      return () => {
        cancelled = true;
      };
    }

    setLoading(true);
    void artifactClient
      .getArtifactHistory(sessionId, 4)
      .then((response) => {
        if (cancelled) return;
        setEntries(response.success ? response.entries : []);
      })
      .catch((error) => {
        if (cancelled) return;
        logger.warn('加载 artifact history 失败:', error);
        setEntries([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const variants = useMemo(() => {
    const historyVariants = entries
      .map((entry) => buildHistoryVariant(entry, content))
      .filter((variant): variant is PlanVariant => Boolean(variant));

    const currentVariant = buildArtifactCompareVariant(artifact, {
      id: runId || 'artifact-current',
      runId,
      source: 'artifact-current',
      subagentEvents,
      fallbackContent: content,
      fallbackTitle: '当前方案',
    });

    const nextVariants = currentVariant ? [currentVariant, ...historyVariants] : historyVariants;
    const deduped = new Map<string, PlanVariant>();

    nextVariants.forEach((variant) => {
      const key = buildVariantIdentity(variant);
      if (!deduped.has(key)) deduped.set(key, variant);
    });

    return Array.from(deduped.values()).slice(0, 4);
  }, [artifact, content, entries, runId, subagentEvents]);

  return { loading, variants };
}
