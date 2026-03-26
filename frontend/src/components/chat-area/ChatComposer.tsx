'use client';

import React from 'react';
import { Badge, Button, Checkbox, Input, InputNumber, Popover, Select, Space, Tag } from 'antd';
import { FilterOutlined, SendOutlined, StopOutlined } from '@ant-design/icons';
import type { ChatMode } from '@/types';
import ChatModeSelector from '@/components/ChatModeSelector';
import { PRESET_CONSTRAINTS, type ComparePlanCount } from './shared';

const { TextArea } = Input;
const TEXTAREA_AUTOSIZE = process.env.NODE_ENV === 'test' ? false : { minRows: 1, maxRows: 4 };

interface ChatComposerProps {
  chatMode: ChatMode;
  compareModeEnabled: boolean;
  comparePlanCount: ComparePlanCount;
  budgetUpperLimit: number | null;
  inputValue: string;
  isStreaming: boolean;
  selectedConstraintCount: number;
  selectedConstraints: string[];
  onBudgetUpperLimitChange: (value: number | null) => void;
  onChatModeChange: (mode: ChatMode) => void;
  onCompareModeChange: (enabled: boolean) => void;
  onComparePlanCountChange: (count: ComparePlanCount) => void;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onSelectedConstraintsChange: (values: string[]) => void;
  onStop: () => void;
}

const ChatComposer: React.FC<ChatComposerProps> = ({
  chatMode,
  compareModeEnabled,
  comparePlanCount,
  budgetUpperLimit,
  inputValue,
  isStreaming,
  selectedConstraintCount,
  selectedConstraints,
  onBudgetUpperLimitChange,
  onChatModeChange,
  onCompareModeChange,
  onComparePlanCountChange,
  onInputChange,
  onSend,
  onSelectedConstraintsChange,
  onStop,
}) => {
  return (
    <div>
      <div
        style={{
          marginBottom: '14px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
          borderRadius: '14px',
          border: '1px solid rgba(0, 0, 0, 0.06)',
          boxShadow: '0 2px 10px rgba(0, 0, 0, 0.04)',
        }}
      >
        <ChatModeSelector value={chatMode} onChange={onChatModeChange} disabled={isStreaming} />
        <div
          style={{
            fontSize: '12px',
            color: '#722ed1',
            background: 'rgba(114, 46, 209, 0.08)',
            padding: '4px 12px',
            borderRadius: '12px',
          }}
        >
          {chatMode === 'direct' && '快速回答'}
          {chatMode === 'react' && '推理与工具执行'}
          {chatMode === 'plan' && '先计划再执行'}
        </div>
      </div>

      <div
        style={{
          background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
          borderRadius: '20px',
          padding: '12px',
          boxShadow: '0 8px 30px rgba(0, 0, 0, 0.12)',
          border: '1px solid rgba(0, 0, 0, 0.08)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '10px',
          }}
        >
          <Popover
            trigger="click"
            placement="topLeft"
            title={<span style={{ fontSize: '13px' }}>约束条件设置</span>}
            content={
              <div style={{ width: 340, maxWidth: 'calc(100vw - 64px)' }}>
                <div style={{ fontSize: '12px', color: '#334155', marginBottom: '8px' }}>出行限制</div>
                <Checkbox.Group
                  options={PRESET_CONSTRAINTS.map((item) => ({ label: item, value: item }))}
                  value={selectedConstraints}
                  onChange={(values) => onSelectedConstraintsChange(values as string[])}
                />

                <div style={{ fontSize: '12px', color: '#334155', margin: '12px 0 6px' }}>预算上限</div>
                <InputNumber
                  min={100}
                  max={99999}
                  value={budgetUpperLimit ?? undefined}
                  onChange={(value) => onBudgetUpperLimitChange(typeof value === 'number' ? value : null)}
                  placeholder="预算上限(元)"
                  style={{ width: '100%' }}
                />

                <div style={{ marginTop: '10px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <Checkbox checked={compareModeEnabled} onChange={(event) => onCompareModeChange(event.target.checked)}>
                    比较模式
                  </Checkbox>
                  <Select
                    size="small"
                    style={{ width: 120 }}
                    value={comparePlanCount}
                    disabled={!compareModeEnabled}
                    options={[
                      { label: '2 套方案', value: 2 },
                      { label: '3 套方案', value: 3 },
                    ]}
                    onChange={(value) => onComparePlanCountChange(value as ComparePlanCount)}
                  />
                </div>
              </div>
            }
          >
            <Badge count={selectedConstraintCount} size="small">
              <Button icon={<FilterOutlined />} size="small">
                行程约束
              </Button>
            </Badge>
          </Popover>

          {selectedConstraintCount > 0 && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                flexWrap: 'wrap',
                justifyContent: 'flex-end',
              }}
            >
              {selectedConstraints.slice(0, 3).map((item) => (
                <Tag key={item} color="blue">
                  {item}
                </Tag>
              ))}
              {budgetUpperLimit && budgetUpperLimit > 0 && <Tag color="gold">≤ {budgetUpperLimit}元</Tag>}
              {compareModeEnabled && <Tag color="purple">比较 {comparePlanCount} 套</Tag>}
            </div>
          )}
        </div>

        <Space.Compact style={{ width: '100%' }}>
          <TextArea
            value={inputValue}
            onChange={(event) => onInputChange(event.target.value)}
            onPressEnter={(event) => {
              if (!event.shiftKey) {
                event.preventDefault();
                onSend();
              }
            }}
            placeholder={isStreaming ? '正在生成回答...' : '输入你的旅行需求，例如：上海三日游如何安排'}
            disabled={isStreaming}
            autoSize={TEXTAREA_AUTOSIZE}
            style={{ resize: 'none', border: 'none', boxShadow: 'none', outline: 'none' }}
          />
          {isStreaming ? (
            <Button
              type="primary"
              danger
              icon={<StopOutlined />}
              onClick={onStop}
              style={{
                borderRadius: '14px',
                height: '42px',
                padding: '0 20px',
                background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                border: 'none',
                boxShadow: '0 4px 15px rgba(239, 68, 68, 0.4)',
              }}
            >
              停止
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={onSend}
              disabled={!inputValue.trim()}
              style={{
                borderRadius: '14px',
                height: '42px',
                padding: '0 24px',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
              }}
            >
              发送
            </Button>
          )}
        </Space.Compact>
      </div>
    </div>
  );
};

export default ChatComposer;
