'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  App,
  Button,
  Card,
  Checkbox,
  Divider,
  Progress,
  Slider,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  CheckSquareOutlined,
  CompassOutlined,
  EnvironmentOutlined,
  HeartFilled,
  HeartOutlined,
  FileImageOutlined,
  FundOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  ShareAltOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import html2canvas from 'html2canvas';
import type { Message, RoutePreviewResponse } from '@/types';
import { apiService } from '@/services/api';
import {
  applyConflictFixes,
  buildChecklist,
  buildConfidenceSummary,
  buildPracticalInfoCards,
  buildReminders,
  buildRoutePoints,
  buildSpotDecisionInfos,
  detectDayConflicts,
  getBudgetProjection,
  parseDayPlanCards,
  parsePlanVariants,
  reorderByDistance,
} from '@/utils/travelPlan';
import type { DayPlanCard, ItineraryConflict, PlanVariant, PracticalInfoCard, SpotDecisionInfo } from '@/utils/travelPlan';

interface TravelPlanToolkitProps {
  messageId: string;
  content: string;
  diagnostics?: Message['diagnostics'];
  onContinuePrompt?: (prompt: string) => void;
}

type BudgetMode = 'saving' | 'balanced' | 'comfort';
type PeriodType = 'morning' | 'afternoon' | 'evening';

interface TimelineItem {
  timeLabel: string | null;
  content: string;
  timeMinutes: number | null;
  originalIndex: number;
}

interface CompareRow {
  key: string;
  metric: string;
  values: Record<string, string>;
}

interface QuickRefineAction {
  key: string;
  label: string;
  prompt: string;
}

function normalizeTipText(tip: string): string {
  return tip
    .replace(/^\s*小贴士[:：]?\s*/i, '')
    .replace(/^\s*当日小贴士[:：]?\s*/i, '')
    .replace(/^\s*⚠️?\s*提示[:：]?\s*/i, '')
    .replace(/^\s*⚠️?\s*注意事项[:：]?\s*/i, '')
    .replace(/(?<!\d)\s*[:：]{2,}\s*(?!\d)/g, '：')
    .replace(/(?<!\d)\s*[:：]\s*(?!\d)/g, '：')
    .replace(/^[：:\-\s]+/, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function compactTips(tips: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const raw of tips) {
    const normalized = normalizeTipText(raw);
    const key = normalized.toLowerCase();
    if (!normalized || seen.has(key)) continue;
    seen.add(key);
    result.push(normalized);
  }
  return result;
}

function sliderToMode(value: number): BudgetMode {
  if (value <= 33) return 'saving';
  if (value >= 67) return 'comfort';
  return 'balanced';
}

function modeToSliderValue(mode: BudgetMode): number {
  if (mode === 'saving') return 10;
  if (mode === 'comfort') return 90;
  return 50;
}

function periodMeta(period: PeriodType): { title: string; color: string } {
  if (period === 'morning') return { title: '上午', color: '#0ea5e9' };
  if (period === 'afternoon') return { title: '下午', color: '#f59e0b' };
  return { title: '晚上', color: '#8b5cf6' };
}

function splitTimelineItems(rawText: string): TimelineItem[] {
  const normalized = rawText
    .replace(/\r\n?/g, '\n')
    .replace(/\s+/g, ' ')
    .replace(/[；;。]/g, '；')
    .replace(/\s*(->|→)\s*/g, '；')
    .replace(/\|/g, '；');

  return normalized
    .split('；')
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item) => !/^(上午|下午|晚上)\b/.test(item))
    .map((item, index) => {
      const timeMatch = item.match(/(?:^|\s)(\d{1,2}[:：]\d{2})(?:\s|$)/);
      if (!timeMatch) {
        return { timeLabel: null, content: item, timeMinutes: null, originalIndex: index };
      }

      const normalizedTime = timeMatch[1].replace('：', ':');
      const [hourStr, minuteStr] = normalizedTime.split(':');
      const hour = Number(hourStr);
      const minute = Number(minuteStr);
      const isValid = Number.isFinite(hour) && Number.isFinite(minute) && hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59;

      return {
        timeLabel: normalizedTime,
        content: item.replace(timeMatch[1], '').replace(/^\s*[-:：]?\s*/, '').trim() || item,
        timeMinutes: isValid ? hour * 60 + minute : null,
        originalIndex: index,
      };
    })
    .sort((a, b) => {
      if (a.timeMinutes !== null && b.timeMinutes !== null) return a.timeMinutes - b.timeMinutes;
      if (a.timeMinutes !== null) return -1;
      if (b.timeMinutes !== null) return 1;
      return a.originalIndex - b.originalIndex;
    });
}

