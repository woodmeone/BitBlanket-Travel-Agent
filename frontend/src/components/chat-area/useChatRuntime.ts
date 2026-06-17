// 【核心】useChatRuntime.ts — 聊天运行时的核心自定义 Hook
// 本文件管理聊天系统的所有运行时状态和流式通信逻辑，是整个聊天功能的中枢
//
// 核心职责：
// 1. 管理聊天输入、流式响应、思考状态等 UI 状态
// 2. 协调会话创建、消息发送、流式接收的完整流程
// 3. 处理 AI 回复中的推理过程、工具调用、子 Agent、Artifact 等事件
// 4. 支持中断（停止生成）和错误恢复
//
// 场景举例：用户输入"帮我规划三亚5日游"并点击发送
// → handleSend 被调用 → 准备输入 → 创建/获取会话 → 发起流式请求
// → 逐步接收 AI 的推理过程(onReasoning)、正文(onChunk)、工具调用(onToolStart/End)
// → 最终完成(onComplete)将完整消息写入聊天记录

'use client';
// 'use client' 是 Next.js 的标记，表示这个组件/Hook 在浏览器端运行（而非服务器端渲染）
// 只有标记了 'use client' 的文件才能使用 useState、useEffect 等浏览器端 Hook

// React 核心 Hook 和类型
import React, { useEffect, useRef, useState } from 'react';
// useState: 声明响应式状态，状态变化会触发组件重新渲染
// useEffect: 副作用 Hook，在组件渲染后执行（如订阅、定时器、DOM 操作）
// useRef: 创建"引用"，与 useState 的区别是修改 .current 不会触发重渲染，适合存不参与渲染的数据

// Ant Design 的全局提示组件，用于显示 success/error/warning 消息
import { App } from 'antd';

// 全局应用上下文，提供会话ID、消息列表、流式状态等共享数据
import { useAppContext } from '@/context/AppContext';

// API 客户端：chatClient 负责流式聊天请求，sessionClient 负责会话管理
// StreamMetadata 是流式响应的元数据类型
import { chatClient, sessionClient, type StreamMetadata } from '@/services/api';

// 类型定义：PlanPreview(计划预览)、StreamStageEvent(流式阶段事件)、
// SubagentEvent(子Agent事件)、TripPlanArtifact(行程计划结构化数据)
import type { PlanPreview, StreamStageEvent, SubagentEvent, TripPlanArtifact } from '@/types';

// 日志工具，用于开发调试时输出日志
import { logger } from '@/utils/logger';

// 合并行程计划 Artifact 的工具函数（将增量补丁合并到已有 Artifact）
import { mergeTripPlanArtifact } from '@/utils/agentArtifacts';

// 聊天区域内部共享的工具函数和类型
import {
  messageTimestamp,   // 生成消息时间戳
  subagentLabel,      // 获取子Agent的可读标签名
  type ActiveView,    // 当前活跃视图类型（'chat' | 'plan' | ...）
  type ComparePlanCount, // 对比模式下的方案数量（2 或 3）
  type RuntimeLog,    // 运行时日志条目
} from './shared';

// 聊天输入预处理：校验输入、组装富化提示词、生成会话名称
import { buildStoppedMessageContent, prepareChatInput } from './chatInputPolicy';

// 子 Hook：Artifact 运行时状态管理（行程计划的结构化数据）
import { useArtifactRuntimeState } from './useArtifactRuntimeState';

// 子 Hook：聊天运行状态管理（工具调用、思考状态、阶段追踪等）
import { useChatRunState } from './useChatRunState';

// 子 Hook：流式缓冲区管理（将流式数据分批更新到UI，避免频繁渲染）
import { useStreamBuffer } from './useStreamBuffer';

// 子 Hook：会话水合（从服务端元数据恢复聊天状态，用于页面刷新后恢复）
import { useChatSessionHydration } from './useChatSessionHydration';

// 运行时消息构建器：生成完成/中断时的诊断信息
import { buildCompletionDiagnostics, buildFinalReasoning, buildStoppedDiagnostics } from './runtimeMessageBuilders';

