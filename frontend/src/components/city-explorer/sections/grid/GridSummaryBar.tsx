// 'use client' —— 客户端组件声明
'use client';

import React from 'react';
// Button —— 按钮，Space —— 间距容器
import { Button, Space } from 'antd';

// GridSummaryBarProps —— 网格摘要栏的属性类型
interface GridSummaryBarProps {
  displayedCityCount: number;   // 当前展示的城市数量
  filteredCityCount: number;    // 筛选后的总城市数量
  initialVisibleCityCount: number; // 初始显示数量（用于"收起"时恢复）
  loadMoreCityCount: number;    // 每次加载更多的数量
  onLoadMore: () => void;       // 加载更多的回调
  onReset: () => void;          // 收起列表的回调
  visibleCityCount: number;     // 当前可见的城市数量
}

// GridSummaryBar —— 网格上方的摘要栏
// 功能：显示当前展示的城市数量，提供"加载更多"和"收起"按钮
// 应用场景：筛选后有30个城市，但默认只展示12个，
//           用户点击"再看6个"可以加载更多，点击"收起列表"恢复初始数量
export const GridSummaryBar: React.FC<GridSummaryBarProps> = ({
  displayedCityCount,
  filteredCityCount,
  initialVisibleCityCount,
  loadMoreCityCount,
  onLoadMore,
  onReset,
  visibleCityCount,
}) => (
  // flex 布局：左右两端对齐
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
    {/* 左侧：城市数量统计 */}
    <div style={{ fontSize: 13, color: '#475569' }}>
      已展示 <span style={{ fontWeight: 700, color: '#0f172a' }}>{displayedCityCount}</span> / {filteredCityCount} 座城市
    </div>
    {/* 右侧：操作按钮 */}
    <Space wrap size={8}>
      {/* "加载更多"按钮：只在还有更多城市可加载时显示 */}
      {/* 条件渲染：{condition && <Component />} 表示条件为真时才渲染该组件 */}
      {filteredCityCount > visibleCityCount && (
        <Button size="small" onClick={onLoadMore}>
          再看 {loadMoreCityCount} 个
        </Button>
      )}
      {/* "收起"按钮：只在已加载超过初始数量时显示 */}
      {visibleCityCount > initialVisibleCityCount && (
        <Button size="small" onClick={onReset}>
          收起列表
        </Button>
      )}
    </Space>
  </div>
);
