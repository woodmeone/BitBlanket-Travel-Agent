import { App } from 'antd';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type React from 'react';
import { describe, expect, it, beforeEach, vi } from 'vitest';

const cityClientMock = vi.hoisted(() => ({
  getRegions: vi.fn(),
  getTags: vi.fn(),
  getCities: vi.fn(),
  getCityDetail: vi.fn(),
}));

vi.mock('@/services/api', () => ({
  cityClient: cityClientMock,
}));

import CityExplorer from '@/components/CityExplorer';

const renderWithApp = (ui: React.ReactElement) => render(<App>{ui}</App>);

const baseCity = {
  id: 'hangzhou',
  name: '杭州',
  region: '华东',
  tags: ['美食', '西湖', '周末'],
  description: '适合慢节奏周末游。',
  avg_budget_per_day: 480,
  best_seasons: ['春季', '秋季'],
  trip_duration: '2-3天',
  walk_intensity: 'low' as const,
  rain_friendly: true,
  family_friendly: true,
  food_friendly: true,
  style_label: '轻松慢游',
  editorial_note: '第一次去也很容易上手。',
  data_source: 'curated' as const,
};

describe('CityExplorer', () => {
  beforeEach(() => {
    cityClientMock.getRegions.mockReset();
    cityClientMock.getTags.mockReset();
    cityClientMock.getCities.mockReset();
    cityClientMock.getCityDetail.mockReset();

    cityClientMock.getRegions.mockResolvedValue({ regions: ['华东', '华北'] });
    cityClientMock.getTags.mockResolvedValue({ tags: ['美食', '亲子'] });
    cityClientMock.getCities.mockResolvedValue({ cities: [baseCity] });
    cityClientMock.getCityDetail.mockResolvedValue({
      ...baseCity,
      attractions: [
        {
          name: '西湖',
          type: '自然',
          duration: '2-3h',
          ticket: 0,
          district: '西湖区',
          note: '清晨和傍晚更舒服。',
        },
      ],
    });
  });

  it('loads curated cities and triggers curated prompt actions', async () => {
    const onUsePrompt = vi.fn();
    renderWithApp(<CityExplorer onUsePrompt={onUsePrompt} />);

    await waitFor(() => {
      expect(screen.getByText('杭州')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /周末快闪/ }));
    expect(onUsePrompt).toHaveBeenCalledWith(
      '请推荐适合周末两天出发、预算 1500 内、地铁友好的真实城市目的地，并给出选择理由。'
    );
  });

  it('opens city detail drawer from city cards', async () => {
    renderWithApp(<CityExplorer onUsePrompt={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('杭州')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /详\s*情/ }));

    await waitFor(() => {
      expect(cityClientMock.getCityDetail).toHaveBeenCalledWith('hangzhou');
    });

    const drawer = await screen.findByRole('dialog');
    expect(within(drawer).getByText('核心景点')).toBeInTheDocument();
    expect(within(drawer).getByText('西湖')).toBeInTheDocument();
  });
});
