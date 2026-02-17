# Agent Memory 系统优化方案

本文档描述 Shuai-Travel-Agent 中记忆管理系统的优化方案，解决当前模块集成度低、功能分散的问题。

---

## 目录

- [当前问题分析](#当前问题分析)
- [优化架构设计](#优化架构设计)
- [核心组件设计](#核心组件设计)
- [数据流设计](#数据流设计)
- [实施路线图](#实施路线图)

---

## 当前问题分析

### 1.1 模块集成度低

当前 `agent/src/memory/` 包含 8 个文件、20+ 个类：

| 文件 | 类数量 | 实际使用情况 |
|------|--------|-------------|
| `manager.py` | 3 | TravelAgent 直接使用 |
| `redis_memory.py` | 1 | 可选，未强制集成 |
| `importance_scorer.py` | 4 | **未使用** |
| `eviction_manager.py` | 4 | **未使用** |
| `summarizer.py` | 4 | **未使用** |
| `user_profile.py` | 5 | **未使用** |
| `hierarchical_store.py` | 5 | **未使用** |
| `consolidation.py` | 4 | **未使用** |

**问题**: TravelAgent 仅使用了 `MemoryManager` 的基础功能（添加消息、获取历史、清除会话），其他 6 个高级模块完全未被集成调用。

### 1.2 记忆层次断裂

```
ReActTravelAgent
    │
    ├── ShortTermMemory (react_agent.py) ──┐
    │     ReAct 推理循环中的中间思考存储      │
    │                                      │
    └──────────────────────────────────────┤
                                           │
MemoryManager (manager.py)                 │
    │                                      │ 断裂！中间思考结果
    ├── conversation_history               │ 不会回流到主记忆
    ├── user_preference                   │
    ├── session_state                     │
    └── long_term_memory ─────────────────┘
           仅有基础归档，无智能检索
```

### 1.3 会话跨越问题

```
用户会话 1: "我喜欢去海边"
    └── preference.budget = None (未持久化)

用户会话 2: "推荐一个旅游地"
    └── 无法获取会话 1 的偏好
    └── 重新询问用户预算
```

**原因**: 用户偏好通过正则提取后仅存在当前会话 `MemoryManager.user_preference`，跨会话用户画像 `UserProfileStore` 从未被创建或查询。

### 1.4 Redis 与内存模式不统一

- `MemoryManager`: 纯内存模式
- `RedisMemoryManager`: Redis 后端模式
- API 签名不一致，切换成本高

### 1.5 上下文未压缩

长对话场景：
- 100 条消息，每条 ~100 tokens = 10,000 tokens
- 送入 LLM 时全部发送，API 成本高
- `ConversationSummarizer` 存在但从未调用

---

## 优化架构设计

### 2.1 引入 MemoryOrchestrator

新增统一协调器 `MemoryOrchestrator`，作为所有记忆操作的单一入口：

```
┌─────────────────────────────────────────────────────────────────┐
│                     TravelAgent (travel_agent.py)                 │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              MemoryOrchestrator (orchestrator.py)       │    │
│  │                                                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │    │
│  │  │ Importance   │  │   Eviction   │  │Conversation │ │    │
│  │  │   Scorer    │  │   Manager    │  │Summarizer   │ │    │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │    │
│  │                                                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │    │
│  │  │ UserProfile  │  │ Hierarchical │  │   Memory    │ │    │
│  │  │    Store     │  │MemoryStore   │  │Consolidator │ │    │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │    │
│  │                                                          │    │
│  │  ┌──────────────────────────────────────────────────┐   │    │
│  │  │              MemoryManager (基础存储)             │   │    │
│  │  │         (conversation_history + preferences)     │   │    │
│  │  └──────────────────────────────────────────────────┘   │    │
│  │                                                          │    │
│  │  ┌──────────────────────────────────────────────────┐   │    │
│  │  │      RedisMemoryManager (可选持久化后端)            │   │    │
│  │  └──────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 架构职责

| 组件 | 职责 | 状态 |
|------|------|------|
| **MemoryOrchestrator** | 统一入口，协调各子系统 | 新建 |
| **MemoryManager** | 短期对话历史，基础 CRUD | 复用 |
| **RedisMemoryManager** | Redis 持久化后端 | 复用 |
| **ImportanceScorer** | 消息重要性评分 | 集成 |
| **EvictionManager** | 基于重要性的智能淘汰 | 集成 |
| **ConversationSummarizer** | 上下文压缩，减少 token | 集成 |
| **UserProfileStore** | 跨会话用户画像 | 集成 |
| **HierarchicalMemoryStore** | 分层长期记忆存储 | 集成 |
| **MemoryConsolidator** | 记忆整合与遗忘 | 集成 |

---

## 核心组件设计

### 3.1 MemoryOrchestrator 接口

```python
class MemoryOrchestrator:
    """统一记忆协调器"""

    def __init__(
        self,
        config: Optional[Dict] = None,
        llm_client: Optional[Any] = None,
        use_redis: bool = False,
        redis_config: Optional[Dict] = None
    ):
        """初始化所有记忆子系统"""
        ...

    def add_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str
    ) -> Dict[str, Any]:
        """
        添加消息到记忆系统

        流程:
        1. 写入 MemoryManager.conversation_history
        2. 调用 ImportanceScorer 计算重要性
        3. 调用 EvictionManager 检查是否淘汰
        4. 更新 UserProfileStore 用户偏好
        5. 如启用 Redis 则同步
        """
        ...

    def get_context_for_llm(
        self,
        session_id: str,
        user_id: str,
        max_tokens: int = 2000
    ) -> List[Dict[str, Any]]:
        """
        获取 LLM 上下文字符串

        流程:
        1. 获取当前会话历史
        2. 调用 ConversationSummarizer 压缩
        3. 检索相关历史对话 (HierarchicalMemoryStore)
        4. 获取用户画像摘要 (UserProfileStore)
        5. 拼接返回
        """
        ...

    def get_user_preference(self, session_id: str, user_id: str) -> Dict:
        """
        获取用户偏好（合并当前会话 + 历史画像）
        """
        ...

    def end_session(self, session_id: str, user_id: str) -> Dict:
        """
        结束会话，触发归档流程

        流程:
        1. 生成会话摘要 (ConversationSummarizer)
        2. 存入分层存储 (HierarchicalMemoryStore)
        3. 合并用户偏好 (UserProfileStore)
        4. 触发记忆整合 (MemoryConsolidator)
        5. 归档到 MemoryManager.long_term_memory
        """
        ...

    def clear_session(self, session_id: str, archive: bool = True) -> None:
        """清除会话记忆"""
        ...

    def search_historical_context(
        self,
        user_id: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict]:
        """语义检索历史对话"""
        ...

    def get_memory_stats(self) -> Dict:
        """获取记忆系统统计"""
        ...
```

### 3.2 配置项

```yaml
# config/memory_config.yaml
memory:
  # 短期记忆配置
  max_working_memory: 50       # 最大对话消息数
  max_long_term_memory: 100    # 最大归档会话数

  # 重要性评分配置
  importance:
    enable: true
    threshold: 0.5            # 高重要性阈值
    dimensions: [keyword, intent, sentiment, decision, preference]

  # 智能淘汰配置
  eviction:
    enable: true
    strategy: hybrid           # fifo/lfu/lru/priority/hybrid
    max_size: 30
    min_importance: 0.2

  # 摘要配置
  summarization:
    enable: true
    max_tokens: 2000         # 压缩后最大 token
    compression_level: moderate  # light/moderate/aggressive

  # 用户画像配置
  user_profile:
    enable: true
    storage_path: "data/user_profiles.json"

  # 分层存储配置
  hierarchical:
    enable: true
    hot_size: 10              # 热存储容量
    warm_size: 50            # 温存储容量

  # 记忆整合配置
  consolidation:
    enable: true
    interval_hours: 24       # 自动整合间隔
    similarity_threshold: 0.3
    min_importance: 0.2

  # Redis 配置 (可选)
  redis:
    enable: false
    host: "localhost"
    port: 6379
    db: 0
    ttl: 86400              # 消息过期时间 (秒)
```

---

## 数据流设计

### 4.1 消息添加流程

```
用户消息
    │
    ▼
┌─────────────────────┐
│ MemoryOrchestrator │
│   .add_message()   │
└──────────┬──────────┘
           │
           ├── 1. MemoryManager.add_message()
           │     └─→ conversation_history (deque)
           │
           ├── 2. ImportanceScorer.score()
           │     └─→ importance_score (0-1)
           │
           ├── 3. EvictionManager.add()
           │     └─→ 触发淘汰检查，低分消息移出
           │
           ├── 4. UserProfileStore.merge_preferences()
           │     └─→ 从消息中提取偏好，更新画像
           │
           └── 5. RedisMemoryManager (如启用)
                 └─→ 同步到 Redis
```

### 4.2 上下文构建流程

```
LLM 请求上下文
    │
    ▼
┌─────────────────────────────┐
│ MemoryOrchestrator         │
│ .get_context_for_llm()     │
└─────────────┬─────────────┘
              │
              ├── 1. MemoryManager.get_conversation_history()
              │     └─→ 当前会话消息列表
              │
              ├── 2. ConversationSummarizer.compress()
              │     └─→ 按重要性压缩到 max_tokens
              │
              ├── 3. HierarchicalMemoryStore.retrieve_context()
              │     └─→ 相关历史对话 (语义检索)
              │
              ├── 4. UserProfileStore.get_context_for_llm()
              │     └─→ 用户画像摘要
              │
              └── 5. 拼接返回
                    └─→ [system_msg, ...history, user_msg]
```

### 4.3 会话结束流程

```
会话结束 / 新会话开始
    │
    ▼
┌─────────────────────────┐
│ MemoryOrchestrator      │
│   .end_session()        │
└───────────┬─────────────┘
            │
            ├── 1. ConversationSummarizer.summarize()
            │     └─→ 生成会话摘要
            │
            ├── 2. HierarchicalMemoryStore.store_session()
            │     └─→ 存入 COLD 层
            │
            ├── 3. UserProfileStore.merge_preferences()
            │     └─→ 合并到长期用户画像
            │
            ├── 4. MemoryConsolidator.run_scheduled_consolidation()
            │     └─→ 聚类、合并、低重要性遗忘
            │
            └── 5. MemoryManager.archive_current_session()
                  └─→ 归档到 long_term_memory
```

---

## 实施路线图

### 阶段一：设计文档（已完成）

- [x] 问题分析
- [x] 架构设计
- [x] 数据流设计

### 阶段二：核心实现

| 序号 | 任务 | 文件 | 状态 |
|------|------|------|------|
| 1 | 创建 MemoryOrchestrator | `orchestrator.py` | 已实现 |
| 2 | 添加模块导出 | `__init__.py` | 已实现 |
| 3 | 添加工厂方法 | `factory.py` | 已实现 |

### 阶段三：集成改造

| 序号 | 任务 | 文件 | 状态 |
|------|------|------|------|
| 4 | 改造 TravelAgent | `travel_agent.py` | 已实现 |
| 5 | 添加配置加载 | `config_manager.py` | 待实现 |

### 阶段四：测试验证

| 序号 | 任务 | 说明 |
|------|------|------|
| 6 | 单元测试 | orchestrator 单元测试 |
| 7 | 集成测试 | TravelAgent 端到端测试 |
| 8 | 性能测试 | 长对话 token 消耗对比 |

---

## 附录 A：短期记忆详细设计

### A.1 工作记忆层次

```
工作记忆 (Working Memory)
│
├── 即时记忆 (Immediate Memory)
│   ├── 存储内容: 当前正在处理的单个 thought/action
│   ├── 容量: 1-3 条
│   ├── 生命周期: 单次推理循环内
│   └── 特点: 高速访问，无需持久化
│
├── 循环记忆 (Episodic Memory)
│   ├── 存储内容: ReAct 推理循环中的所有中间步骤
│   ├── 容量: max_steps (默认 10)
│   ├── 生命周期: ReAct 循环结束
│   └── 特点: 记录完整推理过程
│
└── 会话记忆 (Conversational Memory)
    ├── 存储内容: 当前会话的所有消息
    ├── 容量: max_working_memory (默认 50)
    ├── 生命周期: 会话结束
    └── 特点: 可被 LLM 上下文访问
```

### A.2 注意力窗口 (Attention Window)

```python
class AttentionWindow:
    """
    注意力窗口 - 决定哪些记忆被 LLM 关注

    核心思想：不是所有记忆都同等重要
    - 位置编码: 越新的记忆越重要
    - 重要性编码: 高分记忆优先
    - 相关性编码: 与当前任务相关的记忆优先
    """

    def __init__(
        self,
        window_size: int = 10,
        recency_weight: float = 0.3,
        importance_weight: float = 0.4,
        relevance_weight: float = 0.3
    ):
        self.window_size = window_size
        self.weights = {
            "recency": recency_weight,
            "importance": importance_weight,
            "relevance": relevance_weight
        }

    def compute_attention(
        self,
        messages: List[Dict],
        current_query: str
    ) -> List[float]:
        """计算每条消息的注意力分数"""
        scores = []
        for i, msg in enumerate(messages):
            # 1. 位置分数 (越新越高)
            recency = (i + 1) / len(messages)

            # 2. 重要性分数
            importance = msg.get("importance", 0.5)

            # 3. 相关性分数 (关键词重叠)
            relevance = self._compute_relevance(
                msg.get("content", ""),
                current_query
            )

            # 加权求和
            total = (
                self.weights["recency"] * recency +
                self.weights["importance"] * importance +
                self.weights["relevance"] * relevance
            )
            scores.append(total)

        # Softmax 归一化
        exp_scores = [math.exp(s) for s in scores]
        sum_exp = sum(exp_scores)
        return [e / sum_exp for e in exp_scores]

    def _compute_relevance(self, content: str, query: str) -> float:
        """计算内容与查询的相关性"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        overlap = len(query_words & content_words)
        return min(overlap / max(len(query_words), 1), 1.0)
```

### A.3 反思机制 (Reflection)

```python
class ReflectionMechanism:
    """
    反思机制 - 从经验中提取高层次信息

    触发条件:
    - 每 N 条消息后 (trigger_interval)
    - 会话结束时
    - 用户明确要求时
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        trigger_interval: int = 10
    ):
        self.llm_client = llm_client
        self.trigger_interval = trigger_interval

    async def reflect(
        self,
        conversation_history: List[Dict]
    ) -> Dict[str, Any]:
        """
        执行反思

        Returns:
            {
                "key_insights": [...],      # 关键洞察
                "user_intents": [...],      # 用户意图模式
                "knowledge_gaps": [...],    # 知识缺口
                "successful_actions": [...]  # 成功行动
            }
        """
        if not self.llm_client or len(conversation_history) < 5:
            return self._rule_based_reflect(conversation_history)

        prompt = self._build_reflection_prompt(conversation_history)
        response = await self.llm_client.chat(prompt)
        return self._parse_reflection(response)

    def should_reflect(self, message_count: int) -> bool:
        """判断是否应该触发反思"""
        return message_count % self.trigger_interval == 0
```

### A.4 智能淘汰策略

```python
class SmartEvictionPolicy:
    """
    智能淘汰策略 - 基于多维度决策

    淘汰考虑因素:
    1. 重要性分数 (Importance Score)
    2. 时间衰减 (Time Decay)
    3. 访问频率 (Access Frequency)
    4. 任务相关性 (Task Relevance)
    """

    def __init__(self, config: Dict):
        self.config = config

    def compute_priority(self, msg: Dict) -> float:
        """计算消息优先级"""
        # 重要性分数 (0.4)
        importance = msg.get("importance", 0.5)

        # 时间衰减 (0.3)
        msg_time = datetime.fromisoformat(msg.get("timestamp", ""))
        hours_old = (datetime.now() - msg_time).total_seconds() / 3600
        time_score = math.exp(-hours_old / 24)

        # 访问频率 (0.3)
        access_score = min(msg.get("access_count", 1) / 10, 1.0)

        return 0.4 * importance + 0.3 * time_score + 0.3 * access_score
```

---

## 附录 B：长期记忆详细设计

### B.1 分层存储架构

```
长期记忆分层 (Long-term Memory)
│
├── HOT 层 (活跃会话)
│   ├── 存储: 最近活跃的会话
│   ├── 容量: hot_size (默认 10)
│   ├── 淘汰策略: LRU
│   └── 检索速度: 内存级 (最快)
│
├── WARM 层 (用户画像)
│   ├── 存储: 用户 profiles, preferences
│   ├── 容量: warm_size (默认 50)
│   ├── 淘汰策略: 最近最少更新
│   └── 检索速度: 内存 + 索引
│
├── COLD 层 (归档会话)
│   ├── 存储: 历史会话 (带摘要)
│   ├── 容量: cold_size (默认 1000)
│   ├── 淘汰策略: 最低重要性 + 最老
│   └── 检索速度: 向量相似度
│
└── ARCHIVE 层 (冷存储)
    ├── 存储: 极老的会话 (仅摘要)
    ├── 容量: 无限制
    ├── 淘汰策略: 手动触发
    └── 检索速度: 关键词 (最慢)
```

### B.2 对话向量化

```python
class ConversationVectorizer:
    """
    对话向量化 - 将对话转换为向量

    用途:
    - 语义相似度检索
    - 相关对话推荐
    - 上下文补全
    """

    async def vectorize_session(
        self,
        session: SessionData
    ) -> np.ndarray:
        """
        策略: 多粒度向量化
        - 会话摘要向量 (粗粒度)
        - 关键事实向量 (细粒度)
        - 用户画像向量 (抽象)
        """
        vectors = []

        # 摘要向量
        summary_vec = await self._embed(session.summary)
        vectors.append(summary_vec)

        # 关键事实向量
        if session.key_facts:
            facts_text = " | ".join(session.key_facts)
            facts_vec = await self._embed(facts_text)
            vectors.append(facts_vec)

        # 用户偏好向量
        if session.user_preferences:
            pref_text = self._serialize_preferences(session.user_preferences)
            pref_vec = await self._embed(pref_text)
            vectors.append(pref_vec)

        # 加权平均
        return np.mean(vectors, axis=0)
```

### B.3 用户画像系统

```python
class UserProfile:
    """
    用户画像 - 多维度用户特征

    维度:
    - 基础属性: 年龄、性别、职业
    - 旅行偏好: 目的地、季节、预算
    - 行为模式: 活跃时间、交互风格
    - 知识状态: 已了解、感兴趣
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.travel_preferences = {
            "favorite_regions": [],
            "favorite_cities": [],
            "budget_range": None,
            "preferred_duration": None,
            "travel_companion": None,
        }
        self.interest_tags: List[str] = []
        self.knowledge_state = {
            "visited_cities": [],
            "interested_cities": [],
        }

    def merge_from_conversation(self, messages: List[Dict]) -> None:
        """从对话中提取并合并用户画像"""
        for msg in messages:
            if msg["role"] != "user":
                continue
            content = msg["content"]

            # 提取目的地
            destinations = self._extract_destinations(content)
            self.travel_preferences["favorite_cities"].extend(destinations)

            # 提取预算
            budget = self._extract_budget(content)
            if budget:
                self.travel_preferences["budget_range"] = budget

    def to_context_string(self) -> str:
        """转换为上下文字符串"""
        parts = []
        if self.travel_preferences["favorite_cities"]:
            parts.append(f"喜欢去: {', '.join(self.travel_preferences['favorite_cities'][:3])}")
        if self.travel_preferences["budget_range"]:
            parts.append(f"预算: {self.travel_preferences['budget_range']}")
        return " | ".join(parts) if parts else "暂无偏好信息"
```

---

## 附录 C：长短记忆交互机制

### C.1 记忆回流

```
┌─────────────────────────────────────────────────────────────────┐
│                    记忆生命周期循环                                 │
│                                                                  │
│  ┌──────────┐    添加     ┌──────────┐    反思     ┌─────────┐ │
│  │ 工作记忆  │ ────────→ │ 短期记忆  │ ────────→ │ 长期记忆 │ │
│  │ (ReAct)  │            │(会话级)   │            │(归档)   │ │
│  └──────────┘            └──────────┘            └─────────┘ │
│       ↑                                                │        │
│       │             检索                              │        │
│       └───────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

**回流触发条件**:
1. **阈值触发**: 重要性超过 0.7
2. **频率触发**: 同一话题出现 3 次以上
3. **时间触发**: 会话结束
4. **手动触发**: 用户明确要求

### C.2 记忆检索增强 (RAG)

```python
class ContextAwareMemoryRetrieval:
    """
    上下文感知的记忆检索

    检索策略:
    1. 当前任务上下文匹配
    2. 用户画像偏好匹配
    3. 时间相关性
    4. 多样性 (避免相似结果重复)
    """

    async def retrieve(
        self,
        session_id: str,
        user_id: str,
        current_query: str,
        top_k: int = 3
    ) -> List[RetrievedMemory]:
        # 1. 获取用户画像
        profile = self.profile_store.get(user_id)

        # 2. 扩展查询 (融入用户偏好)
        expanded_query = self._expand_query(current_query, profile)

        # 3. 多路检索 (语义 + 偏好 + 时间)
        results = await self._multi_way_search(
            expanded_query,
            profile,
            top_k
        )

        # 4. RRF 重排序
        return self._rerank(results, top_k)

    def _expand_query(self, query: str, profile) -> str:
        """扩展查询，融入用户画像"""
        user_context = profile.to_context_string() if profile else ""
        return f"{query} [用户偏好: {user_context}]" if user_context else query
```

---

## 相关文件索引

### 核心协调器
| 文件 | 说明 |
|------|------|
| [agent/src/memory/orchestrator.py](agent/src/memory/orchestrator.py) | 统一记忆协调器 (已实现) |
| [agent/src/memory/factory.py](agent/src/memory/factory.py) | 记忆工厂方法 |

### 存储层
| 文件 | 说明 |
|------|------|
| [agent/src/memory/manager.py](agent/src/memory/manager.py) | 基础记忆管理 |
| [agent/src/memory/redis_memory.py](agent/src/memory/redis_memory.py) | Redis 后端 |
| [agent/src/memory/hierarchical_store.py](agent/src/memory/hierarchical_store.py) | 分层存储 |

### 短期记忆 (v2.2 新增)
| 文件 | 说明 |
|------|------|
| [agent/src/memory/attention.py](agent/src/memory/attention.py) | 注意力窗口 (已实现) |
| [agent/src/memory/reflection.py](agent/src/memory/reflection.py) | 反思机制 (已实现) |
| [agent/src/memory/eviction_policy.py](agent/src/memory/eviction_policy.py) | 智能淘汰策略 (已实现) |
| [agent/src/memory/importance_scorer.py](agent/src/memory/importance_scorer.py) | 重要性评分 |
| [agent/src/memory/eviction_manager.py](agent/src/memory/eviction_manager.py) | 淘汰管理器 |

### 长期记忆 (v2.2 新增)
| 文件 | 说明 |
|------|------|
| [agent/src/memory/vectorizer.py](agent/src/memory/vectorizer.py) | 对话向量化 (已实现) |
| [agent/src/memory/user_profile.py](agent/src/memory/user_profile.py) | 用户画像 |
| [agent/src/memory/summarizer.py](agent/src/memory/summarizer.py) | 对话摘要 |

### 长短交互 (v2.2 新增)
| 文件 | 说明 |
|------|------|
| [agent/src/memory/recirculation.py](agent/src/memory/recirculation.py) | 记忆回流 (已实现) |
| [agent/src/memory/retrieval.py](agent/src/memory/retrieval.py) | 上下文检索 (已实现) |
| [agent/src/memory/consolidation.py](agent/src/memory/consolidation.py) | 记忆整合 |

### 集成
| 文件 | 说明 |
|------|------|
| [agent/src/core/travel_agent.py](agent/src/core/travel_agent.py) | TravelAgent 入口 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构文档 |
