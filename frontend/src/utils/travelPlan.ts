// 【核心】行程解析工具模块
// 将 AI 生成的自由文本行程（Markdown/纯文本）解析为结构化的数据对象，
// 供前端组件渲染使用。同时提供预算估算、路线规划、冲突检测等功能。
//
// 核心流程：AI 回答文本 → parseDayPlanCards() 解析为每日卡片 → 前端展示
// 应用场景：AI 返回 "Day1: 上午宽窄巷子，下午武侯祠…" 这样的自由文本，
// 本模块将其解析为 { dayLabel: "Day1", morning: "宽窄巷子", afternoon: "武侯祠" } 结构

import type { MessageDiagnostics } from '@/types';

import type { TripPlanArtifact } from '@/types';

// 每日行程卡片 —— 描述一天行程的结构化数据
// 应用场景：前端用这个数据渲染"第1天"卡片，分别展示上午/下午/晚上的安排
export interface DayPlanCard {
  dayLabel: string;                      // 日期标签，如 "Day 1"、"第1天"
  morning: string;                       // 上午安排，如 "宽窄巷子逛吃"
  afternoon: string;                     // 下午安排，如 "武侯祠+锦里"
  evening: string;                       // 晚上安排，如 "春熙路夜景"
  tips: string[];                        // 当天小贴士列表，如 ["提前预约武侯祠门票"]
  baseBudget: number;                    // 当天基础预算（元）
  spots: string[];                       // 当天涉及的景点名称列表
}

// 行程方案变体 —— 描述一个可选的行程方案
// 应用场景：AI 可能生成"省钱版"、"均衡版"、"舒适版"等多个方案供用户选择
export interface PlanVariant {
  id: string;                            // 方案唯一标识
  title: string;                         // 方案标题，如 "省钱版"、"舒适版"
  content: string;                       // 方案内容文本
  artifact?: TripPlanArtifact | null;    // 关联的旅行计划产物
  source?: 'text' | 'artifact-history' | 'artifact-current';
  // 联合类型：方案来源
  // 'text'：从 AI 回答文本中解析
  // 'artifact-history'：来自历史产物
  // 'artifact-current'：来自当前产物
  runId?: string | null;                 // 运行ID
  messageTimestamp?: string | null;      // 消息时间戳
}

// 预算预测 —— 根据预算滑块值计算的费用预测
// 应用场景：用户拖动"预算偏好"滑块后，实时计算住宿/餐饮/交通的占比和总额
export interface BudgetProjection {
  totalBudget: number;                   // 总预算（元）
  perDayBudget: number;                  // 每日预算（元）
  hotelShare: number;                    // 住宿占比（0~1 之间，如 0.39 表示 39%）
  foodShare: number;                     // 餐饮占比
  trafficShare: number;                  // 交通占比
}

// 路线坐标点 —— 地图上的一个位置
export interface RoutePoint {
  name: string;                          // 地点名称
  lat: number;                           // 纬度
  lng: number;                           // 经度
}

// 清单项 —— 行前准备清单中的一项
// 应用场景：生成"出发前要准备的事项"清单，如 "预订城际交通"、"确认酒店入住政策"
export interface ChecklistItem {
  id: string;                            // 清单项ID
  label: string;                         // 清单项内容
}

// 提醒项 —— 出发前的定时提醒
// 应用场景：出发前7天/3天/1天分别提醒用户做不同的准备工作
export interface ReminderItem {
  id: string;                            // 提醒ID
  phase: 'T-7' | 'T-3' | 'T-1';        // 联合类型：提醒阶段
                                         // 'T-7'：出发前7天
                                         // 'T-3'：出发前3天
                                         // 'T-1'：出发前1天
  title: string;                         // 提醒标题
  detail: string;                        // 提醒详情
}

// 置信度摘要 —— 行程方案的可靠性评估
// 应用场景：前端展示"方案可信度 85分（高）"，并提示风险项
export interface ConfidenceSummary {
  score: number;                         // 置信度分数（20~98）
  level: 'high' | 'medium' | 'low';     // 置信度等级：高/中/低
  risks: string[];                       // 风险提示列表
}

// 景点决策信息 —— 帮助用户决定是否去某个景点的参考信息
// 应用场景：在"景点决策卡片"中展示"迪士尼建议游玩4-8h，亲子友好，费用较高"
export interface SpotDecisionInfo {
  name: string;                          // 景点名称
  stayDuration: string;                  // 建议停留时长，如 "4-8h"
  bestArrival: string;                   // 最佳到达时间，如 "开园前后"
  audience: string;                      // 适合人群，如 "亲子/第一次来"
  costHint: string;                      // 费用提示，如 "较高"、"中等"
}

// 实用信息卡片 —— 旅行中的实用提示
// 应用场景：展示"天气与穿衣"、"交通建议"、"证件准备"等实用信息卡片
export interface PracticalInfoCard {
  id: string;                            // 卡片ID
  title: string;                         // 卡片标题
  value: string;                         // 卡片内容
  tone: 'neutral' | 'warn' | 'good';    // 视觉色调：中性/警告/良好
}

