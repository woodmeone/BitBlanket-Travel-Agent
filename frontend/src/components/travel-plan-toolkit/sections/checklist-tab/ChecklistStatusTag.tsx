// 清单项状态标签组件
// 应用场景：在执行清单中，每个清单项右侧显示"已完成"或"待处理"的状态标签
//   已完成为绿色，待处理为蓝色

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { checklistStatusMeta } from '../../shared';

// ChecklistStatusTagProps 状态标签接收的参数
interface ChecklistStatusTagProps {
  completed: boolean;  // 是否已完成
}

export const ChecklistStatusTag: React.FC<ChecklistStatusTagProps> = ({ completed }) => {
  const meta = checklistStatusMeta(completed);  // 获取状态对应的文字和颜色
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        borderRadius: 999,                       // border-radius: 999 让边框变成胶囊形状
        padding: '2px 8px',
        fontSize: 11,
        fontWeight: 700,
        background: meta.background,
        border: `1px solid ${meta.border}`,
        color: meta.color,
      }}
    >
      {meta.label}
    </span>
  );
};
