// 'use client'：客户端组件声明，因为本组件有用户交互（拖拽排序、编辑输入框、弹窗操作）
'use client';

// React 核心库及钩子：
// useEffect：副作用钩子，当 day 或 open 变化时重新初始化编辑数据
// useMemo：缓存钩子，只在行程项变化时重新计算景点预览
// useState：状态钩子，存储上午/下午/晚上的行程项列表
import React, { useEffect, useMemo, useState } from 'react';
// Button：按钮组件
// Input：输入框组件
// Modal：弹窗/对话框组件
// Space：间距容器
// Tag：标签，用于显示景点预览
import { Button, Input, Modal, Space, Tag } from 'antd';
// DeleteOutlined：删除图标
// PlusOutlined：加号图标
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
// DayPlanCard：一日行程卡片的数据类型，包含上午/下午/晚上的活动安排
import type { DayPlanCard } from '@/utils/travelPlan';

// type：TypeScript 中定义类型别名的关键字
// PeriodKey：一天中的时段类型，只能是 'morning'（上午）、'afternoon'（下午）、'evening'（晚上）之一
// 这种写法叫"联合类型"，限制了变量只能取这几个值
type PeriodKey = 'morning' | 'afternoon' | 'evening';

// TravelDayEditorProps：行程日编辑器组件接收的属性
interface TravelDayEditorProps {
  open: boolean;                          // 弹窗是否打开
  day: DayPlanCard | null;                // 当前编辑的那天行程数据，null 表示没有选中
  onClose: () => void;                    // 关闭弹窗的回调函数
  onApply: (nextDay: DayPlanCard) => void; // 保存修改后的行程数据的回调函数
}

// ItemDraft：行程项草稿的数据结构
// 应用场景：用户编辑"上午"时段时，每个活动项（如"参观故宫"）就是一个 ItemDraft
interface ItemDraft {
  id: string;    // 唯一标识，用于列表渲染和拖拽排序
  value: string; // 活动内容文本，如"参观故宫"、"午餐：烤鸭"
}

// 【核心】splitItems：将文本按分隔符拆分为行程项列表
// 应用场景：后端返回的上午行程是一整段文字，如"参观故宫；游览天安门广场；午餐：烤鸭"
// 这个函数把它拆分成多个可独立编辑的项：["参观故宫", "游览天安门广场", "午餐：烤鸭"]
function splitItems(text: string): ItemDraft[] {
  return text
    .split(/[；;。]/)          // 用正则表达式按中文分号、英文分号、句号拆分
    .map((item) => item.trim()) // trim()：去除每项前后的空白字符
    .filter(Boolean)            // 过滤掉空字符串（Boolean() 将空字符串转为 false）
    .map((item, index) => ({
      // 生成唯一 id：格式为 "item-序号-随机字符串"
      // Math.random().toString(36) 生成36进制随机字符串，slice(2,7) 取5位
      id: `item-${index}-${Math.random().toString(36).slice(2, 7)}`,
      value: item,
    }));
}

// 【核心】joinItems：将行程项列表合并回文本
// 应用场景：用户编辑完各行程项后，需要把它们合并成一段文字保存回后端
// 例如：["参观故宫", "游览天安门广场"] → "参观故宫；游览天安门广场"
function joinItems(items: ItemDraft[]): string {
  return items.map((item) => item.value.trim()).filter(Boolean).join('；');  // 用中文分号连接
}

// extractSpots：从文本中提取景点名称
// 应用场景：用户编辑行程后，自动识别出其中的景点名称，显示在"路线点位预览"区域
// 例如："9:00 参观故宫 > 游览天安门广场" → 提取出 ["参观故宫", "游览天安门广场"]
function extractSpots(text: string): string[] {
  const raw = text
    .split(/[，、；;,。>→]/)  // 按逗号、顿号、分号、句号、箭头等拆分
    .map((item) => item.replace(/\d{1,2}[:：]\d{2}/g, '').trim())  // 去掉时间标记（如 "9:00"、"14：30"）
    .filter((item) => item.length >= 2 && item.length <= 18)  // 只保留2~18个字符的项（太短或太长的不是景点名）
    .filter((item) => !/(预算|建议|交通|住宿|餐饮|小贴士|自由安排)/.test(item));  // 排除非景点的关键词
  // new Set(raw)：去重（Set 是不允许重复值的集合）
  // Array.from()：将 Set 转回数组
  // .slice(0, 10)：最多取前10个景点
  return Array.from(new Set(raw)).slice(0, 10);
}

