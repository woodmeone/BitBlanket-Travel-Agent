// 'use client' 是 Next.js 的指令，告诉框架这个文件只在浏览器端运行（不在服务器端渲染）
'use client';

// 【核心】每次"刷新"（tick）从回答文本中取出多少个字符来显示
// 效果类似"打字机"：值越小，打字越慢；值越大，打字越快
// 例如 ANSWER_CHARS_PER_TICK = 1 表示每次刷新只显示 1 个字符
export const ANSWER_CHARS_PER_TICK = 1;
// 每次刷新从"推理过程"文本中取出多少个字符来显示
// 推理文本通常较长，所以比回答的取字速度快（2 vs 1）
export const REASONING_CHARS_PER_TICK = 2;
// 流式刷新的时间间隔（毫秒），即每隔多少毫秒执行一次"取字符"操作
// 28ms 约等于每秒刷新约 35 次，肉眼看起来是连续的打字效果
export const STREAM_FLUSH_INTERVAL_MS = 28;
// 事件日志最多保留多少条，超过后旧日志会被丢弃
export const MAX_EVENT_LOGS = 14;
// 阶段日志最多保留多少条
export const MAX_STAGE_LOGS = 8;
// 子智能体（subagent）事件最多保留多少条
export const MAX_SUBAGENT_EVENTS = 10;
// 【核心】预设的旅行约束条件列表
// 'as const' 是 TypeScript 语法，表示"常量断言"——把数组变成只读的元组类型
// 元组类型：普通数组是 string[]（任意长度的字符串数组），而元组是 ['亲子', '老人', ...]（固定长度、固定顺序）
// 例如 PRESET_CONSTRAINTS 的类型会变成 readonly ['亲子', '老人', '无车', '雨天', '少走路']，而不是 string[]
// 这样做的好处：TypeScript 能精确知道数组里有哪些值，方便做类型检查
export const PRESET_CONSTRAINTS = ['亲子', '老人', '无车', '雨天', '少走路'] as const;
// 快速开始的示例提示词，展示在聊天界面供用户一键点击使用
export const QUICK_START_PROMPTS = [
  '帮我做一个上海周末 2 天轻松游，地铁可达，预算 1500 元以内',
  '请规划北京亲子 3 日游，包含室内备选和午休节奏',
  '做一个杭州 2 天游预算版，优先高性价比美食和免费景点',
];

// 类型别名：给类型起个短名字，方便复用
// ActiveView 表示当前激活的视图页面，只能是 'chat'（聊天）、'city'（城市）、'status'（状态）三者之一
// 类似于"枚举"，但用字符串字面量联合类型实现
export type ActiveView = 'chat' | 'city' | 'status';
// ComparePlanCount 表示对比方案的个数，只能是 2 或 3
// 用数字字面量联合类型限制取值范围，防止传入 1 或 4 等不合理的值
export type ComparePlanCount = 2 | 3;

// 运行时日志的数据结构
// interface 是 TypeScript 中定义对象"形状"的方式，类似于其他语言的"结构体"
export interface RuntimeLog {
  id: string;       // 日志唯一标识
  label: string;    // 日志标题/标签
  detail?: string;  // 日志详情（可选，? 表示该字段可以不填）
  time: string;     // 日志时间
}

// 【核心】从源字符串中取出前 count 个字符，返回 [取出的部分, 剩余部分]
// 返回值是元组类型 [string, string]——一个固定长度为 2 的数组，第一个元素是取出的字符，第二个是剩余的字符
// 应用场景：流式输出时，每次调用 takeChars 从缓冲区取出一小段字符显示，剩余的留给下次取
// 例如：takeChars('你好世界', 2) 返回 ['你好', '世界']
export function takeChars(source: string, count: number): [string, string] {
  if (!source) return ['', ''];
  // 用 Array.from 而非 source.slice，是为了正确处理 emoji 等多字节字符
  // 例如 '👋👋'.slice(0,1) 可能截断 emoji，而 Array.from 会把每个 emoji 当作一个整体
  const chars = Array.from(source);
  return [chars.slice(0, count).join(''), chars.slice(count).join('')];
}

