// 实用信息网格组件
// 应用场景：在实用信息标签页中，以网格布局展示所有实用信息卡片
//   每张卡片包含标题、语气标签和详细内容

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import type { PracticalInfoCard } from '@/utils/travelPlan';
import { PracticalInfoCardItem } from './PracticalInfoCardItem';

// PracticalInfoGridProps 实用信息网格接收的参数
interface PracticalInfoGridProps {
  messageId: string;                   // 消息 ID
  practicalInfo: PracticalInfoCard[];  // 实用信息卡片列表
}

export const PracticalInfoGrid: React.FC<PracticalInfoGridProps> = ({ messageId, practicalInfo }) => (
  <div
    style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',  // 自适应网格，每个卡片最小宽度220px
      gap: 10,
    }}
  >
    {practicalInfo.map((item) => (
      <PracticalInfoCardItem key={`${messageId}-practical-${item.id}`} cardKey={`${messageId}-practical-${item.id}`} item={item} />
    ))}
  </div>
);
