// cityClient.ts —— 城市数据 API 客户端
// 本文件负责与后端的城市相关接口通信，包括：
// 1. 获取地区列表（如华北、华南等）
// 2. 获取标签列表（如美食、历史、自然等）
// 3. 按条件筛选城市列表
// 4. 获取城市详细信息
//
// 应用场景举例：
// 用户在首页选择"华东"地区 + "美食"标签，系统展示符合条件的城市列表；
// 用户点击某个城市卡片，进入城市详情页

import type { CityDetail, CityListResponse, RegionListResponse, TagListResponse } from '@/types';
import { API_PREFIX, apiClient } from './core';

// CityClient 类 —— 城市数据的 API 客户端
class CityClient {
  // getRegions —— 获取地区列表
  // 应用场景：首页的"按地区筛选"下拉菜单，展示所有可选地区
  async getRegions(): Promise<RegionListResponse> {
    const response = await apiClient.get(`${API_PREFIX}/regions`);
    return response.data;
  }

  // getTags —— 获取标签列表
  // 应用场景：首页的"按标签筛选"区域，展示所有可选标签（如美食、历史、自然风光等）
  async getTags(): Promise<TagListResponse> {
    const response = await apiClient.get(`${API_PREFIX}/tags`);
    return response.data;
  }

  // 【核心】getCities —— 按条件筛选城市列表
  // 应用场景：用户选择"华东"地区和"美食"标签后，获取符合条件的城市
  // 参数说明：
  // - region?: 按地区筛选（可选），如 "华东"
  // - tags?: 按标签筛选（可选），如 ["美食", "历史"]
  // params 中的 undefined 值会被 axios 自动忽略，不会出现在 URL 中
  // tags 数组用 join(',') 拼接为逗号分隔的字符串，如 "美食,历史"
  async getCities(params?: { region?: string; tags?: string[] }): Promise<CityListResponse> {
    const response = await apiClient.get(`${API_PREFIX}/cities`, {
      params: {
        region: params?.region || undefined,
        tags: params?.tags && params.tags.length > 0 ? params.tags.join(',') : undefined,
      },
    });
    return response.data;
  }

  // getCityDetail —— 获取城市详细信息
  // 应用场景：用户点击城市卡片，进入详情页，展示该城市的景点、美食、住宿等完整信息
  // cityId：城市的唯一标识
  async getCityDetail(cityId: string): Promise<CityDetail> {
    const response = await apiClient.get(`${API_PREFIX}/cities/${cityId}`);
    return response.data;
  }
}

// 导出 CityClient 的单例实例
export const cityClient = new CityClient();