// 获取当前时间的标签，格式如 "14:30:05"（时:分:秒）
export function nowLabel(): string {
  return new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

// 获取消息的时间戳，格式如 "14:30"（时:分），比 nowLabel 少了秒数
export function messageTimestamp(): string {
  return new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

// 将步骤对象归一化为可读的标签文字
// 优先取 title，其次 description，其次 tool，都没有则用"步骤 N"
// 应用场景：AI 返回的步骤数据格式不统一，此函数确保总能拿到一个可读的名称
export function normalizeStepLabel(step: Record<string, unknown>, index: number): string {
  const title = typeof step.title === 'string' ? step.title : '';
  const description = typeof step.description === 'string' ? step.description : '';
  const tool = typeof step.tool === 'string' ? step.tool : '';
  return title || description || tool || `步骤 ${index + 1}`;
}

// 将子智能体的英文名翻译为中文名
// 子智能体是 AI 内部的分工角色，如"规划"负责排行程，"研究"负责查信息，"校验"负责检查结果
export function subagentLabel(name: string | null | undefined): string {
  if (name === 'planning') return '规划';
  if (name === 'research') return '研究';
  if (name === 'verification') return '校验';
  return name || 'unknown';
}

// 【核心】将用户输入的原始文本与约束条件、对比模式、输出格式要求拼接成增强提示词
// rawInput: 用户在输入框中输入的原始文字
// options: 包含选中的约束条件、预算上限、是否开启对比模式、对比方案数量
// 返回值: 拼接后的完整提示词，会发送给 AI
// 应用场景举例：用户输入"帮我规划上海3天游"，选中了"亲子"约束、预算2000元、开启3套对比
//   → 最终提示词 = "帮我规划上海3天游\n\n约束条件：亲子、预算上限 2000 元\n\n请同时生成 3 套方案用于对比...\n\n请按每日行程卡输出..."
export function buildEnhancedPrompt(
  rawInput: string,
  options: {
    selectedConstraints: string[];       // 用户选中的预设约束，如 ['亲子', '少走路']
    budgetUpperLimit: number | null;     // 预算上限（元），null 表示未设置
    compareModeEnabled: boolean;         // 是否开启对比模式
    comparePlanCount: ComparePlanCount;  // 对比方案的套数（2 或 3）
  }
): string {
  // 把选中的约束条件复制一份，避免修改原数组
  const constraints = [...options.selectedConstraints];
  // 如果设置了预算上限，把它也加到约束条件中
  // 模板字符串：用反引号 `` 包裹，${变量} 会替换为变量的值
  // 例如 budgetUpperLimit = 2000 → "预算上限 2000 元"
  if (options.budgetUpperLimit && options.budgetUpperLimit > 0) {
    constraints.push(`预算上限 ${options.budgetUpperLimit} 元`);
  }
  // 如果有约束条件，拼接成一行，如 "约束条件：亲子、预算上限 2000 元"；否则为空字符串
  const constraintLine = constraints.length > 0 ? `约束条件：${constraints.join('、')}` : '';
  // 如果开启对比模式，添加对比方案的要求；否则为空字符串
  const compareLine = options.compareModeEnabled
    ? `请同时生成 ${options.comparePlanCount} 套方案用于对比，至少覆盖省钱版、均衡版、舒适版中的任意组合。`
    : '';
  // 固定的输出格式要求，要求 AI 按"每日行程卡"格式输出
  const formatLine =
    '请按"每日行程卡"输出：每一天包含上午 / 下午 / 晚上安排、当日预算、小贴士，并在每天给出景点点位列表。最后附上可执行清单与 T-7 / T-3 / T-1 提醒。';

  // 将所有部分用双换行拼接，filter(Boolean) 过滤掉空字符串（没有约束或没开对比时对应行为空）
  // 最终效果：用户输入 + 约束条件 + 对比要求 + 格式要求，各部分之间空一行
  return [rawInput, constraintLine, compareLine, formatLine].filter(Boolean).join('\n\n');
}
