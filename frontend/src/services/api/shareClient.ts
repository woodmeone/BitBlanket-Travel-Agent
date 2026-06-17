// shareClient.ts —— 分享功能 API 客户端
// 本文件负责与后端的分享接口通信，包括：
// 1. 创建分享链接
// 2. 获取分享详情
//
// 应用场景举例：
// 用户规划好"北京3日游"行程后，点击"分享"按钮生成一个链接，
// 将链接发给朋友，朋友打开链接即可查看完整的行程方案

import type { ShareCreateRequest, ShareCreateResponse, ShareDetailResponse } from '@/types';
import { API_PREFIX, apiClient } from './core';

// ShareClient 类 —— 分享功能的 API 客户端
class ShareClient {
  // 【核心】createShareLink —— 创建分享链接
  // 应用场景：用户点击"分享行程"按钮，系统生成一个可分享的链接
  // payload 包含要分享的行程数据（如会话ID、行程内容等）
  // 返回值包含生成的分享链接ID和完整URL
  async createShareLink(payload: ShareCreateRequest): Promise<ShareCreateResponse> {
    const response = await apiClient.post(`${API_PREFIX}/share-links`, payload);
    return response.data;
  }

  // getShareDetail —— 获取分享的行程详情
  // 应用场景：用户打开别人分享的链接，前端根据链接中的 shareId 获取行程数据
  // encodeURIComponent(shareId)：对 shareId 进行 URL 编码
  // 防止 shareId 中包含特殊字符（如 /、?、#）导致 URL 解析错误
  // 例如："abc/def" 编码后变为 "abc%2Fdef"
  async getShareDetail(shareId: string): Promise<ShareDetailResponse> {
    const response = await apiClient.get(`${API_PREFIX}/share-links/${encodeURIComponent(shareId)}`);
    return response.data;
  }
}

// 导出 ShareClient 的单例实例
export const shareClient = new ShareClient();
