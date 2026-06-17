// 产物投递（Delivery）相关的类型定义
// "投递"是指将 AI 生成的旅行计划产物打包、格式化后，交付给用户的过程
// 类比：就像快递打包——把旅行计划装进标准化的包裹里，附上标签和说明

// 'use client' 是 Next.js 的指令，标记此文件中的代码只在客户端（浏览器）运行
// 在 Next.js 中，组件和文件默认在服务端渲染，加上这个指令后切换为客户端执行
'use client';

// 产物概览指标 —— 在产物卡片上展示的关键指标
// 应用场景：在行程概览卡片上显示"总预算 ¥3000"、"行程天数 3天"等指标
export interface ArtifactOverviewMetric {
  label: string;                         // 指标标签，如 "总预算"、"行程天数"
  value: string;                         // 指标值，如 "¥3000"、"3天"
  tone?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  // 可选的视觉色调，用于前端展示不同颜色：
  // 'default'：默认色（灰色）
  // 'success'：成功色（绿色），如 "验证通过"
  // 'warning'：警告色（黄色），如 "部分数据可能过时"
  // 'danger'：危险色（红色），如 "验证未通过"
  // 'info'：信息色（蓝色），如 "已使用3个工具"
}

// 产物投递章节 —— 产物文档中的一个内容章节
// 应用场景：行程分享文档中，"行程安排"、"预算明细"、"实用信息"各是一个章节
export interface ArtifactDeliverySection {
  key: string;                           // 章节唯一标识，如 'itinerary'、'budget'
  title: string;                         // 章节标题，如 "行程安排"
  items: string[];                       // 章节内容条目列表，如 ["Day1: 宽窄巷子", "Day2: 武侯祠"]
}

// 【核心】产物投递描述符 —— 描述产物投递包的元信息
// 应用场景：当用户分享行程时，描述符记录了这份分享的标题、摘要、指标等展示信息
// 类比：就像快递包裹上的面单——写明了里面是什么、怎么展示
export interface ArtifactDeliveryDescriptor {
  title: string;                         // 投递标题，如 "成都3日美食之旅"
  filenameBase: string;                  // 导出文件的基础文件名，如 "chengdu-3day-food-tour"
  summary: string;                       // 一句话摘要
  summaryLines: string[];                // 多行摘要（用于详细展示）
  metrics: ArtifactOverviewMetric[];     // 概览指标列表
  warnings: string[];                    // 警告信息列表，如 ["部分景点门票价格可能已变更"]
  subagentTrail: string[];               // 子代理执行轨迹，如 ['research_agent', 'planning_agent']
  shareContent: string;                  // 分享的纯文本内容
  htmlDocumentTitle: string;             // HTML 文档的标题
  htmlSections: ArtifactDeliverySection[];  // HTML 文档的章节列表
}

// 产物投递分享元数据 —— 分享功能所需的元信息
export interface ArtifactDeliveryShareMetadata {
  title: string;                         // 分享标题
  content: string;                       // 分享内容
}

// 【核心】产物投递包 —— 完整的产物投递数据包
// 应用场景：这是产物投递的最终数据结构，包含了从产物数据到展示格式到分享信息的所有内容
// 类比：一个完整的快递包裹，里面有物品（artifact）、面单（descriptor）、
//       精美包装（htmlContent）和收件人信息（share）
export interface ArtifactDeliveryBundle {
  schemaVersion: '2026-03-29';          // 数据格式版本号（字面量类型，固定为这个日期字符串）
                                         // 字面量类型：TypeScript 中可以精确限定为某个具体值，
                                         // 而不是宽泛的 string 类型，用于版本控制和数据兼容性检查
  descriptor: ArtifactDeliveryDescriptor;  // 投递描述符（包裹面单）
  artifact: Record<string, unknown> | null;  // 原始产物数据（包裹里的物品），null 表示无产物
  executionReceipt: Record<string, unknown> | null;  // 执行回执（包裹的物流追踪信息）
  htmlContent: string;                   // HTML 格式的展示内容（精美包装）
  share: ArtifactDeliveryShareMetadata;  // 分享元数据（收件人信息）
}
