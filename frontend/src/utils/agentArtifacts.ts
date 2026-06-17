// 产物（Artifact）合并工具模块
// 提供 TripPlanArtifact（旅行计划产物）的创建、深拷贝、合并和判空功能
//
// 核心概念：
// - Artifact（产物）：AI 一次规划生成的完整旅行方案数据
// - Patch（补丁）：对已有产物的部分更新，只包含变化的字段
// - 合并（merge）：将补丁应用到基础产物上，生成新的完整产物
//
// 应用场景：AI 流式输出时，先返回基础产物，后续通过 artifact_patch 事件
// 逐步更新各个部分（如先更新行程，再更新预算），前端需要将补丁合并到基础产物上

import type { ArtifactPatch, TripPlanArtifact } from '@/types';

// 判断一个值是否为普通对象（Record）
// value is Record<string, unknown> 是 TypeScript 的"类型谓词"（type predicate），
// 告诉编译器：如果这个函数返回 true，那么 value 的类型就是 Record<string, unknown>
// 应用场景：在合并产物时，需要判断某个字段是对象还是基本类型，对象需要递归合并
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// 【核心】深拷贝（deep clone）—— 递归地复制对象的所有层级
// 与浅拷贝不同，深拷贝会复制嵌套的对象和数组，修改副本不会影响原始数据
// 应用场景：合并产物前，先深拷贝基础产物，避免修改原始数据
// 例如：cloneValue({ a: { b: 1 } }) 返回一个全新的对象，修改返回值不影响原对象
function cloneValue<T>(value: T): T {
  if (Array.isArray(value)) return value.map((item) => cloneValue(item)) as T;  // 数组：递归拷贝每个元素
  if (isRecord(value)) {
    const next: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value)) next[key] = cloneValue(item);  // 对象：递归拷贝每个字段
    return next as T;
  }
  return value;                         // 基本类型（string/number/boolean 等）：直接返回（基本类型天然不可变，无需拷贝）
}

// 【核心】递归合并两个对象 —— 将 patch 的字段合并到 target 上
// 合并规则：
// - 如果两边都是对象，递归合并（深度合并）
// - 否则，patch 的值覆盖 target 的值（浅层覆盖）
// 应用场景：基础产物 { intent: { name: 'general' } } + 补丁 { intent: { name: '美食之旅' } }
//   → 合并结果 { intent: { name: '美食之旅' } }
function mergeRecord(
  target: Record<string, unknown>,
  patch: Record<string, unknown>
): Record<string, unknown> {
  const merged: Record<string, unknown> = { ...target };  // 浅拷贝 target 作为合并基础
  for (const [key, value] of Object.entries(patch)) {
    const current = merged[key];
    if (isRecord(current) && isRecord(value)) {
      // 两边都是对象 → 递归深度合并
      merged[key] = mergeRecord(current, value);
      continue;
    }
    // 一方不是对象 → patch 的值直接覆盖
    merged[key] = cloneValue(value);
  }
  return merged;
}

// 创建一个空的 TripPlanArtifact —— 所有字段都设为默认的空值
// 应用场景：当没有基础产物时，用空产物作为合并的起点
// 例如：AI 第一次规划时还没有基础产物，先创建空产物，再将补丁合并上去
export function createEmptyTripPlanArtifact(): TripPlanArtifact {
  return {
    intent: {
      name: 'general',                  // 默认意图名称
      confidence: null,                 // 置信度未知
      entities: {},                     // 空实体
      detail: {},                       // 空详情
    },
    research: {
      summary: '',                      // 空摘要
      evidence: [],                     // 空证据列表
      destinations: [],                 // 空目的地列表
      sourceTools: [],                  // 空工具列表
    },
    itinerary: {
      planId: null,                     // 无计划ID
      explanation: '',                  // 空说明
      steps: [],                        // 空步骤列表
      validationStatus: 'pass',        // 默认验证通过
      validationErrors: [],             // 空错误列表
    },
    budget: {
      summary: {},                      // 空预算摘要
      executionBudget: {},              // 空执行预算
      staleResultCount: 0,              // 无过期数据
      fallbackSteps: 0,                 // 无降级步骤
    },
    verification: {
      passed: null,                     // 验证结果未知
      shouldRetry: false,               // 不需要重试
      issues: [],                       // 空问题列表
      refreshTargets: [],               // 空刷新目标
      summary: '',                      // 空摘要
    },
    answer: '',                         // 空回答
    reasoning: '',                      // 空推理
    toolsUsed: [],                      // 空工具列表
    metadata: {},                       // 空元数据
  };
}

// 【核心】合并旅行计划产物 —— 将补丁应用到基础产物上
// 这是产物合并的主函数，处理各种边界情况
// 应用场景：AI 流式输出时，先返回基础产物，后续通过 artifact_patch 事件推送增量更新，
// 前端调用此函数将补丁合并到基础产物上，得到最新的完整产物
// 例如：基础产物有完整行程但预算为空，补丁只包含预算部分 → 合并后行程+预算都完整
export function mergeTripPlanArtifact(
  baseArtifact: TripPlanArtifact | null | undefined,
  patch: ArtifactPatch | TripPlanArtifact | null | undefined
): TripPlanArtifact | null {
  if (!patch) return baseArtifact ?? null;  // 无补丁则返回基础产物（或 null）

  const nextBase = baseArtifact ? cloneValue(baseArtifact) : createEmptyTripPlanArtifact();
  // 深拷贝基础产物（避免修改原始数据），如果没有基础产物则创建空产物
  return mergeRecord(
    nextBase as unknown as Record<string, unknown>,
    patch as unknown as Record<string, unknown>
  ) as unknown as TripPlanArtifact;
  // as unknown as X 是 TypeScript 的"双重断言"，用于在类型不兼容时强制转换类型
  // 这里因为 mergeRecord 返回 Record<string, unknown>，需要转换回 TripPlanArtifact
}

// 判断产物是否包含有效数据 —— 检查关键字段是否有内容
// 应用场景：前端判断是否展示行程详情面板，如果产物为空则不展示
export function hasArtifactData(artifact: TripPlanArtifact | null | undefined): boolean {
  if (!artifact) return false;

  return Boolean(
    artifact.answer ||                   // 有回答文本
      artifact.reasoning ||              // 有推理过程
      artifact.toolsUsed.length > 0 ||   // 使用了工具
      artifact.research.summary ||       // 有研究摘要
      artifact.research.evidence.length > 0 ||  // 有搜索证据
      artifact.itinerary.planId ||       // 有行程计划ID
      artifact.itinerary.steps.length > 0 ||    // 有行程步骤
      artifact.verification.summary ||   // 有验证摘要
      artifact.verification.passed !== null &&
        artifact.verification.passed !== undefined  // 验证结果不为 null/undefined
  );
}
