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
      <MessageList
        messages={messages}
        reasoningExpanded={{}}
        onToggleReasoning={vi.fn()}
      />
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
});
