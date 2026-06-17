// 【核心】core.ts —— 前端 API 通信的基础配置文件
// 本文件负责：API 地址配置、请求追踪（trace）、axios 实例创建与拦截器
//
// 关键概念解释：
// - axios：一个流行的 HTTP 请求库，用来发送 GET/POST/PUT/DELETE 等请求
// - axios.create()：创建一个独立的 axios 实例，可以给它设置统一的配置（如基地址、超时时间），
//   类似于"定制一个专属的快递员"，所有通过这个实例发出的请求都会带上这些统一配置
// - 拦截器（interceptor）：在请求发出前或响应返回后自动执行的钩子函数，
//   类似于"快递发出前贴标签"和"快递收到后验货"

// import：从外部库或文件中引入需要的功能
// axios 是 HTTP 请求库，InternalAxiosRequestConfig 是 axios 提供的请求配置类型
import axios, { type InternalAxiosRequestConfig } from 'axios';
// logger 是项目自定义的日志工具，用来在控制台输出调试信息
import { logger } from '@/utils/logger';

// 【核心】API_BASE —— 后端服务的根地址
// 优先级从高到低：
// 1. 浏览器运行时从 window.ENV 读取（用于部署时动态配置）
// 2. 构建时从环境变量 process.env 读取
// 3. 都没有则默认用本地开发地址 http://localhost:38000
//
// typeof window !== 'undefined'：判断当前是否在浏览器环境中运行
// （Node.js 服务端渲染时 window 不存在，所以需要判断）
export const API_BASE =
  (typeof window !== 'undefined' && window.ENV?.NEXT_PUBLIC_API_BASE) ||
  process.env.NEXT_PUBLIC_API_BASE ||
  'http://localhost:38000';

// API_PREFIX —— 完整的 API 请求前缀，所有接口地址都以此开头
// 例如：http://localhost:38000/api/session/new
export const API_PREFIX = `${API_BASE}/api`;

// AxiosTraceConfig —— 扩展 axios 的请求配置类型，增加追踪信息
// type：TypeScript 中用来定义类型别名的关键字，这里给一个组合类型取了个短名字
// & 是交叉类型，表示"同时拥有"左右两边的所有属性
// InternalAxiosRequestConfig 是 axios 原始的请求配置，metadata 是我们额外加的追踪数据
type AxiosTraceConfig = InternalAxiosRequestConfig & {
  metadata?: {
    requestId: string; // 请求唯一标识，用于在日志中追踪某一次请求
    traceId: string;   // 链路追踪ID，用于在多个服务之间追踪同一条请求链路
    startedAt: number; // 请求开始的时间戳（毫秒），用来计算请求耗时
  };
};

// APIRequestOptions —— 调用 API 时可传入的额外选项
// interface：TypeScript 中定义对象结构的语法，描述一个对象"长什么样"
// signal?：问号表示这个属性是可选的。AbortSignal 用来取消正在进行的请求
//   （例如用户切换了页面，可以中断未完成的请求）
// timeoutMs?：超时时间（毫秒），超过这个时间请求自动失败
export interface APIRequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}

