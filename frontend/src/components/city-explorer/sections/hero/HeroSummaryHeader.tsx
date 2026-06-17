// 'use client' —— 客户端组件声明
'use client';

import React from 'react';
// 从 ant-design 图标库引入三个图标组件
// 图标组件本质上是 SVG 矢量图，可以直接当 React 组件使用
import { CompassOutlined, HeartFilled, SwapOutlined } from '@ant-design/icons';

// HeroSummaryHeaderProps —— 顶部摘要栏的属性类型
interface HeroSummaryHeaderProps {
  compareCount: number;   // 对比池中的城市数量
  favoriteCount: number;  // 候选池中的城市数量
  summaryText: string;    // 当前筛选条件摘要，如"全部城市"
}

// SummaryStatCard —— 通用的统计卡片组件（内部使用，不导出）
// 用途：在顶部展示一条简短信息，如"当前视图：全部城市"
// 参数：
//   accentColor —— 卡片边框颜色
//   background —— 卡片背景样式
//   children —— 卡片内容（React.ReactNode 表示任意可渲染的 React 内容）
function SummaryStatCard({
  accentColor,
  background,
  children,
}: {
  accentColor: string;
  background: string;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        display: 'grid',
        gap: 2,
        minWidth: 190,
        maxWidth: 260,
        padding: '8px 12px',
        borderRadius: 12,           // 圆角半径 12px
        border: `1px solid ${accentColor}`, // 动态边框颜色
        background,
      }}
    >
      {children}
    </div>
  );
}

// 【核心】HeroSummaryHeader —— 顶部摘要信息栏
// 布局：左侧是标题和说明，右侧是统计卡片（当前视图、对比池、候选池）
export const HeroSummaryHeader: React.FC<HeroSummaryHeaderProps> = ({ compareCount, favoriteCount, summaryText }) => (
  // flex 布局：左右两端对齐，垂直顶部对齐，间距 12px，允许换行
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
    {/* 左侧：图标 + 标题 + 说明文字 */}
    <div style={{ display: 'flex', gap: 12 }}>
      {/* 指南针图标容器：渐变背景 + 阴影，营造立体感 */}
      <div
        style={{
          width: 42,
          height: 42,
          borderRadius: 14,
          display: 'grid',
          placeItems: 'center', // 水平垂直居中
          background: 'linear-gradient(135deg, #0c4a6e 0%, #0f766e 100%)', // 深蓝到深绿渐变
          boxShadow: '0 10px 24px rgba(2, 132, 199, 0.35)', // 外阴影，产生浮起效果
        }}
      >
        <CompassOutlined style={{ color: '#f0f9ff', fontSize: 20 }} />
      </div>
      <div>
        {/* 标题 */}
        <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: 0.2, color: '#0f172a', marginBottom: 4 }}>城市探索</div>
        {/* 说明文字 */}
        <div style={{ fontSize: 13, color: '#475569', maxWidth: 760, lineHeight: 1.75 }}>
          当前只展示真实策展城市库，详情中的景点名称、区位和备注都来自人工整理，不再混入模板化生成城市。
        </div>
      </div>
    </div>

    {/* 右侧：统计信息区域 */}
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      {/* 当前视图摘要卡片 */}
      <SummaryStatCard accentColor="#bfdbfe" background="linear-gradient(180deg, #eff6ff 0%, #f8fbff 100%)">
        <span style={{ fontSize: 11, color: '#1d4ed8', fontWeight: 700 }}>当前视图</span>
        <span style={{ fontSize: 12, color: '#334155', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {summaryText}
        </span>
      </SummaryStatCard>

      {/* 对比池数量指示器 */}
      {/* 当对比池有城市时，背景变为暖色渐变，文字变为深棕色，视觉上更醒目 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '8px 12px',
          borderRadius: 12,
          border: '1px solid rgba(245, 158, 11, 0.35)',
          background: compareCount > 0 ? 'linear-gradient(180deg, #fff7ed 0%, #fffbeb 100%)' : '#ffffff',
          color: compareCount > 0 ? '#92400e' : '#64748b',
          fontSize: 13,
          fontWeight: 700,
        }}
      >
        <SwapOutlined />
        对比池 {compareCount}/3
      </div>

      {/* 候选池数量指示器 */}
      {/* 当候选池有城市时，背景变为粉红渐变，心形图标变红 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '8px 12px',
          borderRadius: 12,
          border: '1px solid rgba(239, 68, 68, 0.3)',
          background: favoriteCount > 0 ? 'linear-gradient(180deg, #fff1f2 0%, #fff7f7 100%)' : '#ffffff',
          color: favoriteCount > 0 ? '#be123c' : '#64748b',
          fontSize: 13,
          fontWeight: 700,
        }}
      >
        <HeartFilled style={{ color: favoriteCount > 0 ? '#e11d48' : '#94a3b8' }} />
        候选池 {favoriteCount}
      </div>
    </div>
  </div>
);
