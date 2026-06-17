// 子代理事件工具模块
// 为 SubagentEvent（子代理事件）生成唯一标识键，用于 React 渲染时的列表去重和 key 属性
//
// 核心概念：
// - 子代理（Subagent）：AI 规划行程时的子步骤执行者，如"搜索代理"、"规划代理"
// - 子代理事件（SubagentEvent）：记录子代理的启动、完成等状态变化
// - clientKey：前端为事件生成的唯一标识，用于 React 列表渲染的 key 属性
//
// 应用场景：React 渲染子代理事件列表时，每个列表项需要一个唯一的 key，
// 此函数根据事件的各种属性组合生成一个稳定的唯一字符串

import type { SubagentEvent } from '@/types';

// 【核心】构建子代理事件的唯一标识键
// 优先使用服务端返回的 clientKey，如果没有则根据事件属性组合生成
// 应用场景：<div key={buildSubagentEventKey(event, index)}>...</div>
export function buildSubagentEventKey(event: SubagentEvent, index = 0): string {
  // 如果服务端已经提供了 clientKey，直接使用（最可靠）
  if (event.clientKey) return event.clientKey;

  // 否则，用多个字段拼接成唯一键，用 "::" 分隔
  // 拼接规则：子代理名::序号::时间戳::状态/触发器::摘要/描述::技能列表::数组索引
  // 例如："research_agent::1::2026-01-01T10:00::completed::搜索完成::search|weather::0"
  return [
    event.subagent || 'unknown',                          // 子代理名称
    event.sequence ?? 'na',                               // 执行序号（?? 是空值合并运算符，null/undefined 时用 'na'）
    event.timestamp ?? 'na',                              // 时间戳
    event.status ?? event.trigger ?? 'started',           // 状态或触发器，都没有则用 'started'
    event.summary ?? event.description ?? 'no-summary',   // 摘要或描述，都没有则用 'no-summary'
    event.skills?.join('|') || 'no-skills',               // 技能列表用 "|" 连接，如 "search|weather"
    index,                                                // 数组中的位置索引（兜底保证唯一性）
  ].join('::');
}
