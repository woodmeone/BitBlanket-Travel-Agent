// 'use client' 是 Next.js 的指令，表示此文件仅在浏览器端运行
'use client';

// React 的 Hook 和类型导入
// useEffect：副作用 Hook，在组件渲染后执行某些操作（如数据加载、事件监听）
// useRef：创建一个可变引用，值变化不会触发重新渲染
// Dispatch / SetStateAction：useState 返回的 setter 函数的类型
import { useEffect, useRef, type Dispatch, type MutableRefObject, type SetStateAction } from 'react';
// 分享服务的 API 客户端和流式元数据类型
import { shareClient, type StreamMetadata } from '@/services/api';
// 项目类型定义
import type { ArtifactDeliveryBundle, ExecutionReceipt, Message, SubagentEvent, TripPlanArtifact } from '@/types';
// 日志工具
import { logger } from '@/utils/logger';
import { messageTimestamp, type ActiveView } from './shared';

// 消息提示 API 的接口（如"成功"/"错误"弹窗）
// 应用场景：加载分享链接成功时弹出"已打开分享方案"，失败时弹出错误提示
interface ChatHydrationMessageApi {
  success: (content: string) => void;  // 显示成功提示
  error: (content: string) => void;    // 显示错误提示
}

// 【核心】会话水合（Hydration）Hook 的配置选项
// "水合"是前端术语，指将服务端/外部的数据"注入"到客户端状态中，使页面"活"起来
// 在本文件中，水合主要指：加载分享链接的数据、切换会话时恢复状态
interface UseChatSessionHydrationOptions {
  currentSessionId: string | null;      // 当前会话 ID
  clearStreamRuntimeRefs: () => void;   // 清除流式运行时的引用
  messageApi: ChatHydrationMessageApi;  // 消息提示 API
  resetArtifactRuntimeState: () => void; // 重置 Artifact 运行时状态
  resetRunState: () => void;            // 重置运行状态
  setActiveView: Dispatch<SetStateAction<ActiveView>>;  // 设置当前激活的视图
  setCurrentSessionId: (id: string | null) => void;    // 设置当前会话 ID
  setIsStreaming: (value: boolean) => void;             // 设置是否正在流式输出
  setMessages: (messages: Message[]) => void;           // 设置消息列表
  setStopStreaming: (value: boolean) => void;           // 设置是否停止流式输出
  setStreamingMessage: (value: string) => void;         // 设置当前流式输出的消息内容
  setStreamingReasoning: (value: string) => void;       // 设置当前流式输出的推理内容
  stopRef: MutableRefObject<boolean>;                   // 停止标志的引用
}

// 会话水合 Hook 的返回值
interface UseChatSessionHydrationResult {
  clearHydrationMetadata: () => void;                           // 清除水合元数据
  markSkipNextSessionReset: () => void;                         // 标记跳过下一次会话重置
  metadataRef: MutableRefObject<StreamMetadata | null>;         // 流式元数据的引用
  setHydrationMetadata: (metadata: StreamMetadata | null) => void;  // 设置水合元数据
}

// 从 URL 的查询参数中提取分享 ID
// 例如 URL 为 "?share=abc123"，则返回 "abc123"
// URLSearchParams 是浏览器内置 API，用于解析 URL 中的查询参数
// 应用场景：用户点击分享链接（如 https://example.com?share=abc123），此函数提取出 "abc123"
export function extractShareId(search: string): string | null {
  const shareId = new URLSearchParams(search).get('share');
  return shareId?.trim() || null;
}

// 构建分享链接对应的助手消息
// 当用户通过分享链接打开一个行程方案时，需要构造一条"助手消息"来展示方案内容
export function buildSharedAssistantMessage(content: string): Message {
  return {
    role: 'assistant',         // 消息角色为"助手"（AI 的回复）
    content: content.trim(),   // 消息内容（去除首尾空白）
    timestamp: messageTimestamp(),  // 消息时间戳
  };
}

// 类型守卫：判断一个值是否为普通对象（Record）
// value is Record<string, unknown> 是 TypeScript 的类型谓词语法
// 表示如果函数返回 true，TypeScript 会把 value 的类型收窄为 Record<string, unknown>
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// 安全地获取字符串值：如果是字符串则去除首尾空白，否则返回空字符串
function trimText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

// 从交付包（delivery bundle）中提取分享内容文本
// 优先取 bundle.share.content，其次取 bundle.descriptor.shareContent
// 应用场景：分享链接对应的数据包中，分享文本可能存在不同位置，此函数统一提取
function deliveryBundleShareContent(bundle: ArtifactDeliveryBundle | null | undefined): string {
  return trimText(bundle?.share?.content) || trimText(bundle?.descriptor?.shareContent);
}

