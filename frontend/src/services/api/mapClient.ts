// mapClient.ts —— 地图相关 API 客户端
// 本文件负责与后端的地图接口通信，目前包含：
// 1. 获取路线预览数据
//
// 应用场景举例：
// 用户在行程规划页面查看"北京3日游"的路线，
// 前端调用此接口获取各景点之间的路线信息（距离、时间、途经点等），
// 然后在地图上绘制路线

import type { RoutePreviewRequest, RoutePreviewResponse } from '@/types';
import { API_PREFIX, apiClient } from './core';

// MapClient 类 —— 地图功能的 API 客户端
class MapClient {
  // 【核心】getRoutePreview —— 获取路线预览数据
  // 应用场景：用户查看行程时，地图上需要显示从"故宫"到"天坛"的路线
  // payload 包含起点、终点、途经点等信息
  // 返回值包含路线的详细信息（距离、预计时间、路线坐标点等）
  async getRoutePreview(payload: RoutePreviewRequest): Promise<RoutePreviewResponse> {
    // apiClient.post：发送 POST 请求，第二个参数 payload 是请求体
    const response = await apiClient.post(`${API_PREFIX}/map/route-preview`, payload);
    return response.data;
  }
}

// 导出 MapClient 的单例实例
export const mapClient = new MapClient();
