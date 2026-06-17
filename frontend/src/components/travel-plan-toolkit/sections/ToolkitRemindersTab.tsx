// 出发提醒标签页组件
// 应用场景：展示出发前的提醒事项，按阶段分组（出发前1天/3天/1周）
//   例如："出发前1天 → 请确认酒店入住信息"

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import type { ReminderItem } from '@/utils/travelPlan';
import { RemindersList } from './reminders-tab/RemindersList';

// ToolkitRemindersTabProps 提醒标签页接收的参数
interface ToolkitRemindersTabProps {
  messageId: string;           // 消息 ID
  reminders: ReminderItem[];   // 提醒项列表
}

export const ToolkitRemindersTab: React.FC<ToolkitRemindersTabProps> = ({ messageId, reminders }) => (
  <RemindersList messageId={messageId} reminders={reminders} />
);
