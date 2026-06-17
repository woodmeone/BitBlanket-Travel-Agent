// 每日行程时间线组件和小贴士处理工具
// 应用场景：在每日行程卡片中，把一段文字（如"9:00 故宫；12:00 午餐；14:00 天坛"）
//   解析成带时间标签的时间线列表，按时间排序展示

// 'use client' 是 Next.js 的标记，表示这个文件只在浏览器端（客户端）运行
'use client';

// React 是前端框架，所有组件都需要引入
import React from 'react';
// Button 是 Ant Design 提供的按钮组件，直接使用不用自己写样式
import { Button } from 'antd';

// PeriodType 时段类型：上午(morning)、下午(afternoon)、晚上(evening)
type PeriodType = 'morning' | 'afternoon' | 'evening';

// TimelineItem 时间线中的单个条目
interface TimelineItem {
  timeLabel: string | null;    // 时间标签，如"9:00"；如果没有时间则为 null
  content: string;             // 条目内容，如"游览故宫"
  timeMinutes: number | null;  // 转换为分钟数的时间，用于排序；如 9:00 = 540
  originalIndex: number;       // 原始顺序索引，没有时间的条目按此排序
}

// 清理小贴士文本中的冗余前缀
// 例如："小贴士：记得带防晒霜" → "记得带防晒霜"
function normalizeTipText(tip: string): string {
  return tip
    .replace(/^\s*(?:小贴士|当日小贴士|Tips?|提示|注意事项)[:：]?\s*/i, '')  // 去掉"小贴士："等前缀
    .replace(/(?<!\d)\s*[：:]{2,}\s*(?!\d)/g, '：')   // 多个冒号合并为一个
    .replace(/(?<!\d)\s*[：:]\s*(?!\d)/g, '：')        // 统一为中文冒号
    .replace(/^[：:\-\s]+/, '')                          // 去掉开头的冒号、横线、空格
    .replace(/\s+/g, ' ')                               // 多个空格合并为一个
    .trim();                                             // 去掉首尾空格
}

// 【核心】对小贴士列表去重和清理
// 应用场景：AI 可能生成重复的小贴士，需要去重后展示
// 例如：["小贴士：带防晒霜", "Tips：带防晒霜"] → ["带防晒霜"]
export function compactTips(tips: string[]): string[] {
  const seen = new Set<string>();   // Set 是一种不重复的集合，用来记录已出现过的小贴士
  const result: string[] = [];
  for (const raw of tips) {
    const normalized = normalizeTipText(raw);  // 先清理文本
    const key = normalized.toLowerCase();       // 统一转小写用于比较（不区分大小写去重）
    if (!normalized || seen.has(key)) continue; // 空文本或已存在则跳过
    seen.add(key);
    result.push(normalized);
  }
  return result;
}

// 根据时段返回标题和颜色
// 上午 → 天蓝色，下午 → 琥珀色，晚上 → 紫色
function periodMeta(period: PeriodType): { title: string; color: string } {
  if (period === 'morning') return { title: '上午', color: '#0ea5e9' };
  if (period === 'afternoon') return { title: '下午', color: '#f59e0b' };
  return { title: '晚上', color: '#8b5cf6' };
}

// 【核心】将一段文字拆分成时间线条目
// 应用场景：AI 返回"9:00 故宫；12:00 午餐；14:00 天坛"这样的文字，
//   需要解析成独立条目，提取时间，并按时间排序
function splitTimelineItems(rawText: string): TimelineItem[] {
  // 第一步：统一格式——换行合并、多余空格合并、句号变分号、箭头变分号、竖线变分号
  const normalized = rawText
    .replace(/\r\n?/g, '\n')                   // Windows 换行(\r\n) 统一为 \n
    .replace(/\s+/g, ' ')                      // 多个空白字符合并为一个空格
    .replace(/[。]/g, '；')                    // 句号变分号（用于拆分）
    .replace(/\s*(?:->|→)\s*/g, '；')          // 箭头变分号
    .replace(/\|/g, '；');                     // 竖线变分号

  // 第二步：按分号/分号拆分，过滤空条目和时段前缀（如"上午"）
  return normalized
    .split(/[；;]/)                             // 按中英文分号拆分
    .map((item) => item.trim())                 // 去掉首尾空格
    .filter(Boolean)                            // 过滤空字符串
    .filter((item) => !/^(上午|下午|晚上)\b/.test(item))  // 去掉纯时段词（如单独的"上午"）
    .map((item, index) => {
      // 第三步：尝试提取时间标签（如"9:00"）
      const timeMatch = item.match(/(?:^|\s)(\d{1,2}[:：]\d{2})(?:\s|$)/);
      if (!timeMatch) {
        // 没有时间标签的条目
        return { timeLabel: null, content: item, timeMinutes: null, originalIndex: index };
      }

      // 第四步：解析时间并验证合法性
      const normalizedTime = timeMatch[1].replace('：', ':');  // 中文冒号转英文冒号
      const [hourStr, minuteStr] = normalizedTime.split(':');
      const hour = Number(hourStr);
      const minute = Number(minuteStr);
      const isValid =
        Number.isFinite(hour) && Number.isFinite(minute) && hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59;

      return {
        timeLabel: normalizedTime,                                                               // 显示用的时间标签
        content: item.replace(timeMatch[1], '').replace(/^\s*[-:：]?\s*/, '').trim() || item,    // 去掉时间部分后的内容
        timeMinutes: isValid ? hour * 60 + minute : null,                                        // 转为分钟数，用于排序
        originalIndex: index,
      };
    })
    .sort((a, b) => {
      // 第五步：排序——有时间标签的按时间排前面，没时间的保持原顺序
      if (a.timeMinutes !== null && b.timeMinutes !== null) return a.timeMinutes - b.timeMinutes;
      if (a.timeMinutes !== null) return -1;   // 有时间的排前面
      if (b.timeMinutes !== null) return 1;    // 没时间的排后面
      return a.originalIndex - b.originalIndex; // 都没时间则按原顺序
    });
}

