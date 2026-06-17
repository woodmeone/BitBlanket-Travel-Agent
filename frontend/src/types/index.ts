// 【核心】整个前端项目的 TypeScript 类型定义中心
// TypeScript 的 interface（接口）用来描述"一个对象应该有哪些字段、什么类型"，
// 类似于数据库表结构的定义——规定了数据长什么样，但不包含具体的数据值。
// 例如：interface Person { name: string; age: number; } 表示"人"有名字（字符串）和年龄（数字）

// 从 delivery.ts 文件导入 ArtifactDeliveryBundle 类型
// import type 表示只导入类型信息，不会在编译后产生实际代码
import type { ArtifactDeliveryBundle } from './delivery';

// 【核心】消息接口 —— 描述聊天对话中每一条消息的结构
// 应用场景：用户和 AI 助手之间的每条对话都遵循这个结构
// 例如：{ role: 'user', content: '帮我规划成都3日游', timestamp: '2026-01-01T10:00:00Z' }
export interface Message {
  role: 'user' | 'assistant';  // 联合类型：只能是 'user'（用户）或 'assistant'（AI助手）两个字符串之一
  content: string;              // 消息正文内容
  timestamp: string;            // 消息发送时间（ISO 格式的字符串，如 '2026-01-01T10:00:00Z'）
  reasoning?: string;           // 可选字段（?表示可以不填）：AI 的推理过程文本
  diagnostics?: MessageDiagnostics;  // 可选字段：消息的诊断信息（用于调试和展示执行细节）
}

// 【核心】消息诊断信息 —— 记录 AI 回答这条消息时的执行细节
// 应用场景：当 AI 回答"成都3日游攻略"时，diagnostics 会记录用了哪些工具、验证是否通过等
export interface MessageDiagnostics {
  sessionId?: string;                    // 会话ID，标识一次完整的对话会话
  toolsUsed?: string[];                  // AI 回答时调用了哪些工具，如 ['search', 'weather_api']
  verificationPassed?: boolean | null;   // 联合类型：boolean（true/false）或 null（未知），验证是否通过
  staleResultCount?: number;             // 过期结果数量（如天气数据已过期的条目数）
  fallbackSteps?: number;                // 降级步骤数（当主工具失败时使用备用方案的次数）
  planId?: string | null;                // 行程计划ID，或 null（尚未生成计划）
  executionStats?: Record<string, unknown>;  // Record<string, unknown> 表示"键是字符串、值是任意类型的对象"，类似一个灵活的字典
  artifact?: TripPlanArtifact | null;    // 本次回答生成的行程计划产物，或 null
  subagentEvents?: SubagentEvent[];      // 子代理事件列表（记录 AI 各个子步骤的执行情况）
  executionReceipt?: ExecutionReceipt;   // 执行回执（完整记录本次 AI 执行的全过程）
  runId?: string;                        // 运行ID，标识一次 AI 推理运行
  requestId?: string;                    // 请求ID，标识一次 API 请求
  traceId?: string;                      // 追踪ID，用于分布式追踪请求链路
}

// 旅行意图产物 —— 描述用户想要什么样的旅行
// 应用场景：用户说"我想去成都吃火锅"，AI 解析出意图为 { name: '美食之旅', confidence: 0.9 }
export interface TripIntentArtifact {
  name: string;                          // 意图名称，如 '美食之旅'、'文化探索'
  confidence?: number | null;            // AI 对意图判断的置信度（0~1 之间），null 表示未知
  entities: Record<string, unknown>;     // 提取出的实体信息，如 { destination: '成都', duration: '3天' }
  detail: Record<string, unknown>;       // 意图的详细描述信息
}

// 研究证据产物 —— 记录 AI 搜索到的单条证据
// 应用场景：AI 搜索"成都必去景点"时，每条搜索结果就是一条 ResearchEvidenceArtifact
export interface ResearchEvidenceArtifact {
  tool?: string;                         // 使用的搜索工具名称，如 'web_search'
  status?: string;                       // 搜索状态，如 'success'、'failed'
  query?: string;                        // 搜索关键词，如 '成都必去景点'
  [key: string]: unknown;                // 索引签名：允许对象包含任意额外的字段，值类型为 unknown（任意类型）
                                         // 例如：还可能有 url、snippet 等未预定义的字段
}

