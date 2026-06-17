/* 【核心】旅行方案工具包操作 Hook */
/* 本文件是整个 travel-plan-toolkit 模块最核心的自定义 Hook（自定义 Hook 是 React 中复用逻辑的方式， */
/* 类似"工具箱"——把一堆相关函数和状态打包在一起，供组件直接调用）。 */
/* 它封装了用户在旅行方案页面上能做的所有交互操作，包括： */
/*   - 收藏/取消收藏景点 */
/*   - 获取真实路线预览 */
/*   - 按距离重排景点顺序 */
/*   - 导出方案为图片 */
/*   - 分享方案链接 */
/*   - 快速微调（如"增加预算"、"换酒店"等一键操作） */
/*   - 选择对比方案并继续细化 */
/* 应用场景举例：用户在"每日行程"标签页点击某个景点的"收藏"按钮， */
/* 实际就是调用了这里的 handleToggleFavoriteSpot 函数； */
/* 用户点击"导出图片"按钮，调用的是 handleExportImage 函数。 */

/* 'use client' —— Next.js 标记，表示这个文件只在浏览器端运行（客户端组件） */
/* 因为这里用到了 useState、useEffect 等 React Hook，以及 DOM 操作（html2canvas）， */
/* 这些都需要在浏览器环境中才能工作 */
'use client';

/* 从 React 引入三个 Hook： */
/*   useEffect —— 副作用 Hook，当某些数据变化时自动执行一段逻辑（类似"当XX变化时，自动做YY"） */
/*   useMemo —— 缓存计算结果 Hook，避免每次渲染都重新计算（类似"记住上次算的结果，数据没变就不重算"） */
/*   useState —— 状态 Hook，用来声明组件内部的可变数据（类似"声明一个变量，修改后页面自动更新"） */
import { useEffect, useMemo, useState } from 'react';
/* 从 Ant Design 引入 App 组件，用于显示轻提示消息（如"已收藏"、"导出成功"等） */
import { App } from 'antd';
/* html2canvas —— 一个第三方库，可以把网页上的 DOM 元素"截图"变成 Canvas 画布， */
/* 进而导出为 PNG 图片。应用场景：用户点击"导出图片"时，把行程卡片截图保存 */
import html2canvas from 'html2canvas';
/* 引入 React 类型，用于类型标注（TypeScript 中用 React.RefObject 表示"对 DOM 元素的引用"） */
import type React from 'react';
/* 引入类型定义： */
/*   ExecutionReceipt —— 执行回执（子 Agent 完成任务后的结果记录） */
/*   RoutePreviewResponse —— 路线预览响应（地图 API 返回的路线数据） */
/*   SubagentEvent —— 子 Agent 事件（如"研究 Agent 正在搜索景点信息"） */
/*   TripPlanArtifact —— 旅行方案制品（AI 生成的完整旅行方案数据结构） */
import type { ExecutionReceipt, RoutePreviewResponse, SubagentEvent, TripPlanArtifact } from '@/types';
/* 引入 API 客户端： */
/*   mapClient —— 地图服务客户端，用于获取真实路线预览 */
/*   shareClient —— 分享服务客户端，用于创建分享短链 */
import { mapClient, shareClient } from '@/services/api';
/* 引入旅行方案工具函数： */
/*   buildRoutePoints —— 把景点列表转换为路线点列表（供路线计算使用） */
/*   reorderByDistance —— 按距离重排景点顺序（让游览路线更合理，不走回头路） */
import { buildRoutePoints, reorderByDistance } from '@/utils/travelPlan';
/* 引入旅行方案相关类型： */
/*   DayPlanCard —— 每日行程卡片数据（包含当天所有景点、标签等） */
/*   PlanVariant —— 方案变体（多方案对比时的一个备选方案） */
/*   SpotDecisionInfo —— 景点决策信息（包含景点名称、推荐理由等） */
import type { DayPlanCard, PlanVariant, SpotDecisionInfo } from '@/utils/travelPlan';
/* 引入制品构建工具（从 shared 目录）： */
/*   buildArtifactDeliveryBundle —— 构建完整的制品交付包（用于分享） */
/*   buildArtifactDeliveryDescriptor —— 构建制品描述信息（用于导出图片时的标题、摘要等） */
/*   QuickRefineAction —— 快速微调操作类型（如"增加预算"、"换酒店"等预定义操作） */
import { buildArtifactDeliveryBundle, buildArtifactDeliveryDescriptor, type QuickRefineAction } from './shared';
/* 引入操作提示词构建工具： */
/*   buildArtifactAwarePrompt —— 构建带制品上下文的提示词（让 AI 知道当前方案的状态） */
/*   buildFavoritesQuickRefineAction —— 构建基于收藏列表的快速微调操作 */
/*   buildVariantContinuePrompt —— 构建方案继续细化的提示词（选择某个对比方案后继续优化） */
import { buildArtifactAwarePrompt, buildFavoritesQuickRefineAction, buildVariantContinuePrompt } from './actionPrompts';

