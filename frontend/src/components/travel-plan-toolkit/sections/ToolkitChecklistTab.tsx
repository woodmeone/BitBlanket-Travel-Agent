// 执行清单标签页组件
// 应用场景：展示出行前的待办事项清单，如"预订酒店"、"购买保险"等
//   用户可以逐项勾选完成

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import type { ChecklistItem } from '@/utils/travelPlan';
import { ChecklistList } from './checklist-tab/ChecklistList';

// ToolkitChecklistTabProps 清单标签页接收的参数
interface ToolkitChecklistTabProps {
  checklist: ChecklistItem[];                                      // 清单项列表
  completedChecklist: Record<string, boolean>;                     // 已完成的清单项
  messageId: string;                                               // 消息 ID
  onToggleChecklist: (itemId: string, checked: boolean) => void;   // 切换完成状态的回调
}

export const ToolkitChecklistTab: React.FC<ToolkitChecklistTabProps> = ({
  checklist,
  completedChecklist,
  messageId,
  onToggleChecklist,
}) => (
  <ChecklistList
    checklist={checklist}
    completedChecklist={completedChecklist}
    messageId={messageId}
    onToggleChecklist={onToggleChecklist}
  />
);
