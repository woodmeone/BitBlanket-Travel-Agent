// chatClient.ts —— 聊天相关的 API 客户端
// 本文件负责与后端的聊天接口通信，包括：
// 1. 清空聊天记录
// 2. 发送流式聊天请求（SSE 方式）
// 3. 管理请求的取消、重连、超时等
//
// 关键概念解释：
// - class（类）：TypeScript/JavaScript 中定义"蓝图"的语法，类可以包含属性和方法
//   类似于"模板"，通过 new 可以创建出具体的实例
// - async/await：处理异步操作的语法糖
//   async 标记一个函数为异步函数，await 等待一个异步操作完成
//   例如：await fetch(...) 表示"等 fetch 请求完成后再继续往下执行"
// - fetch：浏览器原生提供的 HTTP 请求函数，比 axios 更底层
//   这里用 fetch 而不是 axios，是因为 fetch 原生支持流式读取响应体（ReadableStream）
// - AbortController：浏览器提供的用于取消请求的 API
//   调用 controller.abort() 可以中断正在进行的 fetch 请求

import type { ChatRequest, ChatResponse } from '@/types';
import { logger } from '@/utils/logger';
import { handleChatStreamLine } from './chatStreamParser';
import { API_PREFIX, apiClient, buildTraceHeaders } from './core';
import { SSEConnectionStatus, type StreamCallbacks } from './chatStreamTypes';

// ChatClient 类 —— 聊天功能的 API 客户端
// private 关键字表示该属性/方法只在类内部使用，外部不能直接访问
class ChatClient {
  private maxReconnectAttempts = 3;  // 最大重连次数，超过后放弃
  private baseReconnectDelay = 1000; // 重连基础延迟（毫秒），实际延迟会指数递增
  // pendingRequests —— 正在进行的请求映射表
  // Map 是 JavaScript 中的键值对数据结构，类似于对象但键可以是任意类型
  // 键是请求的唯一标识，值是对应的 AbortController（用于取消请求）
  private pendingRequests = new Map<string, AbortController>();
  // connectionStatus —— 当前连接状态
  private connectionStatus: SSEConnectionStatus = SSEConnectionStatus.IDLE;

  // getConnectionStatus —— 获取当前连接状态
  // 外部组件可以调用此方法了解连接情况，例如在界面上显示"连接中..."
  getConnectionStatus(): SSEConnectionStatus {
    return this.connectionStatus;
  }

  // setConnectionStatus —— 更新连接状态
  // 同时触发 onConnectionChange 回调，通知上层组件状态变化
  private setConnectionStatus(status: SSEConnectionStatus, callbacks?: StreamCallbacks): void {
    this.connectionStatus = status;
    callbacks?.onConnectionChange?.(status);
    // ?. 可选链：如果 callbacks 存在且 onConnectionChange 存在，才调用
  }

  // getRequestKey —— 生成请求的唯一标识
  // 由"会话ID:消息前50字符"组成，用来区分不同的请求
  private getRequestKey(request: ChatRequest): string {
    return `${request.session_id || 'new'}:${request.message.slice(0, 50)}`;
  }

  // cancelAllRequests —— 取消所有正在进行的请求
  // 应用场景：用户退出聊天页面时，需要中断所有未完成的请求
  cancelAllRequests(): void {
    for (const controller of this.pendingRequests.values()) controller.abort();
    // 遍历所有 AbortController，调用 abort() 取消对应请求
    this.pendingRequests.clear(); // 清空映射表
  }

  // finalizeRequest —— 结束一个请求，从映射表中移除
  private finalizeRequest(requestKey: string): void {
    this.pendingRequests.delete(requestKey);
  }

  // getReconnectDelay —— 计算第 N 次重连的延迟时间
  // 使用指数退避策略：第1次等1秒，第2次等2秒，第3次等4秒...
  // 这样避免在服务器压力大时频繁重连导致雪崩
  private getReconnectDelay(attempt: number): number {
    return this.baseReconnectDelay * Math.pow(2, attempt - 1);
    // Math.pow(2, n) 计算 2 的 n 次方
  }

