/**
 * 【核心】应用根布局文件
 *
 * 这是 Next.js App Router 的根布局组件，所有页面都会被这个布局包裹。
 * 类比理解：如果整个应用是一本书，layout.tsx 就是书的封面和装订——
 * 每一页（每个路由页面）都在这个"封面"里面。
 *
 * Next.js App Router 约定：
 * - src/app/ 目录下的 layout.tsx 是根布局，必须存在
 * - 根布局必须包含 <html> 和 <body> 标签
 * - children 属性代表当前路由对应的页面内容（自动注入，无需手动传递）
 */

// Metadata 是 Next.js 提供的类型，用于定义页面的 SEO 元信息
import type { Metadata } from 'next';
// 导入全局样式，使这些 CSS 在整个应用生效
import './globals.css';
// AppProvider 是全局状态管理容器，为所有子组件提供共享数据
import { AppProvider } from '@/context/AppContext';
// AntdConfig 是 Ant Design 组件库的主题配置，统一管理 UI 风格
import AntdConfig from '@/components/AntdConfig';

// 【核心】metadata 是 Next.js 的 SEO 配置对象
// 这些信息会渲染到 HTML 的 <head> 中，影响浏览器标签页标题和搜索引擎收录
// 场景举例：用户在浏览器标签页看到"放心游旅行助手"，搜索引擎爬虫读取 description 了解网站用途
export const metadata: Metadata = {
  title: '放心游旅行助手 - 智能AI旅游推荐系统',
  description: '基于 ReAct Agent 架构的智能旅行助手，提供城市推荐、景点查询和行程规划功能',
  keywords: ['旅游', 'AI助手', 'ReAct Agent', '旅游推荐', '路线规划'],
  icons: {
    icon: '/favicon.ico',
  },
};

// 【核心】根布局组件
// React.ReactNode 是 React 中"任何可渲染内容"的类型，包括字符串、数字、JSX、数组等
// { children } 是 ES6 解构赋值语法——从 props 对象中取出 children 属性
// 场景举例：当用户访问首页时，children 就是 page.tsx 导出的 Home 组件
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // lang="zh-CN" 告诉浏览器页面主要语言是简体中文，影响屏幕阅读器和翻译提示
    <html lang="zh-CN">
      <body>
        {/* 组件嵌套顺序（从外到内）：AntdConfig → AppProvider → 页面内容
            - AntdConfig 在最外层：确保所有 Ant Design 组件都能读到主题配置
            - AppProvider 在中间：确保所有页面组件都能访问全局状态
            - children 在最内层：实际的页面内容 */}
        <AntdConfig>
          <AppProvider>{children}</AppProvider>
        </AntdConfig>
      </body>
    </html>
  );
}
