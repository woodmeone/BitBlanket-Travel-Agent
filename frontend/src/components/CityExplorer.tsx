'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Drawer, Empty, Select, Space, Spin, Table, Tag } from 'antd';
import {
  CompassOutlined,
  EnvironmentOutlined,
  HeartFilled,
  HeartOutlined,
  RiseOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { apiService } from '@/services/api';
import type { CityDetail, CitySummary } from '@/types';

interface CityExplorerProps {
  onUsePrompt: (prompt: string) => void;
}

type QuickFilterKey = 'weekend' | 'budget' | 'family' | 'easywalk' | 'rainy' | 'food';

interface QuickFilterOption {
  key: QuickFilterKey;
  label: string;
}

interface DerivedCityProfile {
  budgetLevel: 'low' | 'medium' | 'high';
  tripDuration: string;
  walkIntensity: 'low' | 'medium' | 'high';
  rainFriendly: boolean;
  familyFriendly: boolean;
  foodFriendly: boolean;
  styleLabel: string;
  recommendation: string;
}

interface CompareTableRow {
  key: string;
  metric: string;
  values: Record<string, string>;
}

const QUICK_FILTERS: QuickFilterOption[] = [
  { key: 'weekend', label: '周末可去' },
  { key: 'budget', label: '预算友好' },
  { key: 'family', label: '亲子友好' },
  { key: 'easywalk', label: '少走路' },
  { key: 'rainy', label: '雨天也能玩' },
  { key: 'food', label: '美食优先' },
];

function includesAny(source: string[], patterns: string[]): boolean {
  const text = source.join(' ').toLowerCase();
  return patterns.some((pattern) => text.includes(pattern.toLowerCase()));
}

function buildCityProfile(city: CitySummary | CityDetail): DerivedCityProfile {
  const budgetValue = city.avg_budget_per_day || 0;
  const tags = city.tags || [];
  const budgetLevel: DerivedCityProfile['budgetLevel'] =
    budgetValue <= 500 ? 'low' : budgetValue <= 900 ? 'medium' : 'high';

  return {
    budgetLevel,
    tripDuration: city.trip_duration || '2-3天',
    walkIntensity: city.walk_intensity || 'medium',
    rainFriendly: city.rain_friendly ?? includesAny(tags, ['博物馆', '室内', '文化']),
    familyFriendly: city.family_friendly ?? includesAny(tags, ['亲子', '家庭', '乐园']),
    foodFriendly: city.food_friendly ?? includesAny(tags, ['美食', '小吃', '夜市']),
    styleLabel: city.style_label || '综合体验',
    recommendation: city.editorial_note?.trim() || city.description?.trim() || `${city.name}适合做轻量旅行。`,
  };
}

function budgetLabel(level: DerivedCityProfile['budgetLevel']): string {
  if (level === 'low') return '预算友好';
  if (level === 'high') return '预算偏高';
  return '预算均衡';
}

function walkLabel(level: DerivedCityProfile['walkIntensity']): string {
  if (level === 'low') return '少走路';
  if (level === 'high') return '步行偏多';
  return '步行适中';
}

function boolLabel(value: boolean): string {
  return value ? '友好' : '一般';
}

function foodLabel(value: boolean): string {
  return value ? '高' : '中';
}

function seasonLabel(seasons: string[]): string {
  return seasons.slice(0, 2).join(' / ') || '四季皆可';
}

function buildPlanPrompt(cityName: string): string {
  return `请为我规划 ${cityName} 3 天旅行计划，包含每日时间轴、预算估算、住宿建议、拍照点位、下雨天备选和适合第一次去的顺序安排。`;
}

function buildComparePrompt(cityNames: string[]): string {
  return `请比较这些城市作为下一次旅行目的地的差异：${cityNames.join('、')}。请从预算、适合天数、步行强度、亲子友好度、雨天可玩度、核心景点真实性和整体旅行氛围做并排对比，并给出推荐结论。`;
}

export default function CityExplorer({ onUsePrompt }: CityExplorerProps) {
  const initialVisibleCityCount = 24;
  const loadMoreCityCount = 24;
  const [regions, setRegions] = useState<string[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<string | undefined>(undefined);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedQuickFilters, setSelectedQuickFilters] = useState<QuickFilterKey[]>([]);
  const [cities, setCities] = useState<CitySummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isFilterLoading, setIsFilterLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeCityDetail, setActiveCityDetail] = useState<CityDetail | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [compareCityIds, setCompareCityIds] = useState<string[]>([]);
  const [favoriteCityIds, setFavoriteCityIds] = useState<string[]>([]);
  const [visibleCityCount, setVisibleCityCount] = useState(initialVisibleCityCount);

  useEffect(() => {
    async function loadFilterOptions() {
      try {
        setIsFilterLoading(true);
        const [regionData, tagData] = await Promise.all([apiService.getRegions(), apiService.getTags()]);
        setRegions(regionData.regions || []);
        setTags(tagData.tags || []);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : '加载筛选项失败');
      } finally {
        setIsFilterLoading(false);
      }
    }

    void loadFilterOptions();
  }, []);

  useEffect(() => {
    async function loadCities() {
      try {
        setIsLoading(true);
        setError(null);
        const response = await apiService.getCities({ region: selectedRegion, tags: selectedTags });
        setCities(response.cities || []);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : '加载城市失败');
      } finally {
        setIsLoading(false);
      }
    }

    void loadCities();
  }, [selectedRegion, selectedTags]);

  useEffect(() => {
    setVisibleCityCount(initialVisibleCityCount);
  }, [selectedQuickFilters, selectedRegion, selectedTags]);

  const filteredCities = useMemo(() => {
    return cities.filter((city) => {
      if (selectedQuickFilters.length === 0) return true;
      const profile = buildCityProfile(city);

      return selectedQuickFilters.every((filterKey) => {
        if (filterKey === 'weekend') return /^2/.test(profile.tripDuration);
        if (filterKey === 'budget') return profile.budgetLevel === 'low';
        if (filterKey === 'family') return profile.familyFriendly;
        if (filterKey === 'easywalk') return profile.walkIntensity === 'low';
        if (filterKey === 'rainy') return profile.rainFriendly;
        if (filterKey === 'food') return profile.foodFriendly;
        return true;
      });
    });
  }, [cities, selectedQuickFilters]);

  const compareCities = useMemo(
    () => filteredCities.filter((city) => compareCityIds.includes(city.id)).slice(0, 3),
    [compareCityIds, filteredCities]
  );

  const favoriteCities = useMemo(
    () => cities.filter((city) => favoriteCityIds.includes(city.id)),
    [cities, favoriteCityIds]
  );

  const displayedCities = useMemo(
    () => filteredCities.slice(0, visibleCityCount),
    [filteredCities, visibleCityCount]
  );

  const summaryText = useMemo(() => {
    const segments: string[] = [];
    if (selectedRegion) segments.push(selectedRegion);
    if (selectedTags.length > 0) segments.push(selectedTags.join(' / '));
    if (selectedQuickFilters.length > 0) {
      segments.push(
        QUICK_FILTERS.filter((item) => selectedQuickFilters.includes(item.key))
          .map((item) => item.label)
          .join(' / ')
      );
    }
    return segments.length > 0 ? segments.join(' · ') : '全部真实策展城市';
  }, [selectedQuickFilters, selectedRegion, selectedTags]);

  async function openCityDetail(cityId: string) {
    try {
      const detail = await apiService.getCityDetail(cityId);
      setActiveCityDetail(detail);
      setIsDetailOpen(true);
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : '加载城市详情失败');
    }
  }

  function toggleQuickFilter(filterKey: QuickFilterKey) {
    setSelectedQuickFilters((previous) =>
      previous.includes(filterKey) ? previous.filter((item) => item !== filterKey) : [...previous, filterKey]
    );
  }

  function toggleCompareCity(cityId: string) {
    setCompareCityIds((previous) => {
      if (previous.includes(cityId)) return previous.filter((item) => item !== cityId);
      if (previous.length >= 3) return [...previous.slice(1), cityId];
      return [...previous, cityId];
    });
  }

  function toggleFavoriteCity(cityId: string) {
    setFavoriteCityIds((previous) =>
      previous.includes(cityId) ? previous.filter((item) => item !== cityId) : [...previous, cityId]
    );
  }

  const activeDetailProfile = activeCityDetail ? buildCityProfile(activeCityDetail) : null;

  const compareColumns: ColumnsType<CompareTableRow> = [
    {
      title: '对比项',
      dataIndex: 'metric',
      key: 'metric',
      width: 140,
      fixed: 'left',
      render: (value: string) => <span style={{ fontWeight: 700, color: '#1f2937' }}>{value}</span>,
    },
    ...compareCities.map((city) => ({
      title: city.name,
      dataIndex: ['values', city.id],
      key: city.id,
      width: 220,
      render: (_value: string, row: CompareTableRow) => (
        <div style={{ whiteSpace: 'pre-wrap', color: '#334155', lineHeight: 1.7 }}>{row.values[city.id] || '-'}</div>
      ),
    })),
  ];

  const compareRows: CompareTableRow[] = compareCities.length
    ? [
        {
          key: 'region',
          metric: '地区',
          values: Object.fromEntries(compareCities.map((city) => [city.id, city.region])),
        },
        {
          key: 'budget',
          metric: '预算',
          values: Object.fromEntries(
            compareCities.map((city) => [city.id, `¥${city.avg_budget_per_day} / ${budgetLabel(buildCityProfile(city).budgetLevel)}`])
          ),
        },
        {
          key: 'days',
          metric: '适合天数',
          values: Object.fromEntries(compareCities.map((city) => [city.id, buildCityProfile(city).tripDuration])),
        },
        {
          key: 'walk',
          metric: '步行强度',
          values: Object.fromEntries(compareCities.map((city) => [city.id, walkLabel(buildCityProfile(city).walkIntensity)])),
        },
        {
          key: 'season',
          metric: '合适季节',
          values: Object.fromEntries(compareCities.map((city) => [city.id, seasonLabel(city.best_seasons)])),
        },
        {
          key: 'style',
          metric: '旅行气质',
          values: Object.fromEntries(compareCities.map((city) => [city.id, buildCityProfile(city).styleLabel])),
        },
        {
          key: 'note',
          metric: '编辑建议',
          values: Object.fromEntries(compareCities.map((city) => [city.id, buildCityProfile(city).recommendation])),
        },
      ]
    : [];

  return (
    <div style={{ margin: '0 16px 16px' }}>
      <Card
        style={{
          borderRadius: 20,
          border: '1px solid rgba(15, 23, 42, 0.08)',
          background:
            'radial-gradient(circle at top left, rgba(14,165,233,0.16), transparent 34%), linear-gradient(140deg, #ffffff 0%, #f8fafc 45%, #eef6ff 100%)',
          overflow: 'hidden',
        }}
        styles={{ body: { padding: 18 } }}
      >
        <div style={{ display: 'grid', gap: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#0f172a', marginBottom: 6 }}>
                <CompassOutlined style={{ marginRight: 10, color: '#0369a1' }} />
                城市探索
              </div>
              <div style={{ fontSize: 13, color: '#475569', maxWidth: 760 }}>
                当前只展示真实策展城市库，详情中的景点名称、区位和备注都来自人工整理，不再混入模板化生成城市。
              </div>
            </div>
            <Space wrap>
              <Tag color="blue">{summaryText}</Tag>
              <Tag color={compareCities.length > 0 ? 'gold' : 'default'}>对比池 {compareCities.length}/3</Tag>
              <Tag color={favoriteCities.length > 0 ? 'red' : 'default'}>收藏 {favoriteCities.length}</Tag>
            </Space>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1.3fr 1fr',
              gap: 14,
            }}
          >
            <div
              style={{
                borderRadius: 18,
                padding: 16,
                background: 'linear-gradient(135deg, #082f49 0%, #155e75 100%)',
                color: '#f8fafc',
                minHeight: 180,
              }}
            >
              <div style={{ fontSize: 12, letterSpacing: 1.2, opacity: 0.75, marginBottom: 10 }}>CURATED</div>
              <div style={{ fontSize: 24, fontWeight: 700, lineHeight: 1.3, marginBottom: 12 }}>
                先判断城市是否适合你，
                <br />
                再决定要不要继续做 AI 行程规划。
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <Button onClick={() => onUsePrompt('请推荐适合周末两天出发、预算 1500 内、地铁友好的真实城市目的地，并给出选择理由。')}>
                  本周末去哪
                </Button>
                <Button onClick={() => onUsePrompt('请推荐亲子友好、少走路、下雨也不容易废行程的真实城市，并说明为什么适合。')}>
                  亲子省心
                </Button>
                <Button onClick={() => onUsePrompt('请推荐预算友好、以美食为主、景点不需要太密集的城市，并做简短对比。')}>
                  预算美食
                </Button>
              </div>
            </div>

            <div
              style={{
                borderRadius: 18,
                padding: 16,
                background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
                border: '1px solid #dbe4ee',
                display: 'grid',
                gap: 10,
              }}
            >
              <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>目的地 shortlist</div>
              {favoriteCities.length === 0 ? (
                <div style={{ fontSize: 13, color: '#64748b' }}>先收藏几个城市，这里会变成你的候选池。</div>
              ) : (
                favoriteCities.slice(0, 4).map((city) => (
                  <div key={`favorite-${city.id}`} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                    <div>
                      <div style={{ fontWeight: 600, color: '#1f2937' }}>{city.name}</div>
                      <div style={{ fontSize: 12, color: '#64748b' }}>{buildCityProfile(city).recommendation}</div>
                    </div>
                    <Button size="small" onClick={() => onUsePrompt(buildPlanPrompt(city.name))}>
                      继续规划
                    </Button>
                  </div>
                ))
              )}
            </div>
          </div>

          <Space wrap size={10}>
            <Select
              allowClear
              loading={isFilterLoading}
              placeholder="按地区筛选"
              style={{ width: 180 }}
              value={selectedRegion}
              onChange={(value) => setSelectedRegion(value)}
              options={regions.map((item) => ({ label: item, value: item }))}
            />
            <Select
              mode="multiple"
              loading={isFilterLoading}
              placeholder="按标签筛选"
              style={{ width: 320 }}
              value={selectedTags}
              onChange={(value) => setSelectedTags(value)}
              options={tags.map((item) => ({ label: item, value: item }))}
            />
            <Button onClick={() => onUsePrompt('请帮我从当前真实城市库里选一个适合第一次出发的目的地，并从预算、步行强度、雨天备选和核心景点真实性解释原因。')}>
              让助手帮我选
            </Button>
          </Space>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {QUICK_FILTERS.map((filter) => {
              const active = selectedQuickFilters.includes(filter.key);
              return (
                <Button
                  key={filter.key}
                  size="small"
                  type={active ? 'primary' : 'default'}
                  onClick={() => toggleQuickFilter(filter.key)}
                  style={
                    active
                      ? {
                          background: 'linear-gradient(135deg, #0284c7 0%, #0f766e 100%)',
                          borderColor: 'transparent',
                        }
                      : undefined
                  }
                >
                  {filter.label}
                </Button>
              );
            })}
          </div>

          {compareCities.length > 0 && (
            <Card
              size="small"
              style={{ borderRadius: 16, border: '1px solid #fde68a', background: 'linear-gradient(180deg, #fffdf2 0%, #ffffff 100%)' }}
              styles={{ body: { padding: 14 } }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: '#92400e' }}>城市对比池</div>
                  <div style={{ fontSize: 12, color: '#78716c' }}>最多放 3 个真实城市，快速比较后直接继续规划。</div>
                </div>
                <Space wrap>
                  <Button icon={<SwapOutlined />} onClick={() => onUsePrompt(buildComparePrompt(compareCities.map((city) => city.name)))}>
                    让助手对比
                  </Button>
                  <Button onClick={() => setCompareCityIds([])}>清空</Button>
                </Space>
              </div>
              <Table size="small" pagination={false} rowKey="key" columns={compareColumns} dataSource={compareRows} scroll={{ x: 780 }} />
            </Card>
          )}

          {error && <Alert type="error" showIcon message={error} />}

          {isLoading ? (
            <div style={{ padding: 40, textAlign: 'center' }}>
              <Spin />
            </div>
          ) : filteredCities.length === 0 ? (
            <Empty description="没有匹配的城市，换个筛选试试。" />
          ) : (
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <div style={{ fontSize: 13, color: '#475569' }}>
                  已显示 <span style={{ fontWeight: 700, color: '#0f172a' }}>{displayedCities.length}</span> / {filteredCities.length} 个城市
                </div>
                <Space wrap size={8}>
                  {filteredCities.length > visibleCityCount && (
                    <Button size="small" onClick={() => setVisibleCityCount((count) => count + loadMoreCityCount)}>
                      再看 24 个
                    </Button>
                  )}
                  {visibleCityCount > initialVisibleCityCount && (
                    <Button size="small" onClick={() => setVisibleCityCount(initialVisibleCityCount)}>
                      收起到首屏
                    </Button>
                  )}
                </Space>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
                {displayedCities.map((city) => {
                  const profile = buildCityProfile(city);
                  const inCompare = compareCityIds.includes(city.id);
                  const favorite = favoriteCityIds.includes(city.id);

                  return (
                    <Card
                      key={city.id}
                      size="small"
                      style={{
                        borderRadius: 16,
                        border: inCompare ? '1px solid #f59e0b' : '1px solid #e2e8f0',
                        background: inCompare
                          ? 'linear-gradient(180deg, #fffaf0 0%, #ffffff 100%)'
                          : 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
                      }}
                      styles={{ body: { padding: 12 } }}
                    >
                      <div style={{ display: 'grid', gap: 8 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                          <div>
                            <div style={{ fontSize: 17, fontWeight: 700, color: '#0f172a' }}>{city.name}</div>
                            <div style={{ fontSize: 12, color: '#64748b' }}>{city.region}</div>
                          </div>
                          <Button
                            type="text"
                            size="small"
                            icon={favorite ? <HeartFilled style={{ color: '#ef4444' }} /> : <HeartOutlined />}
                            onClick={() => toggleFavoriteCity(city.id)}
                          />
                        </div>

                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          <Tag color="blue" style={{ marginInlineEnd: 0 }}>
                            {budgetLabel(profile.budgetLevel)}
                          </Tag>
                          <Tag color="green" style={{ marginInlineEnd: 0 }}>
                            {profile.tripDuration}
                          </Tag>
                          <Tag color="purple" style={{ marginInlineEnd: 0 }}>
                            {profile.styleLabel}
                          </Tag>
                          <Tag color="cyan" style={{ marginInlineEnd: 0 }}>
                            {seasonLabel(city.best_seasons)}
                          </Tag>
                        </div>

                        <div style={{ fontSize: 12, lineHeight: 1.65, color: '#334155', minHeight: 58 }}>{profile.recommendation}</div>

                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {city.tags.slice(0, 3).map((tag) => (
                            <Tag key={`${city.id}-${tag}`} style={{ marginBottom: 4 }}>
                              {tag}
                            </Tag>
                          ))}
                        </div>

                        <div
                          style={{
                            display: 'grid',
                            gridTemplateColumns: '1fr 1fr',
                            gap: 6,
                            fontSize: 12,
                            color: '#475569',
                            background: '#f8fafc',
                            borderRadius: 10,
                            padding: 8,
                          }}
                        >
                          <div>人均: ¥{city.avg_budget_per_day}</div>
                          <div>步行: {walkLabel(profile.walkIntensity)}</div>
                          <div>雨天: {boolLabel(profile.rainFriendly)}</div>
                          <div>亲子: {boolLabel(profile.familyFriendly)}</div>
                          <div>美食: {foodLabel(profile.foodFriendly)}</div>
                          <div>数据: {city.data_source}</div>
                        </div>

                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          <Button size="small" onClick={() => openCityDetail(city.id)}>
                            详情
                          </Button>
                          <Button size="small" icon={<RiseOutlined />} onClick={() => toggleCompareCity(city.id)}>
                            {inCompare ? '移出对比' : '加入对比'}
                          </Button>
                          <Button size="small" type="primary" onClick={() => onUsePrompt(buildPlanPrompt(city.name))}>
                            规划
                          </Button>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </Card>

      <Drawer
        title={
          <span>
            <EnvironmentOutlined style={{ marginRight: 8 }} />
            {activeCityDetail?.name || '城市详情'}
          </span>
        }
        open={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        size="large"
      >
        {activeCityDetail && activeDetailProfile && (
          <div style={{ display: 'grid', gap: 14 }}>
            <Card size="small" style={{ borderRadius: 14 }}>
              <div style={{ display: 'grid', gap: 10 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#0f172a' }}>城市气质</div>
                <div style={{ color: '#334155', lineHeight: 1.8 }}>{activeCityDetail.description}</div>
                <div style={{ fontSize: 13, color: '#475569' }}>{activeDetailProfile.recommendation}</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <Tag color="blue">{budgetLabel(activeDetailProfile.budgetLevel)}</Tag>
                  <Tag color="green">{activeDetailProfile.tripDuration}</Tag>
                  <Tag color="purple">{activeDetailProfile.styleLabel}</Tag>
                  <Tag color="cyan">{walkLabel(activeDetailProfile.walkIntensity)}</Tag>
                  <Tag color="gold">真实策展</Tag>
                </div>
              </div>
            </Card>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 10 }}>
              <Card size="small" styles={{ body: { padding: 12 } }}>
                <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>人均预算</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#111827' }}>¥{activeCityDetail.avg_budget_per_day}</div>
              </Card>
              <Card size="small" styles={{ body: { padding: 12 } }}>
                <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>家庭预算</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#111827' }}>¥{Math.round(activeCityDetail.avg_budget_per_day * 2.4)}</div>
              </Card>
              <Card size="small" styles={{ body: { padding: 12 } }}>
                <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>最佳季节</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#111827' }}>{seasonLabel(activeCityDetail.best_seasons)}</div>
              </Card>
            </div>

            <Card size="small" title="怎么玩更顺">
              <div style={{ display: 'grid', gap: 8, fontSize: 13, color: '#475569' }}>
                <div>推荐节奏：{activeDetailProfile.tripDuration}，先安排核心片区，再做跨区延展。</div>
                <div>雨天策略：{activeDetailProfile.rainFriendly ? '可保留大部分行程，优先馆和街区。' : '建议预留 1-2 个室内备选点。'}</div>
                <div>体力管理：{walkLabel(activeDetailProfile.walkIntensity)}，不要把高密度打卡全堆在同一天。</div>
              </div>
            </Card>

            <Card size="small" title="核心景点">
              <div style={{ display: 'grid', gap: 8 }}>
                {activeCityDetail.attractions.map((attraction) => (
                  <div
                    key={attraction.name}
                    style={{
                      border: '1px solid #e2e8f0',
                      borderRadius: 12,
                      padding: '10px 12px',
                      background: '#ffffff',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                      <div style={{ fontWeight: 700, color: '#1f2937' }}>{attraction.name}</div>
                      <Tag color="geekblue">{attraction.type}</Tag>
                    </div>
                    <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                      建议停留 {attraction.duration} · 门票 ¥{attraction.ticket}
                      {attraction.district ? ` · ${attraction.district}` : ''}
                    </div>
                    {attraction.note && <div style={{ fontSize: 12, color: '#475569', marginTop: 4 }}>{attraction.note}</div>}
                  </div>
                ))}
              </div>
            </Card>

            <Card size="small" title="下一步">
              <Space wrap>
                <Button type="primary" onClick={() => onUsePrompt(buildPlanPrompt(activeCityDetail.name))}>
                  直接规划这座城市
                </Button>
                <Button onClick={() => onUsePrompt(buildComparePrompt([activeCityDetail.name, ...favoriteCities.slice(0, 2).map((city) => city.name)]))}>
                  和候选城市对比
                </Button>
              </Space>
            </Card>
          </div>
        )}
      </Drawer>
    </div>
  );
}
