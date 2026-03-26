'use client';

import React from 'react';
import { Progress, Tag } from 'antd';
import type { ConfidenceSummary } from '@/utils/travelPlan';

interface BudgetConfidencePanelProps {
  confidence: ConfidenceSummary;
}

export const BudgetConfidencePanel: React.FC<BudgetConfidencePanelProps> = ({ confidence }) => (
  <div>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
      <span style={{ fontSize: 13, color: '#334155' }}>结果可信度</span>
      <Tag color={confidence.level === 'high' ? 'green' : confidence.level === 'medium' ? 'gold' : 'red'}>
        {confidence.level}
      </Tag>
    </div>
    <Progress percent={confidence.score} size="small" />
    <div style={{ display: 'grid', gap: 4, marginTop: 6 }}>
      {confidence.risks.map((risk, index) => (
        <div key={`confidence-risk-${index}`} style={{ fontSize: 12, color: '#92400e' }}>
          风险提示：{risk}
        </div>
      ))}
    </div>
  </div>
);
