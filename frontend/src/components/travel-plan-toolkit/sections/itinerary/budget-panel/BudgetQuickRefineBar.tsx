'use client';

import React from 'react';
import { Button } from 'antd';
import type { QuickRefineAction } from '../../../shared';

interface BudgetQuickRefineBarProps {
  quickRefineActions: QuickRefineAction[];
  onQuickRefine: (action: QuickRefineAction) => void;
}

export const BudgetQuickRefineBar: React.FC<BudgetQuickRefineBarProps> = ({ quickRefineActions, onQuickRefine }) => {
  if (quickRefineActions.length === 0) return null;

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
