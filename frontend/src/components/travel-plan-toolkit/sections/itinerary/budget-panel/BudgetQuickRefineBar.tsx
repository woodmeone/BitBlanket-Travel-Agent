// 预算快速微调按钮栏组件
// 应用场景：在预算面板中，提供一组快捷操作按钮
//   例如"增加预算"、"减少天数"等，点击后直接发送提示词给 AI 调整方案

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Button } from 'antd';
import type { QuickRefineAction } from '../../../shared';

// BudgetQuickRefineBarProps 快速微调栏接收的参数
interface BudgetQuickRefineBarProps {
  quickRefineActions: QuickRefineAction[];                  // 快速微调操作列表
  onQuickRefine: (action: QuickRefineAction) => void;       // 点击微调按钮的回调
}

export const BudgetQuickRefineBar: React.FC<BudgetQuickRefineBarProps> = ({ quickRefineActions, onQuickRefine }) => {
  if (quickRefineActions.length === 0) return null;  // 没有微调操作时不渲染

  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      {quickRefineActions.map((action) => (
        <Button key={action.key} size="small" onClick={() => onQuickRefine(action)}>
          {action.label}
        </Button>
      ))}
    </div>
  );
};
