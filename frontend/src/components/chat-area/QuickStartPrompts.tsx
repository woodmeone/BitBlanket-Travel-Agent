// 'use client'：客户端组件声明，因为有点击交互
'use client';

import React from 'react';
// Button：按钮组件
import { Button } from 'antd';
// QUICK_START_PROMPTS：预定义的快速开始提示语列表，定义在 shared.ts 共享文件中
// 例如：["帮我规划3天成都旅行", "推荐适合亲子游的景点", ...]
import { QUICK_START_PROMPTS } from './shared';

// QuickStartPromptsProps：快速开始提示组件接收的属性
interface QuickStartPromptsProps {
  // onPickPrompt：用户点击某个提示语后的回调函数
  // 参数 prompt 是用户选中的提示语文本，父组件会将它填入输入框并发送
  onPickPrompt: (prompt: string) => void;
}

// 【核心】QuickStartPrompts：快速开始提示组件
// 作用：在聊天界面底部显示几个预设的示例问题，帮助新用户快速上手
// 应用场景：用户第一次打开页面不知道问什么，看到"帮我规划3天成都旅行"的按钮，
// 点击后自动将这段文字填入输入框，降低使用门槛
const QuickStartPrompts: React.FC<QuickStartPromptsProps> = ({ onPickPrompt }) => {
  return (
    <div
      style={{
        margin: '0 16px 16px',
        padding: '14px',
        borderRadius: '14px',
        border: '1px dashed rgba(30, 64, 175, 0.35)',  // 虚线边框，暗示"可点击"
        background: 'linear-gradient(135deg, #ffffff 0%, #eff6ff 100%)',  // 白色到浅蓝色渐变
      }}
    >
      {/* 标题 */}
      <div style={{ fontSize: '13px', fontWeight: 600, color: '#1e3a8a', marginBottom: '8px' }}>3 秒上手示例</div>
      {/* 提示语按钮列表 */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {/* map()：遍历提示语列表，为每个提示语生成一个按钮 */}
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
