// 【核心】制品历史对比 Hook——从服务端获取历史方案，构建对比变体列表
// "Hook"是 React 的自定义钩子函数，以 use 开头，用于封装可复用的状态逻辑
// 应用场景：在"多方案对比"标签页中，需要加载当前会话的历史方案，
//   与当前方案一起组成对比列表

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import { useEffect, useMemo, useState } from 'react';
import { artifactClient } from '@/services/api';
import type { ArtifactHistoryEntry, SubagentEvent, TripPlanArtifact } from '@/types';
import { logger } from '@/utils/logger';
import type { PlanVariant } from '@/utils/travelPlan';
import { buildArtifactCompareVariant } from './shared';

// Hook 的配置选项
interface UseArtifactHistoryCompareOptions {
  artifact?: TripPlanArtifact | null;    // 当前旅行方案制品
  content: string;                        // 备用文本内容
  runId?: string | null;                  // 当前运行 ID
  sessionId?: string | null;              // 会话 ID，用于查询历史方案
  subagentEvents?: SubagentEvent[];       // 子 Agent 事件列表
}

// Hook 的返回结果
interface UseArtifactHistoryCompareResult {
  loading: boolean;           // 是否正在加载历史方案
  variants: PlanVariant[];    // 对比变体列表（当前方案 + 历史方案）
}

// 构建变体的唯一标识（用于去重）
// 优先级：runId > planId > messageTimestamp > id
function buildVariantIdentity(variant: PlanVariant): string {
  return variant.runId || variant.artifact?.itinerary.planId || variant.messageTimestamp || variant.id;
}

// 将历史条目转换为对比变体
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

// 【核心】制品历史对比 Hook
// 工作流程：
//   1. 根据 sessionId 从服务端加载历史方案（最多4条）
//   2. 将当前方案和历史方案都转换为对比变体
//   3. 去重后返回变体列表
export function useArtifactHistoryCompare({
  artifact = null,
  content,
  runId = null,
  sessionId = null,
  subagentEvents = [],
}: UseArtifactHistoryCompareOptions): UseArtifactHistoryCompareResult {
  const [entries, setEntries] = useState<ArtifactHistoryEntry[]>([]);  // 历史条目列表
  const [loading, setLoading] = useState(false);                       // 加载状态

  // useEffect 是 React 的副作用钩子，当 sessionId 变化时重新加载历史方案
  useEffect(() => {
    let cancelled = false;  // 取消标志，防止组件卸载后仍更新状态

    if (!sessionId) {
      setEntries([]);
      setLoading(false);
      return () => {
        cancelled = true;
      };
    }

    setLoading(true);
    // 调用 API 获取历史方案（最多4条）
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
      cancelled = true;  // 组件卸载时设置取消标志
    };
  }, [sessionId]);

  // useMemo 是 React 的缓存钩子，只有依赖项变化时才重新计算
  // 这里将历史条目和当前制品合并为对比变体列表
  const variants = useMemo(() => {
    // 将历史条目转换为变体
    const historyVariants = entries
      .map((entry) => buildHistoryVariant(entry, content))
      .filter((variant): variant is PlanVariant => Boolean(variant));

    // 构建当前方案的变体
    const currentVariant = buildArtifactCompareVariant(artifact, {
      id: runId || 'artifact-current',
      runId,
      source: 'artifact-current',
      subagentEvents,
      fallbackContent: content,
      fallbackTitle: '当前方案',
    });

    // 合并当前方案和历史方案，当前方案排在最前面
    const nextVariants = currentVariant ? [currentVariant, ...historyVariants] : historyVariants;
    // 去重：相同标识的变体只保留第一个
    const deduped = new Map<string, PlanVariant>();

    nextVariants.forEach((variant) => {
      const key = buildVariantIdentity(variant);
      if (!deduped.has(key)) deduped.set(key, variant);
    });

    return Array.from(deduped.values()).slice(0, 4);  // 最多返回4个变体
  }, [artifact, content, entries, runId, subagentEvents]);

  return { loading, variants };
}
