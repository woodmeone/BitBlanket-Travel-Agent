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

interface ItineraryDayCardProps {
  day: DayPlanCard;
  dayIndex: number;
  dayKey: string;
  expandedPeriods: Record<string, boolean>;
  expandedTips: Record<string, boolean>;
  favoriteSpots: Record<string, SpotDecisionInfo>;
  onFetchRoute: (dayKey: string, day: DayPlanCard) => void;
  onOneClickFix: (dayKey: string, dayIndex: number, day: DayPlanCard) => void;
  onReorderByDistance: (dayKey: string, dayIndex: number, day: DayPlanCard) => void;
  onToggleFavoriteSpot: (spot: SpotDecisionInfo) => void;
  onTogglePeriod: (periodKey: string) => void;
  onToggleTips: (dayKey: string) => void;
  conflicts: ItineraryConflict[];
  route?: RoutePreviewResponse;
  routeLoadingDay: string | null;
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
  const decisionInfos = buildSpotDecisionInfos(day.spots);
  const compactedTips = compactTips(day.tips);
  const tipsExpanded = expandedTips[dayKey] ?? false;
  const visibleTips = tipsExpanded ? compactedTips : compactedTips.slice(0, 2);
  const hiddenTipCount = compactedTips.length - visibleTips.length;

  return (
    <Card size="small" title={day.dayLabel}>
      <div style={{ display: 'grid', gap: 10 }}>
        <ItineraryConflictSection conflicts={conflicts} dayKey={dayKey} />

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

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Tag color="blue">当日预算：¥{day.baseBudget}</Tag>
          <Tag color="processing">景点数：{day.spots.length}</Tag>
          <Tag color="purple">路线距离：{formatDistance(route?.distance_m)}</Tag>
        </div>

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

        {route?.static_map_url && (
          <img src={route.static_map_url} alt={`${day.dayLabel} route`} style={{ width: '100%', borderRadius: 10, border: '1px solid #e2e8f0' }} />
        )}

        <ItinerarySpotDecisionGrid
          dayKey={dayKey}
          decisionInfos={decisionInfos}
          favoriteSpots={favoriteSpots}
          onToggleFavoriteSpot={onToggleFavoriteSpot}
        />

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