  // clearChat —— 清空指定会话的聊天记录
  // async：标记为异步函数，返回 Promise
  // Promise<ChatResponse>：表示这个函数最终会返回一个 ChatResponse 类型的结果
  // apiClient.post：发送 POST 请求，第二个参数 null 表示请求体为空
  // { params: { session_id: sessionId } }：URL 查询参数，最终请求为 /api/clear?session_id=xxx
  async clearChat(sessionId: string): Promise<ChatResponse> {
    const response = await apiClient.post(`${API_PREFIX}/clear`, null, { params: { session_id: sessionId } });
    return response.data; // axios 响应的 data 字段包含服务器返回的实际数据
  }

  // 【核心】fetchStreamChat —— 发送流式聊天请求
  // 这是聊天功能的核心方法，用户发送消息后通过此方法与后端建立 SSE 连接
  //
  // 参数说明：
  // - request: 聊天请求（包含消息内容、会话ID等）
  // - callbacks: 流式回调函数集合，用于接收服务器推送的各种事件
  //
  // 应用场景：用户在聊天框输入"帮我规划北京3日游"并点击发送，
  // 前端调用此方法，后端通过 SSE 逐步返回AI的思考过程和回答
  async fetchStreamChat(request: ChatRequest, callbacks: StreamCallbacks): Promise<void> {
    const requestKey = this.getRequestKey(request);
    // 防止重复请求：如果同一个请求已经在处理中，直接返回错误
    if (this.pendingRequests.has(requestKey)) {
      callbacks.onError('请求正在处理中，请稍候');
      return;
    }

    // 创建 AbortController，用于在需要时取消请求
    const controller = new AbortController();
    this.pendingRequests.set(requestKey, controller);
    await this.executeStreamRequest(request, callbacks, controller, requestKey);
  }

