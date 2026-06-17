// service.ts —— API 服务统一封装层（门面模式）
// 本文件将所有分散的 API 客户端（chatClient、sessionClient 等）整合到一个类中，
// 提供统一的调用入口，上层代码只需要使用 apiService 即可访问所有 API
//
// 关键概念解释：
// - 门面模式（Facade Pattern）：将复杂的子系统（多个 Client）封装为一个简单的接口
//   类似于"前台"——你不需要知道酒店有哪些部门，只需要告诉前台你的需求
// - Parameters<typeof xxx>[0]：TypeScript 的工具类型，获取某个函数第一个参数的类型
//   这样可以自动同步参数类型，避免手动维护两份类型定义
// - 箭头函数（=>）：一种简洁的函数写法，(参数) => 表达式
//   例如 getLatestArtifact = (sessionId) => artifactClient.getLatestArtifact(sessionId)
//   等价于 getLatestArtifact(sessionId) { return artifactClient.getLatestArtifact(sessionId); }

import { artifactClient } from './artifactClient';
import { chatClient } from './chatClient';
import { cityClient } from './cityClient';
import { healthClient } from './healthClient';
import { mapClient } from './mapClient';
import { modelClient } from './modelClient';
import { sessionClient } from './sessionClient';
import { shareClient } from './shareClient';

// 【核心】APIService 类 —— 所有 API 的统一入口
// 每个属性都是一个箭头函数，直接委托给对应的 Client 实例
// 上层代码通过 apiService.xxx() 调用，无需关心底层是哪个 Client
export class APIService {
  // ---- 行程产物相关 ----
  getLatestArtifact = (sessionId: string) => artifactClient.getLatestArtifact(sessionId);
  getArtifactHistory = (sessionId: string, limit?: number) => artifactClient.getArtifactHistory(sessionId, limit);

  // ---- 健康检查相关 ----
  checkHealth = () => healthClient.checkHealth();
  checkLLMHealth = () => healthClient.checkLLMHealth();
  checkToolsHealth = () => healthClient.checkToolsHealth();
  checkToolsIntentsHealth = () => healthClient.checkToolsIntentsHealth();

  // ---- 会话管理相关 ----
  createSession = () => sessionClient.createSession();
  getSessions = () => sessionClient.getSessions();
  getSessionMessages = (sessionId: string) => sessionClient.getSessionMessages(sessionId);
  deleteSession = (sessionId: string) => sessionClient.deleteSession(sessionId);
  updateSessionName = (sessionId: string, name: string) => sessionClient.updateSessionName(sessionId, name);

  // ---- 模型管理相关 ----
  // Parameters<typeof modelClient.getAvailableModels>[0]：自动获取 getAvailableModels 函数第一个参数的类型
  // 这样当 modelClient 的参数类型变化时，这里会自动同步，不需要手动修改
  getAvailableModels = (options?: Parameters<typeof modelClient.getAvailableModels>[0]) =>
    modelClient.getAvailableModels(options);
  setSessionModel = (sessionId: string, modelId: string) => modelClient.setSessionModel(sessionId, modelId);
  getSessionModel = (sessionId: string) => modelClient.getSessionModel(sessionId);

  // ---- 城市数据相关 ----
  getRegions = () => cityClient.getRegions();
  getTags = () => cityClient.getTags();
  getCities = (params?: Parameters<typeof cityClient.getCities>[0]) => cityClient.getCities(params);
  getCityDetail = (cityId: string) => cityClient.getCityDetail(cityId);

  // ---- 地图相关 ----
  getRoutePreview = (payload: Parameters<typeof mapClient.getRoutePreview>[0]) => mapClient.getRoutePreview(payload);

  // ---- 分享功能相关 ----
  createShareLink = (payload: Parameters<typeof shareClient.createShareLink>[0]) => shareClient.createShareLink(payload);
  getShareDetail = (shareId: string) => shareClient.getShareDetail(shareId);

  // ---- 聊天相关 ----
  clearChat = (sessionId: string) => chatClient.clearChat(sessionId);
  fetchStreamChat = (
    request: Parameters<typeof chatClient.fetchStreamChat>[0],
    callbacks: Parameters<typeof chatClient.fetchStreamChat>[1]
  ) => chatClient.fetchStreamChat(request, callbacks);
  cancelAllRequests = () => chatClient.cancelAllRequests();
  getConnectionStatus = () => chatClient.getConnectionStatus();
}

// 【核心】apiService —— APIService 的全局单例实例
// 整个应用共享这一个实例，通过 import { apiService } 使用
export const apiService = new APIService();
