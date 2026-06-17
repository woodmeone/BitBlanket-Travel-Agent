// 【核心】操作提示词构建工具
// 应用场景：用户在工具包中执行操作（如快速微调、选择方案、用候选池重做）时，
//   需要构建发送给 AI 的提示词，告诉 AI 当前方案的上下文和用户的操作意图

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import type { TripPlanArtifact } from '@/types';
import type { PlanVariant, SpotDecisionInfo } from '@/utils/travelPlan';
import type { QuickRefineAction } from './shared';
import { buildArtifactEditingContext } from './shared/artifact';

// 构建带制品上下文的提示词
// 在用户的基础提示词前面，自动拼接当前方案的关键信息（目的地、预算等）
// 这样 AI 就知道当前方案的状态，可以更精准地执行调整
// 例如：基础提示词"增加预算" → 最终提示词"请基于当前结构化旅行方案继续编辑：\n- 目的地：北京\n任务要求：\n增加预算"
export function buildArtifactAwarePrompt(basePrompt: string, artifact?: TripPlanArtifact | null): string {
  const context = buildArtifactEditingContext(artifact);
  if (!context) return basePrompt;  // 无制品上下文时，直接返回基础提示词
  return `${context}

任务要求：
${basePrompt}`;
}

// 构建方案细化提示词——用户选中某个方案后，让 AI 基于该方案继续细化
// 提示词包含：当前方案上下文 + 细化要求（时间轴、交通、预算）+ 原方案内容
export function buildVariantContinuePrompt(variant: PlanVariant, artifact?: TripPlanArtifact | null): string {
  return `${buildArtifactAwarePrompt(`请基于"${variant.title}"继续细化：
1) 输出每日详细时间轴（含时刻）
2) 补充交通衔接与预计时长
3) 补充每段预算与备选方案
`, artifact)}

原方案：
${variant.content}`;
}

// 构建候选池重做方案的快速微调操作
// 应用场景：用户在收藏标签页点击"用候选池重做方案"时，
//   告诉 AI 优先基于收藏的景点重新生成方案
export function buildFavoritesQuickRefineAction(favoriteSpotList: SpotDecisionInfo[]): QuickRefineAction {
  return {
    key: 'favorites-build',
    label: '根据候选池重做',
    prompt: `请优先基于以下候选景点重新生成一版更精炼的旅行方案，并保留清晰时间轴：${favoriteSpotList
      .map((item) => item.name)
      .join('、')}`,
  };
}