// 研究档案产物 —— 汇总所有搜索证据的档案
// 应用场景：AI 完成所有搜索后，将结果汇总成一份 ResearchDossierArtifact
export interface ResearchDossierArtifact {
  summary: string;                       // 研究摘要，如 "成都以美食和熊猫闻名，建议3-5天行程"
  evidence: ResearchEvidenceArtifact[];  // 所有搜索证据的列表
  destinations: string[];                // 涉及的目的地列表，如 ['成都', '都江堰']
  sourceTools: string[];                 // 使用的数据源工具列表，如 ['web_search', 'weather_api']
}

// 行程草稿产物 —— AI 生成的行程计划草稿
// 应用场景：AI 根据研究结果生成一份初步行程，如 "Day1: 宽窄巷子→锦里→春熙路"
export interface ItineraryDraftArtifact {
  planId?: string | null;                // 行程计划ID
  explanation: string;                   // 行程说明，如 "3天成都美食文化之旅"
  steps: Record<string, unknown>[];      // 行程步骤列表，每个步骤是一个对象（如景点、时间、交通等）
  validationStatus: string;              // 验证状态，如 'pass'（通过）、'fail'（未通过）
  validationErrors: unknown[];           // 验证错误列表（如"景点已关闭"、"距离过远"等）
}

// 预算报告产物 —— 行程的费用预算
// 应用场景：AI 估算成都3日游总花费约 3000 元，其中住宿 1200、餐饮 600 等
export interface BudgetReportArtifact {
  summary: Record<string, unknown>;      // 预算摘要信息
  executionBudget: Record<string, unknown>;  // 执行预算明细
  staleResultCount: number;              // 过期数据条目数（如价格信息可能已过时）
  fallbackSteps: number;                 // 降级步骤数
}

// 验证报告产物 —— 对行程计划的验证结果
// 应用场景：AI 检查行程后发现"武侯祠17:00闭馆，但安排了18:00参观"，生成验证报告
export interface VerificationReportArtifact {
  passed?: boolean | null;               // 验证是否通过
  shouldRetry: boolean;                  // 是否需要重新生成行程
  issues: Record<string, unknown>[];     // 发现的问题列表
  refreshTargets: string[];              // 需要刷新数据的目标（如需要重新查询天气的城市）
  summary: string;                       // 验证摘要
}

// 【核心】旅行计划产物 —— 整个旅行规划的核心数据结构
// 应用场景：这是 AI 一次完整规划的结果，包含意图→研究→行程→预算→验证的完整链路
// 类比：就像一份完整的旅行方案书，从"想去哪"到"怎么去"到"花多少钱"到"方案是否靠谱"
export interface TripPlanArtifact {
  intent: TripIntentArtifact;            // 旅行意图（用户想干什么）
  research: ResearchDossierArtifact;     // 研究档案（AI 搜到了什么信息）
  itinerary: ItineraryDraftArtifact;     // 行程草稿（具体怎么玩）
  budget: BudgetReportArtifact;          // 预算报告（花多少钱）
  verification: VerificationReportArtifact;  // 验证报告（方案是否靠谱）
  answer: string;                        // AI 给用户的最终回答文本
  reasoning: string;                     // AI 的推理过程说明
  toolsUsed: string[];                   // 使用的工具列表
  metadata: Record<string, unknown>;     // 其他元数据
}

// 产物补丁 —— 对已有旅行计划的部分更新
// 应用场景：AI 发现行程中某个景点闭馆了，只需更新 itinerary 部分，不需要重新生成全部
// Partial<T> 是 TypeScript 内置工具类型，表示"把 T 的所有字段都变成可选的"
// 例如 Partial<TripIntentArtifact> 意味着 intent 的每个字段都可以不填
export interface ArtifactPatch {
  intent?: Partial<TripIntentArtifact>;           // 可选：更新意图的部分字段
  research?: Partial<ResearchDossierArtifact>;    // 可选：更新研究的部分字段
  itinerary?: Partial<ItineraryDraftArtifact>;    // 可选：更新行程的部分字段
  budget?: Partial<BudgetReportArtifact>;         // 可选：更新预算的部分字段
  verification?: Partial<VerificationReportArtifact>;  // 可选：更新验证的部分字段
  answer?: string;                                // 可选：更新回答文本
  reasoning?: string;                             // 可选：更新推理过程
  toolsUsed?: string[];                           // 可选：更新工具列表
  metadata?: Record<string, unknown>;             // 可选：更新元数据
  [key: string]: unknown;                         // 索引签名：允许包含其他未预定义的字段
}

