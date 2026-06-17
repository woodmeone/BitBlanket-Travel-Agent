// 景点决策卡网格组件
// 应用场景：在每日行程卡片中，展示当天所有景点的决策信息
//   每个景点卡片包含：名称、停留时长、最佳到达时间、适合人群、花费感知
//   用户可以点击爱心按钮收藏/取消收藏景点

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Button } from 'antd';
import { HeartFilled, HeartOutlined } from '@ant-design/icons';
import type { SpotDecisionInfo } from '@/utils/travelPlan';

// ItinerarySpotDecisionGridProps 景点决策网格接收的参数
interface ItinerarySpotDecisionGridProps {
  dayKey: string;                                        // 当天的唯一标识键
  decisionInfos: SpotDecisionInfo[];                     // 景点决策信息列表
  favoriteSpots: Record<string, SpotDecisionInfo>;       // 已收藏的景点（键是景点名）
  onToggleFavoriteSpot: (spot: SpotDecisionInfo) => void; // 切换景点收藏状态的回调
}

export const ItinerarySpotDecisionGrid: React.FC<ItinerarySpotDecisionGridProps> = ({
  dayKey,
  decisionInfos,
  favoriteSpots,
  onToggleFavoriteSpot,
}) => {
  if (decisionInfos.length === 0) return null;  // 没有景点时不渲染

  return (
    <div style={{ display: 'grid', gap: 8 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: '#1f2937' }}>景点决策卡</div>
      {/* 网格布局，每个卡片最小宽度180px，自动换行 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 10,
        }}
      >
        {decisionInfos.map((spot) => {
          const active = Boolean(favoriteSpots[spot.name]);  // 该景点是否已收藏
          return (
            <div
              key={`${dayKey}-${spot.name}`}
              style={{
                border: '1px solid #dbe4ee',
                borderRadius: 12,
                padding: 12,
                // 已收藏的景点有橙色渐变背景，未收藏为白色
                background: active ? 'linear-gradient(135deg, #fff7ed 0%, #ffffff 100%)' : '#ffffff',
              }}
            >
              {/* 景点名称和收藏按钮 */}
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
              {/* 景点详细信息 */}
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
