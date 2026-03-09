'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Drawer, Empty, Select, Space, Spin, Tag } from 'antd';
import { CompassOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { apiService } from '@/services/api';
import type { CityDetail, CitySummary } from '@/types';

interface CityExplorerProps {
  onUsePrompt: (prompt: string) => void;
}

const CityExplorer: React.FC<CityExplorerProps> = ({ onUsePrompt }) => {
  const [regions, setRegions] = useState<string[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<string | undefined>(undefined);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [cities, setCities] = useState<CitySummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isFilterLoading, setIsFilterLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeCityDetail, setActiveCityDetail] = useState<CityDetail | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  useEffect(() => {
    const loadFilterOptions = async () => {
      try {
        setIsFilterLoading(true);
        const [regionsData, tagsData] = await Promise.all([apiService.getRegions(), apiService.getTags()]);
        setRegions(regionsData.regions || []);
        setTags(tagsData.tags || []);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : '加载筛选条件失败');
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

  const summaryText = useMemo(() => {
    if (selectedRegion && selectedTags.length > 0) return `${selectedRegion} · ${selectedTags.join(' / ')}`;
    if (selectedRegion) return selectedRegion;
    if (selectedTags.length > 0) return selectedTags.join(' / ');
    return '全部城市';
  }, [selectedRegion, selectedTags]);

  const openCityDetail = async (cityId: string) => {
    try {
      const detail = await apiService.getCityDetail(cityId);
      setActiveCityDetail(detail);
      setIsDetailOpen(true);
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : '加载城市详情失败');
    }
  };

  return (
    <div style={{ margin: '0 16px 16px' }}>
      <Card
        style={{
          borderRadius: 16,
          border: '1px solid rgba(37, 99, 235, 0.15)',
          background: 'linear-gradient(140deg, #ffffff 0%, #f0f9ff 100%)',
        }}
        styles={{ body: { padding: 16 } }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#1e3a8a' }}>
            <CompassOutlined style={{ marginRight: 8 }} />
            城市探索
          </div>
          <Tag color="blue">{summaryText}</Tag>
        </div>

        <Space wrap size={10} style={{ marginBottom: 12 }}>
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
            style={{ width: 300 }}
            value={selectedTags}
            onChange={(value) => setSelectedTags(value)}
            options={tags.map((item) => ({ label: item, value: item }))}
          />
          <Button onClick={() => onUsePrompt('请推荐一个适合周末两天出行的城市并给出理由')} type="default">
            让助手帮我选
          </Button>
        </Space>

        {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} />}
        {isLoading ? (
          <div style={{ padding: 28, textAlign: 'center' }}>
            <Spin />
          </div>
        ) : cities.length === 0 ? (
          <Empty description="没有匹配的城市" />
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
              gap: 12,
            }}
          >
            {cities.map((city) => (
              <Card key={city.id} size="small" style={{ borderRadius: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: 15, fontWeight: 600 }}>{city.name}</div>
                  <Tag color="geekblue">{city.region}</Tag>
                </div>
                <div style={{ marginTop: 8, marginBottom: 10, minHeight: 26 }}>
                  {city.tags.map((tag) => (
                    <Tag key={`${city.id}-${tag}`} style={{ marginBottom: 4 }}>
                      {tag}
                    </Tag>
                  ))}
                </div>
                <Space>
                  <Button size="small" onClick={() => openCityDetail(city.id)}>
                    查看详情
                  </Button>
                  <Button
                    size="small"
                    type="primary"
                    onClick={() => onUsePrompt(`请为我规划 ${city.name} 3 天旅行计划，包含景点、预算和住宿建议`)}
                  >
                    一键发起规划
                  </Button>
                </Space>
              </Card>
            ))}
          </div>
        )}
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
        {activeCityDetail && (
          <div style={{ display: 'grid', gap: 12 }}>
            <Card size="small">
              <div style={{ color: '#334155' }}>{activeCityDetail.description}</div>
            </Card>
            <Card size="small" title="旅行信息">
              <div>人均预算/天: ¥{activeCityDetail.avg_budget_per_day}</div>
              <div style={{ marginTop: 8 }}>
                最佳季节:
                {activeCityDetail.best_seasons.map((season) => (
                  <Tag key={season} color="green" style={{ marginLeft: 6 }}>
                    {season}
                  </Tag>
                ))}
              </div>
            </Card>
            <Card size="small" title="推荐景点">
              <div style={{ display: 'grid', gap: 8 }}>
                {activeCityDetail.attractions.map((attraction) => (
                  <div
                    key={attraction.name}
                    style={{
                      border: '1px solid #e2e8f0',
                      borderRadius: 10,
                      padding: '8px 10px',
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{attraction.name}</div>
                    <div style={{ fontSize: 12, color: '#64748b', marginTop: 3 }}>
                      {attraction.type} · 建议时长 {attraction.duration} · 门票 ¥{attraction.ticket}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default CityExplorer;
