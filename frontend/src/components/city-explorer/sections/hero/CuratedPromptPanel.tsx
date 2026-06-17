// 'use client' —— 客户端组件声明
'use client';

import React from 'react';
// Button 是 Ant Design 的按钮组件
import { Button } from 'antd';
// CompassOutlined 是指南针图标，用于"灵感起点"标签
import { CompassOutlined } from '@ant-design/icons';
// CURATED_PROMPTS —— 预置的策展推荐场景列表（定义在 shared.tsx 中）
import { CURATED_PROMPTS } from '../../shared';

// CuratedPromptPanelProps —— 策展推荐面板的属性类型
interface CuratedPromptPanelProps {
  onUsePrompt: (prompt: string) => void; // 使用提示词的回调函数
}

// 【核心】CuratedPromptPanel —— 策展推荐场景面板
// 功能：展示预置的旅行场景（如"周末快闪"、"亲子省心"），用户点击后直接发送 AI 提示词
// 应用场景：用户不知道去哪旅行时，可以从这些场景出发，
//           例如点击"周末快闪"，AI 会推荐适合周末两天、预算1500元内的城市
export const CuratedPromptPanel: React.FC<CuratedPromptPanelProps> = ({ onUsePrompt }) => (
  // 面板容器：圆角卡片，白色渐变背景 + 阴影
  <div
    style={{
      borderRadius: 20,
      padding: 20,
      background: 'linear-gradient(180deg, rgba(255,255,255,0.98) 0%, #f8fbff 100%)',
      border: '1px solid #dbe4ee',
      boxShadow: '0 14px 30px rgba(15, 23, 42, 0.08)', // 外阴影，产生浮起效果
      color: '#0f172a',
      display: 'grid',
      gap: 16,
      alignContent: 'start', // 内容从顶部开始排列
    }}
  >
    {/* "灵感起点"标签：蓝色药丸形标签 */}
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        width: 'fit-content', // 宽度适应内容
        padding: '6px 10px',
        borderRadius: 999,    // 完全圆角，形成药丸形状
        border: '1px solid #dbeafe',
        background: '#eff6ff',
        color: '#1d4ed8',
        fontSize: 12,
        fontWeight: 700,
      }}
    >
      <CompassOutlined />
      灵感起点
    </div>

    {/* 标题 */}
    <div style={{ display: 'grid', gap: 8 }}>
      <div style={{ fontSize: 24, fontWeight: 800, lineHeight: 1.2, color: '#0f172a', maxWidth: 520 }}>
        从场景出发，找到对的城市
      </div>
    </div>

    {/* 场景按钮网格：每个场景是一个可点击的卡片按钮 */}
    {/* gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' —— 自适应列布局 */}
    {/* 每列最小 160px，空间足够时并排显示，不足时自动换行 */}
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: 10,
      }}
    >
      {/* 遍历 CURATED_PROMPTS 数组，为每个场景生成一个按钮 */}
      {CURATED_PROMPTS.map((item) => (
        <Button
          key={item.label}
          block // block 让按钮占满整列宽度
          aria-label={`使用场景 ${item.label}`} // 无障碍标签
          style={{
            height: '100%',
            minHeight: 92,
            padding: '14px 16px',
            borderRadius: 16,
            border: `1px solid ${item.borderColor}`,  // 每个场景有不同颜色的边框
            background: item.background,                // 每个场景有不同渐变背景
            color: '#0f172a',
            boxShadow: 'none',
            whiteSpace: 'normal', // 允许文字换行（默认按钮文字不换行）
          }}
          onClick={() => onUsePrompt(item.prompt)} // 点击时把该场景的提示词传给父组件
        >
          <div style={{ display: 'grid', gap: 6, textAlign: 'left' }}>
            <span style={{ fontSize: 16, fontWeight: 700 }}>{item.label}</span>
            <span style={{ fontSize: 12, lineHeight: 1.65, color: '#64748b', fontWeight: 500 }}>{item.hint}</span>
          </div>
        </Button>
      ))}
    </div>
  </div>
);
