import { App } from 'antd';
import { fireEvent, render, screen } from '@testing-library/react';
import type React from 'react';
import { describe, expect, it, vi } from 'vitest';
import ChatComposer from '@/components/chat-area/ChatComposer';

const renderWithApp = (ui: React.ReactElement) => render(<App>{ui}</App>);

const baseProps = {
  chatMode: 'react' as const,
  compareModeEnabled: false,
  comparePlanCount: 2 as const,
  budgetUpperLimit: null,
  inputValue: '',
  isStreaming: false,
  selectedConstraintCount: 0,
  selectedConstraints: [] as string[],
  onBudgetUpperLimitChange: vi.fn(),
  onChatModeChange: vi.fn(),
  onCompareModeChange: vi.fn(),
  onComparePlanCountChange: vi.fn(),
  onInputChange: vi.fn(),
  onSend: vi.fn(),
  onSelectedConstraintsChange: vi.fn(),
  onStop: vi.fn(),
};

describe('ChatComposer', () => {
  it('disables send when input is empty and enables it when input exists', () => {
    const firstRender = renderWithApp(<ChatComposer {...baseProps} />);

    expect(screen.getByRole('button', { name: /发送/ })).toBeDisabled();

    firstRender.unmount();
    renderWithApp(<ChatComposer {...baseProps} inputValue="上海周末两日游" />);

    expect(screen.getByRole('button', { name: /发送/ })).not.toBeDisabled();
  });

  it('shows selected constraint summary tags', () => {
    renderWithApp(
      <ChatComposer
        {...baseProps}
        budgetUpperLimit={2000}
        compareModeEnabled
        comparePlanCount={3}
        inputValue="杭州 2 日游"
        selectedConstraintCount={3}
        selectedConstraints={['亲子']}
      />
    );

    expect(screen.getByText('亲子')).toBeInTheDocument();
    expect(screen.getByText('≤ 2000元')).toBeInTheDocument();
    expect(screen.getByText('比较 3 套')).toBeInTheDocument();
  });

  it('renders stop button while streaming and triggers stop callback', () => {
    const onStop = vi.fn();
    renderWithApp(<ChatComposer {...baseProps} isStreaming onStop={onStop} inputValue="生成中" />);

    const stopButton = screen.getByRole('button', { name: /停止/ });
    expect(stopButton).toBeInTheDocument();
    fireEvent.click(stopButton);
    expect(onStop).toHaveBeenCalledTimes(1);
  });
});