// 【核心】UseChatRuntimeResult — useChatRuntime Hook 的返回值类型定义
// interface 是 TypeScript 中定义对象"形状"的方式，规定了对象必须有哪些字段及字段类型
// 这个接口定义了聊天运行时对外暴露的所有状态和操作方法，供 UI 组件使用
interface UseChatRuntimeResult {
  activeSubagent: string | null;         // 当前正在运行的子Agent名称，如"酒店搜索Agent"；null表示无子Agent运行
  activeView: ActiveView;                // 当前活跃视图：'chat'(聊天) | 'plan'(计划) 等，控制右侧面板显示内容
  artifactState: TripPlanArtifact | null;// 行程计划的结构化数据（Artifact），包含景点、酒店、交通等；null表示暂无
  budgetUpperLimit: number | null;       // 用户设置的预算上限（元），null表示未设置
  chatMode: ReturnType<typeof useAppContext>['chatMode']; // 当前聊天模式，如'plan'(规划模式)、'chat'(闲聊模式)
  // ReturnType<typeof useAppContext>['chatMode'] 是 TypeScript 的工具类型写法：
  // 表示"取 useAppContext 返回值类型中的 chatMode 字段的类型"，避免重复定义
  compareModeEnabled: boolean;           // 是否开启了方案对比模式（同时生成2-3个方案供比较）
  comparePlanCount: ComparePlanCount;    // 对比模式下的方案数量，2或3
  currentTool: string | null;            // 当前正在调用的工具名称，如"search_hotel"；null表示无工具调用
  error: string | null;                  // 最近一次错误信息；null表示无错误
  inputValue: string;                    // 输入框当前文本内容
  isStreaming: boolean;                  // 是否正在接收流式响应（AI正在"打字"中）
  isThinking: boolean;                   // AI是否正在推理/思考中（对应"思考中..."动画）
  messages: ReturnType<typeof useAppContext>['messages']; // 聊天消息列表，包含用户和助手的所有消息
  messagesEndRef: React.RefObject<HTMLDivElement | null>; // 消息列表底部DOM引用，用于自动滚动到底部
  // React.RefObject 是 React 的泛型类型，泛型<T>表示"这个类型可以适配不同的具体类型"
  // 这里 RefObject<HTMLDivElement> 表示"指向一个 div 元素的引用"
  metadata: StreamMetadata | null;       // 流式响应的元数据（工具使用情况、耗时等）；null表示暂无
  planPreview: PlanPreview | null;       // 计划预览数据，AI生成行程计划时的中间预览状态
  reasoningExpanded: Record<string, boolean>; // 各消息的推理过程展开状态，key是消息ID，value是是否展开
  // Record<string, boolean> 是 TypeScript 的工具类型，表示"键为string、值为boolean的对象"
  // 例如：{ "msg1": true, "msg2": false } 表示消息1的推理展开，消息2的推理折叠
  runtimeLogs: RuntimeLog[];             // 运行时日志列表，记录工具调用、子Agent启停等事件，用于调试面板
  selectedConstraintCount: number;       // 用户选中的约束条件总数（含预算、对比模式等附加条件）
  selectedConstraints: string[];         // 用户选中的约束条件列表，如["亲子游","海岛"]
  stageHistory: StreamStageEvent[];      // 流式阶段历史记录，如["理解需求","搜索信息","生成方案"]
  stageState: StreamStageEvent | null;   // 当前流式阶段，如"生成方案"；null表示空闲
  streamingMessage: string;              // 正在流式接收中的AI回复文本（逐字增长的"打字"效果）
  streamingReasoning: string;            // 正在流式接收中的AI推理过程文本
  subagentEvents: SubagentEvent[];       // 子Agent事件列表，记录各子Agent的启动和完成
  waitingForResponse: boolean;           // 是否正在等待AI首次响应（请求已发出但还没收到任何数据）
  handleContinueRefine: (prompt: string) => void; // 继续细化：将细化指令填入输入框并切换到规划模式
  // (prompt: string) => void 表示"接收一个string参数、无返回值的函数"
  handlePickQuickStartPrompt: (prompt: string) => void; // 快速开始：将预设提示词填入输入框
  handleSend: () => Promise<void>;       // 【核心】发送消息，触发整个流式聊天流程
  // Promise<void> 表示"一个异步操作"，async函数的返回值类型
  // Promise 可以理解为"承诺未来会完成的事"：调用后不会立即完成，而是稍后异步完成
  handleStop: () => void;                // 停止生成：中断正在进行的流式响应
  handleUsePromptFromExplorer: (prompt: string) => void; // 从探索器使用提示词：填入提示词并切换到规划模式
  setActiveView: React.Dispatch<React.SetStateAction<ActiveView>>; // 设置当前活跃视图
  // React.Dispatch<React.SetStateAction<T>> 是 useState 返回的 setter 函数的类型
  // 调用方式：setActiveView('plan') 即可切换视图
  setBudgetUpperLimit: React.Dispatch<React.SetStateAction<number | null>>; // 设置预算上限
  setChatMode: ReturnType<typeof useAppContext>['setChatMode']; // 切换聊天模式
  setCompareModeEnabled: React.Dispatch<React.SetStateAction<boolean>>; // 开关对比模式
  setComparePlanCount: React.Dispatch<React.SetStateAction<ComparePlanCount>>; // 设置对比方案数量
  setInputValue: React.Dispatch<React.SetStateAction<string>>; // 设置输入框内容
  setSelectedConstraints: React.Dispatch<React.SetStateAction<string[]>>; // 设置选中的约束条件
  toggleReasoning: (messageId: string) => void; // 切换某条消息的推理过程展开/折叠
}