// 【核心】PeriodSection：时段编辑区域组件（上午/下午/晚上各一个）
// 这是一个内部子组件，负责渲染一个时段的行程项列表，支持拖拽排序、编辑、添加、删除
function PeriodSection({
  title,     // 时段标题，如"上午（拖拽排序）"
  items,     // 当前时段的行程项列表
  setItems,  // 更新行程项列表的函数
}: {
  title: string;
  items: ItemDraft[];
  setItems: (next: ItemDraft[]) => void;
}) {
  // newValue：新增行程项输入框的值
  const [newValue, setNewValue] = useState('');
  // draggingId：当前正在被拖拽的行程项的 id，null 表示没有在拖拽
  const [draggingId, setDraggingId] = useState<string | null>(null);

  // moveItem：拖拽排序的核心逻辑，将一个行程项从原位置移动到目标位置
  // 应用场景：用户想把"午餐"从第3项拖到第1项，这个函数处理位置交换
  const moveItem = (sourceId: string, targetId: string) => {
    const sourceIndex = items.findIndex((item) => item.id === sourceId);  // 找到被拖拽项的索引
    const targetIndex = items.findIndex((item) => item.id === targetId);  // 找到目标位置的索引
    // 如果找不到或者位置相同，不做任何操作
    if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;
    const next = [...items];  // 浅拷贝数组（... 展开运算符）
    // splice(起始位置, 删除数量)：从数组中删除元素
    const [moved] = next.splice(sourceIndex, 1);  // 取出被拖拽的项
    next.splice(targetIndex, 0, moved);  // 将该项插入到目标位置（0表示不删除，只插入）
    setItems(next);  // 更新列表
  };

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 10 }}>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>{title}</div>
      {/* 行程项列表 */}
      <div style={{ display: 'grid', gap: 8 }}>
        {items.map((item) => (
          <div
            key={item.id}
            draggable                          // HTML5 拖拽属性，让元素可以被拖动
            onDragStart={() => setDraggingId(item.id)}  // 开始拖拽时，记录被拖拽项的 id
            onDragOver={(event) => event.preventDefault()}  // 允许放置（默认行为是禁止放置，必须阻止）
            onDrop={() => {                    // 放下时，执行位置交换
              if (draggingId) moveItem(draggingId, item.id);
              setDraggingId(null);             // 清除拖拽状态
            }}
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 36px',  // 两列布局：输入框占满剩余空间，删除按钮固定36px宽
              gap: 8,
              alignItems: 'center',
              border: '1px dashed #cbd5e1',     // 虚线边框，表示可编辑区域
              borderRadius: 8,
              padding: 8,
              background: '#fff',
            }}
          >
            {/* 编辑输入框：修改行程项内容 */}
            <Input
              value={item.value}
              onChange={(event) =>
                // map()：遍历列表，找到 id 匹配的项更新其 value，其余项保持不变
                // ...candidate：展开运算符，复制原有属性，然后覆盖 value
                setItems(items.map((candidate) => (candidate.id === item.id ? { ...candidate, value: event.target.value } : candidate)))
              }
            />
            {/* 删除按钮：点击后从列表中移除该行程项 */}
            <Button
              size="small"
              danger                // danger 样式（红色），表示危险操作
              icon={<DeleteOutlined />}
              onClick={() => setItems(items.filter((candidate) => candidate.id !== item.id))}  // filter：过滤掉被删除的项
            />
          </div>
        ))}
      </div>
      {/* 新增行程项区域：输入框 + 添加按钮 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 90px', gap: 8, marginTop: 8 }}>
        <Input value={newValue} placeholder="新增行程项" onChange={(event) => setNewValue(event.target.value)} />
        <Button
          type="dashed"            // 虚线边框样式
          icon={<PlusOutlined />}
          onClick={() => {
            if (!newValue.trim()) return;  // 空内容不添加
            // Date.now()：当前时间戳，用作新项的 id（保证唯一性）
            setItems([...items, { id: `item-${Date.now()}`, value: newValue.trim() }]);
            setNewValue('');  // 清空输入框
          }}
        >
          添加
        </Button>
      </div>
    </div>
  );
}

// 【核心】TravelDayEditor：行程日编辑器主组件
// 应用场景：用户在行程卡片上点击"编辑"按钮，弹出这个弹窗，可以修改某一天的上午/下午/晚上安排
const TravelDayEditor: React.FC<TravelDayEditorProps> = ({ open, day, onClose, onApply }) => {
  // 三个时段的行程项列表状态
  const [morningItems, setMorningItems] = useState<ItemDraft[]>([]);    // 上午行程项
  const [afternoonItems, setAfternoonItems] = useState<ItemDraft[]>([]); // 下午行程项
  const [eveningItems, setEveningItems] = useState<ItemDraft[]>([]);    // 晚上行程项

  // useEffect：当 day 或 open 变化时，将行程数据拆分为可编辑的列表项
  // 应用场景：用户选中第2天的行程打开编辑器，这里将"上午：参观故宫；午餐"拆分为 ["参观故宫", "午餐"]
  useEffect(() => {
    if (!day || !open) return;  // 没有选中行程或弹窗未打开时，不做处理
    setMorningItems(splitItems(day.morning));
    setAfternoonItems(splitItems(day.afternoon));
    setEveningItems(splitItems(day.evening));
  }, [day, open]);

  // previewSpots：根据编辑内容自动提取的景点预览
  // 应用场景：用户修改了行程项后，底部自动显示识别出的景点名称，如"故宫"、"天安门"
  const previewSpots = useMemo(() => {
    // 先将三个时段的行程项合并回文本，再拼接在一起，最后提取景点
    return extractSpots([joinItems(morningItems), joinItems(afternoonItems), joinItems(eveningItems)].join('；'));
  }, [morningItems, afternoonItems, eveningItems]);

  // 如果没有选中任何行程数据，不渲染任何内容
  if (!day) return null;

  return (
    <Modal
      title={`编辑 ${day.dayLabel}`}  // 弹窗标题，如"编辑 第2天"
      open={open}                       // 控制弹窗显示/隐藏
      onCancel={onClose}                // 点击取消或遮罩层关闭弹窗
      width={900}                       // 弹窗宽度900像素
      footer={
        // 自定义底部按钮区域
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button
            type="primary"              // 主按钮样式（蓝色）
            onClick={() => {
              // 【核心】保存逻辑：将编辑后的行程项合并回 DayPlanCard 格式
              const nextDay: DayPlanCard = {
                ...day,                  // 保留原有的其他属性（如 dayLabel）
                morning: joinItems(morningItems),    // 将上午列表项合并为文本
                afternoon: joinItems(afternoonItems), // 将下午列表项合并为文本
                evening: joinItems(eveningItems),     // 将晚上列表项合并为文本
                // 如果提取到了景点就用新的，否则保留原有景点
                spots: previewSpots.length > 0 ? previewSpots : day.spots,
              };
              onApply(nextDay);  // 调用回调函数，将修改后的数据传回父组件
              onClose();         // 关闭弹窗
            }}
          >
            保存
          </Button>
        </Space>
      }
    >
      <div style={{ display: 'grid', gap: 10 }}>
        {/* 三个时段编辑区域 */}
        <PeriodSection title="上午（拖拽排序）" items={morningItems} setItems={setMorningItems} />
        <PeriodSection title="下午（拖拽排序）" items={afternoonItems} setItems={setAfternoonItems} />
        <PeriodSection title="晚上（拖拽排序）" items={eveningItems} setItems={setEveningItems} />
        {/* 景点预览区域 */}
        <div>
          <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6 }}>更新后路线点位预览</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {previewSpots.map((spot) => (
              <Tag key={spot}>{spot}</Tag>  // 每个景点用一个标签显示
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default TravelDayEditor;
