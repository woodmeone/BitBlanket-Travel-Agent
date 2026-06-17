// index.ts —— API 模块的统一导出文件
// 本文件将 api 目录下所有模块的导出项集中重新导出，
// 这样外部代码只需要写 import { xxx } from '@/services/api' 即可，
// 不需要记住每个子模块的具体路径
//
// 关键概念解释：
// - export { xxx } from './yyy'：从另一个模块重新导出，相当于"转发"
//   外部代码 import 时，感觉就像这些内容定义在当前文件中一样
// - export type { xxx }：只导出类型（不导出运行时的值）
//   用于 TypeScript 的类型系统，不会增加打包后的代码体积

// 导出各个 API 客户端实例
export { artifactClient } from './artifactClient';
// 导出基础配置（API地址、axios实例、追踪头构建函数）
export { API_BASE, API_PREFIX, apiClient, buildTraceHeaders } from './core';
export { chatClient } from './chatClient';
export { cityClient } from './cityClient';
export { healthClient } from './healthClient';
export { mapClient } from './mapClient';
export { modelClient } from './modelClient';
export { sessionClient } from './sessionClient';
export { shareClient } from './shareClient';
// 导出统一服务入口（类和实例）
export { apiService, APIService } from './service';
// 导出 SSE 连接状态枚举（运行时值，需要正常导出）
export { SSEConnectionStatus } from './chatStreamTypes';
// 导出流式相关类型（仅类型导出，不产生运行时代码）
export type { StreamCallbacks, StreamCompletionPayload, StreamMetadata } from './chatStreamTypes';
