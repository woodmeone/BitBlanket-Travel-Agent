// 冲突摘要标签组件
// 应用场景：在冲突检测标签页顶部，显示冲突总数的状态标签
//   有冲突时显示橙色警告，无冲突时显示绿色安全

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Tag } from 'antd';

// ConflictSummaryTagProps 冲突摘要标签接收的参数
interface ConflictSummaryTagProps {
  totalConflicts: number;  // 冲突总数
}

export const ConflictSummaryTag: React.FC<ConflictSummaryTagProps> = ({ totalConflicts }) => (
  <Tag color={totalConflicts > 0 ? 'orange' : 'green'}>
    {totalConflicts > 0 ? `检测到 ${totalConflicts} 个冲突风险` : '未检测到明显冲突'}
  </Tag>
);
