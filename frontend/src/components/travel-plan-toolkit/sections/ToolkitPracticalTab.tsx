// 实用信息标签页组件
// 应用场景：展示旅行目的地的实用信息，如天气、交通、货币、签证等
//   每条信息带有语气标签（建议/注意/常规）

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import type { PracticalInfoCard } from '@/utils/travelPlan';
import { PracticalInfoGrid } from './practical-tab/PracticalInfoGrid';

// ToolkitPracticalTabProps 实用信息标签页接收的参数
interface ToolkitPracticalTabProps {
  messageId: string;                   // 消息 ID
  practicalInfo: PracticalInfoCard[];  // 实用信息卡片列表
}

export const ToolkitPracticalTab: React.FC<ToolkitPracticalTabProps> = ({ messageId, practicalInfo }) => (
  <PracticalInfoGrid messageId={messageId} practicalInfo={practicalInfo} />
);
