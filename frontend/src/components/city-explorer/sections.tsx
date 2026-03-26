'use client';

import React from 'react';
import { Alert, Button, Card, Drawer, Empty, Select, Space, Spin, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  CompassOutlined,
  EnvironmentOutlined,
  HeartFilled,
  HeartOutlined,
  RiseOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import type { CityDetail, CitySummary } from '@/types';
import {
  buildCityProfile,
  budgetLabel,
  boolLabel,
  buildComparePrompt,
  buildPlanPrompt,
  CompareTableRow,
  CURATED_PROMPTS,
  DerivedCityProfile,
  foodLabel,
  QUICK_FILTERS,
  QuickFilterKey,
  seasonLabel,
  walkLabel,
} from './shared';

interface CityExplorerHeroProps {
  compareCities: CitySummary[];
  favoriteCities: CitySummary[];
  onUsePrompt: (prompt: string) => void;
  summaryText: string;
}

export const CityExplorerHero: React.FC<CityExplorerHeroProps> = ({
  compareCities,
  favoriteCities,
  onUsePrompt,
  summaryText,
}) => (
  <div
    style={{
      display: 'grid',
      gap: 16,
      position: 'relative',
      zIndex: 1,
    }}
  >
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
      <div style={{ display: 'flex', gap: 12 }}>
        <div
          style={{
            width: 42,
            height: 42,
            borderRadius: 14,
            display: 'grid',
            placeItems: 'center',
            background: 'linear-gradient(135deg, #0c4a6e 0%, #0f766e 100%)',
            boxShadow: '0 10px 24px rgba(2, 132, 199, 0.35)',
          }}
        >
          <CompassOutlined style={{ color: '#f0f9ff', fontSize: 20 }} />
        </div>
        <div>
          <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: 0.2, color: '#0f172a', marginBottom: 4 }}>城市探索</div>
          <div style={{ fontSize: 13, color: '#475569', maxWidth: 760, lineHeight: 1.75 }}>
            当前只展示真实策展城市库，详情中的景点名称、区位和备注都来自人工整理，不再混入模板化生成城市。
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <div
          style={{
            display: 'grid',
            gap: 2,
            minWidth: 190,
            maxWidth: 260,
            padding: '8px 12px',
            borderRadius: 12,
            border: '1px solid #bfdbfe',
            background: 'linear-gradient(180deg, #eff6ff 0%, #f8fbff 100%)',
          }}
        >
          <span style={{ fontSize: 11, color: '#1d4ed8', fontWeight: 700 }}>当前视图</span>
          <span style={{ fontSize: 12, color: '#334155', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {summaryText}
          </span>
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '8px 12px',
            borderRadius: 12,
            border: '1px solid rgba(245, 158, 11, 0.35)',
            background: compareCities.length > 0 ? 'linear-gradient(180deg, #fff7ed 0%, #fffbeb 100%)' : '#ffffff',
            color: compareCities.length > 0 ? '#92400e' : '#64748b',
            fontSize: 13,
            fontWeight: 700,
          }}
        >
          <SwapOutlined />
          对比池 {compareCities.length}/3
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '8px 12px',
            borderRadius: 12,
            border: '1px solid rgba(239, 68, 68, 0.3)',
            background: favoriteCities.length > 0 ? 'linear-gradient(180deg, #fff1f2 0%, #fff7f7 100%)' : '#ffffff',
            color: favoriteCities.length > 0 ? '#be123c' : '#64748b',
            fontSize: 13,
            fontWeight: 700,
          }}
        >
          <HeartFilled style={{ color: favoriteCities.length > 0 ? '#e11d48' : '#94a3b8' }} />
          收藏 {favoriteCities.length}
        </div>
      </div>
    </div>

    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: 16,
        alignItems: 'stretch',
      }}
    >
      <div
        style={{
          borderRadius: 20,
          padding: 20,
          background: 'linear-gradient(180deg, rgba(255,255,255,0.98) 0%, #f8fbff 100%)',
          border: '1px solid #dbe4ee',
          boxShadow: '0 14px 30px rgba(15, 23, 42, 0.08)',
          color: '#0f172a',
          display: 'grid',
          gap: 16,
          alignContent: 'start',
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            width: 'fit-content',
            padding: '6px 10px',
            borderRadius: 999,
            border: '1px solid #dbeafe',
            background: '#eff6ff',
            color: '#1d4ed8',
            fontSize: 12,
            fontWeight: 700,
          }}
        >
          <CompassOutlined />
          灵感起点
        </div>
        <div style={{ display: 'grid', gap: 8 }}>
          <div style={{ fontSize: 24, fontWeight: 800, lineHeight: 1.2, color: '#0f172a', maxWidth: 520 }}>
            从场景出发，找到对的城市
          </div>
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: 10,
          }}
        >
          {CURATED_PROMPTS.map((item) => (
            <Button
              key={item.label}
              block
              style={{
                height: '100%',
                minHeight: 92,
                padding: '14px 16px',
                borderRadius: 16,
                border: `1px solid ${item.borderColor}`,
                background: item.background,
                color: '#0f172a',
                boxShadow: 'none',
                whiteSpace: 'normal',
              }}
              onClick={() => onUsePrompt(item.prompt)}
            >
              <div style={{ display: 'grid', gap: 6, textAlign: 'left' }}>
                <span style={{ fontSize: 16, fontWeight: 700 }}>{item.label}</span>
                <span style={{ fontSize: 12, lineHeight: 1.65, color: '#64748b', fontWeight: 500 }}>{item.hint}</span>
              </div>
            </Button>
          ))}
        </div>
      </div>

      <div
        style={{
          borderRadius: 20,
          padding: 18,
          background: 'linear-gradient(180deg, rgba(255,255,255,0.96) 0%, #f8fafc 100%)',
          border: '1px solid #dbe4ee',
          boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.8)',
          display: 'grid',
          gap: 10,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a' }}>目的地 shortlist</div>
          <Tag color="blue" style={{ marginInlineEnd: 0, borderRadius: 999, paddingInline: 10 }}>
            {favoriteCities.length}/4
          </Tag>
        </div>
        {favoriteCities.length === 0 ? (
          <div
            style={{
              minHeight: 108,
              borderRadius: 14,
              border: '1px dashed #cbd5e1',
              background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
              display: 'grid',
              placeItems: 'center',
              fontSize: 13,
              color: '#64748b',
              textAlign: 'center',
              padding: 12,
            }}
          >
            先收藏几个城市，这里会变成你的候选池。
          </div>
        ) : (
          favoriteCities.slice(0, 4).map((city) => (
            <div
              key={`favorite-${city.id}`}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                gap: 12,
                border: '1px solid #e2e8f0',
                borderRadius: 12,
                padding: '10px 12px',
                background: '#ffffff',
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 700, color: '#1f2937' }}>{city.name}</div>
                <div
                  style={{
                    fontSize: 12,
                    color: '#64748b',
                    lineHeight: 1.55,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {buildCityProfile(city).recommendation}
                </div>
              </div>
              <Button
                size="small"
                type="primary"
                style={{ borderRadius: 999, border: 'none', background: 'linear-gradient(135deg, #0284c7 0%, #0f766e 100%)' }}
                onClick={() => onUsePrompt(buildPlanPrompt(city.name))}
              >
                继续规划
              </Button>
            </div>
          ))
        )}
      </div>
    </div>
  </div>
);