// 计划预览步骤 —— 行程中单个步骤的预览信息
export interface PlanPreviewStep {
  id?: string;                           // 步骤ID
  title?: string;                        // 步骤标题，如 "参观武侯祠"
  description?: string;                  // 步骤描述
  tool?: string;                         // 使用的工具名称
  [key: string]: unknown;                // 索引签名：允许额外字段
}

// 【核心】计划预览 —— AI 流式输出时，逐步展示给用户的行程预览
// 应用场景：用户发送"帮我规划成都3日游"后，AI 一边思考一边通过流式事件推送 PlanPreview，
// 前端实时展示"正在搜索…→正在规划行程…→行程预览"
export interface PlanPreview {
  planId?: string | null;                // 行程计划ID
  intent?: string | null;                // 意图描述
  explanation?: string | null;           // 行程说明
  validationStatus?: string | null;      // 验证状态
  validationErrors?: unknown[];          // 验证错误
  steps: PlanPreviewStep[];              // 行程步骤列表
  artifact?: TripPlanArtifact | null;    // 完整的旅行计划产物
  artifactPatch?: ArtifactPatch | null;  // 产物的增量更新（只包含变化的部分）
  subagent?: string | null;              // 当前执行的子代理名称
  skills?: string[];                     // 当前使用的技能列表
}

// 【核心】聊天流式事件类型常量 —— 定义 AI 流式响应中所有可能的事件类型
// as const 是 TypeScript 的"常量断言"，让编译器把这些值当作不可变的字面量类型
// 例如 'session_id' 不会被推断为 string，而是精确的 'session_id' 字面量类型
export const CHAT_STREAM_EVENT_TYPES = {
  SESSION_ID: 'session_id',              // 会话ID事件：返回本次对话的会话标识
  REASONING_START: 'reasoning_start',    // 推理开始事件：AI 开始思考
  REASONING_CHUNK: 'reasoning_chunk',    // 推理片段事件：AI 思考过程的文本片段
  REASONING_END: 'reasoning_end',        // 推理结束事件：AI 思考完毕
  ANSWER_START: 'answer_start',          // 回答开始事件：AI 开始输出正式回答
  STAGE: 'stage',                        // 阶段事件：当前执行到哪个阶段（如搜索、规划、验证）
  PLAN_PREVIEW: 'plan_preview',          // 计划预览事件：推送行程预览数据
  SUBAGENT_START: 'subagent_start',      // 子代理开始事件：某个子代理开始工作
  SUBAGENT_END: 'subagent_end',          // 子代理结束事件：某个子代理完成工作
  ARTIFACT_PATCH: 'artifact_patch',      // 产物补丁事件：推送行程计划的增量更新
  TOOL_START: 'tool_start',              // 工具调用开始事件
  TOOL_END: 'tool_end',                  // 工具调用结束事件
  CHUNK: 'chunk',                        // 文本片段事件：AI 回答的文本片段
  METADATA: 'metadata',                  // 元数据事件
  ERROR: 'error',                        // 错误事件
  DONE: 'done',                          // 完成事件：整个流式响应结束
} as const;

// 【核心】聊天流式事件类型的联合类型
// typeof CHAT_STREAM_EVENT_TYPES 获取常量对象的类型
// keyof 获取对象所有键的联合类型（即 'SESSION_ID' | 'REASONING_START' | ...）
// [keyof typeof ...] 通过索引访问获取所有值的联合类型
// 最终结果：'session_id' | 'reasoning_start' | 'reasoning_chunk' | ... | 'done'
// 应用场景：函数参数需要接收事件类型时，限制只能传入这些合法值
export type ChatStreamEventType = (typeof CHAT_STREAM_EVENT_TYPES)[keyof typeof CHAT_STREAM_EVENT_TYPES];

// 流式阶段事件 —— 描述当前执行阶段的信息
// 应用场景：前端展示"正在搜索目的地信息…"的进度提示
export interface StreamStageEvent {
  stage?: string;                        // 阶段标识，如 'research'、'planning'
  label?: string;                        // 阶段显示名称，如 "搜索目的地信息"
  progress?: number | null;              // 进度百分比（0~100），null 表示未知
  subagent?: string | null;              // 当前阶段的子代理名称
}

