/* 【核心】全局状态管理 —— AppContext */
/* React Context API 是 React 提供的"全局数据共享"机制 */
/* 应用场景：想象一个树形结构的应用，如果最顶层的组件有一个数据（比如当前用户名）， */
/* 需要一层一层通过 props（属性）传递给最底层的组件，非常麻烦。Context 可以让所有组件直接访问共享数据， */
/* 就像"广播"一样，顶层 Provider（提供者）发出数据，任何层级的组件都可以用 useContext（消费者）接收数据 */
/* 本文件定义了整个应用的全局状态，包括：配置、模型选择、聊天模式、会话管理、消息列表、流式输出状态等 */
'use client';

/* createContext：创建一个"上下文"对象，用于在组件树中共享数据 */
/* useContext：在子组件中获取上下文数据 */
/* useState：创建可变状态 */
/* ReactNode：React 子元素的类型 */
import React, { createContext, useContext, useState, type ReactNode } from 'react';
/* 导入各种类型定义 */
import type { AppConfig, ChatMode, Message, ModelInfo, SessionInfo } from '@/types';
/* 导入模型引导状态钩子 */
import { useModelBootstrapState } from './useModelBootstrapState';
/* 导入会话历史状态钩子 */
import { useSessionHistoryState } from './useSessionHistoryState';

/* 【核心】API 基础地址的默认值 */
/* 优先级：1. 浏览器环境变量 window.ENV?.NEXT_PUBLIC_API_BASE */
/*         2. Node.js 环境变量 process.env.NEXT_PUBLIC_API_BASE */
/*         3. 兜底值 http://localhost:38000 */
/* 应用场景：开发环境连接本地后端（localhost:38000），生产环境连接线上后端 */
const DEFAULT_API_BASE =
  (typeof window !== 'undefined' && window.ENV?.NEXT_PUBLIC_API_BASE) ||
  process.env.NEXT_PUBLIC_API_BASE ||
  'http://localhost:38000';

/* 【核心】全局应用状态接口 —— 定义了所有共享数据的类型 */
/* 这个接口就是整个应用的"数据字典"，任何组件都可以通过 useAppContext() 获取这些数据 */
interface AppState {
  /* 应用配置 */
  config: AppConfig;                    // 配置对象（包含 API 地址等）
  setConfig: (config: AppConfig) => void;  // 修改配置的函数

  /* 模型相关 */
  availableModels: ModelInfo[];         // 可用的 AI 模型列表
  currentModelId: string | null;        // 当前选中的模型 ID
  setCurrentModelId: (modelId: string) => Promise<void>;  // 切换模型的函数（异步，因为需要通知后端）
  loadingModels: boolean;               // 是否正在加载模型列表

  /* 聊天模式 */
  chatMode: ChatMode;                   // 当前聊天模式（如 'react' 模式）
  setChatMode: (mode: ChatMode) => void;  // 切换聊天模式的函数

  /* 会话管理 */
  currentSessionId: string | null;      // 当前会话 ID
  setCurrentSessionId: (id: string | null) => void;  // 设置当前会话 ID
  switchSession: (id: string | null) => Promise<void>;  // 切换会话（异步，需要加载消息）
  refreshSessions: (includeEmpty?: boolean) => Promise<void>;  // 刷新会话列表
  sessions: SessionInfo[];              // 所有会话列表

  /* 消息管理 */
  messages: Message[];                  // 当前会话的消息列表
  addMessage: (message: Message) => void;  // 添加一条消息
  clearMessages: () => void;            // 清空消息列表
  setMessages: (messages: Message[]) => void;  // 替换整个消息列表

  /* 流式输出状态 */
  isStreaming: boolean;                 // 是否正在流式输出（AI 正在生成回答）
  setIsStreaming: (streaming: boolean) => void;  // 设置流式输出状态
  stopStreaming: boolean;               // 是否需要停止流式输出
  setStopStreaming: (stop: boolean) => void;  // 设置停止流式输出标志
}

/* 【核心】创建 React Context 对象 */
/* createContext<AppState | undefined>(undefined) 表示初始值为 undefined */
/* 初始值设为 undefined 是为了在 useAppContext 中做安全检查：如果组件不在 Provider 内部，就报错提醒 */
const AppContext = createContext<AppState | undefined>(undefined);

/* 【核心】应用状态提供者组件 —— 包裹在应用最外层，为所有子组件提供全局数据 */
/* 应用场景：在应用的根组件中用 <AppProvider> 包裹所有内容，之后任何组件都可以用 useAppContext() 获取数据 */
/* 类比：就像一个"广播站"，AppProvider 是发射器，useAppContext() 是接收器 */
export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  /* 应用配置状态 */
  const [config, setConfig] = useState<AppConfig>({ apiBase: DEFAULT_API_BASE });
  /* 流式输出状态 */
  const [isStreaming, setIsStreaming] = useState(false);
  const [stopStreaming, setStopStreaming] = useState(false);
  /* 聊天模式状态，默认 'react' 模式 */
  const [chatMode, setChatModeState] = useState<ChatMode>('react');

  /* 从会话历史状态钩子中获取会话和消息相关的状态和方法 */
  const {
    currentSessionId,
    setCurrentSessionId,
    switchSession,
    refreshSessions,
    sessions,
    messages,
    addMessage,
    clearMessages,
    setMessages,
  } = useSessionHistoryState({
    /* 当从后端恢复会话的模型 ID 时，同步更新到模型状态 */
    onRecoveredModelId: (modelId) => recoverModelId(modelId),
  });

  /* 从模型引导状态钩子中获取模型相关的状态和方法 */
  const { availableModels, currentModelId, loadingModels, recoverModelId, setCurrentModelId } =
    useModelBootstrapState({
      currentSessionId,  /* 传入当前会话 ID，以便切换模型时通知后端 */
    });

  /* 将所有状态和方法组装成一个对象，作为 Context 的值 */
  const value: AppState = {
    config,
    setConfig,
    availableModels,
    currentModelId,
    setCurrentModelId,
    loadingModels,
    chatMode,
    setChatMode: setChatModeState,
    currentSessionId,
    setCurrentSessionId,
    switchSession,
    refreshSessions,
    sessions,
    messages,
    addMessage,
    clearMessages,
    setMessages,
    isStreaming,
    setIsStreaming,
    stopStreaming,
    setStopStreaming,
  };

  /* 【核心】AppContext.Provider 是 React Context 的"提供者"组件 */
  /* value 属性就是所有子组件可以访问的共享数据 */
  /* children 是被 AppProvider 包裹的所有子组件 */
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

/* 【核心】自定义 Hook —— 获取全局应用状态的快捷方式 */
/* 应用场景：任何组件需要访问全局数据时，只需调用 const { messages, addMessage } = useAppContext() */
/* 如果组件不在 AppProvider 内部（即没有包裹 Provider），会抛出错误提醒开发者 */
export const useAppContext = (): AppState => {
  /* useContext(AppContext) 从最近的 AppContext.Provider 中获取 value */
  const context = useContext(AppContext);
  /* 安全检查：如果 context 为 undefined，说明组件不在 AppProvider 内部 */
  if (!context) throw new Error('useAppContext must be used within AppProvider');
  return context;
};
