'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { App, Card, Tabs } from 'antd';
import {
  CheckSquareOutlined,
  CompassOutlined,
  HeartOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  FundOutlined,
} from '@ant-design/icons';
import html2canvas from 'html2canvas';
import type { Message, RoutePreviewResponse, SubagentEvent, TripPlanArtifact } from '@/types';
import { mapClient, shareClient } from '@/services/api';
import { hasArtifactData } from '@/utils/agentArtifacts';
import {
  applyConflictFixes,
  buildChecklist,
  buildConfidenceSummary,
  buildPracticalInfoCards,
  buildReminders,
  buildRoutePoints,
  detectDayConflicts,
  getBudgetProjection,
  parseDayPlanCards,
  parsePlanVariants,
  reorderByDistance,
} from '@/utils/travelPlan';
import type { DayPlanCard, PlanVariant, SpotDecisionInfo } from '@/utils/travelPlan';
import type { QuickRefineAction } from './travel-plan-toolkit/shared';
import {
  ToolkitChecklistTab,
  ToolkitCompareTab,
  ToolkitConflictsTab,
  ToolkitFavoritesTab,
  ToolkitItineraryTab,
  ToolkitOverviewPanel,
  ToolkitPracticalTab,
  ToolkitRemindersTab,
} from './travel-plan-toolkit/sections';
import { looksLikeItineraryContent, modeToSliderValue, type BudgetMode } from './travel-plan-toolkit/shared';

interface TravelPlanToolkitProps {
  messageId: string;
  content: string;
  diagnostics?: Message['diagnostics'];
  artifact?: TripPlanArtifact | null;
  subagentEvents?: SubagentEvent[];
  onContinuePrompt?: (prompt: string) => void;
}

const QUICK_REFINE_ACTIONS: QuickRefineAction[] = [
  { key: 'cheaper', label: '换成更省钱', prompt: '请基于当前方案改成更省钱版本，优先保留核心体验，减少高价项目，并重算预算。' },
  { key: 'easy', label: '少走路版', prompt: '请基于当前方案改成少走路版本，压缩跨区移动，增加打车衔接和休息点。' },
  { key: 'rainy', label: '下雨天重排', prompt: '请把当前方案改成下雨天可执行版本，优先室内点位，并替换不适合雨天的安排。' },
  { key: 'family', label: '加亲子备选', prompt: '请在当前方案基础上增加亲子友好备选点和午休/室内 fallback。' },
];

type ToolkitTabItem = NonNullable<React.ComponentProps<typeof Tabs>['items']>[number];

