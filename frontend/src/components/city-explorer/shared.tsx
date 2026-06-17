// 'use client' —— 声明这是一个客户端组件（在浏览器端运行），React 会在浏览器中渲染它
// 如果没有这行，组件默认在服务器端渲染（SSR），交互功能（如点击、状态）将无法工作
'use client';

// import —— 从其他文件中引入需要用到的类型和工具
// type 关键字表示只引入"类型定义"，不会产生实际的运行代码，仅用于代码提示和类型检查
import type { CityDetail, CitySummary } from '@/types';

// 【核心】QuickFilterKey —— 快速筛选的标识类型
// type 是 TypeScript 的类型别名语法，用来给一种类型起个短名字
// 这里定义了6种快速筛选场景，用 | 连接表示"或者"的关系（联合类型）
// 例如：'weekend' 表示"周末可去"，'budget' 表示"预算友好"
export type QuickFilterKey = 'weekend' | 'budget' | 'family' | 'easywalk' | 'rainy' | 'food';

// interface —— 定义"接口"，即描述一个对象应该有哪些属性
// QuickFilterOption 描述一个快速筛选项，包含：
//   key —— 筛选项的唯一标识（如 'weekend'）
//   label —— 显示给用户看的文字（如"周末可去"）
export interface QuickFilterOption {
  key: QuickFilterKey;
  label: string;
}

// CuratedPromptOption —— 策展推荐场景的配置
// 每个场景（如"周末快闪"）对应一个预置的 AI 提示词，用户点击后直接发送给 AI 助手
export interface CuratedPromptOption {
  label: string;       // 场景名称，如"周末快闪"
  hint: string;        // 场景简短描述，如"低预算，出行轻松。"
  prompt: string;      // 发送给 AI 的完整提示词
  borderColor: string; // 按钮边框颜色（CSS 颜色值）
  background: string;  // 按钮背景样式（支持渐变，如 linear-gradient）
}

// 【核心】DerivedCityProfile —— 从城市原始数据推导出的"城市画像"
// 原始数据（CitySummary/CityDetail）包含很多字段，这里把关键信息提炼成更易用的格式
// 例如：把日均预算数值（如 400）转换成预算等级（'low'），方便界面展示和筛选
export interface DerivedCityProfile {
  budgetLevel: 'low' | 'medium' | 'high'; // 预算等级：低/中/高
  tripDuration: string;                    // 建议旅行天数，如"2-3天"
  walkIntensity: 'low' | 'medium' | 'high'; // 步行强度：少走路/适中/偏多
  rainFriendly: boolean;                   // 是否适合雨天游玩
  familyFriendly: boolean;                 // 是否亲子友好
  foodFriendly: boolean;                   // 是否美食友好
  styleLabel: string;                      // 旅行气质标签，如"综合体验"、"文艺小城"
  recommendation: string;                  // 编辑推荐语，用于卡片上的简短描述
}

// CompareTableRow —— 城市对比表格中的一行数据
// 例如：对比项是"预算"，values 记录每个城市的预算值
//   key: 'budget', metric: '预算', values: { 'city-1': '¥400 / 预算友好', 'city-2': '¥800 / 预算均衡' }
export interface CompareTableRow {
  key: string;                       // 行的唯一标识
  metric: string;                    // 对比项名称，如"预算"、"步行强度"
  values: Record<string, string>;    // 每个城市对应的值，key 是城市 id，value 是显示文本
}

// 【核心】QUICK_FILTERS —— 快速筛选按钮的配置列表
// const 声明常量，数组中每个元素都是一个 QuickFilterOption 对象
// 这些筛选项会渲染成筛选栏中的快捷按钮，用户点击即可按场景过滤城市
export const QUICK_FILTERS: QuickFilterOption[] = [
  { key: 'weekend', label: '周末可去' },    // 适合周末两天短途出行
  { key: 'budget', label: '预算友好' },      // 日均花费较低
  { key: 'family', label: '亲子友好' },      // 适合带小朋友
  { key: 'easywalk', label: '少走路' },      // 步行强度低，适合不想暴走的人
  { key: 'rainy', label: '雨天也能玩' },     // 下雨也不影响行程
  { key: 'food', label: '美食优先' },        // 以美食为主要旅行目的
];