interface CityExplorerFilterBarProps {
  isFilterLoading: boolean;
  onUsePrompt: (prompt: string) => void;
  regions: string[];
  selectedQuickFilters: QuickFilterKey[];
  selectedRegion: string | undefined;
  selectedTags: string[];
  tags: string[];
  toggleQuickFilter: (filterKey: QuickFilterKey) => void;
  setSelectedRegion: (value: string | undefined) => void;
  setSelectedTags: (value: string[]) => void;
}

export const CityExplorerFilterBar: React.FC<CityExplorerFilterBarProps> = ({
  isFilterLoading,
  onUsePrompt,
  regions,
  selectedQuickFilters,
  selectedRegion,
  selectedTags,
  tags,
  toggleQuickFilter,
  setSelectedRegion,
  setSelectedTags,
}) => (
  <div
    style={{
      border: '1px solid #dbe4ee',
      borderRadius: 16,
      background: 'linear-gradient(180deg, rgba(255,255,255,0.9) 0%, #f8fbff 100%)',
      padding: 12,
      display: 'grid',
      gap: 10,
    }}
  >
    <Space wrap size={[10, 10]}>
      <Select
        allowClear
        loading={isFilterLoading}
        placeholder="按地区筛选"
        style={{ width: 190 }}
        value={selectedRegion}
        onChange={(value) => setSelectedRegion(value)}
        options={regions.map((item) => ({ label: item, value: item }))}
      />
      <Select
        mode="multiple"
        loading={isFilterLoading}
        placeholder="按标签筛选"
        style={{ width: 340, maxWidth: '100%' }}
        value={selectedTags}
        onChange={(value) => setSelectedTags(value)}
        options={tags.map((item) => ({ label: item, value: item }))}
      />
      <Button
        type="primary"
        style={{
          borderRadius: 999,
          border: 'none',
          background: 'linear-gradient(135deg, #0369a1 0%, #0f766e 100%)',
          boxShadow: '0 8px 20px rgba(14, 116, 144, 0.28)',
        }}
        onClick={() =>
          onUsePrompt('请帮我从当前真实城市库里选一个适合第一次出发的目的地，并从预算、步行强度、雨天备选和核心景点真实性解释原因。')
        }
      >
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
                    borderRadius: 999,
                    fontWeight: 700,
                    background: 'linear-gradient(135deg, #0284c7 0%, #0f766e 100%)',
                    borderColor: 'transparent',
                    boxShadow: '0 8px 16px rgba(2, 132, 199, 0.24)',
                  }
                : {
                    borderRadius: 999,
                    borderColor: '#cbd5e1',
                    color: '#334155',
                    background: '#ffffff',
                  }
            }
          >
            {filter.label}
          </Button>
        );
      })}
    </div>
  </div>
);

