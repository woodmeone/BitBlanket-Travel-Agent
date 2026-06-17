// 【核心】每日行程卡片组件——展示一天的完整行程信息
// 这是行程标签页中最核心的组件，每张卡片代表一天的行程安排
// 包含：时段时间线、冲突提醒、操作按钮、景点决策卡、小贴士等

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Button, Card, Tag } from 'antd';
import { CompassOutlined, EnvironmentOutlined, ThunderboltOutlined } from '@ant-design/icons';
import type { RoutePreviewResponse } from '@/types';
import type { DayPlanCard, ItineraryConflict, SpotDecisionInfo } from '@/utils/travelPlan';
import { buildSpotDecisionInfos } from '@/utils/travelPlan';
import { compactTips, formatDistance, PeriodTimeline } from '../../shared';
import { ItineraryConflictSection } from './day-card/ItineraryConflictSection';
import { ItinerarySpotDecisionGrid } from './day-card/ItinerarySpotDecisionGrid';
import { ItineraryTipsBlock } from './day-card/ItineraryTipsBlock';

// ItineraryDayCardProps 每日行程卡片接收的参数
interface ItineraryDayCardProps {
  day: DayPlanCard;                                        // 当天的行程数据
  dayIndex: number;                                        // 天数索引（从0开始）
  dayKey: string;                                          // 当天的唯一标识键
  expandedPeriods: Record<string, boolean>;                // 各时段的展开/收起状态
  expandedTips: Record<string, boolean>;                   // 小贴士的展开/收起状态
  favoriteSpots: Record<string, SpotDecisionInfo>;         // 已收藏的景点
  onFetchRoute: (dayKey: string, day: DayPlanCard) => void;         // 获取真实路线的回调
  onOneClickFix: (dayKey: string, dayIndex: number, day: DayPlanCard) => void;  // 一键修复冲突的回调
  onReorderByDistance: (dayKey: string, dayIndex: number, day: DayPlanCard) => void;  // 按距离重排景点的回调
  onToggleFavoriteSpot: (spot: SpotDecisionInfo) => void;  // 切换景点收藏状态的回调
  onTogglePeriod: (periodKey: string) => void;             // 切换时段展开/收起的回调
  onToggleTips: (dayKey: string) => void;                  // 切换小贴士展开/收起的回调
  conflicts: ItineraryConflict[];                          // 当天的冲突列表
  route?: RoutePreviewResponse;                            // 路线预览数据（包含地图和距离）
  routeLoadingDay: string | null;                          // 正在加载路线的天标识
}

export const ItineraryDayCard: React.FC<ItineraryDayCardProps> = ({
  day,
  dayIndex,
  dayKey,
  expandedPeriods,
  expandedTips,
  favoriteSpots,
  onFetchRoute,
  onOneClickFix,
  onReorderByDistance,
  onToggleFavoriteSpot,
  onTogglePeriod,
  onToggleTips,
  conflicts,
  route,
  routeLoadingDay,
}) => {
  const decisionInfos = buildSpotDecisionInfos(day.spots);  // 构建景点决策信息
  const compactedTips = compactTips(day.tips);              // 去重和清理小贴士
  const tipsExpanded = expandedTips[dayKey] ?? false;       // 当前天的小贴士是否展开
  const visibleTips = tipsExpanded ? compactedTips : compactedTips.slice(0, 2);  // 收起时只显示2条
  const hiddenTipCount = compactedTips.length - visibleTips.length;  // 隐藏的小贴士数量

  return (
    <Card size="small" title={day.dayLabel}>
      <div style={{ display: 'grid', gap: 10 }}>
        {/* 冲突提醒区域 */}
        <ItineraryConflictSection conflicts={conflicts} dayKey={dayKey} />

        {/* 三个时段的时间线：上午、下午、晚上 */}
        <div style={{ display: 'grid', gap: 8 }}>
          <PeriodTimeline period="morning" rawText={day.morning} dayKey={dayKey} expandedPeriods={expandedPeriods} onToggle={onTogglePeriod} />
          <PeriodTimeline
            period="afternoon"
            rawText={day.afternoon}
            dayKey={dayKey}
            expandedPeriods={expandedPeriods}
            onToggle={onTogglePeriod}
          />
          <PeriodTimeline period="evening" rawText={day.evening} dayKey={dayKey} expandedPeriods={expandedPeriods} onToggle={onTogglePeriod} />
        </div>

        {/* 当日统计标签：预算、景点数、路线距离 */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Tag color="blue">当日预算：¥{day.baseBudget}</Tag>
          <Tag color="processing">景点数：{day.spots.length}</Tag>
          <Tag color="purple">路线距离：{formatDistance(route?.distance_m)}</Tag>
        </div>

        {/* 操作按钮区域 */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button size="small" icon={<EnvironmentOutlined />} loading={routeLoadingDay === dayKey} onClick={() => onFetchRoute(dayKey, day)}>
            真实路线
          </Button>
          <Button size="small" icon={<CompassOutlined />} onClick={() => onReorderByDistance(dayKey, dayIndex, day)}>
            按距离重排
          </Button>
          <Button size="small" icon={<ThunderboltOutlined />} onClick={() => onOneClickFix(dayKey, dayIndex, day)}>
            一键修复冲突
          </Button>
        </div>

        {/* 路线地图图片（如果有的话） */}
        {route?.static_map_url && (
          <img src={route.static_map_url} alt={`${day.dayLabel} route`} style={{ width: '100%', borderRadius: 10, border: '1px solid #e2e8f0' }} />
        )}

        {/* 景点决策卡网格 */}
        <ItinerarySpotDecisionGrid
          dayKey={dayKey}
          decisionInfos={decisionInfos}
          favoriteSpots={favoriteSpots}
          onToggleFavoriteSpot={onToggleFavoriteSpot}
        />

        {/* 小贴士区域 */}
        <ItineraryTipsBlock
          dayKey={dayKey}
          hiddenTipCount={hiddenTipCount}
          tipsExpanded={tipsExpanded}
          visibleTips={visibleTips}
          onToggleTips={onToggleTips}
        />
      </div>
    </Card>
  );
};