// 【核心】时段时间线组件——展示一个时段（上午/下午/晚上）的行程条目
// React.FC 是 React 函数组件的类型写法，<> 中是组件接收的参数类型
// 组件参数说明：
//   period - 时段（上午/下午/晚上）
//   rawText - 原始文本，如"9:00 故宫；12:00 午餐"
//   dayKey - 当天的唯一标识，用于生成展开/收起的 key
//   expandedPeriods - 记录哪些时段处于展开状态的对象
//   onToggle - 点击"展开/收起"按钮时的回调函数
export const PeriodTimeline: React.FC<{
  period: PeriodType;
  rawText: string;
  dayKey: string;
  expandedPeriods: Record<string, boolean>;
  onToggle: (periodKey: string) => void;
}> = ({ period, rawText, dayKey, expandedPeriods, onToggle }) => {
  const items = splitTimelineItems(rawText);           // 解析文本为时间线条目
  const key = `${dayKey}-${period}`;                   // 生成唯一 key，如"day1-morning"
  const isExpanded = expandedPeriods[key] ?? false;    // 当前时段是否展开，默认收起
  const visibleItems = isExpanded ? items : items.slice(0, 3);  // 收起时只显示前3条
  const hasMore = items.length > 3;                    // 是否有更多条目可展开
  const meta = periodMeta(period);                     // 获取时段的标题和颜色

  return (
    <div
      style={{
        border: '1px solid #e2e8f0',
        borderRadius: 10,
        padding: '10px 12px',
        background: '#fff',
      }}
    >
      {/* 时段标题，如"上午" */}
      <div style={{ fontSize: 13, fontWeight: 600, color: '#1e293b', marginBottom: 8 }}>{meta.title}</div>
      {/* 时间线条目列表 */}
      <div style={{ display: 'grid', gap: 8 }}>
        {visibleItems.map((item, index) => (
          <div key={`${key}-${index}`} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            {/* 左侧的时间线圆点和竖线 */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 2 }}>
              {/* 圆点，颜色随时段变化 */}
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: meta.color,
                  display: 'inline-block',
                }}
              />
              {/* 竖线连接线（最后一个条目不显示） */}
              {index < visibleItems.length - 1 && (
                <span
                  style={{
                    width: 1,
                    minHeight: 18,
                    background: '#cbd5e1',
                    marginTop: 2,
                  }}
                />
              )}
            </div>
            {/* 右侧的时间标签和内容 */}
            <div style={{ display: 'grid', gap: 4 }}>
              {/* 时间标签，如"9:00"，蓝色胶囊样式 */}
              {item.timeLabel && (
                <span
                  style={{
                    display: 'inline-flex',
                    width: 'fit-content',
                    fontSize: 11,
                    color: '#1d4ed8',
                    background: '#dbeafe',
                    border: '1px solid #93c5fd',
                    borderRadius: 999,           // border-radius: 999 让边框变成胶囊形状
                    padding: '1px 8px',
                    fontWeight: 600,
                  }}
                >
                  {item.timeLabel}
                </span>
              )}
              {/* 条目内容文字 */}
              <div style={{ fontSize: 13, color: '#334155', lineHeight: 1.6 }}>{item.content}</div>
            </div>
          </div>
        ))}
      </div>
      {/* 展开更多 / 收起 按钮 */}
      {hasMore && (
        <Button size="small" type="link" style={{ padding: 0, marginTop: 6 }} onClick={() => onToggle(key)}>
          {isExpanded ? '收起' : `展开更多（${items.length - 3}）`}
        </Button>
      )}
    </div>
  );
};
