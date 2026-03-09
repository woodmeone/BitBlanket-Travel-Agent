'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Button, Input, Modal, Space, Tag } from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import type { DayPlanCard } from '@/utils/travelPlan';

type PeriodKey = 'morning' | 'afternoon' | 'evening';

interface TravelDayEditorProps {
  open: boolean;
  day: DayPlanCard | null;
  onClose: () => void;
  onApply: (nextDay: DayPlanCard) => void;
}

interface ItemDraft {
  id: string;
  value: string;
}

function splitItems(text: string): ItemDraft[] {
  return text
    .split(/[；;。]/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item, index) => ({ id: `item-${index}-${Math.random().toString(36).slice(2, 7)}`, value: item }));
}

function joinItems(items: ItemDraft[]): string {
  return items.map((item) => item.value.trim()).filter(Boolean).join('；');
}

function extractSpots(text: string): string[] {
  const raw = text
    .split(/[，、；;,。>→]/)
    .map((item) => item.replace(/\d{1,2}[:：]\d{2}/g, '').trim())
    .filter((item) => item.length >= 2 && item.length <= 18)
    .filter((item) => !/(预算|建议|交通|住宿|餐饮|小贴士|自由安排)/.test(item));
  return Array.from(new Set(raw)).slice(0, 10);
}

function PeriodSection({
  title,
  items,
  setItems,
}: {
  title: string;
  items: ItemDraft[];
  setItems: (next: ItemDraft[]) => void;
}) {
  const [newValue, setNewValue] = useState('');
  const [draggingId, setDraggingId] = useState<string | null>(null);

  const moveItem = (sourceId: string, targetId: string) => {
    const sourceIndex = items.findIndex((item) => item.id === sourceId);
    const targetIndex = items.findIndex((item) => item.id === targetId);
    if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;
    const next = [...items];
    const [moved] = next.splice(sourceIndex, 1);
    next.splice(targetIndex, 0, moved);
    setItems(next);
  };

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 10 }}>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>{title}</div>
      <div style={{ display: 'grid', gap: 8 }}>
        {items.map((item) => (
          <div
            key={item.id}
            draggable
            onDragStart={() => setDraggingId(item.id)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => {
              if (draggingId) moveItem(draggingId, item.id);
              setDraggingId(null);
            }}
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 36px',
              gap: 8,
              alignItems: 'center',
              border: '1px dashed #cbd5e1',
              borderRadius: 8,
              padding: 8,
              background: '#fff',
            }}
          >
            <Input
              value={item.value}
              onChange={(event) =>
                setItems(items.map((candidate) => (candidate.id === item.id ? { ...candidate, value: event.target.value } : candidate)))
              }
            />
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => setItems(items.filter((candidate) => candidate.id !== item.id))}
            />
          </div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 90px', gap: 8, marginTop: 8 }}>
        <Input value={newValue} placeholder="新增行程项" onChange={(event) => setNewValue(event.target.value)} />
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={() => {
            if (!newValue.trim()) return;
            setItems([...items, { id: `item-${Date.now()}`, value: newValue.trim() }]);
            setNewValue('');
          }}
        >
          添加
        </Button>
      </div>
    </div>
  );
}

const TravelDayEditor: React.FC<TravelDayEditorProps> = ({ open, day, onClose, onApply }) => {
  const [morningItems, setMorningItems] = useState<ItemDraft[]>([]);
  const [afternoonItems, setAfternoonItems] = useState<ItemDraft[]>([]);
  const [eveningItems, setEveningItems] = useState<ItemDraft[]>([]);

  useEffect(() => {
    if (!day || !open) return;
    setMorningItems(splitItems(day.morning));
    setAfternoonItems(splitItems(day.afternoon));
    setEveningItems(splitItems(day.evening));
  }, [day, open]);

  const previewSpots = useMemo(() => {
    return extractSpots([joinItems(morningItems), joinItems(afternoonItems), joinItems(eveningItems)].join('；'));
  }, [morningItems, afternoonItems, eveningItems]);

  if (!day) return null;

  return (
    <Modal
      title={`编辑 ${day.dayLabel}`}
      open={open}
      onCancel={onClose}
      width={900}
      footer={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button
            type="primary"
            onClick={() => {
              const nextDay: DayPlanCard = {
                ...day,
                morning: joinItems(morningItems),
                afternoon: joinItems(afternoonItems),
                evening: joinItems(eveningItems),
                spots: previewSpots.length > 0 ? previewSpots : day.spots,
              };
              onApply(nextDay);
              onClose();
            }}
          >
            保存
          </Button>
        </Space>
      }
    >
      <div style={{ display: 'grid', gap: 10 }}>
        <PeriodSection title="上午（拖拽排序）" items={morningItems} setItems={setMorningItems} />
        <PeriodSection title="下午（拖拽排序）" items={afternoonItems} setItems={setAfternoonItems} />
        <PeriodSection title="晚上（拖拽排序）" items={eveningItems} setItems={setEveningItems} />
        <div>
          <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6 }}>更新后路线点位预览</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {previewSpots.map((spot) => (
              <Tag key={spot}>{spot}</Tag>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default TravelDayEditor;
