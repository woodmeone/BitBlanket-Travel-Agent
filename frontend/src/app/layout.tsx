/**
 * Application root layout and global metadata declarations.
 * This file defines the shell that wraps all pages in the App Router.
 */

import type { Metadata } from 'next';
import './globals.css';
import { AppProvider } from '@/context/AppContext';
import AntdConfig from '@/components/AntdConfig';

export const metadata: Metadata = {
  title: '小帅旅游助手 - 智能AI旅游推荐系统',
  description: '基于 ReAct Agent 架构的智能旅行助手，提供城市推荐、景点查询和行程规划功能',
  keywords: ['旅游', 'AI助手', 'ReAct Agent', '旅游推荐', '路线规划'],
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <AntdConfig>
          <AppProvider>{children}</AppProvider>
        </AntdConfig>
      </body>
    </html>
  );
}
