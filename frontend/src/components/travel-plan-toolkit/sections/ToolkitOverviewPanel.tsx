// 【核心】行程概览面板组件
// 应用场景：在工具包顶部展示当前方案的核心摘要信息
//   包括：方案标题、摘要文字、指标卡片（目的地/预算/校验状态等）、风险提示、子 Agent 协作轨迹

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';
import { Card, Tag } from 'antd';
import type { SubagentEvent, TripPlanArtifact } from '@/types';
import { buildSubagentEventKey } from '@/utils/subagentEvents';
import { buildArtifactOverviewDescriptor, subagentLabel } from '../shared';

// ToolkitOverviewPanelProps 概览面板接收的参数
interface ToolkitOverviewPanelProps {
  artifact: TripPlanArtifact;        // 旅行方案制品数据
  subagentEvents: SubagentEvent[];   // 子 Agent 事件列表
}

// 将指标语气转换为 Ant Design Tag 颜色
function toneColor(tone: 'default' | 'success' | 'warning' | 'danger' | 'info' | undefined): string {
  if (tone === 'success') return 'green';     // 成功 → 绿色
  if (tone === 'warning') return 'volcano';   // 警告 → 火山红
  if (tone === 'danger') return 'red';        // 危险 → 红色
  if (tone === 'info') return 'geekblue';     // 信息 → 极客蓝
  return 'default';                            // 默认 → 灰色
}

export const ToolkitOverviewPanel: React.FC<ToolkitOverviewPanelProps> = ({ artifact, subagentEvents }) => {
  const descriptor = buildArtifactOverviewDescriptor(artifact, subagentEvents);  // 构建概览描述符

  if (!descriptor) return null;  // 无制品数据时不渲染

  return (
    <Card size="small" style={{ marginBottom: 12 }}>
      <div style={{ display: 'grid', gap: 10 }}>
        {/* 方案标题和摘要 */}
        <div style={{ display: 'grid', gap: 6 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#0f172a' }}>{descriptor.title}</div>
          {descriptor.summary && <div style={{ fontSize: 13, color: '#334155', lineHeight: 1.7 }}>{descriptor.summary}</div>}
        </div>

        {/* 指标卡片网格 */}
        {descriptor.metrics.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10 }}>
            {descriptor.metrics.map((metric) => (
              <div
                key={metric.label}
                style={{
                  borderRadius: 12,
                  padding: '10px 12px',
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                }}
              >
                <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{metric.label}</div>
                <Tag color={toneColor(metric.tone)} style={{ marginInlineEnd: 0 }}>
                  {metric.value}
                </Tag>
              </div>
            ))}
          </div>
        )}

        {/* 风险提示区域 */}
        {descriptor.warnings.length > 0 && (
          <div style={{ display: 'grid', gap: 6 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#9a3412' }}>风险提示</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {descriptor.warnings.map((warning) => (
                <Tag key={warning} color="orange">
                  {warning}
                </Tag>
              ))}
            </div>
          </div>
        )}

        {/* 子 Agent 协作轨迹 */}
        {subagentEvents.length > 0 && (
          <div style={{ display: 'grid', gap: 6 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#155e75' }}>
              子 Agent 轨迹
              {descriptor.subagentTrail.length > 0 ? `：${descriptor.subagentTrail.join(' -> ')}` : ''}
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {subagentEvents.map((event, index) => (
                <Tag key={buildSubagentEventKey(event, index)} color={event.status ? 'green' : 'blue'}>
                  {subagentLabel(event.subagent)}
                  {event.status ? `:${event.status}` : ''}
                </Tag>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