const PeriodTimeline: React.FC<{
  period: PeriodType;
  rawText: string;
  dayKey: string;
  expandedPeriods: Record<string, boolean>;
  onToggle: (periodKey: string) => void;
}> = ({ period, rawText, dayKey, expandedPeriods, onToggle }) => {
  const items = splitTimelineItems(rawText);
  const key = `${dayKey}-${period}`;
  const isExpanded = expandedPeriods[key] ?? false;
  const visibleItems = isExpanded ? items : items.slice(0, 3);
  const hasMore = items.length > 3;
  const meta = periodMeta(period);

  return (
    <div
      style={{
        border: '1px solid #e2e8f0',
        borderRadius: 10,
        padding: '10px 12px',
        background: '#fff',
      }}
    >
      <div style={{ fontSize: 13, fontWeight: 600, color: '#1e293b', marginBottom: 8 }}>{meta.title}</div>
      <div style={{ display: 'grid', gap: 8 }}>
        {visibleItems.map((item, index) => (
          <div key={`${key}-${index}`} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 2 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: meta.color,
                  display: 'inline-block',
                }}
              />
              {index < visibleItems.length - 1 && (
                <span
                  style={{
                    width: 1,
                    minHeight: 18,
                    background: '#cbd5e1',
                    marginTop: 2,
                  }}
                />
              )}
            </div>
            <div style={{ display: 'grid', gap: 4 }}>
              {item.timeLabel && (
                <span
                  style={{
                    display: 'inline-flex',
                    width: 'fit-content',
                    fontSize: 11,
                    color: '#1d4ed8',
                    background: '#dbeafe',
                    border: '1px solid #93c5fd',
                    borderRadius: 999,
                    padding: '1px 8px',
                    fontWeight: 600,
                  }}
                >
                  {item.timeLabel}
                </span>
              )}
              <div style={{ fontSize: 13, color: '#334155', lineHeight: 1.6 }}>{item.content}</div>
            </div>
          </div>
        ))}
      </div>
      {hasMore && (
        <Button size="small" type="link" style={{ padding: 0, marginTop: 6 }} onClick={() => onToggle(key)}>
          {isExpanded ? '收起' : `展开更多（+${items.length - 3}）`}
        </Button>
      )}
    </div>
  );
};

function formatDistance(distanceM: number | undefined): string {
  if (!distanceM || distanceM <= 0) return '-';
  return `${(distanceM / 1000).toFixed(1)} km`;
}

function riskColor(severity: ItineraryConflict['severity']): string {
  if (severity === 'high') return '#dc2626';
  if (severity === 'medium') return '#d97706';
  return '#b45309';
}

function practicalToneStyle(tone: PracticalInfoCard['tone']): { background: string; border: string; color: string } {
  if (tone === 'good') return { background: '#ecfdf5', border: '#a7f3d0', color: '#065f46' };
  if (tone === 'warn') return { background: '#fff7ed', border: '#fed7aa', color: '#9a3412' };
  return { background: '#f8fafc', border: '#cbd5e1', color: '#334155' };
}

function looksLikeItineraryContent(content: string, cards: DayPlanCard[]): boolean {
  if (cards.length >= 2) return true;
  if (/(上午|下午|晚上|预算|小贴士|tips|day\s*\d+|第.{1,4}天|方案|路线|景点)/i.test(content)) return true;
  return false;
}

