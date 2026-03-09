'use client';

import React from 'react';
import { Badge, Select, Tooltip } from 'antd';
import { BulbOutlined, FileTextOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { ChatMode } from '@/types';

interface ChatModeSelectorProps {
  value: ChatMode;
  onChange: (value: ChatMode) => void;
  disabled?: boolean;
}

const modeOptions = [
  {
    value: 'direct',
    label: '直答模式',
    icon: <ThunderboltOutlined />,
    description: '速度最快，直接返回答案',
    color: '#52c41a',
  },
  {
    value: 'react',
    label: 'ReAct 模式',
    icon: <BulbOutlined />,
    description: '推理 + 工具调用，适合复杂旅行问题',
    color: '#1890ff',
  },
  {
    value: 'plan',
    label: 'Plan 模式',
    icon: <FileTextOutlined />,
    description: '先展示计划，再分步执行',
    color: '#722ed1',
  },
] as const;

const ChatModeSelector: React.FC<ChatModeSelectorProps> = ({ value = 'react', onChange, disabled = false }) => {
  const activeMode = modeOptions.find((item) => item.value === value);

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <span style={{ fontSize: '12px', color: '#999', whiteSpace: 'nowrap' }}>对话模式:</span>
      <Select
        value={value}
        onChange={onChange}
        disabled={disabled}
        style={{ width: 170 }}
        size="small"
        options={modeOptions.map((option) => ({
          value: option.value,
          label: (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: option.color }}>{option.icon}</span>
              <span>{option.label}</span>
            </div>
          ),
          title: option.description,
        }))}
      />
      <Tooltip title={activeMode?.description}>
        <Badge color={activeMode?.color} text="" style={{ cursor: 'help' }} />
      </Tooltip>
    </div>
  );
};

export default ChatModeSelector;
