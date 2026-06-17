// 景点候选池/收藏标签页组件
// 应用场景：用户在"景点决策卡"中收藏的景点会汇总到这里
//   可以查看所有收藏的景点，也可以点击"用候选池重做方案"让 AI 基于这些景点重新规划行程

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Button, Card, Tag } from 'antd';
import { HeartFilled } from '@ant-design/icons';
import type { SpotDecisionInfo } from '@/utils/travelPlan';

// ToolkitFavoritesTabProps 收藏标签页接收的参数
interface ToolkitFavoritesTabProps {
  favoriteSpotList: SpotDecisionInfo[];                    // 收藏的景点列表
  canBuildFromFavorites: boolean;                          // 是否可以用候选池重做方案
  onBuildFromFavorites: () => void;                        // 用候选池重做方案的回调
  onToggleFavoriteSpot: (spot: SpotDecisionInfo) => void;  // 切换景点收藏状态的回调
}

export const ToolkitFavoritesTab: React.FC<ToolkitFavoritesTabProps> = ({
  favoriteSpotList,
  canBuildFromFavorites,
  onBuildFromFavorites,
  onToggleFavoriteSpot,
}) => (
  <div style={{ display: 'grid', gap: 10 }}>
    {/* 顶部：候选景点数量标签 + 重做方案按钮 */}
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      <Tag color={favoriteSpotList.length > 0 ? 'gold' : 'default'}>候选景点 {favoriteSpotList.length}</Tag>
      {favoriteSpotList.length > 0 && canBuildFromFavorites && (
        <Button size="small" onClick={onBuildFromFavorites}>
          用候选池重做方案
        </Button>
      )}
    </div>
    {/* 空状态提示 或 收藏景点列表 */}
    {favoriteSpotList.length === 0 ? (
      <div style={{ fontSize: 13, color: '#64748b' }}>先在"景点决策卡"里收藏你想保留的点位，这里会自动汇总。</div>
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