// 行程冲突 —— 检测到的行程问题
// 应用场景：AI 安排了"18:00参观博物馆"，但博物馆17:00闭馆，检测为 closing_risk 冲突
export interface ItineraryConflict {
  id: string;                            // 冲突ID
  type: 'time_conflict' | 'long_distance' | 'closing_risk';
  // 联合类型：冲突类型
  // 'time_conflict'：时间冲突（如两个活动时间重叠）
  // 'long_distance'：距离过远（如一天内安排了相距50km的景点）
  // 'closing_risk'：闭馆风险（如太晚去博物馆可能已关门）
  severity: 'low' | 'medium' | 'high';  // 严重程度：低/中/高
  title: string;                         // 冲突标题
  description: string;                   // 冲突描述
  suggestion: string;                    // 修复建议
}

// 时间条目 —— 解析出的带时间信息的一条行程安排
// 这是内部使用的辅助类型，不对外导出
interface TimeEntry {
  raw: string;                           // 原始文本，如 "09:30 参观武侯祠"
  timeMinutes: number | null;            // 解析出的时间（转为分钟数，如 9*60+30=570），null 表示无时间
  content: string;                       // 去掉时间后的内容，如 "参观武侯祠"
}

// 时段关键词映射表 —— 用于从自由文本中提取上午/下午/晚上的内容
// Record<K, V> 表示"键类型为 K、值类型为 V 的对象"
// 这里键是 'morning'|'afternoon'|'evening'，值是正则表达式（RegExp）
// 正则表达式（RegExp）是用来匹配文本模式的工具，如 /上午/ 可以匹配包含"上午"的文本
const PERIOD_PATTERNS: Record<'morning' | 'afternoon' | 'evening', RegExp> = {
  morning: /(?:\u4e0a\u5348|\u65e9\u4e0a|morning)/i,      // 匹配"上午"、"早上"或"morning"
  afternoon: /(?:\u4e0b\u5348|afternoon)/i,                 // 匹配"下午"或"afternoon"
  evening: /(?:\u665a\u4e0a|\u591c\u95f4|evening|night)/i,  // 匹配"晚上"、"夜间"或"evening"/"night"
};

