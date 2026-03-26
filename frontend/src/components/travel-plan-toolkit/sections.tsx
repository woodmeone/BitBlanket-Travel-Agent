'use client';

import React from 'react';
import {
  Button,
  Card,
  Checkbox,
  Divider,
  Progress,
  Slider,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  CompassOutlined,
  EnvironmentOutlined,
  FileImageOutlined,
  FundOutlined,
  HeartFilled,
  HeartOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  ShareAltOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { RoutePreviewResponse, SubagentEvent } from '@/types';
import { buildSubagentEventKey } from '@/utils/subagentEvents';
import type {
  BudgetProjection,
  ChecklistItem,
  ConfidenceSummary,
  DayPlanCard,
  ItineraryConflict,
  PlanVariant,
  PracticalInfoCard,
  ReminderItem,
  SpotDecisionInfo,
} from '@/utils/travelPlan';
import { buildSpotDecisionInfos } from '@/utils/travelPlan';
import {
  compactTips,
  formatDistance,
  modeToSliderValue,
  PeriodTimeline,
  practicalToneStyle,
  QuickRefineAction,
  riskColor,
  sliderToMode,
  subagentLabel,
  type BudgetMode,
  type CompareRow,
} from './shared';

interface CardEntry {
  day: DayPlanCard;
  dayIndex: number;
  dayKey: string;
}

interface ToolkitOverviewPanelProps {
  artifactIntent: string;
  artifactPlanId: string | null;
  artifactValidationStatus: string;
  artifactVerification: boolean | null;
  artifactTools: string[];
  artifactEvidenceCount: number;
  artifactStepCount: number;
  artifactSummary: string;
  subagentEvents: SubagentEvent[];
}

export const ToolkitOverviewPanel: React.FC<ToolkitOverviewPanelProps> = ({
  artifactIntent,
  artifactPlanId,
  artifactValidationStatus,
  artifactVerification,
  artifactTools,
  artifactEvidenceCount,
  artifactStepCount,
  artifactSummary,
  subagentEvents,
}) => (
  <Card size="small" style={{ marginBottom: 12 }}>
    <div style={{ display: 'grid', gap: 10 }}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {artifactIntent && <Tag color="blue">Intent: {artifactIntent}</Tag>}
        {artifactPlanId && <Tag color="purple">Plan #{artifactPlanId}</Tag>}
        {artifactValidationStatus && <Tag color="cyan">Validation: {artifactValidationStatus}</Tag>}
        <Tag color={artifactVerification === false ? 'red' : artifactVerification ? 'green' : 'default'}>
          校验: {artifactVerification === false ? '未通过' : artifactVerification ? '通过' : '待定'}
        </Tag>
        <Tag color="gold">Tools: {artifactTools.length}</Tag>
        {artifactEvidenceCount > 0 && <Tag color="geekblue">Evidence: {artifactEvidenceCount}</Tag>}
        {artifactStepCount > 0 && <Tag color="processing">Structured Steps: {artifactStepCount}</Tag>}
      </div>

      {artifactSummary && <div style={{ fontSize: 13, color: '#334155', lineHeight: 1.7 }}>{artifactSummary}</div>}

      {subagentEvents.length > 0 && (
        <div style={{ display: 'grid', gap: 6 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#155e75' }}>子 Agent 轨迹</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {subagentEvents.map((event, index) => (
              <Tag key={buildSubagentEventKey(event, index)} color={event.status ? 'green' : 'blue'}>
                {subagentLabel(event.subagent)}
                {event.status ? `:${event.status}` : ''}
              </Tag>
            ))}
          </div>
        </div>
      )}
    </div>
  </Card>
);

interface ToolkitItineraryTabProps {
  messageId: string;
  exportRef: React.RefObject<HTMLDivElement | null>;
  budgetMode: BudgetMode;
  budgetProjection: BudgetProjection;
  familyBudget: number;
  childFriendlyBudget: number;
  confidence: ConfidenceSummary;
  cardEntries: CardEntry[];
  conflictMap: Map<string, ItineraryConflict[]>;
  favoriteSpots: Record<string, SpotDecisionInfo>;
  expandedPeriods: Record<string, boolean>;
  expandedTips: Record<string, boolean>;
  quickRefineActions: QuickRefineAction[];
  routeByDay: Record<string, RoutePreviewResponse | undefined>;
  routeLoadingDay: string | null;
  onBudgetModeChange: (mode: BudgetMode) => void;
  onExportImage: () => void;
  onFetchRoute: (dayKey: string, day: DayPlanCard) => void;
  onOneClickFix: (dayKey: string, dayIndex: number, day: DayPlanCard) => void;
  onQuickRefine: (action: QuickRefineAction) => void;
  onReorderByDistance: (dayKey: string, dayIndex: number, day: DayPlanCard) => void;
  onShare: () => void;
  onToggleFavoriteSpot: (spot: SpotDecisionInfo) => void;
  onTogglePeriod: (periodKey: string) => void;
  onToggleTips: (dayKey: string) => void;
}

export const ToolkitItineraryTab: React.FC<ToolkitItineraryTabProps> = ({
  messageId,
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
    <Card size="small">
      <div style={{ display: 'grid', gap: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <Space>
            <FundOutlined style={{ color: '#0f766e' }} />
            <span style={{ fontSize: 13, color: '#334155' }}>预算档位</span>
            <Tag color={budgetMode === 'saving' ? 'blue' : budgetMode === 'balanced' ? 'gold' : 'green'}>
              {budgetMode === 'saving' ? '省钱' : budgetMode === 'balanced' ? '均衡' : '舒适'}
            </Tag>
          </Space>
          <Space>
            <Tooltip title="导出图片长图">
              <Button size="small" icon={<FileImageOutlined />} onClick={onExportImage} />
            </Tooltip>
            <Tooltip title="生成可分享短链">
              <Button size="small" icon={<ShareAltOutlined />} onClick={onShare} />
            </Tooltip>
          </Space>
        </div>

        <Slider
          min={0}
          max={100}
          value={modeToSliderValue(budgetMode)}
          marks={{ 10: '省钱', 50: '均衡', 90: '舒适' }}
          onChange={(value) => onBudgetModeChange(sliderToMode(Array.isArray(value) ? value[0] : value))}
        />

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Tag color="blue">总预算：¥{budgetProjection.totalBudget}</Tag>
          <Tag color="cyan">住宿：{Math.round(budgetProjection.hotelShare * 100)}%</Tag>
          <Tag color="orange">餐饮：{Math.round(budgetProjection.foodShare * 100)}%</Tag>
          <Tag color="purple">交通：{Math.round(budgetProjection.trafficShare * 100)}%</Tag>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
            gap: 10,
          }}
        >
          <Card size="small" styles={{ body: { padding: 10 } }}>
            <Statistic title="人均预估" value={budgetProjection.totalBudget} prefix="¥" styles={{ content: { fontSize: 18 } }} />
          </Card>
          <Card size="small" styles={{ body: { padding: 10 } }}>
            <Statistic title="家庭总价" value={familyBudget} prefix="¥" styles={{ content: { fontSize: 18 } }} />
          </Card>
          <Card size="small" styles={{ body: { padding: 10 } }}>
            <Statistic title="亲子轻量版" value={childFriendlyBudget} prefix="¥" styles={{ content: { fontSize: 18 } }} />
          </Card>
          <Card size="small" styles={{ body: { padding: 10 } }}>
            <Statistic title="日均预算" value={budgetProjection.perDayBudget} prefix="¥" styles={{ content: { fontSize: 18 } }} />
          </Card>
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {quickRefineActions.map((action) => (
            <Button key={action.key} size="small" onClick={() => onQuickRefine(action)}>
              {action.label}
            </Button>
          ))}
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 13, color: '#334155' }}>结果可信度</span>
            <Tag color={confidence.level === 'high' ? 'green' : confidence.level === 'medium' ? 'gold' : 'red'}>
              {confidence.level}
            </Tag>
          </div>
          <Progress percent={confidence.score} size="small" />
          <div style={{ display: 'grid', gap: 4, marginTop: 6 }}>
            {confidence.risks.map((risk, index) => (
              <div key={`${messageId}-risk-${index}`} style={{ fontSize: 12, color: '#92400e' }}>
                风险提示：{risk}
              </div>
            ))}
          </div>
        </div>
      </div>
    </Card>

    {cardEntries.map(({ day, dayIndex, dayKey }) => {
      const route = routeByDay[dayKey];
      const conflicts = conflictMap.get(dayKey) || [];
      const decisionInfos = buildSpotDecisionInfos(day.spots);
      const compactedTips = compactTips(day.tips);
      const tipsExpanded = expandedTips[dayKey] ?? false;
      const visibleTips = tipsExpanded ? compactedTips : compactedTips.slice(0, 2);
      const hiddenTipCount = compactedTips.length - visibleTips.length;

      return (
        <Card key={`${messageId}-${dayKey}`} size="small" title={day.dayLabel}>
          <div style={{ display: 'grid', gap: 10 }}>
            {conflicts.length > 0 && (
              <div
                style={{
                  display: 'grid',
                  gap: 8,
                  background: 'linear-gradient(135deg, #fff7ed 0%, #fffbeb 100%)',
                  border: '1px solid #fed7aa',
                  borderRadius: 12,
                  padding: 10,
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 700, color: '#9a3412' }}>本日风险提醒</div>
                {conflicts.slice(0, 2).map((conflict) => (
                  <div key={`${dayKey}-risk-${conflict.id}`} style={{ fontSize: 12, color: riskColor(conflict.severity) }}>
                    {conflict.title}：{conflict.suggestion}
                  </div>
                ))}
              </div>
            )}

            <div style={{ display: 'grid', gap: 8 }}>
              <PeriodTimeline
                period="morning"
                rawText={day.morning}
                dayKey={dayKey}
                expandedPeriods={expandedPeriods}
                onToggle={onTogglePeriod}
              />
              <PeriodTimeline
                period="afternoon"
                rawText={day.afternoon}
                dayKey={dayKey}
                expandedPeriods={expandedPeriods}
                onToggle={onTogglePeriod}
              />
              <PeriodTimeline
                period="evening"
                rawText={day.evening}
                dayKey={dayKey}
                expandedPeriods={expandedPeriods}
                onToggle={onTogglePeriod}
              />
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Tag color="blue">当日预算：¥{day.baseBudget}</Tag>
              <Tag color="processing">景点数：{day.spots.length}</Tag>
              <Tag color="purple">路线距离：{formatDistance(route?.distance_m)}</Tag>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Button
                size="small"
                icon={<EnvironmentOutlined />}
                loading={routeLoadingDay === dayKey}
                onClick={() => onFetchRoute(dayKey, day)}
              >
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
              <img
                src={route.static_map_url}
                alt={`${day.dayLabel} route`}
                style={{ width: '100%', borderRadius: 10, border: '1px solid #e2e8f0' }}
              />
            )}

            {decisionInfos.length > 0 && (
              <div style={{ display: 'grid', gap: 8 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#1f2937' }}>景点决策卡</div>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: 10,
                  }}
                >
                  {decisionInfos.map((spot) => {
                    const active = Boolean(favoriteSpots[spot.name]);
                    return (
                      <div
                        key={`${dayKey}-${spot.name}`}
                        style={{
                          border: '1px solid #dbe4ee',
                          borderRadius: 12,
                          padding: 12,
                          background: active ? 'linear-gradient(135deg, #fff7ed 0%, #ffffff 100%)' : '#ffffff',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
                          <div style={{ fontWeight: 700, color: '#1f2937' }}>{spot.name}</div>
                          <Button
                            type="text"
                            size="small"
                            icon={active ? <HeartFilled style={{ color: '#f97316' }} /> : <HeartOutlined />}
                            onClick={() => onToggleFavoriteSpot(spot)}
                          />
                        </div>
                        <div style={{ display: 'grid', gap: 4, fontSize: 12, color: '#475569' }}>
                          <div>停留：{spot.stayDuration}</div>
                          <div>最佳到达：{spot.bestArrival}</div>
                          <div>适合：{spot.audience}</div>
                          <div>花费感知：{spot.costHint}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {conflicts.length > 0 && (
              <div style={{ display: 'grid', gap: 6 }}>
                {conflicts.map((conflict) => (
                  <div
                    key={`${dayKey}-${conflict.id}`}
                    style={{
                      fontSize: 12,
                      color: '#7c2d12',
                      background: '#fff7ed',
                      border: '1px solid #fed7aa',
                      borderRadius: 8,
                      padding: '6px 8px',
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{conflict.title}</div>
                    <div>{conflict.description}</div>
                    <div>建议：{conflict.suggestion}</div>
                  </div>
                ))}
              </div>
            )}

            {compactedTips.length > 0 && (
              <div style={{ display: 'grid', gap: 4 }}>
                {visibleTips.map((tip, index) => (
                  <div key={`${dayKey}-tip-${index}`} style={{ fontSize: 12, color: '#0f766e' }}>
                    小贴士：{tip}
                  </div>
                ))}
                {hiddenTipCount > 0 && (
                  <Button type="link" size="small" style={{ width: 'fit-content', padding: 0 }} onClick={() => onToggleTips(dayKey)}>
                    {tipsExpanded ? '收起' : `展开更多（+${hiddenTipCount}）`}
                  </Button>
                )}
              </div>
            )}
          </div>
        </Card>
      );
    })}
  </div>
);

interface ToolkitCompareTabProps {
  variants: PlanVariant[];
  onChooseVariant: (variant: PlanVariant) => void;
}

export const ToolkitCompareTab: React.FC<ToolkitCompareTabProps> = ({ variants, onChooseVariant }) => {
  if (variants.length < 2) {
    return <div style={{ fontSize: 13, color: '#64748b' }}>未检测到 2 套以上可比较方案，尝试在提问中加入“省钱版 vs 轻松版”。</div>;
  }

  const compareColumns: ColumnsType<CompareRow> = [
    {
      title: '对比项',
      dataIndex: 'metric',
      key: 'metric',
      width: 120,
      fixed: 'left',
    },
    ...variants.map((variant) => ({
      title: variant.title,
      dataIndex: ['values', variant.id],
      key: variant.id,
      render: (_: string, row: CompareRow) => row.values[variant.id] || '-',
    })),
  ];

  const compareRows: CompareRow[] = [
    {
      key: 'positioning',
      metric: '方案定位',
      values: Object.fromEntries(variants.map((variant) => [variant.id, variant.title])),
    },
    {
      key: 'highlights',
      metric: '核心亮点',
      values: Object.fromEntries(
        variants.map((variant) => {
          const lines = variant.content
            .split('\n')
            .map((line) => line.trim())
            .filter(Boolean);
          return [variant.id, lines.slice(0, 3).join('；') || '-'];
        })
      ),
    },
    {
      key: 'suitable',
      metric: '适合人群',
      values: Object.fromEntries(
        variants.map((variant) => {
          const lower = variant.title.toLowerCase();
          if (lower.includes('省')) return [variant.id, '预算优先 / 行程紧凑'];
          if (lower.includes('舒') || lower.includes('轻松')) return [variant.id, '体验优先 / 节奏轻松'];
          return [variant.id, '综合平衡 / 首次出行'];
        })
      ),
    },
  ];

  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <Table size="small" pagination={false} rowKey="key" columns={compareColumns} dataSource={compareRows} scroll={{ x: 720 }} />

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {variants.map((variant) => (
          <Button key={variant.id} onClick={() => onChooseVariant(variant)}>
            选中“{variant.title}”继续细化
          </Button>
        ))}
      </div>
    </div>
  );
};

interface ToolkitChecklistTabProps {
  checklist: ChecklistItem[];
  completedChecklist: Record<string, boolean>;
  messageId: string;
  onToggleChecklist: (itemId: string, checked: boolean) => void;
}

export const ToolkitChecklistTab: React.FC<ToolkitChecklistTabProps> = ({
  checklist,
  completedChecklist,
  messageId,
  onToggleChecklist,
}) => (
  <div style={{ display: 'grid', gap: 8 }}>
    {checklist.map((item) => (
      <Checkbox
        key={`${messageId}-${item.id}`}
        checked={Boolean(completedChecklist[item.id])}
        onChange={(event) => onToggleChecklist(item.id, event.target.checked)}
      >
        {item.label}
      </Checkbox>
    ))}
  </div>
);

interface ToolkitFavoritesTabProps {
  favoriteSpotList: SpotDecisionInfo[];
  onContinuePrompt?: (prompt: string) => void;
  onQuickRefine: (action: QuickRefineAction) => void;
  onToggleFavoriteSpot: (spot: SpotDecisionInfo) => void;
}

export const ToolkitFavoritesTab: React.FC<ToolkitFavoritesTabProps> = ({
  favoriteSpotList,
  onContinuePrompt,
  onQuickRefine,
  onToggleFavoriteSpot,
}) => (
  <div style={{ display: 'grid', gap: 10 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      <Tag color={favoriteSpotList.length > 0 ? 'gold' : 'default'}>候选景点 {favoriteSpotList.length}</Tag>
      {favoriteSpotList.length > 0 && onContinuePrompt && (
        <Button
          size="small"
          onClick={() =>
            onQuickRefine({
              key: 'favorites-build',
              label: '根据候选池重做',
              prompt: `请优先基于以下候选景点重新生成一版更精炼的旅行方案，并保留清晰时间轴：${favoriteSpotList
                .map((item) => item.name)
                .join('、')}`,
            })
          }
        >
          用候选池重做方案
        </Button>
      )}
    </div>
    {favoriteSpotList.length === 0 ? (
      <div style={{ fontSize: 13, color: '#64748b' }}>先在“景点决策卡”里收藏你想保留的点位，这里会自动汇总。</div>
    ) : (
      favoriteSpotList.map((spot) => (
        <Card key={`favorite-${spot.name}`} size="small">
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
            <div style={{ display: 'grid', gap: 4 }}>
              <div style={{ fontWeight: 700 }}>{spot.name}</div>
              <div style={{ fontSize: 12, color: '#475569' }}>
                {spot.stayDuration} | {spot.bestArrival} | {spot.audience}
              </div>
            </div>
            <Button size="small" icon={<HeartFilled style={{ color: '#f97316' }} />} onClick={() => onToggleFavoriteSpot(spot)}>
              移出候选
            </Button>
          </div>
        </Card>
      ))
    )}
  </div>
);

interface ToolkitPracticalTabProps {
  messageId: string;
  practicalInfo: PracticalInfoCard[];
}

export const ToolkitPracticalTab: React.FC<ToolkitPracticalTabProps> = ({ messageId, practicalInfo }) => (
  <div
    style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      gap: 10,
    }}
  >
    {practicalInfo.map((item) => {
      const tone = practicalToneStyle(item.tone);
      return (
        <div
          key={`${messageId}-practical-${item.id}`}
          style={{
            borderRadius: 14,
            padding: 14,
            background: tone.background,
            border: `1px solid ${tone.border}`,
            color: tone.color,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <InfoCircleOutlined />
            <div style={{ fontWeight: 700 }}>{item.title}</div>
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.7 }}>{item.value}</div>
        </div>
      );
    })}
  </div>
);

interface ToolkitRemindersTabProps {
  messageId: string;
  reminders: ReminderItem[];
}

export const ToolkitRemindersTab: React.FC<ToolkitRemindersTabProps> = ({ messageId, reminders }) => (
  <div style={{ display: 'grid', gap: 10 }}>
    {reminders.map((item) => (
      <Card key={`${messageId}-${item.id}`} size="small">
        <Space orientation="vertical" size={2}>
          <Tag color="blue">{item.phase}</Tag>
          <div style={{ fontWeight: 600 }}>{item.title}</div>
          <div style={{ fontSize: 13, color: '#475569' }}>{item.detail}</div>
        </Space>
      </Card>
    ))}
  </div>
);

interface ToolkitConflictsTabProps {
  cardEntries: CardEntry[];
  conflictMap: Map<string, ItineraryConflict[]>;
  messageId: string;
  totalConflicts: number;
  onOneClickFix: (dayKey: string, dayIndex: number, day: DayPlanCard) => void;
}

export const ToolkitConflictsTab: React.FC<ToolkitConflictsTabProps> = ({
  cardEntries,
  conflictMap,
  messageId,
  totalConflicts,
  onOneClickFix,
}) => (
  <div style={{ display: 'grid', gap: 10 }}>
    <Tag color={totalConflicts > 0 ? 'orange' : 'green'}>
      {totalConflicts > 0 ? `检测到 ${totalConflicts} 个冲突风险` : '未检测到明显冲突'}
    </Tag>
    {cardEntries.map(({ day, dayIndex, dayKey }) => {
      const conflicts = conflictMap.get(dayKey) || [];
      if (conflicts.length === 0) {
        return (
          <Card key={`${messageId}-conflict-${dayKey}`} size="small" title={day.dayLabel}>
            <span style={{ fontSize: 13, color: '#16a34a' }}>无冲突</span>
          </Card>
        );
      }

      return (
        <Card key={`${messageId}-conflict-${dayKey}`} size="small" title={day.dayLabel}>
          <div style={{ display: 'grid', gap: 8 }}>
            {conflicts.map((conflict) => (
              <div key={`${dayKey}-${conflict.id}`}>
                <Tag color={conflict.severity === 'high' ? 'red' : conflict.severity === 'medium' ? 'orange' : 'gold'}>
                  {conflict.type}
                </Tag>
                <div style={{ fontWeight: 600, marginTop: 2 }}>{conflict.title}</div>
                <div style={{ fontSize: 13, color: '#475569' }}>{conflict.description}</div>
                <div style={{ fontSize: 12, color: '#7c3aed' }}>建议：{conflict.suggestion}</div>
              </div>
            ))}
            <Divider style={{ margin: '6px 0' }} />
            <Button size="small" icon={<ReloadOutlined />} onClick={() => onOneClickFix(dayKey, dayIndex, day)}>
              一键修复此日
            </Button>
          </div>
        </Card>
      );
    })}
  </div>
);
