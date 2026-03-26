'use client';

import React from 'react';
import { Button } from 'antd';
import { HeartFilled, HeartOutlined } from '@ant-design/icons';
import type { SpotDecisionInfo } from '@/utils/travelPlan';

interface ItinerarySpotDecisionGridProps {
  dayKey: string;
  decisionInfos: SpotDecisionInfo[];
  favoriteSpots: Record<string, SpotDecisionInfo>;
  onToggleFavoriteSpot: (spot: SpotDecisionInfo) => void;
}

export const ItinerarySpotDecisionGrid: React.FC<ItinerarySpotDecisionGridProps> = ({
  dayKey,
  decisionInfos,
  favoriteSpots,
  onToggleFavoriteSpot,
}) => {
  if (decisionInfos.length === 0) return null;

  return (
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
                  aria-label={active ? `取消收藏 ${spot.name}` : `收藏 ${spot.name}`}
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
  );
};
