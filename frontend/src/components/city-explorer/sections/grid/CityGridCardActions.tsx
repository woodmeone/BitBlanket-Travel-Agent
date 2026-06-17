// 'use client' —— 客户端组件声明
'use client';

import React from 'react';
// Button —— Ant Design 按钮组件
import { Button } from 'antd';
// RiseOutlined —— 上升箭头图标，用于"加入对比"按钮
import { RiseOutlined } from '@ant-design/icons';

// CityGridCardActionsProps —— 卡片操作按钮组的属性类型
interface CityGridCardActionsProps {
  cityName: string;                // 城市名称，用于按钮文字和无障碍标签
  inCompare: boolean;              // 是否在对比池中
  onOpenCityDetail: () => void;    // 打开详情的回调
  onToggleCompareCity: () => void; // 切换对比状态的回调
  onUsePlanPrompt: () => void;     // 使用规划提示词的回调
}

// CityGridCardActions —— 城市卡片底部的操作按钮组
// 功能：提供三个操作按钮
//   1. "详情" —— 打开城市详情抽屉
//   2. "加入对比"/"移出对比" —— 把城市加入或移出对比池
//   3. "规划" —— 生成该城市的旅行规划提示词
export const CityGridCardActions: React.FC<CityGridCardActionsProps> = ({
  cityName,
  inCompare,
  onOpenCityDetail,
  onToggleCompareCity,
  onUsePlanPrompt,
}) => (
  // flex 布局，按钮之间间距6px，允许换行
  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
    {/* 详情按钮：打开城市详情抽屉 */}
    <Button size="small" aria-label={`查看${cityName}详情`} onClick={onOpenCityDetail}>
      详情
    </Button>
    {/* 对比按钮：根据当前状态显示不同文字 */}
    <Button
      size="small"
      aria-label={`${inCompare ? '移出对比' : '加入对比'} ${cityName}`}
      icon={<RiseOutlined />}
      onClick={onToggleCompareCity} // 点击切换对比状态
    >
      {inCompare ? '移出对比' : '加入对比'} {/* 三元运算符：条件 ? 真值 : 假值 */}
    </Button>
    {/* 规划按钮：生成旅行规划提示词，primary 样式（蓝色主色调） */}
    <Button size="small" type="primary" aria-label={`规划 ${cityName}`} onClick={onUsePlanPrompt}>
      规划
    </Button>
  </div>
);