// CURATED_PROMPTS —— 策展推荐场景列表
// 每个场景对应一组预设的筛选条件 + AI 提示词
// 用户点击某个场景卡片后，会自动把 prompt 发送给 AI 助手
export const CURATED_PROMPTS: CuratedPromptOption[] = [
  {
    label: '周末快闪',
    hint: '低预算，出行轻松。',
    prompt: '请推荐适合周末两天出发、预算 1500 元内、地铁友好的真实旅行城市，并给出选择理由。',
    borderColor: '#bfdbfe',  // 浅蓝色边框
    background: 'linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%)',  // 浅蓝渐变背景
  },
  {
    label: '亲子省心',
    hint: '少走路，雨天也稳。',
    prompt: '请推荐亲子友好、少走路、下雨也不容易废行程的真实旅行城市，并说明为什么适合。',
    borderColor: '#c7d2fe',  // 浅紫色边框
    background: 'linear-gradient(180deg, #fbfbff 0%, #f3f4ff 100%)',  // 浅紫渐变背景
  },
  {
    label: '预算吃好',
    hint: '好吃不贵，节奏轻松。',
    prompt: '请推荐预算友好、以美食为主、景点不需要太密集的城市，并做简短对比。',
    borderColor: '#bae6fd',  // 浅青色边框
    background: 'linear-gradient(180deg, #f8feff 0%, #edf9ff 100%)',  // 浅青渐变背景
  },
];

// QUICK_FILTER_LABEL_MAP —— 快速筛选 key 到中文标签的映射表
// Object.fromEntries() 把 [key, value] 数组转成对象，如 { weekend: '周末可去', budget: '预算友好', ... }
// 用途：通过 key 快速查找对应的中文标签
const QUICK_FILTER_LABEL_MAP = Object.fromEntries(QUICK_FILTERS.map((item) => [item.key, item.label])) as Record<
  QuickFilterKey,
  string
>;

// includesAny —— 判断源字符串数组中是否包含任意一个关键词
// 参数 source: 要搜索的字符串数组（如城市的标签列表）
// 参数 patterns: 要匹配的关键词列表（如 ['博物馆', '室内', '文化']）
// 返回: 只要 source 中任一字符串包含 patterns 中任一关键词，就返回 true
// 举例：includesAny(['美食之都', '文艺小城'], ['美食', '小吃']) → true（因为"美食之都"包含"美食"）
function includesAny(source: string[], patterns: string[]): boolean {
  const text = source.join(' ').toLowerCase(); // 把数组拼成一个字符串，统一转小写方便匹配
  return patterns.some((pattern) => text.includes(pattern.toLowerCase())); // some() 只要有一个匹配就返回 true
}

// getQuickFilterLabel —— 根据筛选 key 获取中文标签
// 例如：getQuickFilterLabel('weekend') → '周末可去'
export function getQuickFilterLabel(filterKey: QuickFilterKey): string {
  return QUICK_FILTER_LABEL_MAP[filterKey];
}