// 【核心】useChatRuntime — 聊天运行时的核心自定义 Hook
// 自定义 Hook 是 React 中复用状态逻辑的方式：以 use 开头的函数，内部可以使用 useState/useEffect 等
// 与普通函数的区别：自定义 Hook 可以使用 React 的状态 Hook，普通函数不行
// export 表示这个函数可以被其他文件导入使用
//
// 场景举例：用户在输入框输入"帮我规划三亚5日游"并点击发送，这个 Hook 负责整个流程：
// 1. 准备输入数据 → 2. 创建/获取会话 → 3. 发起流式请求 → 4. 逐步接收AI响应 → 5. 更新UI状态
export function useChatRuntime(): UseChatRuntimeResult {
  // ========== 从全局上下文中获取共享状态和方法 ==========
  const {
    currentSessionId,    // 当前会话ID，标识用户正在哪个对话中
    setCurrentSessionId, // 设置当前会话ID（切换对话时使用）
    messages,            // 当前会话的消息列表
    addMessage,          // 向消息列表添加新消息
    isStreaming,         // 是否正在流式接收中
    setIsStreaming,      // 设置流式接收状态
    setStopStreaming,    // 设置停止流式接收的标记
    refreshSessions,     // 刷新会话列表（发送消息后侧边栏需要更新）
    chatMode,            // 当前聊天模式（'plan'规划 / 'chat'闲聊）
    setChatMode,         // 切换聊天模式
    setMessages,         // 直接设置消息列表（用于水合恢复等场景）
  } = useAppContext();

  // Ant Design 的消息提示 API，用于弹出 success/error/warning 提示
  const { message } = App.useApp();

  // ========== 本地 UI 状态 ==========
  const [activeView, setActiveView] = useState<ActiveView>('chat');       // 当前活跃视图，默认聊天视图
  const [inputValue, setInputValue] = useState('');                       // 输入框文本
  const [streamingMessage, setStreamingMessage] = useState('');           // 流式接收中的AI回复文本（逐字增长）
  const [streamingReasoning, setStreamingReasoning] = useState('');       // 流式接收中的推理过程文本
  const [reasoningExpanded, setReasoningExpanded] = useState<Record<string, boolean>>({}); // 各消息推理展开状态
  const [selectedConstraints, setSelectedConstraints] = useState<string[]>([]); // 用户选中的约束条件
  const [budgetUpperLimit, setBudgetUpperLimit] = useState<number | null>(null); // 预算上限
  const [compareModeEnabled, setCompareModeEnabled] = useState(false);    // 对比模式开关
  const [comparePlanCount, setComparePlanCount] = useState<ComparePlanCount>(2); // 对比方案数量，默认2个

  // ========== useRef 引用 ==========
  // useRef 与 useState 的关键区别：修改 .current 不会触发组件重新渲染
  // 适合存储"需要跨渲染周期保持、但不参与UI渲染"的数据
  // 例如：中断标记、流式累积文本等——这些数据变化不需要立即反映到UI上
  const messagesEndRef = useRef<HTMLDivElement>(null);  // 消息列表底部DOM元素引用，用于自动滚动
  const stopRef = useRef(false);                        // 【核心】中断标记：设为true时流式请求会停止

  // ========== 子 Hook：聊天运行状态管理 ==========
  // 管理 AI 回复过程中的工具调用、思考状态、阶段追踪等运行时状态
  const {
    currentTool,      // 当前正在调用的工具名称
    error,            // 最近一次错误信息
    isThinking,       // AI是否正在推理中
    runtimeLogs,      // 运行时日志列表
    stageHistory,     // 流式阶段历史
    stageState,       // 当前流式阶段
    waitingForResponse, // 是否等待首次响应
    beginRun,         // 开始一次运行（重置状态并标记开始）
    completeRun,      // 完成一次运行（标记结束）
    failRun,          // 运行失败（记录错误）
    pushRuntimeLog,   // 添加一条运行时日志
    recordStage,      // 记录流式阶段变化
    recordToolEnd,    // 记录工具调用结束
    recordToolStart,  // 记录工具调用开始
    resetRunState,    // 重置所有运行状态
    setThinking,      // 设置思考状态
    stopRun,          // 停止运行（标记为已中断）
  } = useChatRunState();

  // ========== 子 Hook：Artifact 运行时状态管理 ==========
  // Artifact 是AI生成的结构化数据（如行程计划），这个 Hook 管理其状态和增量更新
  const {
    activeSubagent,        // 当前运行的子Agent名称
    artifactRef,           // Artifact 的 ref 引用（不触发渲染的实时数据）
    artifactState,         // Artifact 的响应式状态（触发渲染）
    planPreview,           // 计划预览数据
    subagentEvents,        // 子Agent事件列表
    subagentEventsRef,     // 子Agent事件的 ref 引用
    applyArtifactPatch,    // 应用Artifact增量补丁（将新数据合并到已有Artifact）
    recordSubagentEvent,   // 记录一个子Agent事件
    resetArtifactRuntimeState, // 重置Artifact运行时状态
    setPlanPreview,        // 设置计划预览
  } = useArtifactRuntimeState();

  // ========== 子 Hook：流式缓冲区管理 ==========
  // 流式响应是逐字到达的，如果每个字都触发渲染会导致性能问题
  // 这个 Hook 通过缓冲队列+定时刷新的方式，将高频更新合并为低频批量更新
  const {
    fullReasoningRef,      // 完整推理文本的 ref（累积所有推理内容）
    fullResponseRef,       // 完整回复文本的 ref（累积所有回复内容）
    reasoningTimestampRef, // 推理时间戳的 ref
    streamScrollMarker,    // 流式滚动标记（变化时触发滚动）
    clearStreamRuntimeRefs,   // 清空所有流式 ref 数据
    drainStreamingQueueToRefs, // 将缓冲队列中的数据刷新到 ref 中（确保数据不丢失）
    enqueueAnswer,         // 将一段回复文本加入缓冲队列
    enqueueReasoning,      // 将一段推理文本加入缓冲队列
    scheduleScrollToBottom, // 调度一次滚动到底部的操作
    setReasoningTimestamp,  // 设置推理时间戳
  } = useStreamBuffer({
    messagesEndRef,
    setStreamingMessage,
    setStreamingReasoning,
  });

  // ========== 子 Hook：会话水合 ==========
  // "水合"(Hydration)是指从服务端返回的元数据中恢复聊天状态
  // 场景：页面刷新后，需要从服务端元数据恢复Artifact、阶段状态等，避免丢失进度
  const { clearHydrationMetadata, markSkipNextSessionReset, metadataRef, setHydrationMetadata } = useChatSessionHydration({
    currentSessionId,           // 当前会话ID
    clearStreamRuntimeRefs,     // 清空流式ref的方法
    messageApi: message,        // Ant Design 消息提示API
    resetArtifactRuntimeState,  // 重置Artifact状态的方法
    resetRunState,              // 重置运行状态的方法
    setActiveView,              // 设置活跃视图的方法
    setCurrentSessionId,        // 设置会话ID的方法
    setIsStreaming,             // 设置流式状态的方法
    setMessages,                // 设置消息列表的方法
    setStopStreaming,           // 设置停止标记的方法
    setStreamingMessage,        // 设置流式消息的方法
    setStreamingReasoning,      // 设置流式推理的方法
    stopRef,                    // 中断标记ref
  });

  // 清除Artifact运行时状态：同时清除水合元数据和Artifact状态
  // 在发送新消息或发生错误时调用，确保上一次的残留状态不会影响新一轮对话
  const clearArtifactRuntimeState = () => {
    clearHydrationMetadata();
    resetArtifactRuntimeState();
  };

  // ========== 自动滚动到底部 ==========
  // useEffect 是 React 的副作用 Hook，在依赖项变化时执行
  // 依赖数组 [messages.length, streamScrollMarker, ...] 表示：
  // 当消息数量变化、滚动标记变化、思考状态变化、工具调用变化、日志变化时，自动滚动到底部
  // 这样用户在AI回复过程中始终能看到最新内容
  useEffect(() => {
    scheduleScrollToBottom();
  }, [messages.length, streamScrollMarker, isThinking, waitingForResponse, currentTool, runtimeLogs.length]);

  // 切换某条消息的推理过程展开/折叠
  // prev => ({...prev, [messageId]: !prev[messageId]}) 是函数式更新：
  // 先拿到之前的状态prev，复制所有字段(...prev)，然后翻转指定消息的展开状态
  const toggleReasoning = (messageId: string) => {
    setReasoningExpanded((prev) => ({ ...prev, [messageId]: !prev[messageId] }));
  };

  // 计算用户选中的约束条件总数
  // = 用户手动选择的约束数量 + 预算条件(如果设了预算则+1) + 对比模式(如果开启则+1)
  // 场景：用户选了"亲子游""海岛"2个约束，设了预算5000，开了对比模式 → 总数 = 2+1+1 = 4
  const selectedConstraintCount =
    selectedConstraints.length + (budgetUpperLimit && budgetUpperLimit > 0 ? 1 : 0) + (compareModeEnabled ? 1 : 0);

  // 【核心】handleSend — 发送消息并启动流式聊天
  // async 表示这是一个异步函数，内部可以使用 await 等待异步操作完成
  // async/await 是处理异步操作的语法：await 会"暂停"函数执行直到异步操作完成，然后继续往下走
  // 比传统的 .then() 链式写法更直观，效果等价但代码更易读
  //
  // 完整流程（以用户输入"帮我规划三亚5日游"为例）：
  // 步骤1: prepareChatInput — 校验输入、组装富化提示词（将约束条件、预算等附加到用户输入）
  // 步骤2: 创建/获取会话 — 如果没有当前会话则创建新会话
  // 步骤3: 添加用户消息到聊天记录
  // 步骤4: 重置所有运行时状态，准备接收新回复
  // 步骤5: 设置会话名称（首条消息时）
  // 步骤6: 发起流式请求，注册各种事件回调
  // 步骤7: 流式接收过程中，各回调逐步更新UI
  // 步骤8: 完成后，将完整消息写入聊天记录
  const handleSend = async () => {
    // ----- 步骤1: 预处理输入 -----
    // prepareChatInput 将用户输入+约束条件+预算+对比模式组合成结构化的请求数据
    // 返回值包含：displayMessage(展示给用户看的消息)、enrichedPrompt(发给AI的富化提示词)、sessionName(会话名称)
    const preparedInput = prepareChatInput(inputValue, {
      selectedConstraints,   // 用户选中的约束条件，如["亲子游","海岛"]
      budgetUpperLimit,      // 预算上限，如5000
      compareModeEnabled,    // 是否开启对比模式
      comparePlanCount,      // 对比方案数量
    });
    // 如果输入为空或无效，提示用户并返回（不发送）
    if (!preparedInput) {
      message.warning('请输入内容');
      return;
    }

    // try/catch 是错误处理机制：
    // try 块中的代码如果抛出异常（如网络错误），会跳到 catch 块处理
    // 确保即使出错也不会导致整个应用崩溃
    try {
      const { displayMessage, enrichedPrompt, sessionName } = preparedInput;
      // 判断是否是本次会话的第一条消息（用于决定是否需要设置会话名称）
      const isFirstMessage = !currentSessionId || messages.length === 0;
      let sessionId = currentSessionId;

      // ----- 步骤2: 创建/获取会话 -----
      // 如果没有当前会话ID，需要先创建一个新会话
      // await 会等待服务端返回新会话的ID后才继续执行
      if (!sessionId) {
        const data = await sessionClient.createSession();
        sessionId = data.session_id;
        // 标记跳过下一次会话重置（防止创建会话后又被其他逻辑误重置）
        markSkipNextSessionReset();
        setCurrentSessionId(sessionId);
      }

      // ----- 步骤3: 添加用户消息到聊天记录 -----
      // addMessage 将用户消息添加到消息列表，UI会立即显示这条消息
      addMessage({
        role: 'user',              // 消息角色：'user'表示用户消息
        content: displayMessage,   // 消息内容：展示给用户看的文本
        timestamp: messageTimestamp(), // 消息时间戳
      });

      // ----- 步骤4: 重置运行时状态，准备接收新回复 -----
      clearStreamRuntimeRefs();    // 清空流式ref（上一轮的累积文本等）
      setInputValue('');           // 清空输入框
      setIsStreaming(true);        // 标记开始流式接收
      setStopStreaming(false);     // 重置停止标记
      setStreamingMessage('');     // 清空流式消息显示
      setStreamingReasoning('');   // 清空流式推理显示
      clearArtifactRuntimeState(); // 清空Artifact状态
      stopRef.current = false;     // 重置中断标记
      beginRun(chatMode.toUpperCase()); // 开始一次运行，传入当前聊天模式（如'PLAN'）

      // ----- 步骤5: 设置会话名称（仅首条消息时） -----
      // 首条消息时，用用户输入的内容作为会话名称，方便在侧边栏识别
      if (isFirstMessage && sessionId) {
        try {
          await sessionClient.updateSessionName(sessionId, sessionName);
        } catch (err) {
          // 会话名称设置失败不影响主流程，只记录日志
          logger.error('设置会话名称失败:', err);
        }
      }

      // ----- 步骤6: 发起流式请求 -----
      // chatClient.fetchStreamChat 是核心API调用，发起流式聊天请求
      // 第一个参数：请求体（消息内容、会话ID、模式等）
      // 第二个参数：各种事件回调函数（回调函数 = 当某事件发生时自动调用的函数）
      // 流式请求的特点：不是等全部结果返回再显示，而是边接收边显示（类似ChatGPT的打字效果）
      await chatClient.fetchStreamChat(
        { message: enrichedPrompt, display_message: displayMessage, session_id: sessionId, mode: chatMode },
        {
          // onSessionId: 当服务端返回会话ID时触发
          // 场景：首次发送消息时，服务端可能通过流式响应返回会话ID
          onSessionId: (sid) => {
            if (!currentSessionId) {
              markSkipNextSessionReset();
              setCurrentSessionId(sid);
            }
          },
          // onStage: 当AI进入新的处理阶段时触发
          // 场景：AI从"理解需求"阶段进入"搜索信息"阶段
          onStage: (stage) => recordStage(stage),
          // onPlanPreview: 当AI生成行程计划预览时触发
          // 场景：AI初步生成了三亚5日游的行程概览
          onPlanPreview: (preview) => {
            setPlanPreview(preview);                                    // 更新计划预览状态
            applyArtifactPatch(preview.artifact ?? preview.artifactPatch); // 将预览数据合并到Artifact
            pushRuntimeLog('计划预览', preview.intent || '已生成');      // 记录运行时日志
          },
          // onSubagentStart: 当子Agent开始工作时触发
          // 子Agent是主Agent调度的专门化Agent，如"酒店搜索Agent""景点推荐Agent"
          onSubagentStart: (event) => {
            recordSubagentEvent(event);  // 记录子Agent事件
            pushRuntimeLog('子 Agent 启动', `${subagentLabel(event.subagent)} | ${event.skills?.join(', ') || 'no skills'}`);
          },
          // onSubagentEnd: 当子Agent完成工作时触发
          onSubagentEnd: (event) => {
            recordSubagentEvent(event);  // 记录子Agent事件
            pushRuntimeLog('子 Agent 完成', `${subagentLabel(event.subagent)} | ${event.status || 'completed'}`);
          },
          // onArtifactPatch: 当子Agent提交结构化数据补丁时触发
          // 场景："酒店搜索Agent"找到了3家酒店，提交一个补丁更新Artifact中的酒店部分
          onArtifactPatch: (subagent, patch) => {
            applyArtifactPatch(patch);   // 将补丁合并到Artifact
            pushRuntimeLog('Artifact 更新', `${subagentLabel(subagent)} 提交结构化补丁`);
          },
          // onChunk: 当收到一段AI回复正文时触发（最频繁的回调）
          // 场景：AI每生成几个字就会触发一次，如"根据您的需求"→"，我推荐"→"以下行程"...
          onChunk: (content) => {
            fullResponseRef.current += content; // 累积到完整回复ref（不触发渲染）
            enqueueAnswer(content);             // 加入缓冲队列（稍后批量更新UI）
          },
          // onReasoning: 当收到一段AI推理过程时触发
          // 推理过程是AI的"思考过程"，展示AI如何分析问题
          onReasoning: (content) => {
            fullReasoningRef.current += content; // 累积到完整推理ref
            enqueueReasoning(content);           // 加入缓冲队列
          },
          // onReasoningStart: AI开始推理时触发，显示"思考中..."动画
          onReasoningStart: () => setThinking(true),
          // onReasoningTimestamp: 收到推理时间戳时触发
          onReasoningTimestamp: (timestamp) => {
            setReasoningTimestamp(timestamp);
          },
          // onReasoningEnd: AI推理结束时触发，关闭"思考中..."动画
          onReasoningEnd: () => setThinking(false),
          // onAnswerStart: AI开始输出正式回复时触发，关闭思考动画
          onAnswerStart: () => setThinking(false),
          // onToolStart: AI调用工具时触发
          // 场景：AI决定调用"搜索酒店"工具
          onToolStart: (toolName) => recordToolStart(toolName),
          // onToolEnd: 工具调用完成时触发
          // 场景："搜索酒店"工具返回了结果
          onToolEnd: (toolName) => recordToolEnd(toolName),
          // onMetadata: 收到流式响应的元数据时触发（通常在最后）
          // 元数据包含工具使用情况、耗时等统计信息
          onMetadata: (data) => {
            setHydrationMetadata(data);                          // 保存元数据（用于水合恢复）
            applyArtifactPatch(data.artifact);                   // 应用元数据中的Artifact
            pushRuntimeLog('执行完成', `工具 ${data.toolsUsed.length} 个`); // 记录日志
          },
          // onError: 流式请求发生错误时触发
          // 场景：网络断开、服务端返回错误等
          onError: (errorMsg) => {
            message.destroy();                   // 关闭之前的提示
            message.error(`错误: ${errorMsg}`);  // 显示错误提示
            clearStreamRuntimeRefs();            // 清空流式数据
            setIsStreaming(false);               // 结束流式状态
            failRun(errorMsg);                   // 标记运行失败
            clearArtifactRuntimeState();         // 清空Artifact
            stopRef.current = false;             // 重置中断标记
            fullResponseRef.current = `抱歉，发生错误：${errorMsg}`; // 将错误信息作为回复内容
            setStreamingMessage(fullResponseRef.current);           // 显示错误信息
          },
          // onComplete: 流式请求完成时触发（正常结束）
          // 这是整个流式流程的收尾步骤，将完整的AI回复写入聊天记录
          onComplete: (completion) => {
            message.destroy();                   // 关闭之前的提示
            drainStreamingQueueToRefs();          // 将缓冲队列中剩余数据刷新到ref（确保不丢失）

            // 组装最终消息的各个部分
            const finalReasoning = buildFinalReasoning(fullReasoningRef.current, reasoningTimestampRef.current); // 最终推理文本
            const finalContent = fullResponseRef.current;       // 最终回复正文
            const finalMetadata = metadataRef.current;          // 最终元数据
            const finalArtifact = mergeTripPlanArtifact(artifactRef.current, completion?.artifact); // 合并Artifact
            const finalSubagentEvents = subagentEventsRef.current; // 最终子Agent事件列表
            const finalDiagnostics = buildCompletionDiagnostics({ // 构建诊断信息（工具使用、子Agent等汇总）
              artifact: finalArtifact,
              completion,
              metadata: finalMetadata,
              sessionId,
              subagentEvents: finalSubagentEvents,
            });

            // 清空流式状态
            clearStreamRuntimeRefs();
            // 将完整的AI回复消息添加到聊天记录
            addMessage({
              role: 'assistant',              // 消息角色：'assistant'表示AI助手
              content: finalContent,          // 回复正文
              reasoning: finalReasoning,      // 推理过程
              diagnostics: finalDiagnostics,  // 诊断信息
              timestamp: messageTimestamp(),  // 时间戳
            });

            // 重置流式显示状态
            setStreamingMessage('');
            setStreamingReasoning('');
            setIsStreaming(false);             // 结束流式状态
            stopRef.current = false;           // 重置中断标记
            clearArtifactRuntimeState();       // 清空Artifact运行时状态
            completeRun();                     // 标记运行完成
          },
          // onStop: 轮询函数，流式请求会定期调用此函数检查是否需要停止
          // 返回 stopRef.current 的值，如果为true则中断流式请求
          onStop: () => stopRef.current,
        }
      );

      // 刷新会话列表（侧边栏需要更新，因为可能有新会话或会话名称变化）
      refreshSessions();
    } catch (err: unknown) {
      // catch 块：处理 try 块中抛出的任何异常
      // err: unknown 是 TypeScript 的类型安全写法，表示"不确定错误的具体类型"
      // 需要用 instanceof 判断后才能安全使用
      message.destroy();
      const errorMsg = err instanceof Error ? err.message : '未知错误';
      message.error(`发送失败: ${errorMsg}`);
      setIsStreaming(false);
      setStreamingMessage('');
      setStreamingReasoning('');
      failRun(errorMsg);
      clearArtifactRuntimeState();
      clearStreamRuntimeRefs();
    }
  };

  // 【核心】handleStop — 中断正在进行的流式响应
  // 用户点击"停止生成"按钮时调用
  // 中断流程：
  // 1. 设置中断标记(stopRef) → 流式请求的 onStop 轮询会检测到并停止
  // 2. 将缓冲队列中已接收但未刷新的数据写入ref（确保已接收的内容不丢失）
  // 3. 将已接收的内容作为一条"被中断"的助手消息保存到聊天记录
  // 4. 重置所有流式状态
  //
  // 场景：AI正在生成三亚5日游方案，用户觉得已经够用了，点击停止
  // → 已生成的部分内容（如前3天的行程）会被保存，消息末尾标记"[已停止]"
  const handleStop = () => {
    stopRef.current = true;       // 设置中断标记，流式请求会通过 onStop 回调检测到并停止
    setStopStreaming(true);       // 通知全局状态流式已停止
    drainStreamingQueueToRefs();  // 将缓冲队列中剩余数据刷新到ref，确保不丢失已接收内容

    // 保存当前已接收的所有数据（中断时刻的快照）
    const stoppedContent = fullResponseRef.current;           // 已接收的回复文本
    const stoppedReasoning = fullReasoningRef.current;        // 已接收的推理文本
    const stoppedArtifact = artifactRef.current;              // 当前的Artifact数据
    const stoppedSubagentEvents = subagentEventsRef.current;  // 当前的子Agent事件
    clearStreamRuntimeRefs();  // 清空流式ref

    setIsStreaming(false);     // 结束流式状态
    stopRun();                 // 标记运行已停止

    // 如果已经接收了部分内容，将其作为一条被中断的助手消息保存
    // buildStoppedMessageContent 会在内容末尾添加"[已停止]"标记
    if (stoppedContent || stoppedReasoning) {
      addMessage({
        role: 'assistant',
        content: buildStoppedMessageContent(stoppedContent),  // 添加"[已停止]"标记
        reasoning: stoppedReasoning,
        diagnostics: buildStoppedDiagnostics({                // 构建中断时的诊断信息
          artifact: stoppedArtifact,
          sessionId: currentSessionId,
          subagentEvents: stoppedSubagentEvents,
        }),
        timestamp: messageTimestamp(),
      });
    }

    // 重置流式显示状态
    setStreamingMessage('');
    setStreamingReasoning('');
    clearArtifactRuntimeState();
  };

  // 从探索器使用提示词：将提示词填入输入框，切换到规划模式，并跳转到聊天视图
  // 场景：用户在"灵感探索"面板看到"三亚5日游攻略"，点击"使用此提示词"
  const handleUsePromptFromExplorer = (prompt: string) => {
    setInputValue(prompt);     // 填入输入框
    setChatMode('plan');       // 切换到规划模式
    setActiveView('chat');     // 切换到聊天视图
  };

  // 继续细化：将细化指令填入输入框，切换到规划模式
  // 与 handleUsePromptFromExplorer 类似，但会额外提示用户
  // 场景：用户对AI生成的行程不满意，点击"继续细化"按钮
  const handleContinueRefine = (prompt: string) => {
    setInputValue(prompt);     // 填入输入框
    setChatMode('plan');       // 切换到规划模式
    setActiveView('chat');     // 切换到聊天视图
    message.info('已填入细化指令，按回车可继续生成。'); // 提示用户可以发送
  };

  // 快速开始：将预设提示词填入输入框（不切换模式、不切换视图）
  // 场景：用户在首页点击"快速开始"卡片上的预设问题
  const handlePickQuickStartPrompt = (prompt: string) => {
    setInputValue(prompt);     // 仅填入输入框，用户可自行修改后再发送
  };

  // 返回所有状态和操作方法，供 UI 组件使用
  // 自定义 Hook 的返回值就是它对外暴露的"API"，组件通过解构获取需要的状态和方法
  // 例如：const { handleSend, isStreaming, messages } = useChatRuntime();
  return {
    // --- 状态数据 ---
    activeSubagent,           // 当前运行的子Agent
    activeView,               // 当前活跃视图
    artifactState,            // 行程计划结构化数据
    budgetUpperLimit,         // 预算上限
    chatMode,                 // 聊天模式
    compareModeEnabled,       // 对比模式开关
    comparePlanCount,         // 对比方案数量
    currentTool,              // 当前调用的工具
    error,                    // 错误信息
    inputValue,               // 输入框内容
    isStreaming,               // 是否流式接收中
    isThinking,                // 是否思考中
    messages,                  // 消息列表
    messagesEndRef,            // 消息底部DOM引用
    metadata: metadataRef.current, // 流式元数据（从ref取最新值）
    planPreview,               // 计划预览
    reasoningExpanded,         // 推理展开状态
    runtimeLogs,               // 运行时日志
    selectedConstraintCount,   // 约束条件总数
    selectedConstraints,       // 选中的约束条件
    stageHistory,              // 阶段历史
    stageState,                // 当前阶段
    streamingMessage,          // 流式消息文本
    streamingReasoning,        // 流式推理文本
    subagentEvents,            // 子Agent事件
    waitingForResponse,        // 是否等待首次响应
    // --- 操作方法 ---
    handleContinueRefine,      // 继续细化
    handlePickQuickStartPrompt, // 快速开始
    handleSend,                // 【核心】发送消息
    handleStop,                // 停止生成
    handleUsePromptFromExplorer, // 使用探索器提示词
    // --- 状态设置器 ---
    setActiveView,             // 设置活跃视图
    setBudgetUpperLimit,       // 设置预算上限
    setChatMode,               // 设置聊天模式
    setCompareModeEnabled,     // 设置对比模式
    setComparePlanCount,       // 设置对比方案数量
    setInputValue,             // 设置输入框内容
    setSelectedConstraints,    // 设置约束条件
    toggleReasoning,           // 切换推理展开
  };
}
