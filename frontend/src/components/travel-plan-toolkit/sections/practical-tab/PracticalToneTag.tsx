'use client';

import React from 'react';
import type { PracticalInfoCard } from '@/utils/travelPlan';
import { practicalToneLabel, practicalToneStyle } from '../../shared';

interface PracticalToneTagProps {
  tone: PracticalInfoCard['tone'];
}

export const PracticalToneTag: React.FC<PracticalToneTagProps> = ({ tone }) => {
  const toneStyle = practicalToneStyle(tone);
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        borderRadius: 999,
        padding: '2px 8px',
        fontSize: 11,
        fontWeight: 700,
        border: `1px solid ${toneStyle.border}`,
        background: '#ffffffb8',
        color: toneStyle.color,
      }}
    >
      {practicalToneLabel(tone)}
    </span>
  );
};
