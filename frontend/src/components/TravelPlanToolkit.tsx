// 'use client' 是 Next.js 的指令，标记此组件为客户端组件
// 客户端组件可以在浏览器中运行，支持 useState、useEffect 等交互功能
'use client';

// 从 React 库导入核心钩子函数：
// - useEffect: 副作用钩子，在组件渲染后执行特定逻辑（如数据请求、订阅）
// - useMemo: 缓存计算结果，避免每次渲染都重新计算
// - useRef: 创建一个跨渲染周期持久化的引用，修改它不会触发重新渲染
// - useState: 状态钩子，创建可变的状态变量，修改时会触发组件重新渲染
import React, { useEffect, useMemo, useRef, useState } from 'react';
// 从 Ant Design 组件库导入 UI 组件：
// - App: 提供全局上下文（如 message 消息提示）
// - Card: 卡片容器，用于包裹内容区域
// - Tabs: 选项卡组件，用于切换不同功能面板
import { App, Card, Tabs } from 'antd';
// 从 Ant Design 图标库导入各 Tab 使用的图标
import {
  CheckSquareOutlined,   // 勾选图标 → 执行清单 Tab
  CompassOutlined,       // 指南针图标 → 每日行程 Tab
  HeartOutlined,         // 爱心图标 → 候选池 Tab
  InfoCircleOutlined,    // 信息图标 → 实用信息 Tab
  ReloadOutlined,        // 刷新图标 → 冲突检测/出发提醒 Tab
  FundOutlined,          // 基金图标 → 多方案对比 Tab
} from '@ant-design/icons';
// 从项目类型定义文件导入类型（type 表示仅导入类型，不会增加运行时代码）：
// - Message: 消息类型
// - SubagentEvent: 子代理事件类型
// - TripPlanArtifact: 行程结构化数据类型
import type { Message, SubagentEvent, TripPlanArtifact } from '@/types';
// 导入判断行程结构化数据是否可用的工具函数
import { hasArtifactData } from '@/utils/agentArtifacts';
// 从行程工具模块导入各类解析/构建函数：
// - applyConflictFixes: 将冲突修复建议应用到某天的行程
// - buildChecklist: 从行程文本构建执行清单
// - buildConfidenceSummary: 基于诊断信息构建置信度摘要
// - buildPracticalInfoCards: 从行程文本提取实用信息卡片
// - buildReminders: 构建出发提醒列表
// - detectDayConflicts: 检测某天行程中的冲突（如时间重叠、距离过远）
// - getBudgetProjection: 根据日均预算和天数计算预算预测
// - parseDayPlanCards: 将行程文本解析为按天划分的卡片数据
// - parsePlanVariants: 从行程文本中解析出多个备选方案
import {
  applyConflictFixes,
  buildChecklist,
  buildConfidenceSummary,
  buildPracticalInfoCards,
  buildReminders,
  detectDayConflicts,
  getBudgetProjection,
  parseDayPlanCards,
  parsePlanVariants,
} from '@/utils/travelPlan';
// 导入 DayPlanCard 类型，表示一天行程的卡片数据结构
import type { DayPlanCard } from '@/utils/travelPlan';
// 导入 QuickRefineAction 类型，定义快速优化操作的数据结构
import type { QuickRefineAction } from './travel-plan-toolkit/shared';
// 从行程工具包的 sections 模块导入各 Tab 面板组件：
// - ToolkitChecklistTab: 执行清单面板
// - ToolkitCompareTab: 多方案对比面板
// - ToolkitConflictsTab: 冲突检测面板
// - ToolkitFavoritesTab: 候选池面板
// - ToolkitItineraryTab: 每日行程面板
// - ToolkitOverviewPanel: 概览面板（显示在 Tabs 上方）
// - ToolkitPracticalTab: 实用信息面板
// - ToolkitRemindersTab: 出发提醒面板
import {
  ToolkitChecklistTab,
  ToolkitCompareTab,
  ToolkitConflictsTab,
  ToolkitFavoritesTab,
  ToolkitItineraryTab,
  ToolkitOverviewPanel,
  ToolkitPracticalTab,
  ToolkitRemindersTab,
} from './travel-plan-toolkit/sections';
// 导入共享工具函数和类型：
// - looksLikeItineraryContent: 判断内容是否像行程文本
// - modeToSliderValue: 将预算模式转换为滑块数值
// - BudgetMode: 预算模式类型（如 'balanced' 均衡、'budget' 省钱、'luxury' 豪华）
import { looksLikeItineraryContent, modeToSliderValue, type BudgetMode } from './travel-plan-toolkit/shared';
// 导入自定义 Hook：useArtifactHistoryCompare
// 职责：获取行程结构化数据的历史版本，用于多方案对比
import { useArtifactHistoryCompare } from './travel-plan-toolkit/useArtifactHistoryCompare';
// 导入自定义 Hook：useTravelPlanToolkitActions
// 职责：封装行程工具包的所有交互操作逻辑（收藏、路线、导出、分享等）
import { useTravelPlanToolkitActions } from './travel-plan-toolkit/useTravelPlanToolkitActions';

