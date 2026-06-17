// 'use client' 声明这是一个客户端组件（在浏览器端运行）
// Next.js 中默认组件是服务端组件，加上这个标记后才能使用 useState、useEffect 等浏览器端功能
'use client';

// 从 React 库中导入三个核心钩子：
// - useEffect: 副作用钩子，用于在组件渲染后执行异步操作（如请求数据）
// - useMemo: 缓存钩子，避免每次渲染都重新计算，只在依赖项变化时才重新计算
// - useState: 状态钩子，用于在函数组件中添加可变状态
import React, { useEffect, useMemo, useState } from 'react';
// Card 是 Ant Design 的卡片容器组件，用于将内容包裹在一个带边框和圆角的容器中
import { Card } from 'antd';
// cityClient 是封装好的城市数据 API 客户端，用于与后端交互获取城市相关数据
import { cityClient } from '@/services/api';
// 导入城市相关的类型定义：
// - CityDetail: 城市详细信息类型（包含景点、美食等详细内容）
// - CitySummary: 城市摘要信息类型（用于列表展示的精简信息）
import type { CityDetail, CitySummary } from '@/types';
// 导入城市探索页面的各个子组件（按页面区域拆分）：
// - CityExplorerComparePanel: 城市对比面板，展示用户选中的对比城市
// - CityExplorerDetailDrawer: 城市详情抽屉，侧滑展示城市完整信息
// - CityExplorerFilterBar: 筛选栏，提供地区、标签、快捷筛选
// - CityExplorerGrid: 城市卡片网格，展示城市列表
// - CityExplorerHero: 顶部英雄区，展示标题和摘要信息
import {
  CityExplorerComparePanel,
  CityExplorerDetailDrawer,
  CityExplorerFilterBar,
  CityExplorerGrid,
  CityExplorerHero,
} from '@/components/city-explorer/sections';
// 导入共享的工具函数和类型：
// - buildCityProfile: 根据城市数据构建城市画像（用于快捷筛选判断）
// - getQuickFilterLabel: 获取快捷筛选项的中文标签
// - QuickFilterKey: 快捷筛选项的键类型
import { buildCityProfile, getQuickFilterLabel, type QuickFilterKey } from '@/components/city-explorer/shared';

// interface 是 TypeScript 的接口定义，用于描述对象的形状（有哪些字段、字段类型是什么）
// 类似于数据库表结构的定义，规定了数据必须包含哪些属性
interface CityExplorerProps {
  // onUsePrompt: 当用户点击某个城市相关的提示词时触发的回调函数
  // 场景举例：用户点击"帮我规划成都3日游"，这个函数会把提示词传递给上层组件处理
  onUsePrompt: (prompt: string) => void;
}

