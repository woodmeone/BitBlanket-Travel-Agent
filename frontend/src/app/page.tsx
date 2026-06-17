// 'use client' 声明这是一个客户端组件
// Next.js 默认所有组件都是服务端组件（在服务器上渲染 HTML 后发给浏览器）
// 加了 'use client' 后，这个组件会在浏览器端运行，支持交互（如点击、状态管理等）
// 场景举例：本页面包含 antd 的 Layout 组件（需要浏览器端交互），所以必须声明为客户端组件
'use client';

/**
 * 【核心】首页——聊天主界面
 *
 * 这是用户访问网站根路径 "/" 时看到的页面。
 * 页面采用左右分栏布局：左侧是会话侧边栏，右侧是聊天工作区。
 *
 * 整体布局结构：
 * ┌──────────────┬───────────────────────────┐
 * │   Sidebar    │       ChatArea            │
 * │  (280px固定) │     (剩余空间)             │
 * │  会话列表     │   聊天消息 + 输入框        │
 * └──────────────┴───────────────────────────┘
 */

// 从 antd 组件库导入 Layout 布局组件
// antd (Ant Design) 是蚂蚁集团开源的 React UI 组件库，提供大量开箱即用的组件
import { Layout } from 'antd';
// ChatArea 是右侧聊天区域组件，包含消息列表和输入框
import ChatArea from '@/components/ChatArea';
// Sidebar 是左侧边栏组件，包含会话历史列表
import Sidebar from '@/components/Sidebar';

// 【核心】首页组件
// export default 表示这是模块的默认导出，Next.js 通过这个约定找到页面组件
// function Home() 是 React 函数组件的写法，函数名即组件名
export default function Home() {
  return (
    // Layout 是 antd 的布局容器组件，提供整体页面结构
    // style={{}} 是 React 中写内联样式的方式，使用 JavaScript 对象而非 CSS 字符串
    // minHeight: '100vh' 表示最小高度为视窗高度的 100%，确保页面撑满屏幕
    // background: 'transparent' 透明背景，让 globals.css 中定义的渐变背景透出来
    <Layout style={{
      minHeight: '100vh',
      background: 'transparent'
    }}>
      {/* Layout.Sider 是 antd 的侧边栏组件
          - width={280} 侧边栏宽度 280 像素
          - theme="light" 使用浅色主题（默认是深色）
          - position="fixed" 固定定位，侧边栏不随页面滚动
          - left/top/bottom: 0 配合 fixed，让侧边栏贴紧左侧，占满全高
          - zIndex: 100 确保侧边栏在其他内容之上
          - background 使用 CSS 渐变：从白色过渡到浅灰色
          - boxShadow 添加右侧阴影，营造层次感 */}
      <Layout.Sider
        width={280}
        theme="light"
        style={{
          borderRight: '1px solid rgba(102, 126, 234, 0.1)',
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
          background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
          boxShadow: '4px 0 20px rgba(102, 126, 234, 0.08)',
        }}
      >
        <Sidebar />
      </Layout.Sider>
      {/* 右侧主内容区
          - marginLeft: 280 与侧边栏宽度一致，避免内容被固定侧边栏遮挡
          - transition: 'margin-left 0.3s ease' 添加过渡动画，侧边栏收起/展开时平滑移动 */}
      <Layout style={{
        marginLeft: 280,
        transition: 'margin-left 0.3s ease',
        background: 'transparent'
      }}>
        {/* Layout.Content 是 antd 的内容区域组件 */}
        <Layout.Content style={{
          margin: 0,
          minHeight: '100vh',
          background: 'transparent'
        }}>
          {/* ChatArea 是核心聊天组件，包含消息展示和输入交互 */}
          <ChatArea />
        </Layout.Content>
      </Layout>
    </Layout>
  );
}