// interface 是 TypeScript 中定义对象类型的语法，类似其他语言的 struct/class 声明
// TravelPlanToolkitProps 定义了 TravelPlanToolkit 组件接收的所有属性（即外部传入的参数）
interface TravelPlanToolkitProps {
  messageId: string;       // 消息唯一标识，用于关联消息上下文
  content: string;         // 行程文本内容，即 AI 生成的行程规划原始文本
  diagnostics?: Message['diagnostics']; // ? 表示可选属性，可能为 undefined；诊断信息，包含执行状态、会话ID等
  artifact?: TripPlanArtifact | null;    // 行程结构化数据，| null 表示可以是 null；比纯文本更结构化的行程数据
  subagentEvents?: SubagentEvent[];     // 子代理事件列表，记录 AI 子代理的执行过程
  onContinuePrompt?: (prompt: string) => void; // 回调函数：当用户需要继续对话时调用，参数为提示词文本
}

// 【核心】QUICK_REFINE_ACTIONS 是快速优化操作的预设配置
// 场景举例：用户觉得行程太贵，点击"换成更省钱"按钮，系统自动发送优化提示词给 AI，AI 基于当前方案生成更省钱的版本
const QUICK_REFINE_ACTIONS: QuickRefineAction[] = [
  { key: 'cheaper', label: '换成更省钱', prompt: '请基于当前方案改成更省钱版本，优先保留核心体验，减少高价项目，并重算预算。' },
  { key: 'easy', label: '少走路版', prompt: '请基于当前方案改成少走路版本，压缩跨区移动，增加打车衔接和休息点。' },
  { key: 'rainy', label: '下雨天重排', prompt: '请把当前方案改成下雨天可执行版本，优先室内点位，并替换不适合雨天的安排。' },
  { key: 'family', label: '加亲子备选', prompt: '请在当前方案基础上增加亲子友好备选点和午休/室内 fallback。' },
];

// type 是 TypeScript 中定义类型别名的语法，给一个类型起个短名字
// ToolkitTabItem 表示 Tabs 组件的 items 数组中单个选项卡的数据类型
// NonNullable<T> 表示去除 T 中的 null 和 undefined；React.ComponentProps<typeof Tabs> 获取 Tabs 组件的属性类型
type ToolkitTabItem = NonNullable<React.ComponentProps<typeof Tabs>['items']>[number];

