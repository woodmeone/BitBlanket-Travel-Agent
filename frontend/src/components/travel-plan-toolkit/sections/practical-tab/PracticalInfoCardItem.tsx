'use client';

import React from 'react';
import { InfoCircleOutlined } from '@ant-design/icons';
import type { PracticalInfoCard } from '@/utils/travelPlan';
import { practicalToneStyle } from '../../shared';
import { PracticalToneTag } from './PracticalToneTag';

interface PracticalInfoCardItemProps {
  cardKey: string;
  item: PracticalInfoCard;
}

export const PracticalInfoCardItem: React.FC<PracticalInfoCardItemProps> = ({ cardKey, item }) => {
  const toneStyle = practicalToneStyle(item.tone);

  return (
    <div
      key={cardKey}
      style={{
        borderRadius: 14,
        padding: 14,
        background: toneStyle.background,
        border: `1px solid ${toneStyle.border}`,
        color: toneStyle.color,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          marginBottom: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <InfoCircleOutlined />
          <div style={{ fontWeight: 700 }}>{item.title}</div>
        </div>
        <PracticalToneTag tone={item.tone} />
      </div>
      <div style={{ fontSize: 13, lineHeight: 1.7 }}>{item.value}</div>
    </div>
  );
};
