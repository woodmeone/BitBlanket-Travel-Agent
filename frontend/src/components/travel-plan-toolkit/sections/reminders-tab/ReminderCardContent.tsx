// 提醒卡片内容组件
// 应用场景：在提醒卡片内部，展示阶段标签、提醒标题和详细内容
//   例如：T-1 | 出发前一天 → "请确认酒店入住信息" → "检查预订确认邮件..."

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Space } from 'antd';
import type { ReminderItem } from '@/utils/travelPlan';
import { ReminderPhaseTag } from './ReminderPhaseTag';

// ReminderCardContentProps 提醒内容接收的参数
interface ReminderCardContentProps {
  item: ReminderItem;  // 提醒项数据
}

export const ReminderCardContent: React.FC<ReminderCardContentProps> = ({ item }) => (
  <Space orientation="vertical" size={2}>
    <ReminderPhaseTag phase={item.phase} />
    <div style={{ fontWeight: 600 }}>{item.title}</div>
    <div style={{ fontSize: 13, color: '#475569' }}>{item.detail}</div>
  </Space>
);