/* 【核心】Hook 的配置参数接口 */
/* interface 是 TypeScript 中定义"数据形状"的方式，类似"模板"或"表格表头" */
/* 这个接口定义了调用 useTravelPlanToolkitActions 时需要传入的所有参数 */
interface UseTravelPlanToolkitActionsOptions {
  /* artifact —— 当前旅行方案制品（AI 生成的完整方案数据），可能为 null（还没有生成方案时） */
  artifact?: TripPlanArtifact | null;
  /* baseCards —— 每日行程卡片数组，是行程的核心数据 */
  /* DayPlanCard[] 表示"DayPlanCard 类型的数组"，即多天的行程数据 */
  baseCards: DayPlanCard[];
  /* content —— 原始文本内容（AI 返回的完整文本，作为导出/分享的兜底内容） */
  content: string;
  /* executionReceipt —— 执行回执（子 Agent 完成任务后的结果记录），可能为 null */
  executionReceipt?: ExecutionReceipt | null;
  /* exportRef —— 导出区域的 DOM 引用 */
  /* React.RefObject<HTMLDivElement | null> 表示"一个指向 div 元素的引用，可能为 null" */
  /* 应用场景：导出图片时，需要知道"页面上哪个区域要截图"，exportRef 就指向那个区域 */
  exportRef: React.RefObject<HTMLDivElement | null>;
  /* onContinuePrompt —— 继续对话的回调函数 */
  /* (prompt: string) => void 表示"接收一个字符串参数，没有返回值" */
  /* 应用场景：用户点击"增加预算"微调按钮后，会调用这个函数把优化指令发给 AI */
  onContinuePrompt?: (prompt: string) => void;
  /* setCards —— 修改行程卡片的函数 */
  /* React.Dispatch<React.SetStateAction<DayPlanCard[]>> 是 useState 返回的第二个值（修改函数） */
  /* 应用场景：按距离重排景点后，需要用这个函数更新卡片数据 */
  setCards: React.Dispatch<React.SetStateAction<DayPlanCard[]>>;
  /* subagentEvents —— 子 Agent 事件数组，记录各个子 Agent 的运行状态 */
  /* 应用场景：导出图片时，需要在图片中展示"研究 Agent 已完成、规划 Agent 进行中"等信息 */
  subagentEvents?: SubagentEvent[];
}

