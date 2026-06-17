// 'use client' 是 Next.js 的指令，表示这个组件只在浏览器端运行（客户端组件）
// 在 Next.js 中，默认组件在服务器端渲染，加上这个指令后组件会在浏览器中运行，支持交互和状态管理
'use client';

/**
 * Ant Design 运行时配置提供者 —— 统一管理全局主题和语言设置
 *
 * 【核心】这个组件包裹在整个应用的最外层，作用是给所有 Ant Design 组件提供统一的样式配置
 * 类比：就像给整个办公室统一采购办公用品，所有人用到的按钮、输入框颜色和圆角都由这里决定
 *
 * 使用方式：在根布局文件中用 <AntdConfig> 包裹页面内容，所有子组件自动继承这些配置
 */

// import：从外部库引入需要的功能，类似"从工具箱里拿出需要的工具"
// React 是前端框架的核心库，所有组件都基于它
import React from 'react';
// ConfigProvider：Ant Design 的全局配置组件，用来设置主题色、圆角等样式
// App as AntApp：Ant Design 的应用容器，提供消息提示、弹窗等全局功能；用 as 重命名避免与变量名冲突
import { ConfigProvider, App as AntApp } from 'antd';

// React.FC 是 TypeScript 中定义函数组件的类型写法，FC = Function Component（函数组件）
// { children: React.ReactNode } 表示这个组件接收一个 children 属性，类型是"任意可渲染的内容"
// children 就像是组件的"插槽"，包裹在 <AntdConfig>...</AntdConfig> 之间的内容都会通过 children 传入
const AntdConfig: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    // 【核心】ConfigProvider 通过 theme.token 设置全局设计令牌（Design Token）
    // token 可以理解为"设计变量"，修改它们会自动影响所有 Ant Design 组件的样式
    <ConfigProvider
      theme={{
        token: {
          // colorPrimary：主色调，影响按钮、链接、选中状态等的颜色
          // '#1890ff' 是 Ant Design 经典蓝色，类似微信的绿色、淘宝的橙色
          colorPrimary: '#1890ff',
          // borderRadius：全局圆角大小，单位是像素
          // 值越大，按钮和卡片的角越圆；0 表示直角
          borderRadius: 6,
        },
      }}
    >
      {/* AntApp 提供全局的 message（消息提示）、notification（通知）、modal（弹窗）功能 */}
      <AntApp>
        {/* children：渲染被包裹的子组件内容 */}
        {children}
      </AntApp>
    </ConfigProvider>
  );
};

// export default：将这个组件作为默认导出，其他文件可以通过 import AntdConfig from './AntdConfig' 来使用
export default AntdConfig;
