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
import { apiService } from '@/services/api';
import type { CityDetail, CitySummary } from '@/types';
import type { ColumnsType } from 'antd/es/table';

interface CityExplorerProps {
  onUsePrompt: (prompt: string) => void;
}

type QuickFilterKey =
  | 'weekend'
  | 'budget'
  | 'family'
  | 'easywalk'
  | 'rainy'
  | 'food';

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
  return patterns.some((pattern) => text.includes(pattern));
}

function buildCityProfile(city: CitySummary | CityDetail): DerivedCityProfile {
  const budgetValue = 'avg_budget_per_day' in city ? city.avg_budget_per_day : 0;
  const tags = city.tags || [];
  const region = city.region || '';

  const familyFriendly = includesAny(tags, ['亲子', '家庭', '儿童', '乐园']);
  const foodFriendly = includesAny(tags, ['美食', '夜市', '小吃', '吃']);
  const rainFriendly = includesAny(tags, ['博物馆', '艺术', '文化', '室内', '展馆']) || ['北京', '上海', '广州', '深圳'].includes(city.name);
  const easyWalk = includesAny(tags, ['轻松', '度假', '慢游', '休闲', '城市漫步']);

  const budgetLevel: DerivedCityProfile['budgetLevel'] =
    budgetValue > 0 ? (budgetValue <= 500 ? 'low' : budgetValue <= 900 ? 'medium' : 'high') : 'medium';
  const walkIntensity: DerivedCityProfile['walkIntensity'] = familyFriendly || easyWalk ? 'low' : foodFriendly ? 'medium' : 'high';
  const tripDuration =
    includesAny(tags, ['周末', '短途', '城市漫步']) || ['华东', '华北'].includes(region) ? '2-3 天' : '3-4 天';

  let styleLabel = '综合体验';
  if (familyFriendly) styleLabel = '亲子轻松';
  else if (foodFriendly) styleLabel = '美食城市';
  else if (rainFriendly) styleLabel = '文化室内';
  else if (easyWalk) styleLabel = '慢节奏度假';

  let recommendation = `${city.name}适合第一次出发，信息密度高，比较容易快速做决定。`;
  if (familyFriendly) recommendation = `${city.name}对亲子用户更友好，行程容错高，也容易安排午休和室内备选。`;
  else if (foodFriendly) recommendation = `${city.name}更适合把“吃”和“逛”结合起来，预算弹性也更好控制。`;
  else if (rainFriendly) recommendation = `${city.name}即使遇到天气变化也不容易废行程，室内内容更充足。`;
  else if (easyWalk) recommendation = `${city.name}节奏相对轻松，适合少走路、低压力的短假期。`;

  return {
    budgetLevel,
    tripDuration,
    walkIntensity,
    rainFriendly,
    familyFriendly,
    foodFriendly,
    styleLabel,
    recommendation,
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

function familyLabel(friendly: boolean): string {
  return friendly ? '较友好' : '一般';
}

function rainLabel(friendly: boolean): string {
  return friendly ? '较友好' : '一般';
}

function foodLabel(friendly: boolean): string {
  return friendly ? '高' : '中';
}

function buildPlanPrompt(cityName: string): string {
  return `请为我规划 ${cityName} 3 天旅行计划，包含每日时间轴、预算估算、住宿建议、适合拍照或放松的点位，以及下雨天备选方案。`;
}

function buildComparePrompt(cityNames: string[]): string {
  return `请比较这几个城市作为下一次旅行目的地的差异：${cityNames.join('、')}。请从预算、适合天数、步行强度、亲子友好度、雨天可玩度和核心亮点做并排对比，并给出推荐结论。`;
}

const CityExplorer: React.FC<CityExplorerProps> = ({ onUsePrompt }) => {
  const INITIAL_VISIBLE_CITY_COUNT = 24;
  const LOAD_MORE_CITY_COUNT = 24;
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
  const [visibleCityCount, setVisibleCityCount] = useState(INITIAL_VISIBLE_CITY_COUNT);

  useEffect(() => {
    const loadFilterOptions = async () => {
      try {
        setIsFilterLoading(true);
        const [regionsData, tagsData] = await Promise.all([apiService.getRegions(), apiService.getTags()]);
        setRegions(regionsData.regions || []);
        setTags(tagsData.tags || []);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : '加载筛选项失败');
      } finally {
        setIsFilterLoading(false);
      }
    };

    loadFilterOptions();
  }, []);

  useEffect(() => {
    const loadCities = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await apiService.getCities({ region: selectedRegion, tags: selectedTags });
        setCities(data.cities || []);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : '加载城市失败');
      } finally {
        setIsLoading(false);
      }
    };

    loadCities();
  }, [selectedRegion, selectedTags]);

  useEffect(() => {
    setVisibleCityCount(INITIAL_VISIBLE_CITY_COUNT);
  }, [selectedRegion, selectedTags, selectedQuickFilters]);

  const filteredCities = useMemo(() => {
    return cities.filter((city) => {
      if (selectedQuickFilters.length === 0) return true;
      const profile = buildCityProfile(city);

      return selectedQuickFilters.every((filterKey) => {
        if (filterKey === 'weekend') return profile.tripDuration === '2-3 天';
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
    [filteredCities, compareCityIds]
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
    return segments.length > 0 ? segments.join(' · ') : '全部城市';
  }, [selectedQuickFilters, selectedRegion, selectedTags]);

  const openCityDetail = async (cityId: string) => {
    try {
      const detail = await apiService.getCityDetail(cityId);
      setActiveCityDetail(detail);
      setIsDetailOpen(true);
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : '加载城市详情失败');
    }
  };

  const toggleQuickFilter = (filterKey: QuickFilterKey) => {
    setSelectedQuickFilters((prev) =>
      prev.includes(filterKey) ? prev.filter((item) => item !== filterKey) : [...prev, filterKey]
    );
  };

  const toggleCompareCity = (cityId: string) => {
    setCompareCityIds((prev) => {
      if (prev.includes(cityId)) return prev.filter((item) => item !== cityId);
      if (prev.length >= 3) return [...prev.slice(1), cityId];
      return [...prev, cityId];
    });
  };

  const toggleFavoriteCity = (cityId: string) => {
    setFavoriteCityIds((prev) =>
      prev.includes(cityId) ? prev.filter((item) => item !== cityId) : [...prev, cityId]
    );
  };

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
          metric: '预算档位',
          values: Object.fromEntries(compareCities.map((city) => [city.id, budgetLabel(buildCityProfile(city).budgetLevel)])),
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
          key: 'rain',
          metric: '雨天友好度',
          values: Object.fromEntries(compareCities.map((city) => [city.id, rainLabel(buildCityProfile(city).rainFriendly)])),
        },
        {
          key: 'family',
          metric: '亲子友好度',
          values: Object.fromEntries(compareCities.map((city) => [city.id, familyLabel(buildCityProfile(city).familyFriendly)])),
        },
        {
          key: 'food',
          metric: '美食密度',
          values: Object.fromEntries(compareCities.map((city) => [city.id, foodLabel(buildCityProfile(city).foodFriendly)])),
        },
        {
          key: 'style',
          metric: '旅行风格',
          values: Object.fromEntries(compareCities.map((city) => [city.id, buildCityProfile(city).styleLabel])),
        },
        {
          key: 'tags',
          metric: '核心标签',
          values: Object.fromEntries(compareCities.map((city) => [city.id, city.tags.slice(0, 4).join(' / ') || '-'])),
        },
        {
          key: 'recommendation',
          metric: '推荐理由',
          values: Object.fromEntries(compareCities.map((city) => [city.id, buildCityProfile(city).recommendation])),
        },
        {
          key: 'decision',
          metric: '适合谁',
          values: Object.fromEntries(
            compareCities.map((city) => {
              const profile = buildCityProfile(city);
              const segments = [];
              if (profile.familyFriendly) segments.push('亲子');
              if (profile.foodFriendly) segments.push('美食党');
              if (profile.walkIntensity === 'low') segments.push('轻松派');
              if (profile.rainFriendly) segments.push('雨天容错高');
              return [city.id, segments.length > 0 ? segments.join(' / ') : '综合体验用户'];
            })
          ),
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
                从“想去哪里”升级成“为什么去、适不适合你、值不值得现在出发”的决策入口。
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
              <div style={{ fontSize: 12, letterSpacing: 1.2, opacity: 0.75, marginBottom: 10 }}>INSPIRATION</div>
              <div style={{ fontSize: 24, fontWeight: 700, lineHeight: 1.3, marginBottom: 12 }}>
                用“出发方式”挑目的地，
                <br />
                比只按地区筛更像真实用户决策。
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <Button onClick={() => onUsePrompt('请推荐适合周末两天出发、预算 1500 内、地铁友好的城市，并说明理由。')}>
                  本周末去哪
                </Button>
                <Button onClick={() => onUsePrompt('请推荐亲子友好、少走路、下雨也不容易废行程的城市。')}>
                  亲子省心版
                </Button>
                <Button onClick={() => onUsePrompt('请推荐适合预算友好、美食优先的旅行城市，并做简短对比。')}>
                  预算美食版
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
              <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>候选城市池</div>
              {favoriteCities.length === 0 ? (
                <div style={{ fontSize: 13, color: '#64748b' }}>先收藏几个城市，这里会变成你的目的地 shortlist。</div>
              ) : (
                favoriteCities.slice(0, 4).map((city) => (
                  <div key={`favorite-${city.id}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 600, color: '#1f2937' }}>{city.name}</div>
                      <div style={{ fontSize: 12, color: '#64748b' }}>{buildCityProfile(city).recommendation}</div>
                    </div>
                    <Button size="small" onClick={() => onUsePrompt(buildPlanPrompt(city.name))}>
                      开始规划
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
            <Button onClick={() => onUsePrompt('请推荐一个适合周末两天出发的城市，并从预算、轻松程度、雨天可玩度解释原因。')}>
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
                  <div style={{ fontSize: 12, color: '#78716c' }}>最多放 3 个城市，快速比较后直接继续规划。</div>
                </div>
                <Space wrap>
                  <Button icon={<SwapOutlined />} onClick={() => onUsePrompt(buildComparePrompt(compareCities.map((city) => city.name)))}>
                    让助手对比
                  </Button>
                  <Button onClick={() => setCompareCityIds([])}>清空</Button>
                </Space>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: `repeat(${compareCities.length}, minmax(0, 1fr))`, gap: 10 }}>
                <Table
                  size="small"
                  pagination={false}
                  rowKey="key"
                  columns={compareColumns}
                  dataSource={compareRows}
                  scroll={{ x: 780 }}
                />
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {compareCities.map((city) => (
                  <Button key={`compare-plan-${city.id}`} size="small" onClick={() => onUsePrompt(buildPlanPrompt(city.name))}>
                    选中“{city.name}”继续规划
                  </Button>
                ))}
              </div>
            </Card>
          )}

          {error && <Alert type="error" showIcon message={error} />}

          {isLoading ? (
            <div style={{ padding: 40, textAlign: 'center' }}>
              <Spin />
            </div>
          ) : filteredCities.length === 0 ? (
            <Empty description="没有匹配的城市，换个筛选试试" />
          ) : (
            <div style={{ display: 'grid', gap: 14 }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 12,
                  flexWrap: 'wrap',
                }}
              >
                <div style={{ fontSize: 13, color: '#475569' }}>
                  {'\u5df2\u663e\u793a ' }
                  <span style={{ fontWeight: 700, color: '#0f172a' }}>{displayedCities.length}</span>
                  {` / ${filteredCities.length} \u4e2a\u57ce\u5e02`}
                </div>
                <Space wrap size={8}>
                  {filteredCities.length > visibleCityCount && (
                    <Button size="small" onClick={() => setVisibleCityCount((count) => count + LOAD_MORE_CITY_COUNT)}>
                      {'\u518d\u770b 24 \u4e2a'}
                    </Button>
                  )}
                  {visibleCityCount > INITIAL_VISIBLE_CITY_COUNT && (
                    <Button size="small" onClick={() => setVisibleCityCount(INITIAL_VISIBLE_CITY_COUNT)}>
                      {'\u6536\u8d77\u5230\u9996\u5c4f'}
                    </Button>
                  )}
                </Space>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
                  gap: 12,
                }}
              >
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
                        </div>

                        <div style={{ fontSize: 12, lineHeight: 1.65, color: '#334155', minHeight: 58 }}>{profile.recommendation}</div>

                        <div style={{ marginTop: -2, minHeight: 24 }}>
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
                          <div>步行: {walkLabel(profile.walkIntensity)}</div>
                          <div>{'\u96e8\u5929: ' }{profile.rainFriendly ? '\u53cb\u597d' : '\u4e00\u822c'}</div>
                          <div>{'\u4eb2\u5b50: ' }{profile.familyFriendly ? '\u53cb\u597d' : '\u4e00\u822c'}</div>
                          <div>{'\u7f8e\u98df: ' }{profile.foodFriendly ? '\u9ad8' : '\u4e2d'}</div>
                        </div>

                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          <Button size="small" onClick={() => openCityDetail(city.id)}>
                            {'\u8be6\u60c5'}
                          </Button>
                          <Button size="small" icon={<RiseOutlined />} onClick={() => toggleCompareCity(city.id)}>
                            {inCompare ? '\u79fb\u51fa\u5bf9\u6bd4' : '\u52a0\u5165\u5bf9\u6bd4'}
                          </Button>
                          <Button size="small" type="primary" onClick={() => onUsePrompt(buildPlanPrompt(city.name))}>
                            {'\u89c4\u5212'}
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
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <Tag color="blue">{budgetLabel(activeDetailProfile.budgetLevel)}</Tag>
                  <Tag color="green">{activeDetailProfile.tripDuration}</Tag>
                  <Tag color="purple">{activeDetailProfile.styleLabel}</Tag>
                  <Tag color="cyan">{walkLabel(activeDetailProfile.walkIntensity)}</Tag>
                </div>
                <div style={{ fontSize: 13, color: '#475569' }}>{activeDetailProfile.recommendation}</div>
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
                <div style={{ fontSize: 18, fontWeight: 700, color: '#111827' }}>
                  {activeCityDetail.best_seasons.slice(0, 2).join(' / ') || '四季皆可'}
                </div>
              </Card>
            </div>

            <Card size="small" title="怎么玩更顺">
              <div style={{ display: 'grid', gap: 8, fontSize: 13, color: '#475569' }}>
                <div>推荐节奏：{activeDetailProfile.tripDuration}，先把核心城区放在前两天，减少跨区折返。</div>
                <div>雨天策略：{activeDetailProfile.rainFriendly ? '可以保留大部分安排，优先室内点位。' : '建议预留 1-2 个室内备选点。'}</div>
                <div>体力管理：{walkLabel(activeDetailProfile.walkIntensity)}，建议把高密度打卡集中在一天内。</div>
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
                    </div>
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
};

export default CityExplorer;