// 【核心】buildCityProfile —— 从城市原始数据构建城市画像
// 这是筛选功能的核心：把原始数据（日均预算、标签等）转换成标准化的画像信息
// 应用场景：用户点击"预算友好"筛选按钮时，系统会检查每个城市的 budgetLevel 是否为 'low'
export function buildCityProfile(city: CitySummary | CityDetail): DerivedCityProfile {
  const budgetValue = city.avg_budget_per_day || 0; // 日均预算，没有则默认 0
  const tags = city.tags || []; // 城市标签列表，如 ['美食', '文艺', '夜市']

  // 根据日均预算金额判断预算等级
  // <=500 为低预算，500-900 为中等，>900 为高预算
  const budgetLevel: DerivedCityProfile['budgetLevel'] =
    budgetValue <= 500 ? 'low' : budgetValue <= 900 ? 'medium' : 'high';

  return {
    budgetLevel,
    tripDuration: city.trip_duration || '2-3天', // 建议旅行天数，默认 2-3 天
    walkIntensity: city.walk_intensity || 'medium', // 步行强度，默认适中
    // ?? 是空值合并运算符：如果左边是 null 或 undefined 才用右边的值
    // 如果后端没有提供 rain_friendly 字段，则通过标签推断：标签中包含"博物馆/室内/文化"则认为雨天友好
    rainFriendly: city.rain_friendly ?? includesAny(tags, ['博物馆', '室内', '文化']),
    // 同理：标签中包含"亲子/家庭/乐园"则认为亲子友好
    familyFriendly: city.family_friendly ?? includesAny(tags, ['亲子', '家庭', '乐园']),
    // 标签中包含"美食/小吃/夜市"则认为美食友好
    foodFriendly: city.food_friendly ?? includesAny(tags, ['美食', '小吃', '夜市']),
    styleLabel: city.style_label || '综合体验', // 旅行气质标签，默认"综合体验"
    // 推荐语优先级：编辑备注 > 城市描述 > 默认文案
    recommendation: city.editorial_note?.trim() || city.description?.trim() || `${city.name}适合做轻量旅行。`,
  };
}

// budgetLabel —— 把预算等级转成中文标签
// 例如：budgetLabel('low') → '预算友好'
export function budgetLabel(level: DerivedCityProfile['budgetLevel']): string {
  if (level === 'low') return '预算友好';
  if (level === 'high') return '预算偏高';
  return '预算均衡';
}

// walkLabel —— 把步行强度转成中文标签
// 例如：walkLabel('low') → '少走路'
export function walkLabel(level: DerivedCityProfile['walkIntensity']): string {
  if (level === 'low') return '少走路';
  if (level === 'high') return '步行偏多';
  return '步行适中';
}

// boolLabel —— 把布尔值转成友好/一般标签
// 例如：boolLabel(true) → '友好'，boolLabel(false) → '一般'
export function boolLabel(value: boolean): string {
  return value ? '友好' : '一般';
}

// foodLabel —— 把美食友好度转成高/中标签
// 例如：foodLabel(true) → '高'，foodLabel(false) → '中'
export function foodLabel(value: boolean): string {
  return value ? '高' : '中';
}

// seasonLabel —— 把季节数组转成展示文本
// 只取前两个季节，用 " / " 连接；如果为空则显示"四季皆可"
// 例如：seasonLabel(['春', '秋', '冬']) → '春 / 秋'
export function seasonLabel(seasons: string[]): string {
  return seasons.slice(0, 2).join(' / ') || '四季皆可';
}

// buildPlanPrompt —— 生成"规划旅行"的 AI 提示词
// 用户点击"规划"按钮时，会调用此函数生成提示词发送给 AI
// 例如：buildPlanPrompt('成都') → '请为我规划成都 3 天旅行计划，包含每日时间轴、预算估算...'
export function buildPlanPrompt(cityName: string): string {
  return `请为我规划${cityName} 3 天旅行计划，包含每日时间轴、预算估算、住宿建议、拍照点位、下雨天备选和适合第一次去的顺序安排。`;
}

// buildComparePrompt —— 生成"城市对比"的 AI 提示词
// 用户点击"让助手对比"时，会调用此函数生成提示词
// 例如：buildComparePrompt(['成都', '重庆']) → '请比较这些城市作为下一次旅行目的地的差异：成都、重庆。...'
export function buildComparePrompt(cityNames: string[]): string {
  return `请比较这些城市作为下一次旅行目的地的差异：${cityNames.join('、')}。请从预算、适合天数、步行强度、亲子友好度、雨天可玩度、核心景点真实性和整体旅行氛围做并排对比，并给出推荐结论。`;
}