const TravelPlanToolkit: React.FC<TravelPlanToolkitProps> = ({
  messageId,
  content,
  diagnostics,
  artifact = null,
  subagentEvents = [],
  onContinuePrompt,
}) => {
  const { message } = App.useApp();
  const exportRef = useRef<HTMLDivElement | null>(null);

  const baseCards = useMemo(() => parseDayPlanCards(content), [content]);
  const variants = useMemo(() => parsePlanVariants(content), [content]);
  const checklist = useMemo(() => buildChecklist(content), [content]);
  const reminders = useMemo(() => buildReminders(), []);
  const confidence = useMemo(() => buildConfidenceSummary(diagnostics), [diagnostics]);
  const practicalInfo = useMemo(() => buildPracticalInfoCards(content), [content]);

  const [cards, setCards] = useState<DayPlanCard[]>(baseCards);
  const [budgetMode, setBudgetMode] = useState<BudgetMode>('balanced');
  const [completedChecklist, setCompletedChecklist] = useState<Record<string, boolean>>({});
  const [expandedPeriods, setExpandedPeriods] = useState<Record<string, boolean>>({});
  const [expandedTips, setExpandedTips] = useState<Record<string, boolean>>({});
  const [favoriteSpots, setFavoriteSpots] = useState<Record<string, SpotDecisionInfo>>({});
  const [routeByDay, setRouteByDay] = useState<Record<string, RoutePreviewResponse | undefined>>({});
  const [routeLoadingDay, setRouteLoadingDay] = useState<string | null>(null);

  const artifactAvailable = hasArtifactData(artifact);
  const artifactIntent = artifact?.intent.name || diagnostics?.artifact?.intent.name || '';
  const artifactPlanId = artifact?.itinerary.planId || diagnostics?.artifact?.itinerary.planId || diagnostics?.planId || null;
  const artifactValidationStatus = artifact?.itinerary.validationStatus || '';
  const artifactVerification = artifact?.verification.passed ?? diagnostics?.verificationPassed ?? null;
  const artifactSummary = artifact?.research.summary || artifact?.verification.summary || '';
  const artifactTools = artifact?.toolsUsed || diagnostics?.toolsUsed || [];
  const artifactEvidenceCount = artifact?.research.evidence.length || 0;
  const artifactStepCount = artifact?.itinerary.steps.length || 0;

  useEffect(() => {
    setCards(baseCards);
    setExpandedPeriods({});
    setExpandedTips({});
    setRouteByDay({});
  }, [baseCards]);

  const cardEntries = useMemo(
    () =>
      cards.map((day, dayIndex) => ({
        day,
        dayIndex,
        dayKey: `day-${dayIndex + 1}`,
      })),
    [cards]
  );

  const totalBaseBudget = useMemo(() => cards.reduce((sum, day) => sum + day.baseBudget, 0), [cards]);
  const budgetProjection = useMemo(() => {
    const dayCount = Math.max(cards.length, 1);
    return getBudgetProjection(totalBaseBudget / dayCount, dayCount, modeToSliderValue(budgetMode));
  }, [budgetMode, cards.length, totalBaseBudget]);

  const familyBudget = Math.round(budgetProjection.totalBudget * 2.4);
  const childFriendlyBudget = Math.round(budgetProjection.totalBudget * 1.7);
  const favoriteSpotList = useMemo(() => Object.values(favoriteSpots), [favoriteSpots]);
  const hasItineraryContent = useMemo(() => looksLikeItineraryContent(content, baseCards), [baseCards, content]);

  const conflictMap = useMemo(() => {
    const map = new Map<string, ReturnType<typeof detectDayConflicts>>();
    cardEntries.forEach(({ day, dayKey }) => {
      const distanceM = routeByDay[dayKey]?.distance_m;
      map.set(dayKey, detectDayConflicts(day, distanceM));
    });
    return map;
  }, [cardEntries, routeByDay]);

  const totalConflicts = useMemo(
    () => Array.from(conflictMap.values()).reduce((sum, list) => sum + list.length, 0),
    [conflictMap]
  );

  if (cards.length === 0 && !artifactAvailable) return null;

  const handleTogglePeriod = (periodKey: string) => {
    setExpandedPeriods((prev) => ({ ...prev, [periodKey]: !prev[periodKey] }));
  };

  const handleToggleTips = (dayKey: string) => {
    setExpandedTips((prev) => ({ ...prev, [dayKey]: !prev[dayKey] }));
  };

  const handleFetchRoute = async (dayKey: string, day: DayPlanCard) => {
    if (day.spots.length < 2) {
      message.warning('当天景点少于 2 个，无法生成路线。');
      return;
    }

    try {
      setRouteLoadingDay(dayKey);
      const result = await mapClient.getRoutePreview({ spots: day.spots.slice(0, 12), provider: 'amap' });
      setRouteByDay((prev) => ({ ...prev, [dayKey]: result }));
      message.success(`已获取 ${day.dayLabel} 真实路线`);
    } catch (error) {
      message.error(`路线获取失败：${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setRouteLoadingDay(null);
    }
  };

  const handleReorderByDistance = (dayKey: string, dayIndex: number, day: DayPlanCard) => {
    const route = routeByDay[dayKey];
    const orderedSpots = route?.points?.length
      ? route.points.map((point) => point.name)
      : reorderByDistance(buildRoutePoints(day.spots)).map((point) => point.name);

    setCards((prev) => prev.map((item, index) => (index === dayIndex ? { ...item, spots: orderedSpots } : item)));
    message.success(`${day.dayLabel} 已按距离重排`);
  };

  const handleOneClickFix = (dayKey: string, dayIndex: number, day: DayPlanCard) => {
    const conflicts = conflictMap.get(dayKey) || [];
    if (conflicts.length === 0) {
      message.info('当前无冲突，无需修复。');
      return;
    }

    const fixed = applyConflictFixes(day, conflicts);
    setCards((prev) => prev.map((item, index) => (index === dayIndex ? fixed : item)));
    message.success(`${day.dayLabel} 已应用修复建议`);
  };

  const handleExportImage = async () => {
    if (!exportRef.current) return;
    try {
      const canvas = await html2canvas(exportRef.current, {
        scale: 2,
        backgroundColor: '#ffffff',
        useCORS: true,
      });
      const dataUrl = canvas.toDataURL('image/png');
      const link = document.createElement('a');
      link.href = dataUrl;
      link.download = `travel-plan-${new Date().toISOString().slice(0, 10)}.png`;
      link.click();
      message.success('已导出长图');
    } catch (error) {
      message.error(`导出失败：${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  const handleShare = async () => {
    try {
      const result = await shareClient.createShareLink({
        title: '旅行方案',
        content,
      });
      await navigator.clipboard.writeText(result.share_url);
      message.success('分享短链已复制到剪贴板');
    } catch (error) {
      message.error(`分享失败：${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  const runQuickRefine = (action: QuickRefineAction) => {
    if (!onContinuePrompt) {
      message.info('当前会话不支持继续优化。');
      return;
    }
    onContinuePrompt(action.prompt);
    message.success(`已填入“${action.label}”优化指令`);
  };

  const handleToggleFavoriteSpot = (spot: SpotDecisionInfo) => {
    setFavoriteSpots((prev) => {
      if (prev[spot.name]) {
        const next = { ...prev };
        delete next[spot.name];
        return next;
      }
      return { ...prev, [spot.name]: spot };
    });
  };

  const handleChooseVariant = (variant: PlanVariant) => {
    if (!onContinuePrompt) {
      message.info('当前会话不支持一键继续细化。');
      return;
    }

    const prompt = `请基于“${variant.title}”继续细化：
1) 输出每日详细时间轴（含时刻）
2) 补充交通衔接与预计时长
3) 补充每段预算与备选方案

原方案：
${variant.content}`;

    onContinuePrompt(prompt);
    message.success(`已选择 ${variant.title}，可继续细化`);
  };

  const tabItems: ToolkitTabItem[] = [];

  if (hasItineraryContent) {
    tabItems.push({
      key: 'itinerary',
      label: '每日行程',
      icon: <CompassOutlined />,
      children: (
        <ToolkitItineraryTab
          messageId={messageId}
          exportRef={exportRef}
          budgetMode={budgetMode}
          budgetProjection={budgetProjection}
          familyBudget={familyBudget}
          childFriendlyBudget={childFriendlyBudget}
          confidence={confidence}
          cardEntries={cardEntries}
          conflictMap={conflictMap}
          favoriteSpots={favoriteSpots}
          expandedPeriods={expandedPeriods}
          expandedTips={expandedTips}
          quickRefineActions={QUICK_REFINE_ACTIONS}
          routeByDay={routeByDay}
          routeLoadingDay={routeLoadingDay}
          onBudgetModeChange={setBudgetMode}
          onExportImage={handleExportImage}
          onFetchRoute={handleFetchRoute}
          onOneClickFix={handleOneClickFix}
          onQuickRefine={runQuickRefine}
          onReorderByDistance={handleReorderByDistance}
          onShare={handleShare}
          onToggleFavoriteSpot={handleToggleFavoriteSpot}
          onTogglePeriod={handleTogglePeriod}
          onToggleTips={handleToggleTips}
        />
      ),
    });
  }

  tabItems.push({
      key: 'compare',
      label: '多方案对比',
      icon: <FundOutlined />,
      children: <ToolkitCompareTab variants={variants} onChooseVariant={handleChooseVariant} />,
    });

  if (hasItineraryContent) {
    tabItems.push({
      key: 'conflicts',
      label: '冲突检测',
      icon: <ReloadOutlined />,
      children: (
        <ToolkitConflictsTab
          cardEntries={cardEntries}
          conflictMap={conflictMap}
          messageId={messageId}
          totalConflicts={totalConflicts}
          onOneClickFix={handleOneClickFix}
        />
      ),
    });

    tabItems.push({
      key: 'favorites',
      label: '候选池',
      icon: <HeartOutlined />,
      children: (
        <ToolkitFavoritesTab
          favoriteSpotList={favoriteSpotList}
          onContinuePrompt={onContinuePrompt}
          onQuickRefine={runQuickRefine}
          onToggleFavoriteSpot={handleToggleFavoriteSpot}
        />
      ),
    });
  }

  tabItems.push(
    {
      key: 'practical',
      label: '实用信息',
      icon: <InfoCircleOutlined />,
      children: <ToolkitPracticalTab messageId={messageId} practicalInfo={practicalInfo} />,
    },
    {
      key: 'checklist',
      label: '执行清单',
      icon: <CheckSquareOutlined />,
      children: (
        <ToolkitChecklistTab
          checklist={checklist}
          completedChecklist={completedChecklist}
          messageId={messageId}
          onToggleChecklist={(itemId, checked) =>
            setCompletedChecklist((prev) => ({ ...prev, [itemId]: checked }))
          }
        />
      ),
    },
    {
      key: 'reminders',
      label: '出发提醒',
      icon: <ReloadOutlined />,
      children: <ToolkitRemindersTab messageId={messageId} reminders={reminders} />,
    },
  );

  return (
    <Card
      size="small"
      style={{ marginTop: 12, borderRadius: 12, border: '1px solid #e2e8f0', background: '#f8fafc' }}
      styles={{ body: { padding: 12 } }}
    >
      {artifactAvailable && (
        <ToolkitOverviewPanel
          artifactIntent={artifactIntent}
          artifactPlanId={artifactPlanId}
          artifactValidationStatus={artifactValidationStatus}
          artifactVerification={artifactVerification}
          artifactTools={artifactTools}
          artifactEvidenceCount={artifactEvidenceCount}
          artifactStepCount={artifactStepCount}
          artifactSummary={artifactSummary}
          subagentEvents={subagentEvents}
        />
      )}
      <Tabs size="small" items={tabItems} />
    </Card>
  );
};

export default TravelPlanToolkit;
