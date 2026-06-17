// 'use client' —— 客户端组件声明
'use client';

import React from 'react';
// Button —— 按钮，Card —— 卡片容器，Tag —— 标签
import { Button, Card, Tag } from 'antd';
// HeartFilled —— 实心爱心图标（已收藏），HeartOutlined —— 空心爱心图标（未收藏）
import { HeartFilled, HeartOutlined } from '@ant-design/icons';
// CitySummary —— 城市摘要数据类型
import type { CitySummary } from '@/types';
// buildCityProfile —— 构建城市画像，budgetLabel —— 预算标签，buildPlanPrompt —— 生成规划提示词，seasonLabel —— 季节标签
import { buildCityProfile, budgetLabel, buildPlanPrompt, seasonLabel } from '../../shared';
// CityGridCardActions —— 卡片底部操作按钮组
import { CityGridCardActions } from './CityGridCardActions';
// CityGridCardMetrics —— 卡片中的指标展示区
import { CityGridCardMetrics } from './CityGridCardMetrics';

// CityGridCardProps —— 城市卡片的属性类型
interface CityGridCardProps {
  city: CitySummary;                             // 城市数据
  favorite: boolean;                             // 是否已收藏
  inCompare: boolean;                            // 是否在对比池中
  onOpenCityDetail: (cityId: string) => void;    // 打开详情的回调
  onToggleCompareCity: (cityId: string) => void; // 切换对比状态的回调
  onToggleFavoriteCity: (cityId: string) => void; // 切换收藏状态的回调
  onUsePrompt: (prompt: string) => void;         // 使用 AI 提示词的回调
}

// 【核心】CityGridCard —— 城市卡片组件
// 功能：在网格中展示单个城市的信息，包括名称、地区、标签、推荐语、指标和操作按钮
// 应用场景：用户浏览城市列表时，每张卡片代表一个城市，
//           可以收藏、加入对比、查看详情或直接规划旅行
export const CityGridCard: React.FC<CityGridCardProps> = ({
  city,
  favorite,
  inCompare,
  onOpenCityDetail,
  onToggleCompareCity,
  onToggleFavoriteCity,
  onUsePrompt,
}) => {
  // 构建城市画像，获取预算等级、推荐语等衍生信息
  const profile = buildCityProfile(city);

  return (
    // Card 是 Ant Design 的卡片容器组件
    // size="small" 使用紧凑尺寸
    // 在对比池中的城市会有橙色边框和暖色背景，视觉上更醒目
    <Card
      size="small"
      style={{
        borderRadius: 16,
        border: inCompare ? '1px solid #f59e0b' : '1px solid #e2e8f0',
        background: inCompare
          ? 'linear-gradient(180deg, #fffaf0 0%, #ffffff 100%)'  // 对比中：暖色渐变
          : 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)', // 默认：白色渐变
      }}
      styles={{ body: { padding: 12 } }}
    >
      <div style={{ display: 'grid', gap: 8 }}>
        {/* 第一行：城市名称 + 地区 + 收藏按钮 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
          <div>
            <div style={{ fontSize: 17, fontWeight: 700, color: '#0f172a' }}>{city.name}</div>
            <div style={{ fontSize: 12, color: '#64748b' }}>{city.region}</div>
          </div>
          {/* 收藏按钮：已收藏显示实心红心，未收藏显示空心爱心 */}
          <Button
            type="text" // text 类型按钮没有背景和边框
            size="small"
            aria-label={favorite ? `取消收藏 ${city.name}` : `收藏 ${city.name}`}
            icon={favorite ? <HeartFilled style={{ color: '#ef4444' }} /> : <HeartOutlined />}
            onClick={() => onToggleFavoriteCity(city.id)} // 点击切换收藏状态
          />
        </div>

        {/* 第二行：标签组（预算、天数、气质、季节） */}
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          <Tag color="blue" style={{ marginInlineEnd: 0 }}>
            {budgetLabel(profile.budgetLevel)} {/* 如"预算友好" */}
          </Tag>
          <Tag color="green" style={{ marginInlineEnd: 0 }}>
            {profile.tripDuration} {/* 如"2-3天" */}
          </Tag>
          <Tag color="purple" style={{ marginInlineEnd: 0 }}>
            {profile.styleLabel} {/* 如"综合体验" */}
          </Tag>
          <Tag color="cyan" style={{ marginInlineEnd: 0 }}>
            {seasonLabel(city.best_seasons)} {/* 如"春 / 秋" */}
          </Tag>
        </div>

        {/* 第三行：推荐语 */}
        <div style={{ fontSize: 12, lineHeight: 1.65, color: '#334155', minHeight: 58 }}>{profile.recommendation}</div>

        {/* 第四行：城市标签（最多显示3个） */}
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {city.tags.slice(0, 3).map((tag) => ( // slice(0, 3) 只取前3个标签
            <Tag key={`${city.id}-${tag}`} style={{ marginBottom: 4 }}>
              {tag}
            </Tag>
          ))}
        </div>

        {/* 第五行：指标展示区（人均预算、步行强度等） */}
        <CityGridCardMetrics city={city} profile={profile} />

        {/* 第六行：操作按钮组（详情、加入对比、规划） */}
        <CityGridCardActions
          cityName={city.name}
          inCompare={inCompare}
          onOpenCityDetail={() => onOpenCityDetail(city.id)}
          onToggleCompareCity={() => onToggleCompareCity(city.id)}
          onUsePlanPrompt={() => onUsePrompt(buildPlanPrompt(city.name))} // 生成该城市的规划提示词
        />
      </div>
    </Card>
  );
};
