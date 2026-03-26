'use client';

import React from 'react';
import { Button, Card, Tag } from 'antd';
import { HeartFilled } from '@ant-design/icons';
import type { SpotDecisionInfo } from '@/utils/travelPlan';

interface ToolkitFavoritesTabProps {
  favoriteSpotList: SpotDecisionInfo[];
  canBuildFromFavorites: boolean;
  onBuildFromFavorites: () => void;
  onToggleFavoriteSpot: (spot: SpotDecisionInfo) => void;
}

export const ToolkitFavoritesTab: React.FC<ToolkitFavoritesTabProps> = ({
  favoriteSpotList,
  canBuildFromFavorites,
  onBuildFromFavorites,
  onToggleFavoriteSpot,
}) => (
  <div style={{ display: 'grid', gap: 10 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      <Tag color={favoriteSpotList.length > 0 ? 'gold' : 'default'}>候选景点 {favoriteSpotList.length}</Tag>
      {favoriteSpotList.length > 0 && canBuildFromFavorites && (
        <Button size="small" onClick={onBuildFromFavorites}>
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