// 子代理事件 —— 记录 AI 子代理（如搜索代理、规划代理）的执行情况
// 应用场景：AI 规划行程时，"搜索代理"先搜索信息，"规划代理"再生成行程，
// 每个子代理的启动和完成都会产生一个 SubagentEvent
export interface SubagentEvent {
  subagent: string;                      // 子代理名称，如 'research_agent'、'planning_agent'
  description?: string | null;           // 子代理的描述
  skills?: string[];                     // 子代理使用的技能列表
  toolNames?: string[];                  // 子代理调用的工具名称列表
  sequence?: number | null;              // 执行序号（第几个执行的子代理）
  trigger?: string | null;               // 触发原因
  status?: string | null;                // 执行状态，如 'running'、'completed'
  summary?: string | null;               // 执行结果摘要
  timestamp?: string;                    // 事件时间戳
  clientKey?: string;                    // 客户端标识键（用于前端去重和唯一标识）
}

// 执行回执阶段 —— 执行回执中的单个阶段记录
export interface ExecutionReceiptStage {
  stage?: string | null;                 // 阶段标识
  label?: string | null;                 // 阶段显示名称
}

// 执行回执片段 —— 单个子代理的执行记录
export interface ExecutionReceiptSegment {
  subagent: string;                      // 子代理名称
  sequence: number;                      // 执行序号
  trigger?: string | null;               // 触发原因
  description?: string | null;           // 描述
  skills?: string[];                     // 使用的技能
  toolNames?: string[];                  // 调用的工具名称
  toolsUsed?: string[];                  // 实际使用的工具列表
  stages?: ExecutionReceiptStage[];      // 执行阶段列表
  artifactPatchSections?: string[];      // 更新的产物部分列表（如 ['itinerary', 'budget']）
  status?: string | null;                // 执行状态
  summary?: string | null;               // 执行摘要
}

// 【核心】执行回执 —— 完整记录一次 AI 执行的全过程
// 应用场景：类似快递追踪，记录"搜索代理→规划代理→验证代理"的完整执行链路
export interface ExecutionReceipt {
  sessionId: string;                     // 会话ID
  runId?: string | null;                 // 运行ID
  chatMode?: string | null;              // 聊天模式
  subagentOrder?: string[];              // 子代理执行顺序列表
  toolsUsed?: string[];                  // 所有使用的工具列表
  artifactPatchSubagents?: string[];     // 产生了产物更新的子代理列表
  segments?: ExecutionReceiptSegment[];  // 各子代理的执行片段列表
}

// 会话信息 —— 描述一个聊天会话的基本信息
export interface SessionInfo {
  session_id: string;                    // 会话唯一标识
  message_count: number;                 // 该会话中的消息数量
  last_active: string;                   // 最后活跃时间
  name?: string;                         // 会话名称（用户可自定义）
  model_id?: string;                     // 使用的 AI 模型ID
}

// 应用配置 —— 前端应用的全局配置
export interface AppConfig {
  apiBase: string;                       // 后端 API 的基础地址，如 'http://localhost:8000'
}

// 聊天模式类型 —— 联合类型，限定 AI 的三种工作模式
// 'direct'：直接回答模式（简单问答）
// 'react'：反应式模式（边思考边调用工具）
// 'plan'：规划模式（完整的多步骤规划流程）
export type ChatMode = 'direct' | 'react' | 'plan';

// 聊天请求 —— 前端发送给后端的聊天请求结构
export interface ChatRequest {
  message: string;                       // 用户输入的消息内容
  display_message?: string;              // 可选：用于展示的消息（可能与实际消息不同）
  session_id: string;                    // 会话ID
  mode?: ChatMode;                       // 可选：聊天模式，默认由后端决定
}

// 聊天响应 —— 后端返回给前端的聊天响应结构
export interface ChatResponse {
  success: boolean;                      // 请求是否成功
  response?: string;                     // AI 的回答内容
  error?: string;                        // 错误信息（请求失败时）
  session_id?: string;                   // 会话ID
}

// 会话消息响应 —— 获取历史消息时的响应结构
export interface SessionMessagesResponse {
  success: boolean;                      // 请求是否成功
  messages: Message[];                   // 该会话的所有消息列表
}

