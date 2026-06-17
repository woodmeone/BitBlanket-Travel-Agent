// 多方案对比的空状态提示组件
// 应用场景：当没有足够的方案（少于2个）可以对比时，显示引导提示
//   告诉用户如何在提问中生成多个方案

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

import React from 'react';

export const CompareEmptyState: React.FC = () => (
  <div style={{ fontSize: 13, color: '#64748b' }}>未检测到 2 套以上可比较方案，尝试在提问中加入"省钱版 vs 轻松版"。</div>
);
