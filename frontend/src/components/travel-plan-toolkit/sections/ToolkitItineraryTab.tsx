// 【核心】每日行程标签页组件——旅行方案工具包的主界面
// 这是用户最常看到的标签页，包含：
//   1. 预算面板（顶部）：预算模式切换、统计摘要、快速微调、可信度
//   2. 每日行程卡片列表：每天一张卡片，展示时段时间线、冲突提醒、景点决策卡、小贴士

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import type { RoutePreviewResponse } from '@/types';
import type {
  BudgetProjection,
  ConfidenceSummary,
  DayPlanCard,
  ItineraryConflict,
  SpotDecisionInfo,
} from '@/utils/travelPlan';
import type { BudgetMode, QuickRefineAction } from '../shared';
import type { CardEntry } from './types';
import { ItineraryBudgetPanel } from './itinerary/ItineraryBudgetPanel';
import { ItineraryDayCard } from './itinerary/ItineraryDayCard';

// ToolkitItineraryTabProps 行程标签页接收的参数
interface ToolkitItineraryTabProps {
  messageId: string;                                              // 消息 ID
  exportRef: React.RefObject<HTMLDivElement | null>;              // 导出图片时引用的 DOM 节点
  budgetMode: BudgetMode;                                        // 当前预算模式
  budgetProjection: BudgetProjection;                             // 预算预测数据
  familyBudget: number;                                           // 家庭总价预算
  childFriendlyBudget: number;                                    // 亲子轻量版预算
  confidence: ConfidenceSummary;                                  // 预算可信度
  cardEntries: CardEntry[];                                       // 每日行程卡片入口数据列表
  conflictMap: Map<string, ItineraryConflict[]>;                  // 按天分组的冲突映射
  favoriteSpots: Record<string, SpotDecisionInfo>;                // 已收藏的景点
  expandedPeriods: Record<string, boolean>;                       // 各时段的展开/收起状态
  expandedTips: Record<string, boolean>;                          // 小贴士的展开/收起状态
  quickRefineActions: QuickRefineAction[];                        // 快速微调操作列表
  routeByDay: Record<string, RoutePreviewResponse | undefined>;   // 按天分组的路线预览数据
  routeLoadingDay: string | null;                                 // 正在加载路线的天标识
  onBudgetModeChange: (mode: BudgetMode) => void;                 // 切换预算模式的回调
  onExportImage: () => void;                                       // 导出图片的回调
  onFetchRoute: (dayKey: string, day: DayPlanCard) => void;       // 获取路线的回调
  onOneClickFix: (dayKey: string, dayIndex: number, day: DayPlanCard) => void;  // 一键修复的回调
  onQuickRefine: (action: QuickRefineAction) => void;             // 快速微调的回调
  onReorderByDistance: (dayKey: string, dayIndex: number, day: DayPlanCard) => void;  // 按距离重排的回调
  onShare: () => void;                                             // 分享的回调
  onToggleFavoriteSpot: (spot: SpotDecisionInfo) => void;         // 切换景点收藏的回调
  onTogglePeriod: (periodKey: string) => void;                    // 切换时段展开的回调
  onToggleTips: (dayKey: string) => void;                         // 切换小贴士展开的回调
}

export const ToolkitItineraryTab: React.FC<ToolkitItineraryTabProps> = ({
  messageId: _messageId,
  exportRef,
  budgetMode,
  budgetProjection,
  familyBudget,
  childFriendlyBudget,
  confidence,
  cardEntries,
  conflictMap,
  favoriteSpots,
  expandedPeriods,
  expandedTips,
  quickRefineActions,
  routeByDay,
  routeLoadingDay,
  onBudgetModeChange,
  onExportImage,
  onFetchRoute,
  onOneClickFix,
  onQuickRefine,
  onReorderByDistance,
  onShare,
  onToggleFavoriteSpot,
  onTogglePeriod,
  onToggleTips,
}) => (
  <div ref={exportRef} style={{ display: 'grid', gap: 12 }}>
    {/* 预算面板 */}
    <ItineraryBudgetPanel
      budgetMode={budgetMode}
      budgetProjection={budgetProjection}
      childFriendlyBudget={childFriendlyBudget}
      confidence={confidence}
      familyBudget={familyBudget}
      onBudgetModeChange={onBudgetModeChange}
      onExportImage={onExportImage}
      onQuickRefine={onQuickRefine}
      onShare={onShare}
      quickRefineActions={quickRefineActions}
    />

    {/* 每日行程卡片列表 */}
    {cardEntries.map(({ day, dayIndex, dayKey }) => (
      <ItineraryDayCard
        key={dayKey}
        conflicts={conflictMap.get(dayKey) || []}
        day={day}
        dayIndex={dayIndex}
        dayKey={dayKey}
        expandedPeriods={expandedPeriods}
        expandedTips={expandedTips}
        favoriteSpots={favoriteSpots}
        onFetchRoute={onFetchRoute}
        onOneClickFix={onOneClickFix}
        onReorderByDistance={onReorderByDistance}
        onToggleFavoriteSpot={onToggleFavoriteSpot}
        onTogglePeriod={onTogglePeriod}
        onToggleTips={onToggleTips}
        route={routeByDay[dayKey]}
        routeLoadingDay={routeLoadingDay}
      />
    ))}
  </div>
);
