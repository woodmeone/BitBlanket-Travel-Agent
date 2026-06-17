// artifactClient.ts —— 行程数据（Artifact）API 客户端
// 本文件负责与后端的行程产物接口通信，包括：
// 1. 获取最新的行程计划
// 2. 获取行程计划的历史版本
//
// 关键概念解释：
// - Artifact（产物）：AI 生成的行程计划数据，包含景点、酒店、路线等信息
//   每次AI修改行程都会产生一个新的版本，类似于文档的"保存历史"
//
// 应用场景举例：
// 用户打开某个会话，需要加载最新的行程计划显示在界面上；
// 用户点击"查看历史版本"，加载之前的行程方案进行对比

import type { ArtifactHistoryResponse, LatestArtifactResponse } from '@/types';
import { API_PREFIX, apiClient } from './core';

// ArtifactClient 类 —— 行程数据的 API 客户端
class ArtifactClient {
  // 【核心】getLatestArtifact —— 获取指定会话的最新行程计划
  // 应用场景：用户打开对话时，自动加载并展示最新的行程方案
  // sessionId：会话ID
  async getLatestArtifact(sessionId: string): Promise<LatestArtifactResponse> {
    const response = await apiClient.get(`${API_PREFIX}/artifacts/${sessionId}/latest`);
    return response.data;
  }

  // getArtifactHistory —— 获取指定会话的行程计划历史版本
  // 应用场景：用户想查看之前AI生成的行程方案，进行对比或恢复
  // limit = 10：默认返回最近10个版本，可以通过参数调整
  // params: { limit } 会被 axios 转换为 URL 查询参数，如 ?limit=10
  async getArtifactHistory(sessionId: string, limit = 10): Promise<ArtifactHistoryResponse> {
    const response = await apiClient.get(`${API_PREFIX}/artifacts/${sessionId}/history`, {
      params: { limit },
    });
    return response.data;
  }
}

// 导出 ArtifactClient 的单例实例
export const artifactClient = new ArtifactClient();
