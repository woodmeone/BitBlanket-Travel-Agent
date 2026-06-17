// 'use client' —— 客户端组件声明
'use client';

import React from 'react';
// Button 是 Ant Design 的按钮组件，Tag 是标签组件
import { Button, Tag } from 'antd';
// CitySummary 是城市摘要数据的类型
import type { CitySummary } from '@/types';
// buildCityProfile —— 从城市数据构建画像（获取推荐语等）
// buildPlanPrompt —— 生成"规划旅行"的 AI 提示词
import { buildCityProfile, buildPlanPrompt } from '../../shared';

// FavoriteShortlistPanelProps —— 候选池面板的属性类型
interface FavoriteShortlistPanelProps {
  favoriteCities: CitySummary[];          // 用户收藏的城市列表（最多4个）
  onUsePrompt: (prompt: string) => void;  // 使用提示词的回调函数
}

// 【核心】FavoriteShortlistPanel —— 候选池面板
// 功能：展示用户收藏的城市，每个城市有"去规划"按钮
// 应用场景：用户浏览城市卡片时点击心形图标收藏，收藏的城市会出现在这里，
//           方便集中查看和快速发起旅行规划
export const FavoriteShortlistPanel: React.FC<FavoriteShortlistPanelProps> = ({ favoriteCities, onUsePrompt }) => (
  // 面板容器：圆角卡片样式，白色渐变背景
  <div
    style={{
      borderRadius: 20,
      padding: 18,
      background: 'linear-gradient(180deg, rgba(255,255,255,0.96) 0%, #f8fafc 100%)',
      border: '1px solid #dbe4ee',
      boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.8)', // 内阴影，产生微妙的凹陷感
      display: 'grid',
      gap: 10,
    }}
  >
    {/* 标题行：左侧"候选池"文字，右侧数量标签 */}
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
      <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a' }}>候选池</div>
      {/* Tag 组件：显示候选数量，如"2/4"，蓝色圆角标签 */}
      <Tag color="blue" style={{ marginInlineEnd: 0, borderRadius: 999, paddingInline: 10 }}>
        {favoriteCities.length}/4
      </Tag>
    </div>

    {/* 条件渲染：根据候选池是否为空，显示不同内容 */}
    {favoriteCities.length === 0 ? (
      /* 空状态：虚线边框提示框，引导用户先收藏城市 */
      <div
        style={{
          minHeight: 108,
          borderRadius: 14,
          border: '1px dashed #cbd5e1', // dashed 虚线边框，表示"可放入"
          background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
          display: 'grid',
          placeItems: 'center', // 水平垂直居中
          fontSize: 13,
          color: '#64748b',
          textAlign: 'center',
          padding: 12,
        }}
      >
        先把感兴趣的城市加入候选池，后面做对比和规划会更快。
      </div>
    ) : (
      /* 有城市时：逐个渲染城市卡片，最多显示4个 */
      // slice(0, 4) —— 只取前4个城市，防止超出候选池容量
      // map() —— 遍历数组，为每个城市生成一个卡片
      favoriteCities.slice(0, 4).map((city) => (
        <div
          key={`favorite-${city.id}`} // key 是 React 列表渲染必需的唯一标识
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
          {/* 城市信息：名称 + 推荐语 */}
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 700, color: '#1f2937' }}>{city.name}</div>
            {/* 推荐语：最多显示2行，超出部分省略 */}
            {/* WebkitLineClamp: 2 —— CSS 属性，限制文本最多显示2行 */}
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
          {/* "去规划"按钮：点击后生成该城市的旅行规划提示词 */}
          <Button
            size="small"
            type="primary"
            aria-label={`规划候选城市 ${city.name}`} // 无障碍标签，屏幕阅读器会读出来
            style={{ borderRadius: 999, border: 'none', background: 'linear-gradient(135deg, #0284c7 0%, #0f766e 100%)' }}
            onClick={() => onUsePrompt(buildPlanPrompt(city.name))} // 点击时调用 buildPlanPrompt 生成提示词
          >
            去规划
          </Button>
        </div>
      ))
    )}
  </div>
);
