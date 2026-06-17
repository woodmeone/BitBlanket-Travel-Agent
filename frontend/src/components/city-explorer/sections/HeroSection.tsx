// 'use client' —— 客户端组件声明，此组件包含交互功能，需要在浏览器端运行
'use client';

// import —— 引入依赖
// React 是 React 库的核心，所有组件都需要引入
import React from 'react';
// CitySummary 是城市摘要数据的类型定义，描述一个城市的基本信息
import type { CitySummary } from '@/types';
// 引入三个子组件，分别负责 Hero 区域的不同部分
import { CuratedPromptPanel } from './hero/CuratedPromptPanel';     // 策展推荐场景面板
import { FavoriteShortlistPanel } from './hero/FavoriteShortlistPanel'; // 候选池面板
import { HeroSummaryHeader } from './hero/HeroSummaryHeader';       // 顶部摘要信息栏

// interface —— 定义组件的属性（props）类型
// React 组件通过 props 接收外部传入的数据，类似函数的参数
// CityExplorerHeroProps 描述了 Hero 区域需要哪些数据
interface CityExplorerHeroProps {
  compareCities: CitySummary[];          // 当前对比池中的城市列表
  favoriteCities: CitySummary[];         // 当前候选池中的城市列表
  onUsePrompt: (prompt: string) => void; // 当用户点击某个场景/规划按钮时，把提示词传给父组件处理
  summaryText: string;                   // 当前筛选条件的摘要文本，如"全部城市"或"华东 / 美食优先"
}

// 【核心】CityExplorerHero —— 城市探索页面的顶部区域组件
// React.FC 是 React 函数组件的类型，<> 中是 props 的类型
// 这个组件组合了三个子组件，形成 Hero 区域的整体布局
export const CityExplorerHero: React.FC<CityExplorerHeroProps> = ({
  compareCities,   // 对比池城市
  favoriteCities,  // 候选池城市
  onUsePrompt,     // 使用提示词的回调函数
  summaryText,     // 筛选摘要文本
}) => (
  // 最外层容器：使用 CSS Grid 布局，gap: 16 表示子元素之间间距 16px
  // position: relative + zIndex: 1 确保此区域在层叠中位于合适的位置
  <div
    style={{
      display: 'grid',
      gap: 16,
      position: 'relative',
      zIndex: 1,
    }}
  >
    {/* 顶部摘要栏：显示对比池数量、候选池数量、当前筛选摘要 */}
    <HeroSummaryHeader
      compareCount={compareCities.length}
      favoriteCount={favoriteCities.length}
      summaryText={summaryText}
    />

    {/* 下方两栏布局：左侧策展推荐场景，右侧候选池 */}
    {/* gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' —— 自适应列布局 */}
    {/* 每列最小宽度 320px，当空间不足时自动换行；1fr 表示平分剩余空间 */}
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: 16,
        alignItems: 'stretch', // 让两栏高度拉伸对齐
      }}
    >
      {/* 策展推荐场景面板：展示"周末快闪"、"亲子省心"等预置场景 */}
      <CuratedPromptPanel onUsePrompt={onUsePrompt} />
      {/* 候选池面板：展示用户收藏的城市，最多4个 */}
      <FavoriteShortlistPanel favoriteCities={favoriteCities} onUsePrompt={onUsePrompt} />
    </div>
  </div>
);