// 日期标题正则 —— 匹配 "Day 1"、"D1"、"第一天" 等日期标题
// ^ 表示行首，#{1,6} 匹配1-6个#号（Markdown标题），\s* 匹配任意空白
const DAY_HEADING_REGEX = /^(#{1,6}\s*)?(Day\s*\d+|D\d+|\u7b2c[\u4e00-\u9fff0-9]+\u5929)/i;

// 标准化行文本：去掉列表标记符号（如 -、*、+、1.、一、等）
// 应用场景：AI 返回 "- 宽窄巷子" → 标准化为 "宽窄巷子"
function normalizeLine(line: string): string {
  return line.replace(/^\s*[-*+\d.\u3001]+\s*/, '').trim();
}

// 去除 Markdown 格式噪声：去掉星号、反引号、链接、图片等 Markdown 语法
// 应用场景：AI 返回 "**宽窄巷子**" → 清理为 "宽窄巷子"
function stripMarkdownNoise(input: string): string {
  return input
    .replace(/[*_`~#>\[\]\(\)]/g, ' ')        // 去掉 Markdown 格式符号
    .replace(/!\[[^\]]*\]\([^)]+\)/g, ' ')     // 去掉图片语法 ![alt](url)
    .replace(/https?:\/\/\S+/gi, ' ')           // 去掉 URL 链接
    .replace(/[|]/g, ' ')                       // 去掉表格分隔符 |
    .replace(/\s+/g, ' ')                       // 多个空格合并为一个
    .trim();
}

// 清理文本用于展示：先去 Markdown 噪声，再清理重复标点
// 应用场景：AI 返回 ";;宽窄巷子，，锦里" → 清理为 "宽窄巷子；锦里"
function cleanForDisplay(input: string): string {
  return stripMarkdownNoise(input)
    .replace(/[;；]{2,}/g, '；')    // 多个分号合并为一个中文分号
    .replace(/[，,]{2,}/g, '，')    // 多个逗号合并为一个中文逗号
    .replace(/^[:：\-\s]+/, '')     // 去掉开头的冒号、破折号、空格
    .trim();
}

// 字符串去重：过滤掉空字符串和重复项
// 应用场景：从行程文本中提取景点列表时，去掉重复的景点名
function dedupeStrings(items: string[]): string[] {
  const seen = new Set<string>();        // Set 是 JavaScript 的集合数据结构，自动去重
  return items.filter((item) => {
    const key = item.trim();
    if (!key || seen.has(key)) return false;  // 空字符串或已存在则过滤掉
    seen.add(key);                             // 记录已出现
    return true;
  });
}

// 从文本中提取金额候选值
// 应用场景：AI 返回 "预算约¥1500，人均1200" → 提取出 [1500, 1200]
function extractMoneyCandidates(content: string): number[] {
  const values = new Set<number>();
  // 正则匹配：¥/￥/RMB/CNY/预算/人均/总计/约 后面跟着2~6位数字
  const regex = /(¥|￥|RMB|CNY|\u9884\u7b97|\u4eba\u5747|\u603b\u8ba1|\u7ea6)\s*([0-9]{2,6})/gi;
  let match = regex.exec(content);
  while (match) {
    const value = Number(match[2]);      // match[2] 是正则中第二个括号匹配的数字部分
    if (Number.isFinite(value) && value > 0) values.add(value);
    match = regex.exec(content);
  }
  return Array.from(values.values());
}

// 将行程文本按天分割成多个文本块
// 应用场景：AI 返回 "Day1: xxx\nDay2: yyy\nDay3: zzz" → 分割为3个文本块
function splitDayBlocks(content: string): string[] {
  // 将行内出现的 "Day X" 标准化为换行开头，确保后续解析稳定
  // 例如："；Day 2" → "；\nDay 2"
  const normalizedContent = content.replace(
    /([；;。]\s*)(#{1,6}\s*)?(Day\s*\d+|D\d+|\u7b2c[\u4e00-\u9fff0-9]+\u5929)/gi,
    (_match, p1, _p2, p3) => `${p1}\n${p3}`
  );
  const lines = normalizedContent.split('\n');
  const blocks: string[][] = [];         // 二维数组：每个元素是一天的所有行
  let currentBlock: string[] = [];       // 当前正在收集的天的行

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;                 // 跳过空行
    if (DAY_HEADING_REGEX.test(line) && currentBlock.length > 0) {
      // 遇到新的日期标题，把之前收集的内容保存为一个块
      blocks.push(currentBlock);
      currentBlock = [line];
      continue;
    }
    currentBlock.push(line);
  }

  if (currentBlock.length > 0) blocks.push(currentBlock);  // 保存最后一个块
  return blocks.map((block) => block.join('\n'));           // 将每个块的行合并为字符串
}

// 从文本块中提取日期标签
// 应用场景："## Day 1 成都美食之旅" → "Day 1 成都美食之旅"
// 如果没有日期标题，则使用 "Day N" 作为默认标签
function pickDayLabel(block: string, fallbackIndex: number): string {
  const firstLine = block.split('\n')[0] || '';
  if (DAY_HEADING_REGEX.test(firstLine)) return cleanForDisplay(firstLine.replace(/^#{1,6}\s*/, ''));
  return `Day ${fallbackIndex + 1}`;
}

// 从行列表中收集旅行小贴士
// 应用场景：AI 返回 "小贴士：提前预约门票" → 提取出 "提前预约门票"
function collectTips(lines: string[]): string[] {
  const tips = lines
    // 筛选包含"小贴士/tips/提示/注意/建议"关键词的行
    .filter((line) => /(?:\u5c0f\u8d34\u58eb|tips|\u63d0\u793a|\u6ce8\u610f|\u5efa\u8bae)/i.test(line))
    // 清理格式：去掉列表标记和关键词前缀
    .map((line) =>
      cleanForDisplay(normalizeLine(line).replace(/^(?:\u5c0f\u8d34\u58eb|Tips?|\u63d0\u793a|\u6ce8\u610f|\u5efa\u8bae)[:：]?\s*/i, ''))
    )
    .filter((line) => line.length >= 4)          // 过滤掉太短的内容（少于4个字符的可能是误匹配）
    .filter((line) => !/^(?:Day\s*\d+|\u7b2c[\u4e00-\u9fff0-9]+\u5929)$/i.test(line));  // 排除日期标题行
  return dedupeStrings(tips).slice(0, 6);        // 去重并最多保留6条
}

// 从行列表中收集景点名称
// 应用场景：从 "上午：宽窄巷子，锦里古街" 中提取出 ["宽窄巷子", "锦里古街"]
function collectSpots(lines: string[]): string[] {
  const spots: string[] = [];
  for (const line of lines) {
    const normalized = cleanForDisplay(normalizeLine(line));
    if (!normalized) continue;
    // 排除包含预算/费用/门票/交通/住宿/餐饮/建议/小贴士关键词的行（这些不是景点名）
    if (/(?:\u9884\u7b97|\u8d39\u7528|\u95e8\u7968|\u4ea4\u901a|\u4f4f\u5bbf|\u9910\u996e|\u5efa\u8bae|\u5c0f\u8d34\u58eb|tips)/i.test(normalized)) continue;
    // 按分隔符拆分：逗号、句号、分号、冒号、大于号、箭头
    const tokens = normalized.split(/[，。；：,;>→]/).map((item) => item.trim());
    for (const token of tokens) {
      // 景点名长度2~24字符，且不包含连续2位以上数字（排除价格等）
      if (token.length >= 2 && token.length <= 24 && !/\d{2,}/.test(token)) spots.push(token);
    }
  }
  return dedupeStrings(spots).slice(0, 8);       // 去重并最多保留8个
}

// 从文本块中提取指定时段（上午/下午/晚上）的内容
// 应用场景：从 "上午：宽窄巷子，锦里" 中提取出 "宽窄巷子；锦里"
function parsePeriodText(blockLines: string[], period: 'morning' | 'afternoon' | 'evening'): string {
  // 找到包含时段关键词的行
  const directLine = blockLines.find((line) => PERIOD_PATTERNS[period].test(line));
  if (!directLine) return '';

  const directIndex = blockLines.indexOf(directLine);
  const capture: string[] = [normalizeLine(directLine)];  // 从关键词行开始收集
  // 继续收集后续行，直到遇到另一个时段关键词为止
  for (let i = directIndex + 1; i < blockLines.length; i += 1) {
    const line = blockLines[i];
    if (PERIOD_PATTERNS.morning.test(line) || PERIOD_PATTERNS.afternoon.test(line) || PERIOD_PATTERNS.evening.test(line)) break;
    capture.push(normalizeLine(line));
  }

  // 清理格式：合并为分号分隔的文本，去掉时段关键词前缀
  return cleanForDisplay(
    capture
      .filter(Boolean)
      .join('；')
      .replace(/^(?:\u4e0a\u5348|\u65e9\u4e0a|morning|\u4e0b\u5348|afternoon|\u665a\u4e0a|\u591c\u95f4|evening|night)[:：]?\s*/i, '')
  );
}

// 【核心】将 AI 的自由文本行程解析为结构化的每日卡片
// 这是本模块最重要的函数，将 Markdown/纯文本行程转换为前端可渲染的结构化数据
// 应用场景：AI 返回 "Day1: 上午宽窄巷子，下午武侯祠…" →
//   [{ dayLabel: "Day 1", morning: "宽窄巷子", afternoon: "武侯祠", evening: "春熙路夜景", ... }]
export function parseDayPlanCards(content: string): DayPlanCard[] {
  if (!content.trim()) return [];        // 空内容直接返回空数组
  const blocks = splitDayBlocks(content);  // 按天分割文本
  const candidateBlocks = blocks.length > 0 ? blocks : [content];  // 如果没有分天标记，整段作为一天
  const baseNumbers = extractMoneyCandidates(content);  // 提取全文中的金额
  const fallbackBudget = baseNumbers[0] || 1200;        // 默认预算1200元

  return candidateBlocks.slice(0, 7).map((block, index) => {  // 最多解析7天
    const lines = block.split('\n').map((line) => line.trim()).filter(Boolean);
    const tips = collectTips(lines);       // 收集小贴士
    const spots = collectSpots(lines);     // 收集景点名称
    const blockMoney = extractMoneyCandidates(block);  // 提取当天的金额
    const morning = parsePeriodText(lines, 'morning');    // 解析上午安排
    const afternoon = parsePeriodText(lines, 'afternoon');  // 解析下午安排
    const evening = parsePeriodText(lines, 'evening');    // 解析晚上安排

    return {
      dayLabel: pickDayLabel(block, index),
      morning: morning || 'Free arrangement or one core attraction',       // 无上午安排时的默认文本
      afternoon: afternoon || 'Core attraction and meal window',            // 无下午安排时的默认文本
      evening: evening || 'Night view or relaxed dinner',                   // 无晚上安排时的默认文本
      tips: tips.length > 0 ? tips : ['Book popular attractions and restaurants early.'],  // 无贴士时的默认提示
      baseBudget: blockMoney[0] || fallbackBudget,
      spots,
    };
  });
}

// 解析行程方案变体 —— 从 AI 回答中提取多个可选方案
// 应用场景：AI 返回 "方案A：省钱版…方案B：舒适版…" → 解析为多个 PlanVariant 对象
export function parsePlanVariants(content: string): PlanVariant[] {
  // 匹配方案标记：方案A/B/C、省钱版、均衡版、舒适版、轻松版、Plan A/B/C
  const markers = content.match(/(方案\s*[A-C]|省钱版|均衡版|舒适版|轻松版|Plan\s*[A-C])/gi);
  if (!markers || markers.length < 2) return [];  // 至少2个方案才有意义

  const lines = content.split('\n');
  const variants: PlanVariant[] = [];
  let currentTitle = '';                  // 当前正在收集的方案标题
  let currentLines: string[] = [];        // 当前方案的文本行

  for (const line of lines) {
    const marker = line.match(/(方案\s*[A-C]|省钱版|均衡版|舒适版|轻松版|Plan\s*[A-C])/i)?.[0] || '';
    if (marker) {
      // 遇到新的方案标记，先保存之前的方案
      if (currentTitle && currentLines.length > 0) {
        variants.push({ id: `${variants.length + 1}`, title: currentTitle, content: currentLines.join('\n').trim() });
      }
      currentTitle = marker;
      currentLines = [line];
      continue;
    }
    if (currentTitle) currentLines.push(line);  // 属于当前方案的内容行
  }

  // 保存最后一个方案
  if (currentTitle && currentLines.length > 0) {
    variants.push({ id: `${variants.length + 1}`, title: currentTitle, content: currentLines.join('\n').trim() });
  }

  return variants.slice(0, 3);            // 最多保留3个方案
}

// 【核心】预算预测 —— 根据预算滑块值计算费用分配
// 不是简单的线性缩放，而是用分段系数映射到"省钱/均衡/舒适"三个档位
// 应用场景：用户将预算滑块拖到30（省钱档）→ 住宿占比31%、每日预算×0.82
//          用户将预算滑块拖到80（舒适档）→ 住宿占比46%、每日预算×1.26
export function getBudgetProjection(baseDailyBudget: number, days: number, sliderValue: number): BudgetProjection {
  const normalized = Math.max(0, Math.min(100, sliderValue));  // 限制滑块值在0~100范围
  // 根据滑块值分三档：0~33省钱档、34~66均衡档、67~100舒适档
  const factor = normalized <= 33 ? 0.82 : normalized >= 67 ? 1.26 : 1;  // 预算缩放系数
  const hotelShare = normalized <= 33 ? 0.31 : normalized >= 67 ? 0.46 : 0.39;  // 住宿占比
  const foodShare = normalized <= 33 ? 0.27 : normalized >= 67 ? 0.24 : 0.25;   // 餐饮占比
  const trafficShare = 1 - hotelShare - foodShare;  // 交通占比 = 剩余部分

  const perDayBudget = Math.round(baseDailyBudget * factor);  // 每日预算
  const totalBudget = perDayBudget * Math.max(days, 1);       // 总预算

  return { totalBudget, perDayBudget, hotelShare, foodShare, trafficShare };
}

// 哈希字符串到坐标值 —— 将景点名称映射为一个伪坐标值
// 注意：这不是真实坐标，仅用于在没有真实坐标时提供演示用的地图展示
// 应用场景：当没有调用高德地图API时，用景点名称哈希生成一个大致在中国范围内的坐标
function hashToCoordinate(input: string, min: number, max: number): number {
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) hash = (hash << 5) - hash + input.charCodeAt(i);
  const normalized = ((hash % 10000) + 10000) % 10000;  // 确保结果为正数
  const ratio = normalized / 10000;                      // 归一化到 0~1
  return Number((min + (max - min) * ratio).toFixed(4)); // 映射到 [min, max] 范围
}

// 构建路线坐标点列表 —— 为景点列表生成伪坐标
// 应用场景：在没有真实地图数据时，为路线预览图生成大致的坐标点
export function buildRoutePoints(spots: string[]): RoutePoint[] {
  return dedupeStrings(spots).map((spot) => ({
    name: spot,
    lat: hashToCoordinate(spot, 22.5, 41.0),     // 纬度范围：中国南部到北部（约22.5°~41°）
    lng: hashToCoordinate(`${spot}-lng`, 102.0, 123.0),  // 经度范围：中国西部到东部（约102°~123°）
  }));
}

// 计算两个坐标点之间的欧几里得距离（简化版，不考虑地球曲率）
function distance(a: RoutePoint, b: RoutePoint): number {
  const dx = a.lat - b.lat;
  const dy = a.lng - b.lng;
  return Math.sqrt(dx * dx + dy * dy);
}

// 【核心】按距离重排路线点 —— 贪心算法，每次选择最近的未访问点
// 应用场景：用户选了5个景点，系统按"从近到远"的顺序重新排列，减少走回头路
// 算法：从第一个点出发，每次找最近的下一个点，直到所有点都访问过
export function reorderByDistance(points: RoutePoint[]): RoutePoint[] {
  if (points.length <= 2) return points;  // 2个点以内无需重排
  const result: RoutePoint[] = [points[0]];  // 从第一个点出发
  const remaining = points.slice(1);          // 剩余待排列的点

  while (remaining.length > 0) {
    const last = result[result.length - 1];  // 当前最后一个点
    let bestIndex = 0;
    let bestDistance = Infinity;

    // 在剩余点中找到距离当前点最近的
    for (let i = 0; i < remaining.length; i += 1) {
      const candidateDistance = distance(last, remaining[i]);
      if (candidateDistance < bestDistance) {
        bestDistance = candidateDistance;
        bestIndex = i;
      }
    }

    const [next] = remaining.splice(bestIndex, 1);  // 取出最近的点
    result.push(next);
  }

  return result;
}

// 构建行前准备清单 —— 根据行程内容生成个性化的准备事项
// 应用场景：AI 生成成都行程后，自动生成"预订城际交通"、"确认酒店入住政策"等清单
export function buildChecklist(content: string): ChecklistItem[] {
  const candidates: string[] = [
    'Book intercity transportation',       // 预订城际交通
    'Confirm hotel and check-in policy',    // 确认酒店入住政策
    'Prepare required IDs/documents',       // 准备身份证件
    'Plan city transport and navigation',   // 规划市内交通
    'Check weather and packing list',       // 查看天气和打包清单
    'Prepare medicine and chargers',        // 准备药品和充电器
  ];

  // 根据行程内容动态添加特定清单项
  if (/visa/i.test(content)) candidates.push('Verify visa/entry requirements');       // 涉及签证
  if (/(?:亲子|儿童)/i.test(content)) candidates.push('Prepare child-friendly supplies');  // 涉及亲子
  if (/(?:老人|长辈)/i.test(content)) candidates.push('Prepare low-walk fallback options'); // 涉及老人

  return dedupeStrings(candidates).map((label, index) => ({ id: `todo-${index + 1}`, label }));
}

// 构建出发前提醒列表 —— 固定返回3个阶段的提醒
// 应用场景：出发前7天/3天/1天分别提醒用户做不同的准备工作
export function buildReminders(): ReminderItem[] {
  return [
    { id: 't7', phase: 'T-7', title: 'Confirm bookings', detail: 'Lock transport/hotel and verify cancellation rules.' },
    { id: 't3', phase: 'T-3', title: 'Pack and verify route', detail: 'Pack by weather and verify each day transfer points.' },
    { id: 't1', phase: 'T-1', title: 'Final check', detail: 'Re-check tickets, orders, payment and departure time.' },
  ];
}

// 推断景点建议游玩时长 —— 根据景点名称中的关键词推断
// 应用场景："上海迪士尼" → "4-8h"，"国家博物馆" → "1.5-3h"
function inferSpotDuration(name: string): string {
  if (/(迪士尼|欢乐谷|环球|乐园|度假区)/i.test(name)) return '4-8h';       // 主题乐园
  if (/(博物馆|美术馆|展|纪念馆|科技馆|图书馆|museum|gallery)/i.test(name)) return '1.5-3h';  // 博物馆类
  if (/(古镇|街|步行街|里|坊|夜市|市集)/i.test(name)) return '1-2h';        // 古镇街区
  if (/(公园|湿地|湖|山|海滩|岛|植物园|动物园)/i.test(name)) return '2-4h';  // 自然景观
  if (/(寺|庙|宫|塔|教堂|故居|古城|城墙|府)/i.test(name)) return '1-2h';    // 历史建筑
  return '1-2h';                         // 默认1-2小时
}

// 推断景点最佳到达时间
// 应用场景："外滩" → "17:30-20:00"（夜景），"国家博物馆" → "09:30-11:30"（上午）
function inferBestArrival(name: string): string {
  if (/(夜市|外滩|江边|灯光|夜景|酒吧|秀)/i.test(name)) return '17:30-20:00';     // 夜间景点
  if (/(博物馆|美术馆|纪念馆|展|museum|gallery)/i.test(name)) return '09:30-11:30';  // 博物馆上午去
  if (/(公园|海边|湖|山|古镇|步行街)/i.test(name)) return '08:30-10:30 / 16:00后';   // 自然景点早晚去
  if (/(乐园|迪士尼|环球|动物园)/i.test(name)) return '开园前后';                    // 乐园开园去
  return '10:00-12:00';                  // 默认上午
}

// 推断景点适合人群
// 应用场景："迪士尼" → "亲子/第一次来"，"博物馆" → "文化爱好者/雨天友好"
function inferAudience(name: string): string {
  if (/(迪士尼|动物园|海洋馆|乐园|科技馆)/i.test(name)) return '亲子/第一次来';
  if (/(博物馆|美术馆|纪念馆|展)/i.test(name)) return '文化爱好者/雨天友好';
  if (/(步行街|古镇|夜市|外滩|江边|街区)/i.test(name)) return '情侣/轻松逛';
  if (/(公园|湖|海滩|湿地|植物园)/i.test(name)) return '少压力散步/拍照';
  return '大众友好';
}

// 推断景点费用提示
// 应用场景："迪士尼" → "较高"，"博物馆" → "低到中"
function inferSpotCost(name: string): string {
  if (/(迪士尼|环球|乐园|演出|索道)/i.test(name)) return '较高';
  if (/(博物馆|公园|古镇|街区|步行街|外滩)/i.test(name)) return '低到中';
  return '中等';
}

// 构建景点决策信息列表 —— 为每个景点生成决策参考
// 应用场景：用户在"去不去迪士尼"之间犹豫时，展示"4-8h、亲子友好、费用较高"帮助决策
export function buildSpotDecisionInfos(spots: string[]): SpotDecisionInfo[] {
  return dedupeStrings(spots)
    .slice(0, 6)                         // 最多6个景点
    .map((name) => ({
      name,
      stayDuration: inferSpotDuration(name),
      bestArrival: inferBestArrival(name),
      audience: inferAudience(name),
      costHint: inferSpotCost(name),
    }));
}

// 构建实用信息卡片 —— 根据行程内容生成天气、交通、证件等实用提示
// 应用场景：在行程详情页展示"天气与穿衣"、"交通建议"等实用信息卡片
export function buildPracticalInfoCards(content: string): PracticalInfoCard[] {
  const cards: PracticalInfoCard[] = [
    {
      id: 'weather',
      title: '天气与穿衣',
      // 根据行程内容判断天气建议
      value: /冬|降温|风大/i.test(content) ? '建议分层穿搭，外层准备防风外套。' : '出发前一天再确认天气，优先准备轻便分层穿搭。',
      tone: 'neutral',
    },
    {
      id: 'transport',
      title: '交通建议',
      // 根据是否提到公共交通给出不同建议
      value: /无车|地铁|公交/i.test(content) ? '优先地铁+步行，跨区移动尽量集中到同一天。' : '热门时段建议地铁优先，晚间返程可预留打车预算。',
      tone: 'good',
    },
    {
      id: 'documents',
      title: '证件准备',
      value: '身份证、预订凭证、酒店订单截图建议提前整理到一个相册。',
      tone: 'neutral',
    },
    {
      id: 'queue',
      title: '排队高峰',
      // 根据是否涉及节假日给出不同建议
      value: /周末|节假日/i.test(content) ? '高峰时段更容易排队，热门景点尽量前置到上午。' : '午后到傍晚通常人流更高，热门点位建议错峰。',
      tone: 'warn',
    },
  ];

  // 如果行程涉及亲子，追加亲子补充卡片
  if (/(亲子|儿童)/i.test(content)) {
    cards.push({
      id: 'family',
      title: '亲子补充',
      value: '给孩子预留午休和临时室内备选，不要把全天排得过满。',
      tone: 'good',
    });
  }

  // 如果行程涉及老人，追加体力管理卡片
  if (/(老人|长辈|少走路)/i.test(content)) {
    cards.push({
      id: 'senior',
      title: '体力管理',
      value: '优先连片景点和可随时打车撤退的区域，控制连续步行时长。',
      tone: 'warn',
    });
  }

  return cards;
}

// 【核心】构建置信度摘要 —— 评估行程方案的可靠性
// 根据诊断信息（验证是否通过、过期数据数量、降级步骤数）计算置信度分数
// 应用场景：前端展示"方案可信度 85分（高）"，并提示"发现2条可能过期的数据"
export function buildConfidenceSummary(diagnostics?: MessageDiagnostics): ConfidenceSummary {
  if (!diagnostics) {
    // 没有诊断信息时，返回中等置信度和风险提示
    return {
      score: 55,
      level: 'medium',
      risks: ['No verification metadata available. Re-check key prices and opening times.'],
    };
  }

  let score = 70;                        // 基础分数70分
  const risks: string[] = [];

  // 验证通过加分，未通过减分
  if (diagnostics.verificationPassed === true) score += 18;
  if (diagnostics.verificationPassed === false) {
    score -= 18;
    risks.push('Verification failed. Some details may be inaccurate.');
  }

  // 过期数据减分（每条减6分，最多减20分）
  const staleCount = Number(diagnostics.staleResultCount || 0);
  if (staleCount > 0) {
    score -= Math.min(20, staleCount * 6);
    risks.push(`Found ${staleCount} potentially stale items. Re-check schedule and pricing.`);
  }

  // 降级步骤减分（每步减3分，最多减12分）
  const fallback = Number(diagnostics.fallbackSteps || 0);
  if (fallback > 0) {
    score -= Math.min(12, fallback * 3);
    risks.push(`Fallback switched ${fallback} times. Some fields may be downgraded.`);
  }

  // 分数限制在20~98之间
  score = Math.max(20, Math.min(98, score));
  // 根据分数确定等级：≥80高、≥60中、<60低
  const level: 'high' | 'medium' | 'low' = score >= 80 ? 'high' : score >= 60 ? 'medium' : 'low';
  if (risks.length === 0) risks.push('Low risk, but still re-check real-time weather and ticket inventory.');
  return { score, level, risks };
}

// 解析时间条目 —— 从文本中提取带时间信息的行程安排
// 应用场景："09:30 参观武侯祠；14:00 游览锦里" →
//   [{ raw: "09:30 参观武侯祠", timeMinutes: 570, content: "参观武侯祠" }, ...]
function parseTimeEntries(text: string): TimeEntry[] {
  return text
    .split(/[；;。]/)                    // 按分号/句号拆分
    .map((item) => item.trim())
    .filter(Boolean)
    .map((raw) => {
      // 尝试匹配时间格式 HH:MM 或 HH：MM
      const timeMatch = raw.match(/(\d{1,2})[:：](\d{2})/);
      if (!timeMatch) return { raw, timeMinutes: null, content: raw };  // 无时间信息
      const hour = Number(timeMatch[1]);
      const minute = Number(timeMatch[2]);
      const isValid = Number.isFinite(hour) && Number.isFinite(minute) && hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59;
      return {
        raw,
        timeMinutes: isValid ? hour * 60 + minute : null,  // 转为分钟数，如 9:30 → 570
        content: raw.replace(timeMatch[0], '').replace(/^\s*[-:：]?\s*/, '').trim(),  // 去掉时间部分
      };
    });
}

// 格式化分钟数为时间字符串
// 应用场景：570 → "09:30"
function formatTime(totalMinutes: number): string {
  const h = Math.floor(totalMinutes / 60).toString().padStart(2, '0');  // padStart 补零，如 "9" → "09"
  const m = (totalMinutes % 60).toString().padStart(2, '0');
  return `${h}:${m}`;
}

// 【核心】检测单日行程冲突 —— 发现时间重叠、距离过远、闭馆风险等问题
// 应用场景：AI 安排了 "09:00 博物馆 → 08:30 公园"（时间倒序），
//   或 "18:00 参观博物馆"（可能已闭馆），此函数会检测出这些冲突
export function detectDayConflicts(day: DayPlanCard, distanceM?: number): ItineraryConflict[] {
  // 冲突检测采用保守策略：宁可多报"可能的问题"，也不漏报
  const conflicts: ItineraryConflict[] = [];
  const periods = [
    { key: 'morning', label: 'Morning', text: day.morning },
    { key: 'afternoon', label: 'Afternoon', text: day.afternoon },
    { key: 'evening', label: 'Evening', text: day.evening },
  ] as const;

  // 检查每个时段内的时间冲突
  periods.forEach((period) => {
    const entries = parseTimeEntries(period.text).filter((item) => item.timeMinutes !== null);
    for (let index = 1; index < entries.length; index += 1) {
      const prev = entries[index - 1];
      const curr = entries[index];
      // 如果后一个时间早于或等于前一个时间，说明时间顺序有问题
      if ((curr.timeMinutes ?? 0) <= (prev.timeMinutes ?? 0)) {
        conflicts.push({
          id: `${period.key}-time-${index}`,
          type: 'time_conflict',
          severity: 'high',
          title: `${period.label} time conflict`,
          description: `Detected timeline overlap or reverse order (${prev.raw} -> ${curr.raw}).`,
          suggestion: 'Sort by time and leave at least 30 minutes buffer between items.',
        });
        break;  // 每个时段只报一个时间冲突
      }
    }
  });

  // 检查路线距离是否过远（超过30km报警）
  if (distanceM && distanceM > 30000) {
    conflicts.push({
      id: 'distance-long',
      type: 'long_distance',
      severity: distanceM > 50000 ? 'high' : 'medium',  // 超过50km为高危
      title: 'Route too long',
      description: `Daily route is about ${(distanceM / 1000).toFixed(1)} km.`,
      suggestion: 'Split into two days or remove 1-2 far points.',
    });
  }

  // 检查闭馆风险：晚上18:30以后去博物馆/景区等可能已闭馆
  const eveningEntries = parseTimeEntries(day.evening);
  const closingKeywords = /(博物馆|美术馆|纪念馆|景区|公园|寺|塔|宫|图书馆|museum|park|gallery)/i;
  const closeRiskEntry = eveningEntries.find((entry) => (entry.timeMinutes ?? 0) >= 1110 && closingKeywords.test(entry.content));
  // 1110分钟 = 18:30，即18:30以后去博物馆等有闭馆风险
  if (closeRiskEntry) {
    conflicts.push({
      id: 'closing-risk-evening',
      type: 'closing_risk',
      severity: 'medium',
      title: 'Potential closing-time risk',
      description: `Late visit may hit closing window: ${closeRiskEntry.raw}`,
      suggestion: 'Move this point to afternoon; keep evening for night-view or dining.',
    });
  }

  return conflicts;
}

// 【核心】应用冲突修复 —— 根据检测到的冲突自动修复行程
// 应用场景：检测到时间冲突后，自动按时间排序并添加30分钟缓冲
export function applyConflictFixes(day: DayPlanCard, conflicts: ItineraryConflict[]): DayPlanCard {
  if (conflicts.length === 0) return day;  // 无冲突则不修改

  // 标准化时段文本：将带时间的条目按时间排序，并确保间隔至少30分钟
  function normalizePeriod(text: string): string {
    const entries = parseTimeEntries(text);
    const timed = entries
      .filter((entry) => entry.timeMinutes !== null)
      .sort((a, b) => (a.timeMinutes ?? 0) - (b.timeMinutes ?? 0));  // 按时间升序排列
    const untimed = entries.filter((entry) => entry.timeMinutes === null);  // 无时间的条目

    let cursor = -1;                      // 上一个安排的结束时间（分钟数）
    const normalizedTimed = timed.map((entry) => {
      // 确保当前条目的时间至少比上一个晚30分钟
      const nextValue = Math.max(entry.timeMinutes ?? 0, cursor + 30);
      cursor = nextValue;
      return `${formatTime(nextValue)} ${entry.content}`.trim();  // 格式化为 "09:30 参观武侯祠"
    });

    // 合并有时间和无时间的条目
    return [...normalizedTimed, ...untimed.map((entry) => entry.content)].filter(Boolean).join('；');
  }

  let nextMorning = day.morning;
  let nextAfternoon = day.afternoon;
  let nextEvening = day.evening;
  const nextTips = [...day.tips];         // 复制原有贴士

  // 如果有时间冲突，对所有时段进行排序修复
  if (conflicts.some((item) => item.type === 'time_conflict')) {
    nextMorning = normalizePeriod(nextMorning);
    nextAfternoon = normalizePeriod(nextAfternoon);
    nextEvening = normalizePeriod(nextEvening);
    nextTips.unshift('Auto-fix: timeline sorted by time with safety buffers.');
  }

  // 如果有距离过远冲突，添加建议
  if (conflicts.some((item) => item.type === 'long_distance')) {
    nextTips.unshift('Suggestion: reduce far points or split this day.');
  }

  // 如果有闭馆风险冲突，添加建议
  if (conflicts.some((item) => item.type === 'closing_risk')) {
    nextTips.unshift('Suggestion: move closing-risk places to afternoon.');
  }

  return {
    ...day,                               // 展开运算符：复制 day 的所有字段
    morning: nextMorning,
    afternoon: nextAfternoon,
    evening: nextEvening,
    tips: dedupeStrings(nextTips).slice(0, 8),  // 去重并最多保留8条
  };
}
