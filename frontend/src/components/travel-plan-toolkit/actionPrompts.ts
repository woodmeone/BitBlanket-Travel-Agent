'use client';

import type { PlanVariant, SpotDecisionInfo } from '@/utils/travelPlan';
import type { QuickRefineAction } from './shared';

export function buildVariantContinuePrompt(variant: PlanVariant): string {
  return `请基于“${variant.title}”继续细化：
1) 输出每日详细时间轴（含时刻）
2) 补充交通衔接与预计时长
3) 补充每段预算与备选方案

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
