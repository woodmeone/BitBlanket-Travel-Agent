'use client';

import React from 'react';
import type { ItineraryConflict } from '@/utils/travelPlan';
import { riskColor } from '../../../shared';

interface ItineraryConflictSectionProps {
  conflicts: ItineraryConflict[];
  dayKey: string;
}

export const ItineraryConflictSection: React.FC<ItineraryConflictSectionProps> = ({ conflicts, dayKey }) => {
  if (conflicts.length === 0) return null;

  return (
    <div style={{ display: 'grid', gap: 10 }}>
      <div
        style={{
          display: 'grid',
          gap: 8,
          background: 'linear-gradient(135deg, #fff7ed 0%, #fffbeb 100%)',
          border: '1px solid #fed7aa',
          borderRadius: 12,
          padding: 10,
        }}
      >
        <div style={{ fontSize: 13, fontWeight: 700, color: '#9a3412' }}>本日风险提醒</div>
        {conflicts.slice(0, 2).map((conflict) => (
          <div key={`${dayKey}-risk-${conflict.id}`} style={{ fontSize: 12, color: riskColor(conflict.severity) }}>
            {conflict.title}：{conflict.suggestion}
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gap: 6 }}>
        {conflicts.map((conflict) => (
          <div
            key={`${dayKey}-${conflict.id}`}
            style={{
              fontSize: 12,
              color: '#7c2d12',
              background: '#fff7ed',
              border: '1px solid #fed7aa',
              borderRadius: 8,
              padding: '6px 8px',
            }}
          >
            <div style={{ fontWeight: 600 }}>{conflict.title}</div>
            <div>{conflict.description}</div>
            <div>建议：{conflict.suggestion}</div>
          </div>
        ))}
      </div>
    </div>
  );
};
