import { describe, expect, it } from 'vitest';
import type { PlanVariant, SpotDecisionInfo } from '@/utils/travelPlan';
import { buildFavoritesQuickRefineAction, buildVariantContinuePrompt } from '@/components/travel-plan-toolkit/actionPrompts';

describe('travel plan action prompts', () => {
  it('builds continue prompts for chosen variants', () => {
    const variant: PlanVariant = {
      id: 'variant-1',
      title: '轻松版',
      content: 'Day 1\n上午：武康路\n下午：新天地',
    };

    expect(buildVariantContinuePrompt(variant)).toContain('请基于“轻松版”继续细化');
    expect(buildVariantContinuePrompt(variant)).toContain('原方案：');
    expect(buildVariantContinuePrompt(variant)).toContain('上午：武康路');
  });

  it('builds favorites-based quick refine actions', () => {
    const spots: SpotDecisionInfo[] = [
      { name: '外滩', stayDuration: '1-2h', bestArrival: '10:00-12:00', audience: '大众友好', costHint: '中等' },
      { name: '豫园', stayDuration: '1-2h', bestArrival: '10:00-12:00', audience: '大众友好', costHint: '中等' },
    ];

    const action = buildFavoritesQuickRefineAction(spots);
    expect(action.key).toBe('favorites-build');
    expect(action.label).toBe('根据候选池重做');
    expect(action.prompt).toContain('外滩、豫园');
  });
});