// 最新产物响应 —— 获取最新旅行计划产物时的响应结构
export interface LatestArtifactResponse {
  success: boolean;                      // 请求是否成功
  session_id: string;                    // 会话ID
  artifact_found: boolean;               // 是否找到了产物
  artifact: TripPlanArtifact | null;     // 旅行计划产物（未找到则为 null）
  run_id?: string | null;                // 运行ID
  message_timestamp?: string | null;     // 产物对应的消息时间戳
  message_index?: number | null;         // 产物对应的消息在列表中的位置索引
}

// 产物历史条目 —— 历史产物列表中的单条记录
export interface ArtifactHistoryEntry {
  artifact: TripPlanArtifact;            // 旅行计划产物
  run_id?: string | null;                // 运行ID
  message_timestamp?: string | null;     // 消息时间戳
  message_index: number;                 // 消息索引位置
}

// 产物历史响应 —— 获取产物历史记录时的响应结构
export interface ArtifactHistoryResponse {
  success: boolean;                      // 请求是否成功
  session_id: string;                    // 会话ID
  count: number;                         // 历史产物总数
  entries: ArtifactHistoryEntry[];       // 历史产物条目列表
}

// 模型信息 —— 描述一个可用的 AI 模型
export interface ModelInfo {
  model_id: string;                      // 模型唯一标识
  name: string;                          // 模型显示名称，如 "GPT-4"
  provider: string;                      // 模型提供商，如 "openai"
  model: string;                         // 模型技术名称，如 "gpt-4-turbo"
}

// 可用模型列表响应
export interface AvailableModelsResponse {
  success: boolean;                      // 请求是否成功
  models: ModelInfo[];                   // 可用模型列表
}

// 设置模型请求 —— 切换 AI 模型时的请求结构
export interface SetModelRequest {
  model_id: string;                      // 要切换到的模型ID
}

// 设置模型响应
export interface SetModelResponse {
  success: boolean;                      // 切换是否成功
  message?: string;                      // 提示信息
  model_id: string;                      // 当前使用的模型ID
}

// 获取会话模型响应
export interface GetSessionModelResponse {
  success: boolean;                      // 请求是否成功
  model_id: string;                      // 当前会话使用的模型ID
}

// 城市景点 —— 描述一个城市中的单个景点
export interface CityAttraction {
  name: string;                          // 景点名称，如 "武侯祠"
  type: string;                          // 景点类型，如 "历史"、"自然"
  duration: string;                      // 建议游览时长，如 "2-3小时"
  ticket: number;                        // 门票价格（元）
  district?: string | null;              // 所在区域，如 "武侯区"
  note?: string | null;                  // 游览提示
}

// 城市摘要 —— 描述一个城市的基本旅行信息
// 应用场景：在城市选择列表中展示每个城市的概要信息
export interface CitySummary {
  id: string;                            // 城市唯一标识
  name: string;                          // 城市名称，如 "成都"
  region: string;                        // 所属区域，如 "西南"
  tags: string[];                        // 标签列表，如 ["美食", "文化", "熊猫"]
  description: string;                   // 城市描述
  avg_budget_per_day: number;            // 每日平均预算（元）
  best_seasons: string[];                // 最佳旅行季节，如 ["春", "秋"]
  trip_duration: string;                 // 建议旅行天数，如 "3-5天"
  walk_intensity: 'low' | 'medium' | 'high';  // 步行强度：低/中/高（联合类型限定三个值）
  rain_friendly: boolean;                // 是否适合雨天游玩
  family_friendly: boolean;              // 是否适合亲子游
  food_friendly: boolean;                // 是否美食友好
  style_label: string;                   // 风格标签，如 "休闲美食"
  editorial_note: string;                // 编辑推荐语
  data_source: 'curated';                // 数据来源：固定为 'curated'（人工策划）
}

// 城市详情 —— extends 表示继承 CitySummary 的所有字段，并额外增加景点列表
// 交叉类型/继承：CityDetail 拥有 CitySummary 的全部字段 + attractions 字段
export interface CityDetail extends CitySummary {
  attractions: CityAttraction[];         // 该城市的景点列表
}

// 城市列表响应
export interface CityListResponse {
  cities: CitySummary[];                 // 城市摘要列表
}

// 区域列表响应
export interface RegionListResponse {
  regions: string[];                     // 区域名称列表，如 ["西南", "华东", "华北"]
}

// 标签列表响应
export interface TagListResponse {
  tags: string[];                        // 标签列表，如 ["美食", "文化", "自然"]
}

