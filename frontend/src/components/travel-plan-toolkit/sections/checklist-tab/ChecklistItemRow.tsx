// 清单项行组件——单个待办事项的展示和交互
// 应用场景：在执行清单中，每个事项占一行，左侧是勾选框，右侧是状态标签
//   勾选后背景变为浅绿色，状态标签变为"已完成"

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Checkbox } from 'antd';
import type { ChecklistItem } from '@/utils/travelPlan';
import { ChecklistStatusTag } from './ChecklistStatusTag';

// ChecklistItemRowProps 清单项行接收的参数
interface ChecklistItemRowProps {
  item: ChecklistItem;                                      // 清单项数据
  completed: boolean;                                       // 是否已完成
  itemKey: string;                                          // 唯一标识键
  onToggleChecklist: (itemId: string, checked: boolean) => void;  // 切换完成状态的回调
}

export const ChecklistItemRow: React.FC<ChecklistItemRowProps> = ({ item, completed, itemKey, onToggleChecklist }) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 12,
      borderRadius: 12,
      padding: '10px 12px',
      border: completed ? '1px solid #bbf7d0' : '1px solid #dbeafe',   // 已完成绿色边框，未完成蓝色边框
      background: completed ? '#f0fdf4' : '#f8fafc',                    // 已完成浅绿背景，未完成浅灰背景
    }}
  >
    <Checkbox key={itemKey} checked={completed} onChange={(event) => onToggleChecklist(item.id, event.target.checked)}>
      {item.label}
    </Checkbox>
    <ChecklistStatusTag completed={completed} />
  </div>
);