// generateClientTraceId —— 生成客户端追踪ID
// function：定义函数的关键字
// prefix = 'req'：参数默认值，如果不传 prefix，默认用 'req'
// 返回值类型 :string 表示这个函数返回一个字符串
function generateClientTraceId(prefix = 'req'): string {
  // globalThis.crypto?.randomUUID?.()：尝试用浏览器/Node.js 提供的加密随机UUID生成器
  // ?. 是可选链操作符，如果前面的值是 null/undefined 就不会报错，而是返回 undefined
  // UUID 是一种几乎不会重复的随机ID，例如 "550e8400-e29b-41d4-a716-446655440000"
  const uuid = globalThis.crypto?.randomUUID?.();
  if (uuid) return `${prefix}-${uuid}`;
  // 如果浏览器不支持 randomUUID，就用时间戳 + 随机字符串作为替代方案
  // Date.now() 返回当前时间的毫秒数
  // Math.random().toString(36) 生成一个36进制的随机字符串
  // .slice(2, 10) 截取第2到第9位字符（去掉前面的 "0."）
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

// 【核心】buildTraceHeaders —— 构建请求追踪头信息
// 每次发请求前调用，生成唯一的 requestId 和 traceId，并放入 HTTP 请求头中
// 这样后端收到请求后，可以在日志中用这些ID追踪请求的完整链路
//
// 应用场景举例：用户反馈"我的聊天请求卡住了"，开发人员可以用 requestId
// 在后端日志中搜索，快速定位该请求经过了哪些服务、耗时多少
export function buildTraceHeaders() {
  const requestId = generateClientTraceId('req');
  const traceId = generateClientTraceId('trace');
  return {
    requestId,
    traceId,
    headers: {
      'X-Request-ID': requestId, // 自定义HTTP头，携带请求ID
      'X-Trace-ID': traceId,     // 自定义HTTP头，携带链路追踪ID
    },
  };
}

// toAxiosRequestConfig —— 将自定义的 APIRequestOptions 转换为 axios 能识别的配置格式
// 这是一个简单的格式转换函数，把我们的 signal/timeoutMs 映射到 axios 的 signal/timeout
export function toAxiosRequestConfig(options?: APIRequestOptions) {
  return {
    signal: options?.signal,
    timeout: options?.timeoutMs,
  };
}

// 【核心】apiClient —— 全局共享的 axios 实例
// 所有 API 请求都通过这个实例发出，这样可以在拦截器中统一处理请求和响应
// axios.create() 创建一个"空白"实例，后续通过拦截器添加统一行为
export const apiClient = axios.create();

// 【核心】请求拦截器 —— 在每个请求发出前自动执行
// 拦截器就像一个"中间人"，在请求发出前自动给请求添加追踪信息
// config 是 axios 的请求配置对象，包含 URL、请求头、参数等
apiClient.interceptors.request.use((config: AxiosTraceConfig) => {
  const trace = buildTraceHeaders(); // 生成追踪信息
  config.headers = config.headers || {};
  config.headers['X-Request-ID'] = trace.requestId; // 在请求头中注入请求ID
  config.headers['X-Trace-ID'] = trace.traceId;     // 在请求头中注入链路追踪ID
  config.metadata = {
    requestId: trace.requestId,
    traceId: trace.traceId,
    startedAt: Date.now(), // 记录请求开始时间，用于后续计算耗时
  };
  return config; // 返回修改后的配置，请求继续发出
});

// 【核心】响应拦截器 —— 在每个响应返回后自动执行
// 第一个参数是成功回调（HTTP 状态码 2xx），第二个参数是失败回调
apiClient.interceptors.response.use(
  (response) => {
    const config = response.config as AxiosTraceConfig;
    // 计算请求耗时：当前时间 - 请求开始时间
    const elapsedMs = config.metadata ? Date.now() - config.metadata.startedAt : undefined;
    if (config.metadata) {
      // 输出请求日志，包含：请求方法、URL、请求ID、链路ID、HTTP状态码、耗时
      logger.info(
        `REST ${response.config.method?.toUpperCase() || 'GET'} ${response.config.url} request_id=${config.metadata.requestId} trace_id=${config.metadata.traceId} status=${response.status} duration_ms=${elapsedMs}`
      );
    }
    return response; // 返回响应，交给后续代码处理
  },
  (error) => {
    const config = (error.config || {}) as AxiosTraceConfig;
    if (config.metadata) {
      // 输出错误日志，方便排查问题
      logger.error(
        `REST ${config.method?.toUpperCase() || 'GET'} ${config.url || ''} request_id=${config.metadata.requestId} trace_id=${config.metadata.traceId} failed: ${error.message}`
      );
    }
    // Promise.reject(error)：将错误继续传递给调用方
    // Promise 是 JavaScript 中处理异步操作的方式，reject 表示"操作失败"
    return Promise.reject(error);
  }
);