interface CityExplorerComparePanelProps {
  compareCities: CitySummary[];
  onClearCompare: () => void;
  onUsePrompt: (prompt: string) => void;
}

export const CityExplorerComparePanel: React.FC<CityExplorerComparePanelProps> = ({
  compareCities,
  onClearCompare,
  onUsePrompt,
}) => {
  if (compareCities.length === 0) return null;

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

  const compareRows: CompareTableRow[] = [
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
  ];

  return (
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
          <Button onClick={onClearCompare}>清空</Button>
        </Space>
      </div>
      <Table size="small" pagination={false} rowKey="key" columns={compareColumns} dataSource={compareRows} scroll={{ x: 780 }} />
    </Card>
  );
};

interface CityExplorerGridProps {
  compareCityIds: string[];
  displayedCities: CitySummary[];
  error: string | null;
  favoriteCityIds: string[];
  filteredCities: CitySummary[];
  initialVisibleCityCount: number;
  isLoading: boolean;
  loadMoreCityCount: number;
  onOpenCityDetail: (cityId: string) => void;
  onToggleCompareCity: (cityId: string) => void;
  onToggleFavoriteCity: (cityId: string) => void;
  onUsePrompt: (prompt: string) => void;
  setVisibleCityCount: React.Dispatch<React.SetStateAction<number>>;
  visibleCityCount: number;
}

export const CityExplorerGrid: React.FC<CityExplorerGridProps> = ({
  compareCityIds,
  displayedCities,
  error,
  favoriteCityIds,
  filteredCities,
  initialVisibleCityCount,
  isLoading,
  loadMoreCityCount,
  onOpenCityDetail,
  onToggleCompareCity,
  onToggleFavoriteCity,
  onUsePrompt,
  setVisibleCityCount,
  visibleCityCount,
}) => {
  if (error) return <Alert type="error" showIcon message={error} />;

  if (isLoading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin />
      </div>
    );
  }

  if (filteredCities.length === 0) {
    return <Empty description="没有匹配的城市，换个筛选试试。" />;
  }

  return (
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
                    onClick={() => onToggleFavoriteCity(city.id)}
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
                  <Button size="small" onClick={() => onOpenCityDetail(city.id)}>
                    详情
                  </Button>
                  <Button size="small" icon={<RiseOutlined />} onClick={() => onToggleCompareCity(city.id)}>
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
  );
};

interface CityExplorerDetailDrawerProps {
  activeCityDetail: CityDetail | null;
  activeDetailProfile: DerivedCityProfile | null;
  favoriteCities: CitySummary[];
  isDetailOpen: boolean;
  onClose: () => void;
  onUsePrompt: (prompt: string) => void;
}

export const CityExplorerDetailDrawer: React.FC<CityExplorerDetailDrawerProps> = ({
  activeCityDetail,
  activeDetailProfile,
  favoriteCities,
  isDetailOpen,
  onClose,
  onUsePrompt,
}) => (
  <Drawer
    title={
      <span>
        <EnvironmentOutlined style={{ marginRight: 8 }} />
        {activeCityDetail?.name || '城市详情'}
      </span>
    }
    open={isDetailOpen}
    onClose={onClose}
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
);
