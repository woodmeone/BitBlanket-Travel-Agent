// 'use client' 声明这是一个客户端组件
// Next.js 默认所有组件都是服务端组件（在服务器上渲染 HTML 后发给浏览器）
// 加了 'use client' 后，这个组件会在浏览器端运行，支持交互（如点击、状态管理等）
'use client';

// 导入 React 核心库，提供创建组件等基础能力
import React from 'react';
// 从 antd（蚂蚁金服 UI 组件库）导入 Tabs 标签页组件
// Tabs 用于在同一区域切换不同内容视图，类似浏览器的标签页
import { Tabs } from 'antd';
// 导入城市探索组件，用于展示城市旅游信息
import CityExplorer from '@/components/CityExplorer';
// 导入系统状态面板组件，用于展示系统运行状态信息
import SystemStatusPanel from '@/components/SystemStatusPanel';
// 导入聊天输入框组件，用于用户输入消息和设置对话参数
import ChatComposer from '@/components/chat-area/ChatComposer';
// 导入对话消息展示组件，用于渲染聊天消息列表
import ChatConversationView from '@/components/chat-area/ChatConversationView';
// 导入聊天运行时 Hook，封装了聊天相关的所有状态和逻辑
// Hook 是 React 中复用状态逻辑的机制，以 use 开头的函数就是 Hook
import { useChatRuntime } from '@/components/chat-area/useChatRuntime';

