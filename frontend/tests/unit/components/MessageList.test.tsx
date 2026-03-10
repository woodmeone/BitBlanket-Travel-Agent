import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App } from 'antd';
import type React from 'react';
import MessageList from '@/components/MessageList';
import type { Message } from '@/types';

const renderWithApp = (ui: React.ReactElement) => {
  return render(<App>{ui}</App>);
};

describe('MessageList', () => {
  it('renders user and assistant messages', () => {
    const messages: Message[] = [
      { role: 'user', content: 'Hello', timestamp: '10:00' },
      { role: 'assistant', content: 'Hi there', timestamp: '10:01' },
    ];

    renderWithApp(
      <MessageList messages={messages} reasoningExpanded={{}} onToggleReasoning={vi.fn()} />
    );

    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there')).toBeInTheDocument();
  });

  it('shows streaming message while waiting', () => {
    renderWithApp(
      <MessageList
        messages={[]}
        streamingMessage="partial answer"
        isWaiting
        reasoningExpanded={{}}
        onToggleReasoning={vi.fn()}
      />
    );

    expect(screen.getByText('partial answer')).toBeInTheDocument();
  });

  it('renders assistant diagnostics metadata', () => {
    const messages: Message[] = [
      {
        role: 'assistant',
        content: '诊断展示',
        timestamp: '10:02',
        diagnostics: {
          toolsUsed: ['get_weather', 'query_hotels'],
          verificationPassed: false,
          staleResultCount: 1,
          fallbackSteps: 2,
        },
      },
    ];

    renderWithApp(
      <MessageList messages={messages} reasoningExpanded={{}} onToggleReasoning={vi.fn()} />
    );

    expect(screen.getByText('验证状态: 未通过')).toBeInTheDocument();
    expect(screen.getByText('过期结果: 1 条')).toBeInTheDocument();
    expect(screen.getByText('备源切换: 2 次')).toBeInTheDocument();
    expect(screen.getByText('工具列表: get_weather, query_hotels')).toBeInTheDocument();
  });

  it('renders richer markdown blocks for assistant messages', () => {
    const messages: Message[] = [
      {
        role: 'assistant',
        timestamp: '10:03',
        content: [
          '# 行程建议',
          '',
          '> 先锁定预约景点',
          '',
          '```bash',
          'pnpm plan-trip',
          '```',
          '',
          '---',
          '',
          '[查看预约](https://example.com)',
        ].join('\n'),
      },
    ];

    const { container } = renderWithApp(
      <MessageList messages={messages} reasoningExpanded={{}} onToggleReasoning={vi.fn()} />
    );

    expect(screen.getByRole('heading', { name: '行程建议' })).toBeInTheDocument();
    expect(container.querySelector('blockquote')).not.toBeNull();
    expect(container.querySelector('pre')).not.toBeNull();
    expect(container.querySelector('hr')).not.toBeNull();
    expect(screen.getByRole('link', { name: '查看预约' })).toHaveAttribute('href', 'https://example.com');
  });
});
