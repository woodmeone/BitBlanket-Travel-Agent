'use client';

import React from 'react';
import { Button } from 'antd';

interface ItineraryTipsBlockProps {
  dayKey: string;
  hiddenTipCount: number;
  tipsExpanded: boolean;
  visibleTips: string[];
  onToggleTips: (dayKey: string) => void;
}

export const ItineraryTipsBlock: React.FC<ItineraryTipsBlockProps> = ({
  dayKey,
  hiddenTipCount,
  tipsExpanded,
  visibleTips,
  onToggleTips,
}) => {
  if (visibleTips.length === 0) return null;

  return (
    <div style={{ display: 'grid', gap: 4 }}>
      {visibleTips.map((tip, index) => (
        <div key={`${dayKey}-tip-${index}`} style={{ fontSize: 12, color: '#0f766e' }}>
          小贴士：{tip}
        </div>
      ))}
      {hiddenTipCount > 0 && (
        <Button type="link" size="small" style={{ width: 'fit-content', padding: 0 }} onClick={() => onToggleTips(dayKey)}>
          {tipsExpanded ? '收起' : `展开更多（${hiddenTipCount}）`}
        </Button>
      )}
    </div>
  );
};
