'use client';

import React from 'react';
import { Button } from 'antd';
import { QUICK_START_PROMPTS } from './shared';

interface QuickStartPromptsProps {
  onPickPrompt: (prompt: string) => void;
}

const QuickStartPrompts: React.FC<QuickStartPromptsProps> = ({ onPickPrompt }) => {
  return (
    <div
      style={{
        margin: '0 16px 16px',
        padding: '14px',
        borderRadius: '14px',
        border: '1px dashed rgba(30, 64, 175, 0.35)',
        background: 'linear-gradient(135deg, #ffffff 0%, #eff6ff 100%)',
      }}
    >
      <div style={{ fontSize: '13px', fontWeight: 600, color: '#1e3a8a', marginBottom: '8px' }}>3 秒上手示例</div>
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {QUICK_START_PROMPTS.map((prompt) => (
          <Button key={prompt} size="small" onClick={() => onPickPrompt(prompt)}>
            {prompt}
          </Button>
        ))}
      </div>
    </div>
  );
};

export default QuickStartPrompts;
