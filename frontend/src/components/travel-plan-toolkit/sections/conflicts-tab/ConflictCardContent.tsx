// 冲突卡片内容组件——展示冲突详情和一键修复按钮
// 应用场景：在每日冲突卡片内部，列出每个冲突的类型、标题、描述和建议
//   底部提供"一键修复此日"按钮，点击后 AI 自动调整当天行程

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Button, Divider, Tag } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import type { DayPlanCard, ItineraryConflict } from '@/utils/travelPlan';

// ConflictCardContentProps 冲突内容接收的参数
interface ConflictCardContentProps {
  conflicts: ItineraryConflict[];                                              // 冲突列表
  day: DayPlanCard;                                                            // 当天行程数据
  dayIndex: number;                                                            // 天数索引
  dayKey: string;                                                              // 当天唯一标识键
  onOneClickFix: (dayKey: string, dayIndex: number, day: DayPlanCard) => void; // 一键修复回调
}

// 根据冲突严重程度返回 Ant Design Tag 的颜色
function severityColor(severity: ItineraryConflict['severity']): 'red' | 'orange' | 'gold' {
  if (severity === 'high') return 'red';      // 高严重性 → 红色
  if (severity === 'medium') return 'orange';  // 中严重性 → 橙色
  return 'gold';                               // 低严重性 → 金色
}

export const ConflictCardContent: React.FC<ConflictCardContentProps> = ({
  conflicts,
  day,
  dayIndex,
  dayKey,
  onOneClickFix,
}) => {
  if (conflicts.length === 0) {
    return <span style={{ fontSize: 13, color: '#16a34a' }}>无冲突</span>;  // 没有冲突时显示绿色"无冲突"
  }

  return (
    <div style={{ display: 'grid', gap: 8 }}>
      {conflicts.map((conflict) => (
        <div key={`${dayKey}-${conflict.id}`}>
          <Tag color={severityColor(conflict.severity)}>{conflict.type}</Tag>
          <div style={{ fontWeight: 600, marginTop: 2 }}>{conflict.title}</div>
          <div style={{ fontSize: 13, color: '#475569' }}>{conflict.description}</div>
          <div style={{ fontSize: 12, color: '#7c3aed' }}>建议：{conflict.suggestion}</div>
        </div>
      ))}
      <Divider style={{ margin: '6px 0' }} />
      <Button size="small" icon={<ReloadOutlined />} onClick={() => onOneClickFix(dayKey, dayIndex, day)}>
        一键修复此日
      </Button>
    </div>
  );
};