  // 【核心】executeStreamChat —— 执行流式请求（支持重连）
  // 这是 fetchStreamChat 的内部实现，包含实际的 fetch 调用和重连逻辑
  //
  // 参数说明：
  // - request: 聊天请求
  // - callbacks: 回调函数集合
  // - controller: 用于取消请求的 AbortController
  // - requestKey: 请求唯一标识
  // - attempt: 当前尝试次数（默认1，重连时递增）
  private async executeStreamRequest(
    request: ChatRequest,
    callbacks: StreamCallbacks,
    controller: AbortController,
    requestKey: string,
    attempt = 1
  ): Promise<void> {
    if (attempt > 1) {
      // 重连时更新状态为 RECONNECTING
      this.setConnectionStatus(SSEConnectionStatus.RECONNECTING, callbacks);
      logger.info(`SSE reconnect attempt ${attempt - 1}`);
    } else {
      // 首次请求，状态为 CONNECTING
      this.setConnectionStatus(SSEConnectionStatus.CONNECTING, callbacks);
    }

    // 设置超时定时器：180秒（3分钟）后自动取消请求
    // setTimeout：在指定时间后执行回调函数
    const timeoutId = setTimeout(() => {
      controller.abort();
      logger.warn('SSE request timed out and was aborted');
    }, 180000);

    try {
      // 构建追踪头信息
      const trace = buildTraceHeaders();
      // 【核心】使用 fetch 发送 POST 请求到流式聊天接口
      // fetch 是浏览器原生 API，比 axios 更适合处理流式响应
      // signal: controller.signal 将 AbortController 与请求关联，调用 abort() 可取消请求
      const response = await fetch(`${API_PREFIX}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': trace.requestId,
          'X-Trace-ID': trace.traceId,
        },
        body: JSON.stringify(request), // 将请求对象转为 JSON 字符串作为请求体
        signal: controller.signal,
      });

      // 请求成功发出，清除超时定时器
      clearTimeout(timeoutId);
      // 更新状态为 STREAMING（正在接收数据）
      this.setConnectionStatus(SSEConnectionStatus.STREAMING, callbacks);
      logger.info(
        `SSE POST ${API_PREFIX}/chat/stream request_id=${trace.requestId} trace_id=${trace.traceId} status=${response.status}`
      );

      // 检查 HTTP 响应状态码，如果不是 2xx 则视为错误
      if (!response.ok) {
        const errorText = await response.text();
        this.setConnectionStatus(SSEConnectionStatus.ERROR, callbacks);
        callbacks.onError(`HTTP error ${response.status}: ${errorText}`);
        this.finalizeRequest(requestKey);
        return;
      }

      // 获取响应体的读取器（ReadableStream）
      // response.body 是一个 ReadableStream，可以逐块读取数据
      // ?. 可选链：如果 body 不存在（某些环境可能不支持），返回 undefined
      const reader = response.body?.getReader();
      if (!reader) {
        this.setConnectionStatus(SSEConnectionStatus.ERROR, callbacks);
        callbacks.onError('无法读取流式响应');
        this.finalizeRequest(requestKey);
        return;
      }

      // TextDecoder：将二进制数据（Uint8Array）解码为文本字符串
      const decoder = new TextDecoder();
      let buffer = '';       // 缓冲区，存放尚未处理完的文本（可能一行数据被分成多个块到达）
      let streamEnded = false; // 标记流是否已结束

      // 【核心】循环读取流式数据
      // while (true) 创建一个无限循环，通过 break 语句退出
      while (true) {
        // 检查请求是否已被取消
        if (controller.signal.aborted) break;
        // 检查外部是否要求停止（如用户点击了"停止生成"按钮）
        if (callbacks.onStop && callbacks.onStop()) {
          await reader.cancel(); // 取消读取器
          break;
        }

        // reader.read() 读取下一块数据
        // 返回 { done: boolean, value: Uint8Array }
        // done 为 true 表示流已结束，value 是本次读取到的二进制数据
        const { done, value } = await reader.read();
        if (done) {
          // 流结束前处理缓冲区中剩余的数据
          if (buffer.trim()) {
            streamEnded =
              handleChatStreamLine(buffer, callbacks, {
                finalizeRequest: () => this.finalizeRequest(requestKey),
                setConnectionStatus: (status) => this.setConnectionStatus(status, callbacks),
              }) || streamEnded;
          }
          this.setConnectionStatus(SSEConnectionStatus.IDLE, callbacks);
          // 如果流自然结束但没有收到 [DONE]/done 信号，仍需触发 onComplete
          if (!streamEnded) callbacks.onComplete();
          break;
        }

        // 将新读取到的二进制数据解码为文本，追加到缓冲区
        // { stream: true } 表示数据可能跨越多个块，解码器会正确处理多字节字符
        buffer += decoder.decode(value, { stream: true });
        // 按换行符分割缓冲区，得到完整的行
        const lines = buffer.split('\n');
        // lines.pop() 取出最后一个元素（可能是不完整的行），保留在缓冲区等待下次拼接
        buffer = lines.pop() ?? '';
        // ?? 是空值合并运算符，当左侧为 null 或 undefined 时使用右侧的值

        // 逐行处理完整的行
        for (const line of lines) {
          streamEnded =
            handleChatStreamLine(line, callbacks, {
              finalizeRequest: () => this.finalizeRequest(requestKey),
              setConnectionStatus: (status) => this.setConnectionStatus(status, callbacks),
            }) || streamEnded;
          if (streamEnded) {
            // 如果某一行表示流已结束，取消读取器并退出循环
            await reader.cancel();
            break;
          }
        }

        if (streamEnded) break;
      }

      // 清理请求
      this.finalizeRequest(requestKey);
    } catch (error: unknown) {
      // 捕获异常
      clearTimeout(timeoutId);
      this.finalizeRequest(requestKey);

      // 如果是用户主动取消的请求，不需要报错
      if (controller.signal.aborted) {
        this.setConnectionStatus(SSEConnectionStatus.DISCONNECTED, callbacks);
        return;
      }

      // 网络错误等异常情况，尝试重连
      const errorMessage = error instanceof Error ? error.message : String(error);
      if (attempt < this.maxReconnectAttempts) {
        // 还可以重连，更新状态并等待一段时间后重试
        this.setConnectionStatus(SSEConnectionStatus.RECONNECTING, callbacks);
        // new Promise((resolve) => setTimeout(resolve, delay))：等待指定时间
        // 这是"暂停执行"的一种方式，await 会让函数暂停直到定时器触发
        await new Promise((resolve) => setTimeout(resolve, this.getReconnectDelay(attempt)));
        // 递归调用自身进行重连，attempt + 1 表示尝试次数加1
        return this.executeStreamRequest(request, callbacks, controller, requestKey, attempt + 1);
      }

      // 超过最大重连次数，报告错误
      this.setConnectionStatus(SSEConnectionStatus.ERROR, callbacks);
      callbacks.onError(`流式请求失败: ${errorMessage}`);
    }
  }
}

// export const：导出一个常量，其他文件可以通过 import { chatClient } 引入使用
// new ChatClient()：创建 ChatClient 类的一个实例
export const chatClient = new ChatClient();
