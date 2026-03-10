'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Progress, Space, Spin, Statistic, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { ReloadOutlined } from '@ant-design/icons';
import { apiService } from '@/services/api';
import type {
  HealthResponse,
  LLMHealthResponse,
  ToolIntentsHealthResponse,
  ToolsHealthResponse,
} from '@/types';

interface IntentRow {
  key: string;
  intent: string;
  requests: number;
  requestShare: number;
  successRate: number;
  timeoutRate: number;
  fallbackRate: number;
}

function toNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function extractRequests(metrics: Record<string, unknown>): number {
  return toNumber(
    metrics.requests ??
      metrics.total_requests ??
      metrics.count ??
      metrics.total ??
      metrics.request_count,
    0
  );
}

function extractRate(metrics: Record<string, unknown>, keys: string[], fallback = 0): number {
  for (const key of keys) {
    if (key in metrics) {
      const value = toNumber(metrics[key], fallback);
      return Math.max(0, Math.min(1, value));
    }
  }
  return fallback;
}

const SystemStatusPanel: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [llmHealth, setLlmHealth] = useState<LLMHealthResponse | null>(null);
  const [toolsHealth, setToolsHealth] = useState<ToolsHealthResponse | null>(null);
  const [intentHealth, setIntentHealth] = useState<ToolIntentsHealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [h, llm, tools, intents] = await Promise.all([
        apiService.checkHealth(),
        apiService.checkLLMHealth(),
        apiService.checkToolsHealth(),
        apiService.checkToolsIntentsHealth(),
      ]);
      setHealth(h);
      setLlmHealth(llm);
      setToolsHealth(tools);
      setIntentHealth(intents);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '加载系统状态失败');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const intentRows = useMemo<IntentRow[]>(() => {
    const aggregate = intentHealth?.intent_aggregate || {};
    const rows = Object.entries(aggregate).map(([intent, raw]) => {
      const metrics = (raw || {}) as Record<string, unknown>;
      return {
        key: intent,
        intent,
        requests: extractRequests(metrics),
        successRate:
          1 -
          extractRate(metrics, ['failure_rate', 'error_rate'], 0),
        timeoutRate: extractRate(metrics, ['timeout_rate']),
        fallbackRate: extractRate(metrics, ['fallback_rate']),
        requestShare: 0,
      };
    });

    const total = rows.reduce((sum, item) => sum + item.requests, 0);
    return rows
      .map((item) => ({
        ...item,
        requestShare: total > 0 ? item.requests / total : 0,
      }))
      .sort((a, b) => b.requests - a.requests);
  }, [intentHealth]);

  const intentColumns = useMemo<ColumnsType<IntentRow>>(
    () => [
      {
        title: 'Intent',
        dataIndex: 'intent',
        key: 'intent',
        width: 180,
        render: (value: string) => <Tag color="geekblue">{value}</Tag>,
      },
      {
        title: '请求量',
        dataIndex: 'requests',
        key: 'requests',
        width: 90,
        sorter: (a, b) => a.requests - b.requests,
      },
      {
        title: '请求占比趋势',
        dataIndex: 'requestShare',
        key: 'requestShare',
        width: 260,
        render: (value: number) => (
          <Progress
            percent={Math.round(value * 100)}
            size="small"
            strokeColor={{ '0%': '#0ea5e9', '100%': '#2563eb' }}
            format={(percent) => `${percent || 0}%`}
          />
        ),
      },
      {
        title: '成功率趋势',
        dataIndex: 'successRate',
        key: 'successRate',
        width: 230,
        render: (value: number) => (
          <Progress
            percent={Math.round(value * 100)}
            size="small"
            strokeColor={{ '0%': '#22c55e', '100%': '#15803d' }}
            format={(percent) => `${percent || 0}%`}
          />
        ),
      },
      {
        title: '超时率',
        dataIndex: 'timeoutRate',
        key: 'timeoutRate',
        width: 90,
        render: (value: number) => `${Math.round(value * 100)}%`,
      },
      {
        title: '回退率',
        dataIndex: 'fallbackRate',
        key: 'fallbackRate',
        width: 90,
        render: (value: number) => `${Math.round(value * 100)}%`,
      },
    ],
    []
  );

  return (
    <div style={{ margin: '0 16px 16px' }}>
      <Card
        style={{
          borderRadius: 16,
          border: '1px solid rgba(16, 185, 129, 0.2)',
          background: 'linear-gradient(145deg, #ffffff 0%, #f0fdf4 100%)',
        }}
        styles={{ body: { padding: 16 } }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#166534' }}>系统状态中心</div>
          <Button icon={<ReloadOutlined />} onClick={loadStatus} loading={isLoading}>
            刷新
          </Button>
        </div>

        {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 12 }} />}
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '30px 0' }}>
            <Spin />
          </div>
        ) : (
          <Space orientation="vertical" size={12} style={{ width: '100%' }}>
            <Card size="small">
              <Space wrap>
                <Tag color={health?.status === 'healthy' ? 'green' : 'red'}>API: {health?.status || 'unknown'}</Tag>
                <Tag color={llmHealth?.status === 'ok' ? 'green' : 'gold'}>LLM: {llmHealth?.status || 'unknown'}</Tag>
                <Tag color={toolsHealth?.status === 'ok' ? 'green' : 'gold'}>
                  Tools: {toolsHealth?.status || 'unknown'}
                </Tag>
                <Tag color="blue">Version: {health?.version || '-'}</Tag>
              </Space>
            </Card>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10 }}>
              <Card size="small">
                <Statistic title="工具总数" value={llmHealth?.tools_count ?? 0} />
              </Card>
              <Card size="small">
                <Statistic title="Circuit Open" value={toolsHealth?.circuit_open_count ?? 0} />
              </Card>
              <Card size="small">
                <Statistic title="监控窗口(分钟)" value={toolsHealth?.window_minutes ?? 0} />
              </Card>
              <Card size="small">
                <Statistic title="请求总量" value={intentHealth?.total_requests ?? 0} />
              </Card>
            </div>

            <Card size="small" title="Intent 聚合（结构化）">
              {intentRows.length === 0 ? (
                <div style={{ color: '#64748b' }}>暂无 intent 聚合数据</div>
              ) : (
                <Table
                  rowKey="key"
                  columns={intentColumns}
                  dataSource={intentRows}
                  pagination={false}
                  size="small"
                  scroll={{ x: 980 }}
                />
              )}
            </Card>
          </Space>
        )}
      </Card>
    </div>
  );
};

export default SystemStatusPanel;