// React.FC 是 React 函数组件的类型缩写，FC = FunctionComponent
// 箭头函数 () => {} 是 ES6 的函数简写方式
// ChatArea 是主聊天区域组件，包含对话、城市探索、系统状态三个标签页
const ChatArea: React.FC = () => {
  // 调用 useChatRuntime Hook 获取聊天运行时对象
  // Hook 返回一个包含所有聊天相关状态和方法的对象
  // 例如：消息列表、输入框内容、发送方法、流式响应状态等
  // 【核心】runtime 是整个聊天功能的中枢，所有状态和操作都从这里获取
  const runtime = useChatRuntime();

  // return 中的 JSX 是 React 的模板语法，看起来像 HTML 但实际上是 JavaScript
  // JSX 会被编译成 JavaScript 对象，最终渲染为真实的 DOM 元素
  return (
    // 最外层容器 div，使用 flex 纵向布局占满整个视口高度
    // style 中的属性采用驼峰命名法（如 flexDirection 对应 CSS 的 flex-direction）
    <div
      className="chat-input-area"
      style={{
        display: 'flex',           // 弹性盒布局
        flexDirection: 'column',   // 子元素纵向排列
        height: '100vh',           // 占满整个浏览器视口高度
        padding: '24px',           // 内边距 24 像素
        background: 'linear-gradient(180deg, #fafbfc 0%, #f3f4f6 100%)', // 从上到下的渐变背景
      }}
    >
      {/* 标签页区域，用于在"对话体验"、"城市探索"、"系统状态"三个视图间切换 */}
      <div style={{ marginBottom: 10 }}>
        {/* 【核心】Tabs 组件：控制页面显示哪个视图
            - activeKey：当前选中的标签页 key，由 runtime.activeView 控制
            - onChange：标签页切换时的回调函数，更新 runtime 中的 activeView 状态
            - items：标签页配置数组，每个项包含 key（唯一标识）和 label（显示文字）
            - value as 'chat' | 'city' | 'status' 是 TypeScript 的类型断言，
              告诉编译器 value 的类型是这三个字符串之一 */}
        <Tabs
          activeKey={runtime.activeView}
          onChange={(value) => runtime.setActiveView(value as 'chat' | 'city' | 'status')}
          items={[
            { key: 'chat', label: '对话体验' },
            { key: 'city', label: '城市探索' },
            { key: 'status', label: '系统状态' },
          ]}
        />
      </div>

      {/* 内容区域，flex: 1 表示占据剩余空间，overflow: auto 内容超出时显示滚动条 */}
      <div style={{ flex: 1, overflow: 'auto', marginBottom: '16px' }}>
        {/* 条件渲染：只有当 activeView 为 'chat' 时才渲染对话视图
            && 是 React 中条件渲染的常见写法，相当于 if (条件) 则渲染 */}
        {runtime.activeView === 'chat' && (
          /* 【核心】ChatConversationView 对话消息展示组件
             通过 props（组件属性）将 runtime 中的状态传递给子组件
             props 是父组件向子组件传递数据的方式，类似函数参数 */
          <ChatConversationView
            messages={runtime.messages}                    // 消息列表数组
            messagesEndRef={runtime.messagesEndRef}        // 消息列表底部引用，用于自动滚动到底部
            streamingMessage={runtime.streamingMessage}    // 正在流式输出的消息内容
            streamingReasoning={runtime.streamingReasoning}// 正在流式输出的推理过程
            waitingForResponse={runtime.waitingForResponse}// 是否正在等待 AI 回复
            isThinking={runtime.isThinking}                // AI 是否正在思考中
            isStreaming={runtime.isStreaming}               // 是否正在流式输出
            currentTool={runtime.currentTool}              // 当前正在调用的工具信息
            reasoningExpanded={runtime.reasoningExpanded}  // 推理过程是否展开显示
            error={runtime.error}                          // 错误信息
            metadata={runtime.metadata}                    // 元数据信息
            stageState={runtime.stageState}                // 当前阶段状态（如规划中、执行中等）
            stageHistory={runtime.stageHistory}             // 阶段历史记录
            runtimeLogs={runtime.runtimeLogs}              // 运行时日志
            planPreview={runtime.planPreview}              // 行程计划预览数据
            artifactState={runtime.artifactState}          // 产物状态（如生成的行程单等）
            activeSubagent={runtime.activeSubagent}        // 当前活跃的子智能体
            subagentEvents={runtime.subagentEvents}        // 子智能体事件列表
            onContinuePrompt={runtime.handleContinueRefine}      // 继续优化提示的回调
            onPickPrompt={runtime.handlePickQuickStartPrompt}    // 选择快捷开始提示的回调
            onToggleReasoning={runtime.toggleReasoning}          // 切换推理过程展开/收起的回调
          />
        )}

        {/* 条件渲染：activeView 为 'city' 时显示城市探索视图
            onUsePrompt 是当用户在城市探索中选择某个推荐后，将推荐内容填入输入框的回调 */}
        {runtime.activeView === 'city' && <CityExplorer onUsePrompt={runtime.handleUsePromptFromExplorer} />}
        {/* 条件渲染：activeView 为 'status' 时显示系统状态面板 */}
        {runtime.activeView === 'status' && <SystemStatusPanel />}
      </div>

      {/* 只在对话视图下显示输入框组件
          ChatComposer 是用户输入消息的区域，包含输入框、发送按钮、模式选择等 */}
      {runtime.activeView === 'chat' && (
        /* 【核心】ChatComposer 聊天输入组件
           传递了大量 props 来控制输入框的行为和外观 */
        <ChatComposer
          chatMode={runtime.chatMode}                              // 聊天模式（如普通对话、行程规划等）
          compareModeEnabled={runtime.compareModeEnabled}          // 是否启用对比模式（同时生成多个方案对比）
          comparePlanCount={runtime.comparePlanCount}              // 对比模式下生成的方案数量
          budgetUpperLimit={runtime.budgetUpperLimit}              // 预算上限
          inputValue={runtime.inputValue}                          // 输入框当前文字
          isStreaming={runtime.isStreaming}                         // 是否正在流式输出（输出中禁用发送）
          selectedConstraintCount={runtime.selectedConstraintCount}// 已选约束条件数量
          selectedConstraints={runtime.selectedConstraints}        // 已选约束条件列表（如"带小孩"、"素食"等）
          onBudgetUpperLimitChange={runtime.setBudgetUpperLimit}   // 预算上限变更回调
          onChatModeChange={runtime.setChatMode}                   // 聊天模式变更回调
          onCompareModeChange={runtime.setCompareModeEnabled}      // 对比模式开关回调
          onComparePlanCountChange={runtime.setComparePlanCount}   // 对比方案数量变更回调
          onInputChange={runtime.setInputValue}                    // 输入框文字变更回调
          onSend={runtime.handleSend}                              // 发送消息回调
          onSelectedConstraintsChange={runtime.setSelectedConstraints} // 约束条件变更回调
          onStop={runtime.handleStop}                              // 停止生成回调
        />
      )}
    </div>
  );
};

// export default 将该组件作为默认导出，其他文件可以通过 import ChatArea from '...' 引入
export default ChatArea;