// 健康检查响应 —— 后端服务健康状态
export interface HealthResponse {
  status: string;                        // 服务状态，如 "ok"
  version: string;                       // 服务版本号
  timestamp: string;                     // 检查时间戳
  services: Record<string, string>;      // 各子服务的状态，如 { "llm": "ok", "tools": "ok" }
}

// LLM 健康检查响应 —— 大语言模型服务的健康状态
export interface LLMHealthResponse {
  status: 'ok' | 'not initialized';      // 联合类型：'ok'（正常）或 'not initialized'（未初始化）
  llm_adapter: boolean;                  // LLM 适配器是否可用
  tools_count: number;                   // 已配置的工具数量
  memory_enabled: boolean;               // 是否启用了记忆功能
}

// 工具健康检查响应 —— 工具服务的健康状态
export interface ToolsHealthResponse {
  status: 'ok' | 'not initialized';      // 服务状态
  initialized: boolean;                  // 是否已初始化
  configured_tools_count: number;        // 已配置的工具数量
  circuit_open_count: number;            // 熔断器打开数量（熔断器：当工具频繁失败时自动停止调用，防止级联故障）
  slo: Record<string, unknown>;          // 服务等级目标（SLO）指标
  intent_aggregate: Record<string, Record<string, unknown>>;  // 意图聚合统计（嵌套的 Record 类型）
  window_minutes: number;                // 统计时间窗口（分钟）
  diagnostics: Record<string, unknown>;  // 诊断信息
}

// 工具意图健康检查响应
export interface ToolIntentsHealthResponse {
  status: 'ok' | 'not initialized';      // 服务状态
  window_minutes: number;                // 统计时间窗口（分钟）
  total_requests: number;                // 总请求数
  intent_aggregate: Record<string, Record<string, unknown>>;  // 意图聚合统计
}

// 路线预览请求 —— 请求路线预览时的参数
export interface RoutePreviewRequest {
  spots: string[];                       // 景点名称列表，如 ["武侯祠", "锦里", "宽窄巷子"]
  city?: string;                         // 城市名称
  provider?: 'auto' | 'amap';            // 路线服务提供商：'auto'（自动选择）或 'amap'（高德地图）
}

// 路线点 —— 地图上的一个坐标点
export interface RoutePoint {
  name: string;                          // 地点名称
  lat: number;                           // 纬度（latitude）
  lng: number;                           // 经度（longitude）
}

// 路线预览响应 —— 路线预览的结果
export interface RoutePreviewResponse {
  success: boolean;                      // 请求是否成功
  provider: 'amap';                      // 使用的路线服务提供商
  points: RoutePoint[];                  // 路线上的坐标点列表
  distance_m: number;                    // 总距离（米）
  duration_s: number;                    // 预计耗时（秒）
  static_map_url: string;                // 静态地图图片 URL
  route_polyline: [number, number][];    // 路线折线坐标数组（每个元素是 [纬度, 经度] 的元组）
}

// 分享创建请求 —— 创建行程分享时的参数
export interface ShareCreateRequest {
  title?: string;                        // 分享标题
  content: string;                       // 分享内容（纯文本）
  html_content?: string;                 // 分享的 HTML 格式内容
  delivery_bundle?: ArtifactDeliveryBundle | null;  // 可选：附带的产物投递包
}

// 分享创建响应
export interface ShareCreateResponse {
  success: boolean;                      // 创建是否成功
  share_id: string;                      // 分享唯一标识
  share_url: string;                     // 分享链接地址
}

// 分享详情响应 —— 获取分享详情时的返回数据
export interface ShareDetailResponse {
  success: boolean;                      // 请求是否成功
  share_id: string;                      // 分享唯一标识
  title?: string;                        // 分享标题
  content: string;                       // 分享内容
  html_content?: string | null;          // HTML 格式内容
  delivery_bundle?: ArtifactDeliveryBundle | null;  // 产物投递包
  created_at: string;                    // 创建时间
}

// 从 delivery.ts 重新导出类型，方便其他模块直接从本文件导入
// 这样其他文件可以写 import { ArtifactDeliveryBundle } from '@/types'
// 而不需要知道它实际定义在 delivery.ts 中
export type {
  ArtifactDeliveryBundle,
  ArtifactDeliveryDescriptor,
  ArtifactDeliverySection,
  ArtifactDeliveryShareMetadata,
  ArtifactOverviewMetric,
} from './delivery';
