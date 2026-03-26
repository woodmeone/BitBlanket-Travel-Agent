'use client';

import React from 'react';
import { Card, Tag } from 'antd';
import type { SubagentEvent, TripPlanArtifact } from '@/types';
import { buildSubagentEventKey } from '@/utils/subagentEvents';
import { buildArtifactOverviewDescriptor, subagentLabel } from '../shared';

interface ToolkitOverviewPanelProps {
  artifact: TripPlanArtifact;
  subagentEvents: SubagentEvent[];
}

function toneColor(tone: 'default' | 'success' | 'warning' | 'danger' | 'info' | undefined): string {
  if (tone === 'success') return 'green';
  if (tone === 'warning') return 'volcano';
  if (tone === 'danger') return 'red';
  if (tone === 'info') return 'geekblue';
  return 'default';
}

export const ToolkitOverviewPanel: React.FC<ToolkitOverviewPanelProps> = ({ artifact, subagentEvents }) => {
  const descriptor = buildArtifactOverviewDescriptor(artifact, subagentEvents);

  if (!descriptor) return null;

  return (
    <Card size="small" style={{ marginBottom: 12 }}>
      <div style={{ display: 'grid', gap: 10 }}>
        <div style={{ display: 'grid', gap: 6 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#0f172a' }}>{descriptor.title}</div>
          {descriptor.summary && <div style={{ fontSize: 13, color: '#334155', lineHeight: 1.7 }}>{descriptor.summary}</div>}
        </div>

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
