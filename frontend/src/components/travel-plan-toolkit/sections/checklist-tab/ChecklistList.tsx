// 执行清单列表组件
// 应用场景：在执行清单标签页中，展示所有待办事项的列表
//   每个事项可以勾选完成，完成后状态标签变为绿色"已完成"

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import type { ChecklistItem } from '@/utils/travelPlan';
import { ChecklistItemRow } from './ChecklistItemRow';

// ChecklistListProps 清单列表接收的参数
interface ChecklistListProps {
  checklist: ChecklistItem[];                              // 清单项列表
  completedChecklist: Record<string, boolean>;             // 已完成的清单项（键是清单项 ID）
  messageId: string;                                       // 消息 ID
  onToggleChecklist: (itemId: string, checked: boolean) => void;  // 切换完成状态的回调
}

export const ChecklistList: React.FC<ChecklistListProps> = ({
  checklist,
  completedChecklist,
  messageId,
  onToggleChecklist,
}) => (
  <div style={{ display: 'grid', gap: 8 }}>
    {checklist.map((item) => (
      <ChecklistItemRow
        key={`${messageId}-${item.id}`}
        item={item}
        itemKey={`${messageId}-${item.id}`}
        completed={Boolean(completedChecklist[item.id])}
        onToggleChecklist={onToggleChecklist}
      />
    ))}
  </div>
);
