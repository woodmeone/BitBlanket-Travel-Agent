// sessionClient.ts —— 会话管理 API 客户端
// 本文件负责与后端的会话（对话）管理接口通信，包括：
// 1. 创建新会话
// 2. 获取会话列表
// 3. 获取会话中的聊天记录
// 4. 删除会话
// 5. 修改会话名称
//
// 关键概念解释：
// - 会话（Session）：一次完整的对话过程，类似于微信中的一个聊天窗口
//   每个会话有唯一的 session_id，用户可以在多个会话之间切换
// - apiClient.get/post/put/delete：对应 HTTP 的 GET/POST/PUT/DELETE 方法
//   GET 用于获取数据，POST 用于创建数据，PUT 用于更新数据，DELETE 用于删除数据

import type { SessionInfo, SessionMessagesResponse } from '@/types';
import { API_PREFIX, apiClient } from './core';

// SessionClient 类 —— 会话管理的 API 客户端
class SessionClient {
  // createSession —— 创建一个新的聊天会话
  // 应用场景：用户点击"新建对话"按钮时调用
  // 返回值包含新创建的会话ID
  async createSession(): Promise<{ session_id: string }> {
    const response = await apiClient.post(`${API_PREFIX}/session/new`);
    return response.data;
  }

  // 【核心】getSessions —— 获取用户的所有会话列表
  // 应用场景：用户打开侧边栏，展示历史对话列表
  // 返回值包含会话信息数组，每个会话包含ID、名称、最后更新时间等
  async getSessions(): Promise<{ sessions: SessionInfo[] }> {
    const response = await apiClient.get(`${API_PREFIX}/sessions`);
    return response.data;
  }

  // getSessionMessages —— 获取指定会话的聊天记录
  // 应用场景：用户点击某个历史会话，加载该会话的所有聊天消息
  // sessionId：会话的唯一标识
  async getSessionMessages(sessionId: string): Promise<SessionMessagesResponse> {
    const response = await apiClient.get(`${API_PREFIX}/session/${sessionId}/messages`);
    // URL 中的 ${sessionId} 是路径参数，例如 /api/session/abc123/messages
    return response.data;
  }

  // deleteSession —— 删除指定会话
  // 应用场景：用户长按某个会话选择"删除"
  async deleteSession(sessionId: string): Promise<{ success: boolean }> {
    const response = await apiClient.delete(`${API_PREFIX}/session/${sessionId}`);
    return response.data;
  }

  // updateSessionName —— 修改会话名称
  // 应用场景：用户双击会话标题，将"新对话"改为"北京3日游规划"
  // 第二个参数 name 是新的会话名称
  async updateSessionName(sessionId: string, name: string): Promise<{ success: boolean; message?: string }> {
    // apiClient.put：发送 PUT 请求更新数据
    // 第二个参数 { name } 是请求体，即要更新的数据
    // { name } 是 { name: name } 的简写（ES6 属性简写语法）
    const response = await apiClient.put(`${API_PREFIX}/session/${sessionId}/name`, { name });
    return response.data;
  }
}

// 导出 SessionClient 的单例实例
export const sessionClient = new SessionClient();
