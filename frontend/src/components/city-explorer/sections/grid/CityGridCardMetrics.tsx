// 'use client' —— 客户端组件声明
'use client';

import React from 'react';
// CitySummary —— 城市摘要数据类型
import type { CitySummary } from '@/types';
// boolLabel —— 布尔值转标签，foodLabel —— 美食友好度标签，DerivedCityProfile —— 城市画像类型，walkLabel —— 步行强度标签
import { boolLabel, foodLabel, type DerivedCityProfile, walkLabel } from '../../shared';

// CityGridCardMetricsProps —— 指标展示区的属性类型
interface CityGridCardMetricsProps {
  city: CitySummary;                // 城市数据
  profile: DerivedCityProfile;      // 城市画像（由 buildCityProfile 生成）
}

// CityGridCardMetrics —— 城市卡片中的指标展示区
// 功能：以2列网格展示城市的关键指标数据
// 应用场景：用户快速了解一个城市的预算、步行强度、雨天适配等关键信息
export const CityGridCardMetrics: React.FC<CityGridCardMetricsProps> = ({ city, profile }) => (
  // 2列网格布局，浅灰背景 + 圆角，形成独立的指标区域
  <div
    style={{
      display: 'grid',
      gridTemplateColumns: '1fr 1fr', // 两列等宽
      gap: 6,
      fontSize: 12,
      color: '#475569',
      background: '#f8fafc',
      borderRadius: 10,
      padding: 8,
    }}
  >
    {/* 人均每日预算 */}
    <div>人均预算：¥{city.avg_budget_per_day}</div>
    {/* 步行强度：如"少走路"、"步行适中" */}
    <div>步行强度：{walkLabel(profile.walkIntensity)}</div>
    {/* 雨天适配：如"友好"、"一般" */}
    <div>雨天适配：{boolLabel(profile.rainFriendly)}</div>
    {/* 亲子友好：如"友好"、"一般" */}
    <div>亲子友好：{boolLabel(profile.familyFriendly)}</div>
    {/* 美食指数：如"高"、"中" */}
    <div>美食指数：{foodLabel(profile.foodFriendly)}</div>
    {/* 数据来源：如"人工策展" */}
    <div>数据来源：{city.data_source}</div>
  </div>
);
