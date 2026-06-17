// 行程冲突提醒区块组件
// 应用场景：当某天的行程存在冲突（如两个景点时间重叠、距离太远），
//   在每日行程卡片顶部显示橙色警告区域，列出冲突和建议

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import type { ItineraryConflict } from '@/utils/travelPlan';
import { riskColor } from '../../../shared';

// ItineraryConflictSectionProps 冲突区块接收的参数
interface ItineraryConflictSectionProps {
  conflicts: ItineraryConflict[];  // 冲突列表
  dayKey: string;                  // 当天的唯一标识键
}

export const ItineraryConflictSection: React.FC<ItineraryConflictSectionProps> = ({ conflicts, dayKey }) => {
  if (conflicts.length === 0) return null;  // 没有冲突时不渲染

  return (
    <div style={{ display: 'grid', gap: 10 }}>
      {/* 顶部风险摘要区域（橙色渐变背景） */}
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
        {/* 最多显示2条风险摘要 */}
        {conflicts.slice(0, 2).map((conflict) => (
          <div key={`${dayKey}-risk-${conflict.id}`} style={{ fontSize: 12, color: riskColor(conflict.severity) }}>
            {conflict.title}：{conflict.suggestion}
          </div>
        ))}
      </div>

      {/* 详细冲突列表 */}
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