// 【核心】TravelPlanToolkit 是行程规划工具包的主组件
// React.FC 是 React 函数组件的类型，泛型参数 TravelPlanToolkitProps 指定了组件接收的属性类型
const TravelPlanToolkit: React.FC<TravelPlanToolkitProps> = ({
  messageId,        // 消息唯一标识
  content,          // 行程文本内容
  diagnostics,      // 诊断信息（可选）
  artifact = null,  // 行程结构化数据，默认值为 null
  subagentEvents = [], // 子代理事件列表，默认值为空数组
  onContinuePrompt,    // 继续对话的回调函数（可选）
}) => {
  // App.useApp() 获取 Ant Design App 组件提供的全局方法，这里用 message 来显示提示信息
  // 场景举例：修复冲突后显示"已应用修复建议"的成功提示
  const { message } = App.useApp();
  // useRef 创建一个持久化的 DOM 引用，指向导出图片时需要截图的区域
  // useRef 与 useState 的区别：修改 useRef 不会触发组件重新渲染，适合存储 DOM 节点等不需要驱动视图的数据
  const exportRef = useRef<HTMLDivElement | null>(null);

  // 【核心】useMemo 缓存计算结果，只有依赖项变化时才重新计算
  // 语法：useMemo(() => 计算逻辑, [依赖项数组])
  // 如果依赖项没变，直接返回上次的缓存结果，避免每次渲染都重新计算

  // baseCards: 将行程文本解析为按天划分的卡片数据，仅当 content 变化时重新解析
  const baseCards = useMemo(() => parseDayPlanCards(content), [content]);
  // textVariants: 从行程文本中解析出多个备选方案，仅当 content 变化时重新解析
  const textVariants = useMemo(() => parsePlanVariants(content), [content]);
  // checklist: 从行程文本构建执行清单（如"预订酒店"、"购买门票"等），仅当 content 变化时重新构建
  const checklist = useMemo(() => buildChecklist(content), [content]);
  // reminders: 构建出发提醒列表（如"检查护照有效期"等），无依赖项，只在组件首次渲染时计算一次
  const reminders = useMemo(() => buildReminders(), []);
  // confidence: 基于诊断信息构建置信度摘要（如行程可行性评分），仅当 diagnostics 变化时重新计算
  const confidence = useMemo(() => buildConfidenceSummary(diagnostics), [diagnostics]);
  // practicalInfo: 从行程文本提取实用信息卡片（如交通、天气等），仅当 content 变化时重新提取
  const practicalInfo = useMemo(() => buildPracticalInfoCards(content), [content]);

  // useState 创建可变的状态变量，修改时会触发组件重新渲染
  // 语法：const [当前值, 修改函数] = useState(初始值)
  // useState<类型> 中的泛型指定了状态变量的类型

  // cards: 当前显示的每日行程卡片数据（可能被冲突修复等操作修改过，与 baseCards 不同）
  const [cards, setCards] = useState<DayPlanCard[]>(baseCards);
  // budgetMode: 预算模式，'balanced' 为均衡，还有 'budget'（省钱）和 'luxury'（豪华）
  const [budgetMode, setBudgetMode] = useState<BudgetMode>('balanced');
  // completedChecklist: 执行清单的完成状态，Record<string, boolean> 表示键为清单项ID、值为是否已完成的对象
  // 场景举例：{ "book-hotel": true, "buy-tickets": false } 表示"预订酒店"已完成，"购买门票"未完成
  const [completedChecklist, setCompletedChecklist] = useState<Record<string, boolean>>({});
  // expandedPeriods: 各天时段（上午/下午/晚上）的展开/折叠状态
  const [expandedPeriods, setExpandedPeriods] = useState<Record<string, boolean>>({});
  // expandedTips: 各天贴士的展开/折叠状态
  const [expandedTips, setExpandedTips] = useState<Record<string, boolean>>({});

  // artifactAvailable: 判断行程结构化数据是否可用（非空且包含有效数据）
  const artifactAvailable = hasArtifactData(artifact);
  // compareSessionId: 从诊断信息中获取会话ID，用于多方案对比时查询历史版本
  // ?. 是可选链操作符，如果 diagnostics 为 undefined 则不会报错，而是返回 undefined
  // ?? 是空值合并操作符，当左侧为 null 或 undefined 时使用右侧的值
  const compareSessionId = diagnostics?.sessionId ?? null;
  // useArtifactHistoryCompare: 自定义 Hook，获取行程结构化数据的历史版本
  // 返回 loading（加载状态）和 variants（历史版本列表）
  const { loading: compareHistoryLoading, variants: artifactHistoryVariants } = useArtifactHistoryCompare({
    artifact,       // 行程结构化数据
    content,        // 行程文本内容（作为 fallback 数据源）
    runId: diagnostics?.runId ?? null,  // 运行ID，用于定位特定一次 AI 执行
    sessionId: compareSessionId,        // 会话ID
    subagentEvents,                     // 子代理事件列表
  });
  // compareVariants: 用于对比的方案列表
  // 优先使用 artifactHistoryVariants（结构化数据的历史版本），如果不足2个则退回到 textVariants（文本解析的备选方案）
  const compareVariants = artifactHistoryVariants.length >= 2 ? artifactHistoryVariants : textVariants;
  // compareSource: 标记对比数据的来源，'artifact-history' 表示来自结构化数据历史，'text' 表示来自文本解析
  const compareSource = artifactHistoryVariants.length >= 2 ? 'artifact-history' : 'text';

  // useEffect 是副作用钩子，在组件渲染后执行
  // 语法：useEffect(() => { 副作用逻辑 }, [依赖项数组])
  // 当依赖项变化时，会在下次渲染后重新执行；如果依赖项为空数组 []，则只在首次渲染后执行一次
  // 这里：当 baseCards 变化时（即行程文本被重新解析），重置卡片数据和展开状态
  // 场景举例：AI 重新生成了行程方案，content 变化 → baseCards 重新计算 → 此 effect 触发，将 cards 同步为新的 baseCards
  useEffect(() => {
    setCards(baseCards);
    setExpandedPeriods({});
    setExpandedTips({});
  }, [baseCards]);

  // 【核心】useTravelPlanToolkitActions: 自定义 Hook，封装行程工具包的所有交互操作逻辑
  // 将复杂的业务逻辑从组件中抽离，使组件代码更清晰
  const {
    favoriteSpots,           // 收藏的景点集合（Set 结构，存储景点名称）
    favoriteSpotList,        // 收藏的景点列表（数组结构，方便遍历渲染）
    routeByDay,              // 各天的路线数据（距离、时间等）
    routeLoadingDay,         // 正在加载路线的天标识
    runQuickRefine,          // 执行快速优化（如"换成更省钱"）
    handleBuildFromFavorites, // 基于收藏的景点重新生成行程
    handleChooseVariant,     // 选择某个备选方案
    handleToggleFavoriteSpot, // 切换景点的收藏状态
    handleFetchRoute,        // 获取某天的路线规划
    handleReorderByDistance,  // 按距离重新排序某天的景点
    handleExportImage,       // 导出行程为图片
    handleShare,             // 分享行程
  } = useTravelPlanToolkitActions({
    artifact,       // 行程结构化数据
    baseCards,      // 原始解析的每日行程卡片
    content,        // 行程文本内容
    executionReceipt: diagnostics?.executionReceipt ?? null, // 执行回执，包含 AI 执行的详细信息
    exportRef,      // 导出图片时的 DOM 引用
    onContinuePrompt, // 继续对话的回调函数
    setCards,       // 修改卡片数据的函数（用于冲突修复后更新）
    subagentEvents, // 子代理事件列表
  });

  // cardEntries: 为每张卡片附加索引和唯一 key，方便后续遍历渲染
  // 场景举例：[{ day: 第1天数据, dayIndex: 0, dayKey: "day-1" }, ...]
  const cardEntries = useMemo(
    () =>
      cards.map((day, dayIndex) => ({
        day,
        dayIndex,
        dayKey: `day-${dayIndex + 1}`,
      })),
    [cards]
  );

  // totalBaseBudget: 所有天的基础预算总和
  const totalBaseBudget = useMemo(() => cards.reduce((sum, day) => sum + day.baseBudget, 0), [cards]);
  // 【核心】budgetProjection: 根据预算模式计算预算预测
  // 场景举例：3天行程，日均预算500元，选择"省钱"模式 → 预测总预算可能降为1200元
  const budgetProjection = useMemo(() => {
    const dayCount = Math.max(cards.length, 1); // 至少1天，避免除以0
    return getBudgetProjection(totalBaseBudget / dayCount, dayCount, modeToSliderValue(budgetMode));
  }, [budgetMode, cards.length, totalBaseBudget]);

  // familyBudget: 家庭预算估算，按总预算的2.4倍计算（考虑2大1小的花费）
  const familyBudget = Math.round(budgetProjection.totalBudget * 2.4);
  // childFriendlyBudget: 亲子友好预算估算，按总预算的1.7倍计算
  const childFriendlyBudget = Math.round(budgetProjection.totalBudget * 1.7);
  // hasItineraryContent: 判断内容是否包含有效的行程信息（用于决定是否显示行程相关的 Tab）
  const hasItineraryContent = useMemo(() => looksLikeItineraryContent(content, baseCards), [baseCards, content]);

  // 【核心】conflictMap: 各天行程的冲突检测结果
  // Map 是 JavaScript 的键值对集合，key 为天的标识（如 "day-1"），value 为该天的冲突列表
  // 场景举例：第1天有两个景点距离超过50公里 → conflictMap.get("day-1") 返回 [{ type: "distance", ... }]
  const conflictMap = useMemo(() => {
    const map = new Map<string, ReturnType<typeof detectDayConflicts>>();
    cardEntries.forEach(({ day, dayKey }) => {
      const distanceM = routeByDay[dayKey]?.distance_m; // 获取该天的路线总距离（米）
      map.set(dayKey, detectDayConflicts(day, distanceM)); // 检测冲突并存入 Map
    });
    return map;
  }, [cardEntries, routeByDay]);

  // totalConflicts: 所有天的冲突总数，用于在冲突检测 Tab 上显示角标数字
  const totalConflicts = useMemo(
    () => Array.from(conflictMap.values()).reduce((sum, list) => sum + list.length, 0),
    [conflictMap]
  );

  // 如果没有行程卡片且没有结构化数据，不渲染任何内容
  // 场景举例：AI 还没生成行程，或者生成的内容不是行程格式
  if (cards.length === 0 && !artifactAvailable) return null;

  // handleTogglePeriod: 切换某天时段的展开/折叠状态
  // 场景举例：用户点击第1天的"下午"时段 → expandedPeriods 变为 { "day-1-afternoon": true }
  const handleTogglePeriod = (periodKey: string) => {
    setExpandedPeriods((prev) => ({ ...prev, [periodKey]: !prev[periodKey] }));
  };

  // handleToggleTips: 切换某天贴士的展开/折叠状态
  const handleToggleTips = (dayKey: string) => {
    setExpandedTips((prev) => ({ ...prev, [dayKey]: !prev[dayKey] }));
  };

  // 【核心】handleOneClickFix: 一键修复某天的行程冲突
  // 场景举例：第1天有两个景点距离太远，点击"一键修复" → 系统自动调整景点顺序或替换景点
  const handleOneClickFix = (dayKey: string, dayIndex: number, day: DayPlanCard) => {
    const conflicts = conflictMap.get(dayKey) || []; // 获取该天的冲突列表
    if (conflicts.length === 0) {
      return; // 无冲突则不做任何操作
    }

    const fixed = applyConflictFixes(day, conflicts); // 应用冲突修复建议
    setCards((prev) => prev.map((item, index) => (index === dayIndex ? fixed : item))); // 只更新被修复的那天
  };

  // handleToggleChecklist: 切换执行清单中某项的完成状态
  // 场景举例：用户勾选"预订酒店" → completedChecklist 变为 { "book-hotel": true }
  const handleToggleChecklist = (itemId: string, checked: boolean) => {
    setCompletedChecklist((prev) => ({ ...prev, [itemId]: checked }));
  };

  // handleOneClickFixWithFeedback: 带用户反馈的一键修复（在 handleOneClickFix 基础上增加了消息提示）
  const handleOneClickFixWithFeedback = (dayKey: string, dayIndex: number, day: DayPlanCard) => {
    const conflicts = conflictMap.get(dayKey) || [];
    if (conflicts.length === 0) {
      message.info('当前无冲突，无需修复。'); // 无冲突时提示用户
      return;
    }

    handleOneClickFix(dayKey, dayIndex, day); // 执行修复
    message.success(`${day.dayLabel} 已应用修复建议`); // 修复成功后提示
  };

  // 【核心】tabItems: 构建 Tab 选项卡列表，根据内容类型动态决定显示哪些 Tab
  const tabItems: ToolkitTabItem[] = [];

  // 只有当内容包含有效行程信息时，才显示"每日行程"Tab
  // 业务含义：展示按天划分的行程详情，包括景点、预算、路线等
  if (hasItineraryContent) {
    tabItems.push({
      key: 'itinerary',
      label: '每日行程',
      icon: <CompassOutlined />,
      children: (
        <ToolkitItineraryTab
          messageId={messageId}
          exportRef={exportRef}
          budgetMode={budgetMode}
          budgetProjection={budgetProjection}
          familyBudget={familyBudget}
          childFriendlyBudget={childFriendlyBudget}
          confidence={confidence}
          cardEntries={cardEntries}
          conflictMap={conflictMap}
          favoriteSpots={favoriteSpots}
          expandedPeriods={expandedPeriods}
          expandedTips={expandedTips}
          quickRefineActions={QUICK_REFINE_ACTIONS}
          routeByDay={routeByDay}
          routeLoadingDay={routeLoadingDay}
          onBudgetModeChange={setBudgetMode}
          onExportImage={handleExportImage}
          onFetchRoute={handleFetchRoute}
          onOneClickFix={handleOneClickFixWithFeedback}
          onQuickRefine={runQuickRefine}
          onReorderByDistance={handleReorderByDistance}
          onShare={handleShare}
          onToggleFavoriteSpot={handleToggleFavoriteSpot}
          onTogglePeriod={handleTogglePeriod}
          onToggleTips={handleToggleTips}
        />
      ),
    });
  }

  // "多方案对比"Tab 始终显示
  // 业务含义：展示多个行程方案供用户对比选择，如方案A（紧凑型）vs 方案B（休闲型）
  tabItems.push({
      key: 'compare',
      label: '多方案对比',
      icon: <FundOutlined />,
      children: (
        <ToolkitCompareTab
          loading={compareHistoryLoading}
          source={compareSource}
          variants={compareVariants}
          onChooseVariant={handleChooseVariant}
        />
      ),
    });

  // 只有当内容包含有效行程信息时，才显示"冲突检测"和"候选池"Tab
  if (hasItineraryContent) {
    // "冲突检测"Tab
    // 业务含义：检测行程中的时间冲突、距离过远等问题，支持一键修复
    // 场景举例：第2天安排了上午9点故宫和上午10点颐和园，时间冲突 → 标红提示并提供修复建议
    tabItems.push({
      key: 'conflicts',
      label: '冲突检测',
      icon: <ReloadOutlined />,
      children: (
        <ToolkitConflictsTab
          cardEntries={cardEntries}
          conflictMap={conflictMap}
          messageId={messageId}
          totalConflicts={totalConflicts}
          onOneClickFix={handleOneClickFixWithFeedback}
        />
      ),
    });

    // "候选池"Tab
    // 业务含义：用户收藏的景点列表，可以基于这些收藏景点重新生成行程
    // 场景举例：用户在行程中收藏了"西湖"、"灵隐寺" → 候选池显示这两个景点 → 点击"基于收藏生成"重新规划
    tabItems.push({
      key: 'favorites',
      label: '候选池',
      icon: <HeartOutlined />,
      children: (
        <ToolkitFavoritesTab
          canBuildFromFavorites={Boolean(onContinuePrompt)} // 是否支持基于收藏生成（需要有 onContinuePrompt 回调）
          favoriteSpotList={favoriteSpotList}
          onBuildFromFavorites={handleBuildFromFavorites}
          onToggleFavoriteSpot={handleToggleFavoriteSpot}
        />
      ),
    });
  }

  // 以下三个 Tab 始终显示

  // "实用信息"Tab
  // 业务含义：展示目的地的实用信息，如交通方式、天气建议、当地习俗等
  tabItems.push(
    {
      key: 'practical',
      label: '实用信息',
      icon: <InfoCircleOutlined />,
      children: <ToolkitPracticalTab messageId={messageId} practicalInfo={practicalInfo} />,
    },
    // "执行清单"Tab
    // 业务含义：出行前的待办事项清单，如预订酒店、购买门票、办理签证等，支持勾选完成
    {
      key: 'checklist',
      label: '执行清单',
      icon: <CheckSquareOutlined />,
      children: (
        <ToolkitChecklistTab
          checklist={checklist}
          completedChecklist={completedChecklist}
          messageId={messageId}
          onToggleChecklist={handleToggleChecklist}
        />
      ),
    },
    // "出发提醒"Tab
    // 业务含义：出发前的提醒事项，如检查护照有效期、确认航班时间等
    {
      key: 'reminders',
      label: '出发提醒',
      icon: <ReloadOutlined />,
      children: <ToolkitRemindersTab messageId={messageId} reminders={reminders} />,
    },
  );

  // 渲染组件 UI：外层 Card 卡片包裹，内部包含概览面板（可选）和 Tab 选项卡
  return (
    <Card
      size="small"  // 紧凑尺寸
      style={{ marginTop: 12, borderRadius: 12, border: '1px solid #e2e8f0', background: '#f8fafc' }}
      styles={{ body: { padding: 12 } }}
    >
      {/* 如果有结构化数据，在 Tabs 上方显示概览面板 */}
      {artifactAvailable && artifact && (
        <ToolkitOverviewPanel
          artifact={artifact}
          subagentEvents={subagentEvents}
        />
      )}
      {/* Tabs 选项卡，items 为动态构建的 tabItems 数组 */}
      <Tabs size="small" items={tabItems} />
    </Card>
  );
};

// 导出组件，使其可以在其他文件中通过 import 使用
export default TravelPlanToolkit;