// 【核心】城市探索主组件 —— 整个城市探索页面的入口，管理所有状态和数据流
// { onUsePrompt }: CityExplorerProps 是解构赋值 + 类型注解
// 解构赋值：从 props 对象中直接取出 onUsePrompt 属性
// 类型注解：告诉 TypeScript 这个参数符合 CityExplorerProps 接口的定义
export default function CityExplorer({ onUsePrompt }: CityExplorerProps) {
  // 初始显示的城市数量（首次加载展示 24 个城市卡片）
  const initialVisibleCityCount = 24;
  // 每次点击"加载更多"时追加显示的城市数量
  const loadMoreCityCount = 24;

  // useState 是 React 的状态钩子，用于在函数组件中添加可变状态
  // const [当前值, 设置值的函数] = useState(初始值)
  // 当调用设置值的函数时，组件会自动重新渲染，页面显示最新数据

  // 可选的地区列表（如"华东"、"西南"等），用于筛选栏的下拉选项
  const [regions, setRegions] = useState<string[]>([]);
  // 泛型 <string[]> 表示这个状态存储的是字符串数组
  // 场景举例：后端返回 ["华东", "西南", "华北"]，setRegions 更新后筛选栏自动显示这些选项

  // 可选的标签列表（如"美食之城"、"历史古都"等），用于筛选栏的标签选择
  const [tags, setTags] = useState<string[]>([]);

  // 当前选中的地区，undefined 表示未选择任何地区（即"全部"）
  // 泛型 <string | undefined> 表示值可以是字符串或 undefined（联合类型）
  const [selectedRegion, setSelectedRegion] = useState<string | undefined>(undefined);

  // 当前选中的标签列表（可多选）
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  // 当前选中的快捷筛选项列表（如"周末游"、"低预算"等）
  // QuickFilterKey 是自定义类型，限定只能选择预定义的快捷筛选键
  const [selectedQuickFilters, setSelectedQuickFilters] = useState<QuickFilterKey[]>([]);

  // 【核心】从后端获取的城市摘要列表，是页面展示的核心数据源
  const [cities, setCities] = useState<CitySummary[]>([]);

  // 是否正在加载城市列表（用于显示加载动画）
  const [isLoading, setIsLoading] = useState(false);

  // 是否正在加载筛选项（地区、标签）
  const [isFilterLoading, setIsFilterLoading] = useState(false);

  // 错误信息，null 表示没有错误
  const [error, setError] = useState<string | null>(null);

  // 当前查看详情的城市完整信息，null 表示没有打开详情
  const [activeCityDetail, setActiveCityDetail] = useState<CityDetail | null>(null);

  // 城市详情抽屉是否打开
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // 【核心】正在对比的城市 ID 列表（最多 3 个）
  const [compareCityIds, setCompareCityIds] = useState<string[]>([]);

  // 收藏的城市 ID 列表
  const [favoriteCityIds, setFavoriteCityIds] = useState<string[]>([]);

  // 当前页面可见的城市数量（用于"加载更多"的分页逻辑）
  const [visibleCityCount, setVisibleCityCount] = useState(initialVisibleCityCount);

  // 【核心】useEffect 副作用钩子 —— 组件首次挂载时加载筛选项（地区和标签）
  // 触发时机：组件首次渲染后执行一次（依赖数组为空 []）
  // 业务目的：页面打开时就需要显示筛选栏的选项，所以必须在一开始就获取
  // void 关键字：显式标记不处理 Promise 的返回值（避免 lint 警告）
  useEffect(() => {
    async function loadFilterOptions() {
      try {
        setIsFilterLoading(true);
        // Promise.all 同时发起两个请求，等两个都返回后再继续
        // 场景举例：同时请求地区列表和标签列表，比依次请求更快
        const [regionData, tagData] = await Promise.all([cityClient.getRegions(), cityClient.getTags()]);
        // || [] 是防御性编程：如果后端返回 undefined 或 null，则使用空数组作为默认值
        setRegions(regionData.regions || []);
        setTags(tagData.tags || []);
      } catch (loadError) {
        // instanceof Error 判断是否是标准错误对象，是则取 message，否则用默认提示
        setError(loadError instanceof Error ? loadError.message : '加载筛选项失败');
      } finally {
        // finally 无论成功还是失败都会执行，确保关闭加载状态
        setIsFilterLoading(false);
      }
    }

    void loadFilterOptions();
  }, []);

  // 【核心】useEffect 副作用钩子 —— 当筛选条件变化时重新加载城市列表
  // 触发时机：selectedRegion 或 selectedTags 变化时执行
  // 业务目的：用户切换地区或标签后，城市列表需要根据新条件重新从后端获取
  // 场景举例：用户从"全部"切换到"华东"地区，此时 selectedRegion 变为"华东"，触发此 effect 重新请求
  useEffect(() => {
    async function loadCities() {
      try {
        setIsLoading(true);
        // 先清除之前的错误信息，避免显示过期的错误提示
        setError(null);
        // 将当前筛选条件传给后端 API，获取符合条件的城市列表
        const response = await cityClient.getCities({ region: selectedRegion, tags: selectedTags });
        setCities(response.cities || []);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : '加载城市失败');
      } finally {
        setIsLoading(false);
      }
    }

    void loadCities();
  }, [selectedRegion, selectedTags]);

  // useEffect —— 当任何筛选条件变化时，重置可见城市数量为初始值
  // 触发时机：selectedQuickFilters、selectedRegion、selectedTags 任一变化时
  // 业务目的：切换筛选条件后，应该从头展示城市，而不是停留在之前的"加载更多"位置
  // 场景举例：用户已经加载到第 48 个城市，然后切换了地区，此时应回到只显示 24 个城市
  useEffect(() => {
    setVisibleCityCount(initialVisibleCityCount);
  }, [selectedQuickFilters, selectedRegion, selectedTags]);

  // 【核心】useMemo 缓存钩子 —— 根据快捷筛选条件过滤城市列表
  // 缓存内容：经过快捷筛选后的城市数组
  // 重新计算时机：cities 或 selectedQuickFilters 变化时
  // 业务目的：快捷筛选（如"周末游"、"低预算"）是前端本地过滤，不需要请求后端
  // 场景举例：用户勾选"周末游"，只保留行程 2 天以内的城市；勾选"低预算"，只保留消费水平低的城市
  // every() 表示所有选中的快捷筛选都必须满足（AND 逻辑，而非 OR）
  const filteredCities = useMemo(() => {
    return cities.filter((city) => {
      // 没有选中任何快捷筛选时，所有城市都通过
      if (selectedQuickFilters.length === 0) return true;
      // buildCityProfile 根据城市数据计算出画像属性（如预算等级、是否适合家庭等）
      const profile = buildCityProfile(city);

      return selectedQuickFilters.every((filterKey) => {
        // weekend: 周末游 —— 行程天数以 2 开头（如"2天1晚"），用正则 /^2/ 匹配
        if (filterKey === 'weekend') return /^2/.test(profile.tripDuration);
        // budget: 低预算 —— 预算等级为 low
        if (filterKey === 'budget') return profile.budgetLevel === 'low';
        // family: 亲子友好 —— 适合家庭出行
        if (filterKey === 'family') return profile.familyFriendly;
        // easywalk: 轻松步行 —— 步行强度低，不用爬山走远路
        if (filterKey === 'easywalk') return profile.walkIntensity === 'low';
        // rainy: 雨天适用 —— 下雨天也有室内活动可玩
        if (filterKey === 'rainy') return profile.rainFriendly;
        // food: 美食之城 —— 美食丰富度高
        if (filterKey === 'food') return profile.foodFriendly;
        return true;
      });
    });
  }, [cities, selectedQuickFilters]);

  // useMemo —— 从过滤后的城市中提取用户选中的对比城市（最多 3 个）
  // 缓存内容：对比面板中展示的城市对象数组
  // 重新计算时机：compareCityIds 或 filteredCities 变化时
  // slice(0, 3) 确保最多只取 3 个城市用于对比
  const compareCities = useMemo(
    () => filteredCities.filter((city) => compareCityIds.includes(city.id)).slice(0, 3),
    [compareCityIds, filteredCities]
  );

  // useMemo —— 从城市列表中提取用户收藏的城市
  // 缓存内容：收藏的城市对象数组
  // 重新计算时机：cities 或 favoriteCityIds 变化时
  const favoriteCities = useMemo(() => cities.filter((city) => favoriteCityIds.includes(city.id)), [cities, favoriteCityIds]);

  // useMemo —— 截取当前可见数量的城市（分页展示逻辑）
  // 缓存内容：当前页面应该显示的城市数组
  // 重新计算时机：filteredCities 或 visibleCityCount 变化时
  // 场景举例：filteredCities 有 100 个城市，visibleCityCount 为 24，则只展示前 24 个
  const displayedCities = useMemo(() => filteredCities.slice(0, visibleCityCount), [filteredCities, visibleCityCount]);

  // useMemo —— 拼接当前筛选条件的摘要文本，显示在页面顶部
  // 缓存内容：拼接好的摘要字符串
  // 重新计算时机：selectedQuickFilters、selectedRegion、selectedTags 任一变化时
  // 场景举例：选中"华东"地区 + "美食之城"标签 + "周末游"快捷筛选
  //   → 输出 "华东 / 美食之城 / 周末游"
  //   没有任何筛选时 → 输出 "全部真实策展城市"
  const summaryText = useMemo(() => {
    // segments 数组用于收集各个筛选维度的文本，最后用 " / " 连接
    const segments: string[] = [];
    if (selectedRegion) segments.push(selectedRegion);
    if (selectedTags.length > 0) segments.push(selectedTags.join(' / '));
    if (selectedQuickFilters.length > 0) {
      // getQuickFilterLabel 将快捷筛选键转为中文标签（如 'weekend' → '周末游'）
      segments.push(selectedQuickFilters.map((key) => getQuickFilterLabel(key)).join(' / '));
    }
    return segments.length > 0 ? segments.join(' / ') : '全部真实策展城市';
  }, [selectedQuickFilters, selectedRegion, selectedTags]);

  // 当前查看详情的城市画像（如果有打开的详情）
  // 三元运算符：条件 ? 值1 : 值2，条件为真取值1，否则取值2
  const activeDetailProfile = activeCityDetail ? buildCityProfile(activeCityDetail) : null;

  // 【核心】打开城市详情 —— 点击城市卡片时调用
  // 业务流程：请求后端获取城市完整数据 → 设置详情状态 → 打开抽屉
  async function openCityDetail(cityId: string) {
    try {
      const detail = await cityClient.getCityDetail(cityId);
      setActiveCityDetail(detail);
      setIsDetailOpen(true);
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : '加载城市详情失败');
    }
  }

  // 切换快捷筛选项的选中状态
  // setSelectedQuickFilters 使用函数式更新（接收前一个值 previous），避免状态竞争问题
  // 场景举例：用户点击"周末游"标签 → 如果已选中则取消，未选中则添加
  function toggleQuickFilter(filterKey: QuickFilterKey) {
    setSelectedQuickFilters((previous) =>
      previous.includes(filterKey) ? previous.filter((item) => item !== filterKey) : [...previous, filterKey]
    );
  }

  // 【核心】切换城市对比选中状态
  // 业务逻辑：
  //   - 如果城市已选中 → 取消选中（从列表中移除）
  //   - 如果城市未选中且已有 3 个 → 移除最早选中的，添加新的（FIFO 队列）
  //   - 如果城市未选中且不足 3 个 → 直接添加
  // 场景举例：用户依次选中了成都、重庆、西安（3个），再点昆明 → 成都被移除，变为重庆、西安、昆明
  function toggleCompareCity(cityId: string) {
    setCompareCityIds((previous) => {
      if (previous.includes(cityId)) return previous.filter((item) => item !== cityId);
      if (previous.length >= 3) return [...previous.slice(1), cityId];
      return [...previous, cityId];
    });
  }

  // 切换城市收藏状态（简单的添加/移除逻辑）
  function toggleFavoriteCity(cityId: string) {
    setFavoriteCityIds((previous) =>
      previous.includes(cityId) ? previous.filter((item) => item !== cityId) : [...previous, cityId]
    );
  }

  // return 语句返回组件的 UI 结构（JSX 语法，类似 HTML 但可以嵌入 JavaScript 表达式）
  return (
    <div style={{ margin: '0 16px 16px' }}>
      {/* 外层卡片容器，提供圆角、渐变背景和阴影效果 */}
      <Card
        style={{
          borderRadius: 24,
          border: '1px solid rgba(15, 23, 42, 0.1)',
          // 多层径向渐变 + 线性渐变叠加，营造视觉层次感
          background:
            'radial-gradient(circle at 12% 0%, rgba(14,165,233,0.18), transparent 36%), radial-gradient(circle at 100% 100%, rgba(15,118,110,0.12), transparent 30%), linear-gradient(150deg, #ffffff 0%, #f8fbff 44%, #eef6ff 100%)',
          overflow: 'hidden',
          boxShadow: '0 16px 42px rgba(15, 23, 42, 0.08)',
        }}
        styles={{ body: { padding: 22, position: 'relative' } }}
      >
        {/* 装饰性背景光斑层（pointerEvents: none 确保不影响鼠标点击） */}
        <div
          style={{
            pointerEvents: 'none',
            position: 'absolute',
            inset: 0,
            overflow: 'hidden',
          }}
        >
          {/* 右上角蓝色光斑装饰 */}
          <div
            style={{
              position: 'absolute',
              width: 320,
              height: 320,
              borderRadius: '50%',
              right: -120,
              top: -130,
              background: 'radial-gradient(circle, rgba(3, 105, 161, 0.16) 0%, transparent 68%)',
            }}
          />
          {/* 左下角绿色光斑装饰 */}
          <div
            style={{
              position: 'absolute',
              width: 260,
              height: 260,
              borderRadius: '50%',
              left: -100,
              bottom: -120,
              background: 'radial-gradient(circle, rgba(15, 118, 110, 0.14) 0%, transparent 70%)',
            }}
          />
        </div>

        {/* 主内容区域，使用 CSS Grid 布局，zIndex: 1 确保在装饰层之上 */}
        <div style={{ display: 'grid', gap: 16, position: 'relative', zIndex: 1 }}>
          {/* 顶部英雄区：展示标题、摘要文本、收藏和对比城市 */}
          <CityExplorerHero
            compareCities={compareCities}
            favoriteCities={favoriteCities}
            onUsePrompt={onUsePrompt}
            summaryText={summaryText}
          />

          {/* 筛选栏：地区选择、标签选择、快捷筛选按钮 */}
          <CityExplorerFilterBar
            isFilterLoading={isFilterLoading}
            onUsePrompt={onUsePrompt}
            regions={regions}
            selectedQuickFilters={selectedQuickFilters}
            selectedRegion={selectedRegion}
            selectedTags={selectedTags}
            tags={tags}
            toggleQuickFilter={toggleQuickFilter}
            setSelectedRegion={setSelectedRegion}
            setSelectedTags={setSelectedTags}
          />

          {/* 城市对比面板：当用户选中对比城市时显示 */}
          <CityExplorerComparePanel
            compareCities={compareCities}
            onClearCompare={() => setCompareCityIds([])}
            onUsePrompt={onUsePrompt}
          />

          {/* 【核心】城市卡片网格：展示城市列表、加载更多、错误提示 */}
          <CityExplorerGrid
            compareCityIds={compareCityIds}
            displayedCities={displayedCities}
            error={error}
            favoriteCityIds={favoriteCityIds}
            filteredCities={filteredCities}
            initialVisibleCityCount={initialVisibleCityCount}
            isLoading={isLoading}
            loadMoreCityCount={loadMoreCityCount}
            onOpenCityDetail={openCityDetail}
            onToggleCompareCity={toggleCompareCity}
            onToggleFavoriteCity={toggleFavoriteCity}
            onUsePrompt={onUsePrompt}
            setVisibleCityCount={setVisibleCityCount}
            visibleCityCount={visibleCityCount}
          />
        </div>
      </Card>

      {/* 城市详情抽屉：侧滑展示城市的完整信息 */}
      <CityExplorerDetailDrawer
        activeCityDetail={activeCityDetail}
        activeDetailProfile={activeDetailProfile}
        favoriteCities={favoriteCities}
        isDetailOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        onUsePrompt={onUsePrompt}
      />
    </div>
  );
}