// 从交付包中提取行程结构化数据（Artifact）
// 先检查 bundle.artifact 是否为有效对象，再进行类型断言
// as unknown as TripPlanArtifact 是双重类型断言：先转为 unknown（未知类型），再转为目标类型
function deliveryBundleArtifact(bundle: ArtifactDeliveryBundle | null | undefined): TripPlanArtifact | null {
  return isRecord(bundle?.artifact) ? (bundle.artifact as unknown as TripPlanArtifact) : null;
}

// 从交付包中提取执行回执
// 执行回执包含 AI 运行的详细过程记录，如各子智能体的执行片段
function deliveryBundleExecutionReceipt(bundle: ArtifactDeliveryBundle | null | undefined): ExecutionReceipt | null {
  return isRecord(bundle?.executionReceipt) ? (bundle.executionReceipt as unknown as ExecutionReceipt) : null;
}

// 【核心】从交付包的执行回执中提取子智能体事件列表
// 执行回执中的 segments 数组记录了每个子智能体的执行片段
// 此函数将每个片段转换为 SubagentEvent 格式
// 应用场景：分享链接的行程方案中，需要展示 AI 用了哪些子智能体（规划、研究、校验）来完成行程
function deliveryBundleSubagentEvents(bundle: ArtifactDeliveryBundle | null | undefined): SubagentEvent[] {
  const executionReceipt = deliveryBundleExecutionReceipt(bundle);
  // 如果没有执行回执或没有片段数据，返回空数组
  if (!executionReceipt?.segments?.length) return [];

  // reduce 是数组的归并方法：遍历每个 segment，将其转换为 SubagentEvent 并累积到 events 数组中
  // <SubagentEvent[]> 是泛型参数，指定归并结果的类型
  return executionReceipt.segments.reduce<SubagentEvent[]>((events, segment) => {
      const subagent = trimText(segment.subagent);
      // 如果片段没有子智能体名称，跳过
      if (!subagent) return events;

      events.push({
        subagent,  // 子智能体名称（如 'planning'、'research'）
        sequence: typeof segment.sequence === 'number' ? segment.sequence : null,  // 执行序号
        trigger: trimText(segment.trigger) || null,       // 触发原因
        description: trimText(segment.description) || null, // 描述
        // 过滤出字符串类型的技能列表
        // filter((skill): skill is string => ...) 是类型守卫过滤
        // skill is string 表示如果回调返回 true，TypeScript 会把 skill 的类型收窄为 string
        skills: Array.isArray(segment.skills) ? segment.skills.filter((skill): skill is string => typeof skill === 'string') : [],
        // 工具名称列表，优先取 toolNames，其次取 toolsUsed
        toolNames: Array.isArray(segment.toolNames)
          ? segment.toolNames.filter((tool): tool is string => typeof tool === 'string')
          : Array.isArray(segment.toolsUsed)
            ? segment.toolsUsed.filter((tool): tool is string => typeof tool === 'string')
            : [],
        status: trimText(segment.status) || null,     // 子智能体状态（如 'completed'）
        summary: trimText(segment.summary) || null,   // 子智能体执行摘要
      });
      return events;
    }, []);
}

// 【核心】从交付包构建完整的分享助手消息
// 与 buildSharedAssistantMessage 的区别：此函数还会提取 artifact、执行回执、子智能体事件等诊断数据
// 应用场景：用户打开分享链接时，不仅展示行程文本，还要展示 AI 的运行详情（诊断信息）
export function buildSharedAssistantMessageFromBundle(
  content: string,
  deliveryBundle: ArtifactDeliveryBundle | null | undefined
): Message {
  // 从交付包提取各部分数据
  const artifact = deliveryBundleArtifact(deliveryBundle);
  const executionReceipt = deliveryBundleExecutionReceipt(deliveryBundle);
  const subagentEvents = deliveryBundleSubagentEvents(deliveryBundle);
  // 如果有 artifact、执行回执或子智能体事件，则构建诊断数据
  const diagnostics =
    artifact || executionReceipt || subagentEvents.length > 0
      ? {
          artifact,
          executionReceipt: executionReceipt ?? undefined,
          subagentEvents: subagentEvents.length > 0 ? subagentEvents : undefined,
        }
      : undefined;

  return {
    role: 'assistant',
    // 优先使用交付包中的分享内容，其次使用传入的 content
    content: deliveryBundleShareContent(deliveryBundle) || trimText(content),
    timestamp: messageTimestamp(),
    diagnostics,  // 诊断数据（可选）
  };
}

