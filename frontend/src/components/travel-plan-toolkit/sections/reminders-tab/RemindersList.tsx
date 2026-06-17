// 出发提醒列表组件
// 应用场景：在出发提醒标签页中，展示所有提醒事项的卡片列表
//   每张卡片包含提醒的阶段标签（T-1/T-3/T-7）、标题和详细内容

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Card } from 'antd';
import type { ReminderItem } from '@/utils/travelPlan';
import { ReminderCardContent } from './ReminderCardContent';

// RemindersListProps 提醒列表接收的参数
interface RemindersListProps {
  messageId: string;               // 消息 ID
  reminders: ReminderItem[];       // 提醒项列表
}

export const RemindersList: React.FC<RemindersListProps> = ({ messageId, reminders }) => (
  <div style={{ display: 'grid', gap: 10 }}>
    {reminders.map((item) => (
      <Card key={`${messageId}-${item.id}`} size="small">
        <ReminderCardContent item={item} />
      </Card>
    ))}
  </div>
);
