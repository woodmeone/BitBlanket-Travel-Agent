'use client';

import type { TripPlanArtifact } from '@/types';
import type { PlanVariant, SpotDecisionInfo } from '@/utils/travelPlan';
import type { QuickRefineAction } from './shared';
import { buildArtifactEditingContext } from './shared/artifact';

export function buildArtifactAwarePrompt(basePrompt: string, artifact?: TripPlanArtifact | null): string {
  const context = buildArtifactEditingContext(artifact);
  if (!context) return basePrompt;
  return `${context}

任务要求：
${basePrompt}`;
}

export function buildVariantContinuePrompt(variant: PlanVariant, artifact?: TripPlanArtifact | null): string {
  return `${buildArtifactAwarePrompt(`请基于“${variant.title}”继续细化：
1) 输出每日详细时间轴（含时刻）
2) 补充交通衔接与预计时长
3) 补充每段预算与备选方案
`, artifact)}

原方案：
${variant.content}`;
}

export function buildFavoritesQuickRefineAction(favoriteSpotList: SpotDecisionInfo[]): QuickRefineAction {
  return {
    key: 'favorites-build',
    label: '根据候选池重做',
    prompt: `请优先基于以下候选景点重新生成一版更精炼的旅行方案，并保留清晰时间轴：${favoriteSpotList
      .map((item) => item.name)
      .join('、')}`,
  };
}
