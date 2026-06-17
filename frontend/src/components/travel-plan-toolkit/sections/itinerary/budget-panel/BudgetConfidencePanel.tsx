// 预算可信度面板组件
// 应用场景：在预算面板底部，展示预算估算结果的可信度
//   包括：可信度等级（high/medium/low）、可信度分数进度条、风险提示列表

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Progress, Tag } from 'antd';
import type { ConfidenceSummary } from '@/utils/travelPlan';

// BudgetConfidencePanelProps 可信度面板接收的参数
interface BudgetConfidencePanelProps {
  confidence: ConfidenceSummary;  // 可信度摘要数据
}

export const BudgetConfidencePanel: React.FC<BudgetConfidencePanelProps> = ({ confidence }) => (
  <div>
    {/* 可信度等级标签 */}
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
      <span style={{ fontSize: 13, color: '#334155' }}>结果可信度</span>
      <Tag color={confidence.level === 'high' ? 'green' : confidence.level === 'medium' ? 'gold' : 'red'}>
        {confidence.level}
      </Tag>
    </div>
    {/* 可信度分数进度条 */}
    <Progress percent={confidence.score} size="small" />
    {/* 风险提示列表 */}
    <div style={{ display: 'grid', gap: 4, marginTop: 6 }}>
      {confidence.risks.map((risk, index) => (
        <div key={`confidence-risk-${index}`} style={{ fontSize: 12, color: '#92400e' }}>
          风险提示：{risk}
        </div>
      ))}
    </div>
  </div>
);