/* 【核心】旅行方案工具包操作 Hook */
/* 这是一个自定义 Hook（函数名以 use 开头是 React 的约定）， */
/* 它接收配置参数，返回一系列状态和操作函数供组件使用。 */
/* 可以理解为：这个函数是一个"工具箱"，你把原材料（参数）放进去， */
/* 它返回一堆工具（操作函数）和中间状态（如收藏列表、路线数据）。 */
export function useTravelPlanToolkitActions({
  /* 参数解构赋值 —— 把传入的对象拆开成单独的变量，方便直接使用 */
  /* artifact 默认值为 null（没有方案时） */
  artifact = null,
  baseCards,
  content,
  /* executionReceipt 默认值为 null */
  executionReceipt = null,
  exportRef,
  onContinuePrompt,
  setCards,
  /* subagentEvents 默认值为空数组 */
  subagentEvents = [],
}: UseTravelPlanToolkitActionsOptions) {
  /* 从 Ant Design 的 App 组件中获取 message 方法，用于显示轻提示 */
  /* message.info() 显示蓝色提示，message.success() 显示绿色提示，message.error() 显示红色提示 */
  const { message } = App.useApp();

  /* 【核心】收藏景点状态 */
  /* useState 声明一个可变状态，返回 [当前值, 修改函数] */
  /* Record<string, SpotDecisionInfo> 是一个对象类型，key 是景点名称（string），value 是景点信息 */
  /* 类似 { "故宫": {name:"故宫", ...}, "长城": {name:"长城", ...} } */
  /* 应用场景：用户点击"收藏"按钮，就把景点信息存到这个对象里；再点一次就删除（取消收藏） */
  const [favoriteSpots, setFavoriteSpots] = useState<Record<string, SpotDecisionInfo>>({});

  /* 路线预览数据状态 —— 按天存储每天的路线信息 */
  /* Record<string, RoutePreviewResponse | undefined> 表示 key 是天的标识（如"day1"）， */
  /* value 是路线数据或 undefined（还没获取路线时） */
  /* 应用场景：用户点击"查看路线"按钮后，路线数据会存到这里，地图组件读取它来绘制路线 */
  const [routeByDay, setRouteByDay] = useState<Record<string, RoutePreviewResponse | undefined>>({});

  /* 当前正在加载路线的天标识 */
  /* string | null 表示"要么是一个字符串（正在加载某天的路线），要么是 null（没有在加载）" */
  /* 应用场景：点击"查看路线"后设为"day1"，路线加载完成后设为 null，用于显示加载动画 */
  const [routeLoadingDay, setRouteLoadingDay] = useState<string | null>(null);

  /* useEffect —— 副作用 Hook：当 baseCards（行程卡片数据）变化时，清空路线数据 */
  /* 因为行程变了，之前的路线就失效了，需要重新获取 */
  /* 依赖数组 [baseCards] 表示"只有 baseCards 变化时才执行"，类似"监听器" */
  useEffect(() => {
    setRouteByDay({});
  }, [baseCards]);

  /* useMemo —— 缓存计算结果：把收藏对象转为数组 */
  /* Object.values() 把对象的值提取成数组，如 {a:1, b:2} → [1, 2] */
  /* 依赖 [favoriteSpots] 表示"只有 favoriteSpots 变化时才重新计算" */
  /* 应用场景：收藏标签页需要展示收藏列表，直接用数组比对象更方便遍历渲染 */
  const favoriteSpotList = useMemo(() => Object.values(favoriteSpots), [favoriteSpots]);

  /* 【核心】执行快速微调操作 */
  /* QuickRefineAction 包含 label（按钮文字）和 prompt（发给 AI 的指令） */
  /* 应用场景举例：用户在预算面板点击"增加预算"按钮， */
  /* 这个函数会把"增加预算"对应的 prompt 发给 AI，让 AI 重新规划预算更高的方案 */
  const runQuickRefine = (action: QuickRefineAction) => {
    /* 如果没有提供 onContinuePrompt 回调，说明当前环境不支持继续对话 */
    if (!onContinuePrompt) {
      message.info('当前会话不支持继续优化。');
      return;
    }
    /* buildArtifactAwarePrompt —— 在 prompt 前面加上当前方案上下文， */
    /* 让 AI 知道"用户是在当前方案基础上做微调"，而不是从零开始 */
    onContinuePrompt(buildArtifactAwarePrompt(action.prompt, artifact));
    message.success(`已填入"${action.label}"优化指令`);
  };

  /* 【核心】选择对比方案并继续细化 */
  /* 应用场景：在"多方案对比"标签页，用户看了三个备选方案后， */
  /* 点击"方案B"的"选择并细化"按钮，这个函数会把方案B的信息发给 AI， */
  /* 让 AI 基于方案B继续深入规划（如细化每天的行程安排） */
  const handleChooseVariant = (variant: PlanVariant) => {
    if (!onContinuePrompt) {
      message.info('当前会话不支持一键继续细化。');
      return;
    }

    /* buildVariantContinuePrompt —— 构建一个包含所选方案信息的提示词， */
    /* 告诉 AI "用户选择了方案X，请基于这个方案继续细化" */
    onContinuePrompt(buildVariantContinuePrompt(variant, artifact));
    message.success(`已选择 ${variant.title}，可继续细化`);
  };

  /* 基于收藏列表生成新方案 */
  /* 应用场景：用户在"景点收藏"标签页收藏了5个景点， */
  /* 点击"基于收藏生成方案"按钮，这个函数会把收藏的5个景点信息发给 AI， */
  /* 让 AI 围绕这些景点重新规划行程 */
  const handleBuildFromFavorites = () => {
    /* 如果收藏列表为空，提示用户先收藏一些景点 */
    if (favoriteSpotList.length === 0) {
      message.info('当前候选池为空。');
      return;
    }
    /* buildFavoritesQuickRefineAction —— 根据收藏列表构建一个快速微调操作， */
    /* 然后通过 runQuickRefine 发给 AI */
    runQuickRefine(buildFavoritesQuickRefineAction(favoriteSpotList));
  };

  /* 【核心】收藏/取消收藏景点 */
  /* 应用场景：在"景点决策卡"上，用户点击"❤ 收藏"按钮， */
  /* 如果该景点还没收藏，就加入收藏；如果已经收藏了，就取消收藏 */
  const handleToggleFavoriteSpot = (spot: SpotDecisionInfo) => {
    /* setFavoriteSpots 使用"函数式更新"——接收上一次的值 prev，返回新的值 */
    /* 这样可以确保在多次快速点击时不会丢失更新 */
    setFavoriteSpots((prev) => {
      /* prev[spot.name] 检查这个景点是否已经在收藏中 */
      /* 如果已收藏，则删除它（取消收藏） */
      if (prev[spot.name]) {
        /* { ...prev } 是"展开运算符"，把 prev 对象的所有属性复制到一个新对象 */
        /* 然后 delete 删除指定景点，返回新对象（不修改原对象，这是 React 的不可变数据原则） */
        const next = { ...prev };
        delete next[spot.name];
        return next;
      }
      /* 如果未收藏，则添加它 */
      /* { ...prev, [spot.name]: spot } 表示"复制 prev 的所有属性，再添加/覆盖 spot.name 这个属性" */
      /* [spot.name] 是"计算属性名"——用变量的值作为属性名，如 spot.name="故宫" 则属性名为"故宫" */
      return { ...prev, [spot.name]: spot };
    });
  };

  /* 【核心】获取真实路线预览 */
  /* 应用场景：用户在"每日行程"卡片上点击"查看路线"按钮， */
  /* 这个函数会调用地图 API（高德地图），获取当天所有景点之间的真实驾车/步行路线， */
  /* 包括距离、时间、途经点等信息，用于在地图上绘制路线 */
  const handleFetchRoute = async (dayKey: string, day: DayPlanCard) => {
    /* 当天景点少于2个时无法生成路线（至少需要起点和终点） */
    if (day.spots.length < 2) {
      message.warning('当天景点少于 2 个，无法生成路线。');
      return;
    }

    try {
      /* 标记当前天正在加载路线（用于显示加载动画） */
      setRouteLoadingDay(dayKey);
      /* 调用地图 API 获取路线预览 */
      /* day.spots.slice(0, 12) 限制最多12个景点（避免路线过长导致 API 超时） */
      /* provider: 'amap' 指定使用高德地图 */
      const result = await mapClient.getRoutePreview({ spots: day.spots.slice(0, 12), provider: 'amap' });
      /* 将路线数据存入 routeByDay，key 是天的标识（如"day1"） */
      setRouteByDay((prev) => ({ ...prev, [dayKey]: result }));
      message.success(`已获取 ${day.dayLabel} 真实路线`);
    } catch (error) {
      /* 路线获取失败时显示错误信息 */
      /* error instanceof Error ? error.message : '未知错误' —— 类型守卫，确保安全地获取错误消息 */
      message.error(`路线获取失败：${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      /* finally 块无论成功还是失败都会执行，用于清除加载状态 */
      setRouteLoadingDay(null);
    }
  };

  /* 【核心】按距离重排景点顺序 */
  /* 应用场景：用户获取了路线预览后，发现当前景点顺序不是最优的（走了回头路）， */
  /* 点击"按距离重排"按钮，这个函数会根据路线数据或直线距离， */
  /* 重新排列景点顺序，让游览路线更合理 */
  const handleReorderByDistance = (dayKey: string, dayIndex: number, day: DayPlanCard) => {
    /* 尝试从路线数据中获取已排序的景点名称列表 */
    const route = routeByDay[dayKey];
    /* 如果有路线数据且包含路线点，优先使用路线点的顺序（更准确） */
    /* 否则使用 reorderByDistance 按直线距离重排（作为备选方案） */
    const orderedSpots = route?.points?.length
      ? route.points.map((point) => point.name)
      : reorderByDistance(buildRoutePoints(day.spots)).map((point) => point.name);

    /* 更新行程卡片数据：只修改指定天（dayIndex）的景点顺序，其他天保持不变 */
    /* prev.map((item, index) => ...) —— 遍历所有天，找到目标天后替换其 spots 字段 */
    setCards((prev) => prev.map((item, index) => (index === dayIndex ? { ...item, spots: orderedSpots } : item)));
    message.success(`${day.dayLabel} 已按距离重排`);
  };

  /* 【核心】导出方案为图片 */
  /* 应用场景：用户对当前方案满意，点击"导出图片"按钮， */
  /* 这个函数会：1. 创建一个临时的 DOM 容器 2. 往里面塞入品牌头图 + 行程卡片 3. 用 html2canvas 截图 4. 下载为 PNG 图片 */
  /* 整个过程对用户来说是"点击按钮→图片下载"，但内部做了很多 DOM 操作 */
  const handleExportImage = async () => {
    /* exportRef.current 指向页面上要截图的区域，如果不存在则直接返回 */
    if (!exportRef.current) return;
    /* 临时 DOM 容器，用于存放截图内容，截图完成后会删除 */
    let exportShell: HTMLDivElement | null = null;

    try {
      /* 构建制品描述信息（标题、摘要、子 Agent 状态等），用于导出图片的头图区域 */
      const descriptor = buildArtifactDeliveryDescriptor(artifact, subagentEvents, { fallbackContent: content });
      /* 格式化当前时间为中文格式（如"2025年1月15日 14:30"），用于显示导出时间 */
      const exportedAt = new Intl.DateTimeFormat('zh-CN', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date());

      /* ---- 创建临时 DOM 容器 ---- */
      /* 这个容器会被放到页面左上角之外（left: -10000px），用户看不到 */
      /* 截图完成后会立即删除，不会影响页面布局 */
      exportShell = document.createElement('div');
      exportShell.style.position = 'fixed';
      exportShell.style.left = '-10000px';
      exportShell.style.top = '0';
      exportShell.style.width = '920px'; /* 固定宽度，确保导出图片尺寸一致 */
      exportShell.style.padding = '28px';
      exportShell.style.background = 'linear-gradient(180deg, #f8fbff 0%, #ffffff 28%, #f8fafc 100%)';
      exportShell.style.boxSizing = 'border-box';

      /* ---- 创建头图区域（品牌 + 方案标题 + 摘要） ---- */
      /* 头图使用深色渐变背景，类似旅行 App 的分享卡片风格 */
      const header = document.createElement('div');
      header.style.display = 'grid';
      header.style.gap = '12px';
      header.style.padding = '20px 22px';
      header.style.marginBottom = '18px';
      header.style.borderRadius = '20px';
      header.style.background = 'linear-gradient(135deg, #082f49 0%, #0f766e 100%)';
      header.style.color = '#ffffff';

      /* 头图上半部分：左侧品牌 + 右侧方案标题 */
      const headerTop = document.createElement('div');
      headerTop.style.display = 'flex';
      headerTop.style.justifyContent = 'space-between';
      headerTop.style.alignItems = 'center';
      headerTop.style.gap = '16px';

      /* 左侧品牌信息 */
      const brand = document.createElement('div');
      brand.style.display = 'grid';
      brand.style.gap = '4px';

      const brandTitle = document.createElement('div');
      brandTitle.textContent = 'BitBlanket Travel Agent';
      brandTitle.style.fontSize = '16px';
      brandTitle.style.fontWeight = '700';

      const brandSubtitle = document.createElement('div');
      brandSubtitle.textContent = 'AI 旅行方案导出卡片';
      brandSubtitle.style.fontSize = '12px';
      brandSubtitle.style.opacity = '0.82';

      brand.appendChild(brandTitle);
      brand.appendChild(brandSubtitle);

      /* 右侧方案标题和导出时间 */
      const meta = document.createElement('div');
      meta.style.textAlign = 'right';

      const metaTitle = document.createElement('div');
      metaTitle.textContent = descriptor.title;
      metaTitle.style.fontSize = '20px';
      metaTitle.style.fontWeight = '700';

      const metaTime = document.createElement('div');
      metaTime.textContent = `导出时间 ${exportedAt}`;
      metaTime.style.fontSize = '12px';
      metaTime.style.opacity = '0.82';

      meta.appendChild(metaTitle);
      meta.appendChild(metaTime);

      headerTop.appendChild(brand);
      headerTop.appendChild(meta);
      header.appendChild(headerTop);

      /* 头图中间：方案摘要文字（如果有且与摘要行不重复） */
      if (descriptor.summary && !descriptor.summaryLines.includes(descriptor.summary)) {
        const summaryText = document.createElement('div');
        summaryText.textContent = descriptor.summary;
        summaryText.style.fontSize = '13px';
        summaryText.style.lineHeight = '1.7';
        summaryText.style.opacity = '0.92';
        header.appendChild(summaryText);
      }

      /* 头图中间：摘要行列表（如"5天4晚"、"8个景点"等关键信息） */
      if (descriptor.summaryLines.length > 0) {
        const summaryList = document.createElement('div');
        summaryList.style.display = 'grid';
        summaryList.style.gap = '6px';
        summaryList.style.padding = '14px 16px';
        summaryList.style.borderRadius = '16px';
        summaryList.style.background = 'rgba(255,255,255,0.12)'; /* 半透明白色背景 */

        descriptor.summaryLines.forEach((line) => {
          const summaryLine = document.createElement('div');
          summaryLine.textContent = line;
          summaryLine.style.fontSize = '13px';
          summaryLine.style.lineHeight = '1.5';
          summaryList.appendChild(summaryLine);
        });

        header.appendChild(summaryList);
      }

      /* 头图底部：各子 Agent 完成的信息区块（如"景点推荐"、"美食攻略"等） */
      if (descriptor.htmlSections.length > 0) {
        const sectionGrid = document.createElement('div');
        sectionGrid.style.display = 'grid';
        /* gridTemplateColumns: repeat(auto-fit, minmax(200px, 1fr)) —— 自适应网格布局 */
        /* 每列最小200px，自动换行，类似"自动排列的卡片" */
        sectionGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(200px, 1fr))';
        sectionGrid.style.gap = '10px';

        descriptor.htmlSections.forEach((section) => {
          const sectionCard = document.createElement('div');
          sectionCard.style.padding = '12px 14px';
          sectionCard.style.borderRadius = '14px';
          sectionCard.style.background = 'rgba(255,255,255,0.12)';

          const sectionTitle = document.createElement('div');
          sectionTitle.textContent = section.title;
          sectionTitle.style.fontSize = '12px';
          sectionTitle.style.fontWeight = '700';
          sectionTitle.style.marginBottom = '6px';
          sectionCard.appendChild(sectionTitle);

          /* 每个区块最多显示3条内容，避免图片过长 */
          section.items.slice(0, 3).forEach((item) => {
            const sectionItem = document.createElement('div');
            sectionItem.textContent = `• ${item}`;
            sectionItem.style.fontSize = '12px';
            sectionItem.style.lineHeight = '1.5';
            sectionItem.style.opacity = '0.88';
            sectionCard.appendChild(sectionItem);
          });

          sectionGrid.appendChild(sectionCard);
        });

        header.appendChild(sectionGrid);
      }

      /* ---- 克隆行程卡片区域 ---- */
      /* cloneNode(true) 深度克隆 DOM 节点（包括所有子节点），类似"复制粘贴整个区域" */
      /* 这样截图用的是克隆的副本，不会影响页面上原始的卡片 */
      const clonedCard = exportRef.current.cloneNode(true) as HTMLDivElement;
      clonedCard.style.maxWidth = '100%';

      /* ---- 组装临时容器并截图 ---- */
      exportShell.appendChild(header);
      exportShell.appendChild(clonedCard);
      /* 把临时容器添加到页面上（虽然在屏幕外），html2canvas 需要它在 DOM 中才能截图 */
      document.body.appendChild(exportShell);

      /* html2canvas 把 DOM 元素渲染为 Canvas 画布 */
      /* scale: 2 表示2倍分辨率（高清截图），backgroundColor 设置背景色，useCORS 允许跨域图片 */
      const canvas = await html2canvas(exportShell, {
        scale: 2,
        backgroundColor: '#f8fbff',
        useCORS: true,
      });
      /* canvas.toDataURL('image/png') 把画布转为 PNG 格式的 Base64 字符串（图片数据） */
      const dataUrl = canvas.toDataURL('image/png');
      /* 创建一个隐藏的 <a> 标签，设置下载链接和文件名，模拟点击下载 */
      const link = document.createElement('a');
      link.href = dataUrl;
      /* 文件名格式如 "北京5日游-2025-01-15.png" */
      link.download = `${descriptor.filenameBase}-${new Date().toISOString().slice(0, 10)}.png`;
      link.click();
      message.success('已导出旅行方案图片');
    } catch (error) {
      message.error(`导出失败：${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      /* 无论成功还是失败，都要把临时容器从页面中删除，避免内存泄漏 */
      if (exportShell?.parentNode) {
        exportShell.parentNode.removeChild(exportShell);
      }
    }
  };

  /* 【核心】分享方案 */
  /* 应用场景：用户点击"分享"按钮，这个函数会： */
  /* 1. 构建完整的制品交付包（包含方案数据、HTML 内容等） */
  /* 2. 调用分享 API 创建一个短链接 */
  /* 3. 把短链接复制到剪贴板，用户可以直接粘贴分享给朋友 */
  const handleShare = async () => {
    try {
      /* 构建制品交付包，包含分享所需的标题、内容、HTML 和完整数据 */
      const bundle = buildArtifactDeliveryBundle(artifact, subagentEvents, {
        executionReceipt,
        fallbackContent: content,
      });
      /* 调用分享 API 创建短链接 */
      const result = await shareClient.createShareLink({
        title: bundle.share.title,
        content: bundle.share.content,
        html_content: bundle.htmlContent,
        delivery_bundle: bundle,
      });
      /* navigator.clipboard.writeText —— 浏览器 API，把文本复制到剪贴板 */
      await navigator.clipboard.writeText(result.share_url);
      message.success('分享短链已复制到剪贴板');
    } catch (error) {
      message.error(`分享失败：${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  /* 【核心】返回所有状态和操作函数 */
  /* 这个 Hook 返回一个对象，组件可以解构使用其中的任意成员 */
  /* 例如：const { favoriteSpots, handleToggleFavoriteSpot } = useTravelPlanToolkitActions(...) */
  return {
    favoriteSpots,           /* 收藏景点对象（key 是景点名，value 是景点信息） */
    favoriteSpotList,        /* 收藏景点数组（方便遍历渲染） */
    routeByDay,              /* 每天的路线数据（key 是天标识，value 是路线信息） */
    routeLoadingDay,         /* 当前正在加载路线的天标识（null 表示没有在加载） */
    runQuickRefine,          /* 执行快速微调操作 */
    handleBuildFromFavorites,/* 基于收藏列表生成新方案 */
    handleChooseVariant,     /* 选择对比方案并继续细化 */
    handleToggleFavoriteSpot,/* 收藏/取消收藏景点 */
    handleFetchRoute,        /* 获取真实路线预览 */
    handleReorderByDistance, /* 按距离重排景点顺序 */
    handleExportImage,       /* 导出方案为图片 */
    handleShare,             /* 分享方案 */
  };
}