const TravelPlanToolkit: React.FC<TravelPlanToolkitProps> = ({ messageId, content, diagnostics, onContinuePrompt }) => {
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

  useEffect(() => {
    setCards(baseCards);
    setExpandedPeriods({});
    setExpandedTips({});
    setRouteByDay({});
  }, [baseCards]);

  const hasItineraryContent = useMemo(() => looksLikeItineraryContent(content, baseCards), [content, baseCards]);

  const cardEntries = useMemo(
    () =>
      cards.map((day, dayIndex) => ({
        day,
        dayIndex,
        // Use index-only keys to avoid duplicate labels causing key collisions.
        dayKey: `day-${dayIndex + 1}`,
      })),
    [cards]
  );

  const totalBaseBudget = useMemo(() => cards.reduce((sum, day) => sum + day.baseBudget, 0), [cards]);
  const budgetProjection = useMemo(() => {
    const dayCount = Math.max(cards.length, 1);
    return getBudgetProjection(totalBaseBudget / dayCount, dayCount, modeToSliderValue(budgetMode));
  }, [cards.length, totalBaseBudget, budgetMode]);
  const familyBudget = Math.round(budgetProjection.totalBudget * 2.4);
  const childFriendlyBudget = Math.round(budgetProjection.totalBudget * 1.7);
  const favoriteSpotList = useMemo(() => Object.values(favoriteSpots), [favoriteSpots]);

  const conflictMap = useMemo(() => {
    const map = new Map<string, ItineraryConflict[]>();
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

  if (cards.length === 0 || !hasItineraryContent) return null;

  const togglePeriod = (periodKey: string) => {
    setExpandedPeriods((prev) => ({ ...prev, [periodKey]: !prev[periodKey] }));
  };

  const handleFetchRoute = async (dayKey: string, day: DayPlanCard) => {
    if (day.spots.length < 2) {
      message.warning('当天景点少于 2 个，无法生成路线。');
      return;
    }

    try {
      setRouteLoadingDay(dayKey);
      const result = await apiService.getRoutePreview({ spots: day.spots.slice(0, 12), provider: 'amap' });
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

    let orderedSpots = day.spots;
    if (route?.points?.length) {
      orderedSpots = route.points.map((point) => point.name);
    } else {
      const points = reorderByDistance(buildRoutePoints(day.spots));
      orderedSpots = points.map((point) => point.name);
    }

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
      const result = await apiService.createShareLink({
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

  const toggleFavoriteSpot = (spot: SpotDecisionInfo) => {
    setFavoriteSpots((prev) => {
      if (prev[spot.name]) {
        const next = { ...prev };
        delete next[spot.name];
        return next;
      }
      return { ...prev, [spot.name]: spot };
    });
  };

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
          const lines = variant.content.split('\n').map((line) => line.trim()).filter(Boolean);
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

  const quickRefineActions: QuickRefineAction[] = [
    { key: 'cheaper', label: '换成更省钱', prompt: '请基于当前方案改成更省钱版本，优先保留核心体验，减少高价项目，并重算预算。' },
    { key: 'easy', label: '少走路版', prompt: '请基于当前方案改成少走路版本，压缩跨区移动，增加打车衔接和休息点。' },
    { key: 'rainy', label: '下雨天重排', prompt: '请把当前方案改成下雨天可执行版本，优先室内点位，并替换不适合雨天的安排。' },
    { key: 'family', label: '加亲子备选', prompt: '请在当前方案基础上增加亲子友好备选点和午休/室内 fallback。' },
  ];

  const handleChooseVariant = (variant: PlanVariant) => {
    if (!onContinuePrompt) {
      message.info('当前会话不支持一键继续细化。');
      return;
    }

    const prompt = `请基于“${variant.title}”继续细化：\n1) 输出每日详细时间轴（含时刻）\n2) 补充交通衔接与预计时长\n3) 补充每段预算与备选方案\n\n原方案：\n${variant.content}`;
    onContinuePrompt(prompt);
    message.success(`已选择 ${variant.title}，可继续细化`);
  };

  const itineraryTab = (
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
                <Button size="small" icon={<FileImageOutlined />} onClick={handleExportImage} />
              </Tooltip>
              <Tooltip title="生成可分享短链">
                <Button size="small" icon={<ShareAltOutlined />} onClick={handleShare} />
              </Tooltip>
            </Space>
          </div>

          <Slider
            min={0}
            max={100}
            value={modeToSliderValue(budgetMode)}
            marks={{ 10: '省钱', 50: '均衡', 90: '舒适' }}
            onChange={(value) => setBudgetMode(sliderToMode(Array.isArray(value) ? value[0] : value))}
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
              <Button key={action.key} size="small" onClick={() => runQuickRefine(action)}>
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
                  onToggle={togglePeriod}
                />
                <PeriodTimeline
                  period="afternoon"
                  rawText={day.afternoon}
                  dayKey={dayKey}
                  expandedPeriods={expandedPeriods}
                  onToggle={togglePeriod}
                />
                <PeriodTimeline
                  period="evening"
                  rawText={day.evening}
                  dayKey={dayKey}
                  expandedPeriods={expandedPeriods}
                  onToggle={togglePeriod}
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
                  onClick={() => handleFetchRoute(dayKey, day)}
                >
                  真实路线
                </Button>
                <Button size="small" icon={<CompassOutlined />} onClick={() => handleReorderByDistance(dayKey, dayIndex, day)}>
                  按距离重排
                </Button>
                <Button size="small" icon={<ThunderboltOutlined />} onClick={() => handleOneClickFix(dayKey, dayIndex, day)}>
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
                              onClick={() => toggleFavoriteSpot(spot)}
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
                    <Button
                      type="link"
                      size="small"
                      style={{ width: 'fit-content', padding: 0 }}
                      onClick={() =>
                        setExpandedTips((prev) => ({
                          ...prev,
                          [dayKey]: !tipsExpanded,
                        }))
                      }
                    >
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

  const compareTab =
    variants.length < 2 ? (
      <div style={{ fontSize: 13, color: '#64748b' }}>未检测到 2 套以上可比较方案，尝试在提问中加入“省钱版 vs 轻松版”。</div>
    ) : (
      <div style={{ display: 'grid', gap: 12 }}>
        <Table size="small" pagination={false} rowKey="key" columns={compareColumns} dataSource={compareRows} scroll={{ x: 720 }} />

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {variants.map((variant) => (
            <Button key={variant.id} onClick={() => handleChooseVariant(variant)}>
              选中“{variant.title}”继续细化
            </Button>
          ))}
        </div>
      </div>
    );

  const checklistTab = (
    <div style={{ display: 'grid', gap: 8 }}>
      {checklist.map((item) => (
        <Checkbox
          key={`${messageId}-${item.id}`}
          checked={Boolean(completedChecklist[item.id])}
          onChange={(event) => setCompletedChecklist((prev) => ({ ...prev, [item.id]: event.target.checked }))}
        >
          {item.label}
        </Checkbox>
      ))}
    </div>
  );

  const favoritesTab = (
    <div style={{ display: 'grid', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <Tag color={favoriteSpotList.length > 0 ? 'gold' : 'default'}>候选景点 {favoriteSpotList.length}</Tag>
        {favoriteSpotList.length > 0 && onContinuePrompt && (
          <Button
            size="small"
            onClick={() =>
              runQuickRefine({
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
              <Button size="small" icon={<HeartFilled style={{ color: '#f97316' }} />} onClick={() => toggleFavoriteSpot(spot)}>
                移出候选
              </Button>
            </div>
          </Card>
        ))
      )}
    </div>
  );

  const practicalTab = (
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

  const remindersTab = (
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

  const conflictsTab = (
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
              <Button size="small" icon={<ReloadOutlined />} onClick={() => handleOneClickFix(dayKey, dayIndex, day)}>
                一键修复此日
              </Button>
            </div>
          </Card>
        );
      })}
    </div>
  );

  const tabItems = [
    { key: 'itinerary', label: '每日行程', children: itineraryTab, icon: <CompassOutlined /> },
    { key: 'compare', label: '多方案对比', children: compareTab, icon: <FundOutlined /> },
    { key: 'conflicts', label: '冲突检测', children: conflictsTab, icon: <ReloadOutlined /> },
    { key: 'favorites', label: '候选池', children: favoritesTab, icon: <HeartOutlined /> },
    { key: 'practical', label: '实用信息', children: practicalTab, icon: <InfoCircleOutlined /> },
    { key: 'checklist', label: '执行清单', children: checklistTab, icon: <CheckSquareOutlined /> },
    { key: 'reminders', label: '出发提醒', children: remindersTab, icon: <ReloadOutlined /> },
  ];

  return (
    <Card
      size="small"
      style={{ marginTop: 12, borderRadius: 12, border: '1px solid #e2e8f0', background: '#f8fafc' }}
      styles={{ body: { padding: 12 } }}
    >
      <Tabs size="small" items={tabItems} />
    </Card>
  );
};

export default TravelPlanToolkit;
