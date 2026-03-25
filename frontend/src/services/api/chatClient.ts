import type { ChatRequest, ChatResponse } from '@/types';
import { logger } from '@/utils/logger';
import { handleChatStreamLine } from './chatStreamParser';
import { API_PREFIX, apiClient, buildTraceHeaders } from './core';
import { SSEConnectionStatus, type StreamCallbacks } from './chatStreamTypes';

class ChatClient {
  private maxReconnectAttempts = 3;
  private baseReconnectDelay = 1000;
  private pendingRequests = new Map<string, AbortController>();
  private connectionStatus: SSEConnectionStatus = SSEConnectionStatus.IDLE;

  getConnectionStatus(): SSEConnectionStatus {
    return this.connectionStatus;
  }

  private setConnectionStatus(status: SSEConnectionStatus, callbacks?: StreamCallbacks): void {
    this.connectionStatus = status;
    callbacks?.onConnectionChange?.(status);
  }

  private getRequestKey(request: ChatRequest): string {
    return `${request.session_id || 'new'}:${request.message.slice(0, 50)}`;
  }

  cancelAllRequests(): void {
    for (const controller of this.pendingRequests.values()) controller.abort();
    this.pendingRequests.clear();
  }

  private finalizeRequest(requestKey: string): void {
    this.pendingRequests.delete(requestKey);
  }

  private getReconnectDelay(attempt: number): number {
    return this.baseReconnectDelay * Math.pow(2, attempt - 1);
  }

  async clearChat(sessionId: string): Promise<ChatResponse> {
    const response = await apiClient.post(`${API_PREFIX}/clear`, null, { params: { session_id: sessionId } });
    return response.data;
  }

  async fetchStreamChat(request: ChatRequest, callbacks: StreamCallbacks): Promise<void> {
    const requestKey = this.getRequestKey(request);
    if (this.pendingRequests.has(requestKey)) {
      callbacks.onError('请求正在处理中，请稍候');
      return;
    }

    const controller = new AbortController();
    this.pendingRequests.set(requestKey, controller);
    await this.executeStreamRequest(request, callbacks, controller, requestKey);
  }

  private async executeStreamRequest(
    request: ChatRequest,
    callbacks: StreamCallbacks,
    controller: AbortController,
    requestKey: string,
    attempt = 1
  ): Promise<void> {
    if (attempt > 1) {
      this.setConnectionStatus(SSEConnectionStatus.RECONNECTING, callbacks);
      logger.info(`SSE reconnect attempt ${attempt - 1}`);
    } else {
      this.setConnectionStatus(SSEConnectionStatus.CONNECTING, callbacks);
    }

    const timeoutId = setTimeout(() => {
      controller.abort();
      logger.warn('SSE request timed out and was aborted');
    }, 180000);

    try {
      const trace = buildTraceHeaders();
      const response = await fetch(`${API_PREFIX}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': trace.requestId,
          'X-Trace-ID': trace.traceId,
        },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      this.setConnectionStatus(SSEConnectionStatus.STREAMING, callbacks);
      logger.info(
        `SSE POST ${API_PREFIX}/chat/stream request_id=${trace.requestId} trace_id=${trace.traceId} status=${response.status}`
      );

      if (!response.ok) {
        const errorText = await response.text();
        this.setConnectionStatus(SSEConnectionStatus.ERROR, callbacks);
        callbacks.onError(`HTTP error ${response.status}: ${errorText}`);
        this.finalizeRequest(requestKey);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        this.setConnectionStatus(SSEConnectionStatus.ERROR, callbacks);
        callbacks.onError('无法读取流式响应');
        this.finalizeRequest(requestKey);
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let streamEnded = false;

      while (true) {
        if (controller.signal.aborted) break;
        if (callbacks.onStop && callbacks.onStop()) {
          await reader.cancel();
          break;
        }

        const { done, value } = await reader.read();
        if (done) {
          if (buffer.trim()) {
            streamEnded =
              handleChatStreamLine(buffer, callbacks, {
                finalizeRequest: () => this.finalizeRequest(requestKey),
                setConnectionStatus: (status) => this.setConnectionStatus(status, callbacks),
              }) || streamEnded;
          }
          this.setConnectionStatus(SSEConnectionStatus.IDLE, callbacks);
          if (!streamEnded) callbacks.onComplete();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          streamEnded =
            handleChatStreamLine(line, callbacks, {
              finalizeRequest: () => this.finalizeRequest(requestKey),
              setConnectionStatus: (status) => this.setConnectionStatus(status, callbacks),
            }) || streamEnded;
          if (streamEnded) {
            await reader.cancel();
            break;
          }
        }

        if (streamEnded) break;
      }

      this.finalizeRequest(requestKey);
    } catch (error: unknown) {
      clearTimeout(timeoutId);
      this.finalizeRequest(requestKey);

      if (controller.signal.aborted) {
        this.setConnectionStatus(SSEConnectionStatus.DISCONNECTED, callbacks);
        return;
      }

      const errorMessage = error instanceof Error ? error.message : String(error);
      if (attempt < this.maxReconnectAttempts) {
        this.setConnectionStatus(SSEConnectionStatus.RECONNECTING, callbacks);
        await new Promise((resolve) => setTimeout(resolve, this.getReconnectDelay(attempt)));
        return this.executeStreamRequest(request, callbacks, controller, requestKey, attempt + 1);
      }

      this.setConnectionStatus(SSEConnectionStatus.ERROR, callbacks);
      callbacks.onError(`流式请求失败: ${errorMessage}`);
    }
  }
}

export const chatClient = new ChatClient();