// 【核心】会话水合（Hydration）Hook
// "水合"在此处指：将外部数据（如分享链接的数据）加载到客户端状态中
// 主要功能：
//   1. 检测 URL 中的分享链接参数，自动加载分享的行程方案
//   2. 切换会话时重置运行时状态
//
// 应用场景举例：
//   场景1：用户收到一个分享链接 https://example.com?share=abc123
//     → Hook 检测到 URL 中的 share 参数
//     → 调用 API 获取分享数据
//     → 将数据注入到消息列表中，用户直接看到行程方案
//
//   场景2：用户从会话A切换到会话B
//     → currentSessionId 变化
//     → Hook 自动重置运行时状态（清空流式输出、重置 artifact 等）
export function useChatSessionHydration({
  currentSessionId,
  clearStreamRuntimeRefs,
  messageApi,
  resetArtifactRuntimeState,
  resetRunState,
  setActiveView,
  setCurrentSessionId,
  setIsStreaming,
  setMessages,
  setStopStreaming,
  setStreamingMessage,
  setStreamingReasoning,
  stopRef,
}: UseChatSessionHydrationOptions): UseChatSessionHydrationResult {
  // 流式元数据的引用，用于在流式处理过程中保存和读取元数据
  const metadataRef = useRef<StreamMetadata | null>(null);
  // 是否已经处理过分享链接的标志，确保只处理一次
  const hasHandledShareRef = useRef(false);
  // 是否跳过下一次会话重置的标志
  // 应用场景：加载分享链接时会设置 sessionId 为 null，这会触发会话重置
  //   但此时我们不需要重置（因为正在加载分享数据），所以需要跳过
  const skipNextSessionResetRef = useRef(false);

  // 清除水合元数据
  const clearHydrationMetadata = () => {
    metadataRef.current = null;
  };

  // 设置水合元数据
  const setHydrationMetadata = (metadata: StreamMetadata | null) => {
    metadataRef.current = metadata;
  };

  // 标记跳过下一次会话重置
  const markSkipNextSessionReset = () => {
    skipNextSessionResetRef.current = true;
  };

  // 重置所有临时的运行时状态
  // "临时"指的是流式输出过程中的中间状态，如正在显示的文字、推理过程等
  // 切换会话或加载分享链接时都需要重置这些状态
  const resetTransientRuntimeState = () => {
    clearStreamRuntimeRefs();
    setStreamingMessage('');
    setStreamingReasoning('');
    resetRunState();
    setIsStreaming(false);
    setStopStreaming(false);
    resetArtifactRuntimeState();
    clearHydrationMetadata();
    stopRef.current = false;
  };

  // 【核心】副作用1：检测并加载分享链接
  // useEffect 是 React 的副作用 Hook，在组件渲染后执行
  // 依赖数组 [messageApi, setActiveView, setCurrentSessionId, setMessages] 表示
  //   只有这些依赖变化时才重新执行
  useEffect(() => {
    // 确保在浏览器环境中执行（SSR 时不执行）
    if (typeof window === 'undefined') return;
    // 如果已经处理过分享链接，不再重复处理
    if (hasHandledShareRef.current) return;

    // 从当前 URL 中提取分享 ID
    const shareId = extractShareId(window.location.search);
    if (!shareId) return;

    // 标记已处理，防止重复加载
    hasHandledShareRef.current = true;
    // 异步加载分享内容的函数
    const loadSharedContent = async () => {
      try {
        // 先重置运行时状态
        resetTransientRuntimeState();
        // 调用 API 获取分享数据
        const result = await shareClient.getShareDetail(shareId);
        // 设置会话 ID 为 null（分享内容不属于任何会话）
        setCurrentSessionId(null);
        // 将分享数据构建为助手消息，设置到消息列表中
        setMessages([buildSharedAssistantMessageFromBundle(result.content, result.delivery_bundle ?? null)]);
        // 切换到聊天视图
        setActiveView('chat');
        // 显示成功提示
        messageApi.success('已打开分享方案');
      } catch (error) {
        // 加载失败时记录日志并显示错误提示
        logger.error('加载分享失败:', error);
        messageApi.error(`加载分享失败: ${error instanceof Error ? error.message : '未知错误'}`);
      }
    };

    // void 表示明确忽略 Promise 的返回值（即不等待异步操作完成）
    void loadSharedContent();
  }, [messageApi, setActiveView, setCurrentSessionId, setMessages]);

  // 副作用2：会话切换时重置运行时状态
  // 当 currentSessionId 变化时（用户切换了会话），重置所有临时状态
  useEffect(() => {
    // 如果标记了跳过本次重置（如加载分享链接时），则跳过并重置标志
    if (skipNextSessionResetRef.current) {
      skipNextSessionResetRef.current = false;
      return;
    }

    resetTransientRuntimeState();
  }, [currentSessionId]);

  return {
    clearHydrationMetadata,
    markSkipNextSessionReset,
    metadataRef,
    setHydrationMetadata,
  };
}
