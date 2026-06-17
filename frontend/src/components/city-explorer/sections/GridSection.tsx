// 'use client' —— 客户端组件声明
'use client';

import React from 'react';
// Alert —— 警告提示框，Empty —— 空状态占位，Spin —— 加载中旋转图标
import { Alert, Empty, Spin } from 'antd';
// CitySummary —— 城市摘要数据类型
import type { CitySummary } from '@/types';
// CityGridCard —— 单个城市卡片组件
import { CityGridCard } from './grid/CityGridCard';
// GridSummaryBar —— 网格上方的摘要栏（显示城市数量、加载更多按钮）
import { GridSummaryBar } from './grid/GridSummaryBar';

// CityExplorerGridProps —— 城市网格的属性类型
interface CityExplorerGridProps {
  compareCityIds: string[];              // 对比池中的城市 ID 列表
  displayedCities: CitySummary[];        // 当前展示的城市列表（分页后）
  error: string | null;                  // 错误信息，有值时显示错误提示
  favoriteCityIds: string[];             // 候选池中的城市 ID 列表
  filteredCities: CitySummary[];         // 筛选后的全部城市列表（未分页）
  initialVisibleCityCount: number;       // 初始显示的城市数量
  isLoading: boolean;                    // 是否正在加载
  loadMoreCityCount: number;             // 每次加载更多的城市数量
  onOpenCityDetail: (cityId: string) => void;      // 打开城市详情的回调
  onToggleCompareCity: (cityId: string) => void;   // 切换城市对比状态的回调
  onToggleFavoriteCity: (cityId: string) => void;  // 切换城市收藏状态的回调
  onUsePrompt: (prompt: string) => void;           // 使用 AI 提示词的回调
  setVisibleCityCount: React.Dispatch<React.SetStateAction<number>>; // 设置可见城市数量的函数
  visibleCityCount: number;              // 当前可见的城市数量
}

// 【核心】CityExplorerGrid —— 城市卡片网格组件
// 功能：以网格形式展示城市卡片，支持分页加载更多
// 应用场景：用户通过筛选栏筛选后，符合条件的城市以卡片形式排列在这里
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
  // 错误状态：显示红色警告框
  if (error) return <Alert type="error" showIcon message={error} />;

  // 加载状态：显示旋转加载图标
  if (isLoading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin />
      </div>
    );
  }

  // 空状态：没有符合筛选条件的城市
  if (filteredCities.length === 0) {
    return <Empty description="没有找到符合当前筛选条件的城市" />;
  }

  // 正常状态：显示摘要栏 + 城市卡片网格
  return (
    <div style={{ display: 'grid', gap: 14 }}>
      {/* 摘要栏：显示城市数量、加载更多/收起按钮 */}
      <GridSummaryBar
        displayedCityCount={displayedCities.length}
        filteredCityCount={filteredCities.length}
        initialVisibleCityCount={initialVisibleCityCount}
        loadMoreCityCount={loadMoreCityCount}
        onLoadMore={() => setVisibleCityCount((count) => count + loadMoreCityCount)} // 加载更多：增加可见数量
        onReset={() => setVisibleCityCount(initialVisibleCityCount)} // 收起：恢复初始数量
        visibleCityCount={visibleCityCount}
      />

      {/* 城市卡片网格 */}
      {/* gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))' —— 自适应填充列 */}
      {/* auto-fill 会自动创建尽可能多的列，每列最小 260px */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
        {/* 遍历当前展示的城市列表，为每个城市生成一张卡片 */}
        {displayedCities.map((city) => (
          <CityGridCard
            key={city.id}
            city={city}
            favorite={favoriteCityIds.includes(city.id)}   // 该城市是否已收藏
            inCompare={compareCityIds.includes(city.id)}   // 该城市是否在对比池中
            onOpenCityDetail={onOpenCityDetail}
            onToggleCompareCity={onToggleCompareCity}
            onToggleFavoriteCity={onToggleFavoriteCity}
            onUsePrompt={onUsePrompt}
          />
        ))}
      </div>
    </div>
  );
};
