"""
自我反思模块

提供 Agent 自我反思、总结改进能力。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class ReflectionResult:
    """反思结果"""
    summary: str
    insights: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    confidence: float = 0.0


class SelfReflector:
    """自我反思器

    特性：
    - 对话总结
    - 经验提取
    - 改进建议
    - LLM 增强反思
    """

    def __init__(self, llm_client: Any = None):
        """
        初始化自我反思器

        Args:
            llm_client: 可选的 LLM 客户端
        """
        self._llm_client = llm_client
        self._history: List[Dict] = []
        logger.info("SelfReflector initialized")

    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self._llm_client = llm_client

    async def reflect(
        self,
        conversation_history: List[Dict],
        context: Dict = None
    ) -> ReflectionResult:
        """进行反思

        Args:
            conversation_history: 对话历史
            context: 上下文信息

        Returns:
            反思结果
        """
        # 如果有 LLM，使用 LLM 进行反思
        if self._llm_client:
            return await self._reflect_with_llm(conversation_history, context)

        # 回退到规则反思
        return self._reflect_with_rules(conversation_history)

    async def _reflect_with_llm(
        self,
        conversation_history: List[Dict],
        context: Dict
    ) -> ReflectionResult:
        """使用 LLM 进行反思

        Args:
            conversation_history: 对话历史
            context: 上下文

        Returns:
            反思结果
        """
        try:
            # 提取对话内容
            messages = []
            for msg in conversation_history[-10:]:  # 最近10条
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    messages.append(f"{role}: {content[:100]}...")

            history_text = "\n".join(messages)
            context_str = json.dumps(context or {}, ensure_ascii=False)

            system_prompt = """你是一个专业的旅游助手反思专家。根据对话历史，进行深度反思和总结。

反思要点：
1. 用户的主要需求和意图
2. 对话中的关键信息
3. 可以改进的地方
4. 总结经验教训"""

            user_prompt = f"""对话历史：
{history_text}

上下文：{context_str}

请以 JSON 格式返回反思结果：
{{
    "summary": "对话总结",
    "insights": ["洞察1", "洞察2"],
    "improvements": ["改进1", "改进2"],
    "confidence": 0.0-1.0
}}

只返回 JSON。"""

            result = self._llm_client.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.5)

            if result.get("success"):
                content = result.get("content", "")
                try:
                    data = json.loads(content)
                    return ReflectionResult(
                        summary=data.get("summary", ""),
                        insights=data.get("insights", []),
                        improvements=data.get("improvements", []),
                        confidence=data.get("confidence", 0.5)
                    )
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM reflection response")

        except Exception as e:
            logger.warning(f"LLM reflection failed: {e}")

        return self._reflect_with_rules(conversation_history)

    def _reflect_with_rules(
        self,
        conversation_history: List[Dict]
    ) -> ReflectionResult:
        """使用规则进行反思

        Args:
            conversation_history: 对话历史

        Returns:
            反思结果
        """
        # 简单统计
        total_messages = len(conversation_history)
        user_messages = sum(1 for m in conversation_history if m.get("role") == "user")
        assistant_messages = total_messages - user_messages

        # 生成总结
        summary = f"对话共 {total_messages} 条消息，其中用户 {user_messages} 条，助手 {assistant_messages} 条。"

        return ReflectionResult(
            summary=summary,
            insights=["对话进行顺利"],
            improvements=["可以增加主动询问"],
            confidence=0.5
        )

    def add_to_history(self, reflection: ReflectionResult):
        """添加反思到历史

        Args:
            reflection: 反思结果
        """
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            "summary": reflection.summary,
            "insights": reflection.insights,
            "improvements": reflection.improvements
        })

    def get_insights(self) -> List[str]:
        """获取历史洞察

        Returns:
            洞察列表
        """
        insights = []
        for item in self._history[-5:]:
            insights.extend(item.get("insights", []))
        return insights


# 全局单例
self_reflector = SelfReflector()


class ExperienceLearner:
    """经验学习器

    特性：
    - 从交互中学习
    - 模式识别
    - 知识沉淀
    - 主动建议
    """

    def __init__(self, llm_client: Any = None):
        self._llm_client = llm_client
        self._patterns: Dict[str, List[Dict]] = {}
        self._knowledge_base: Dict[str, Any] = {}
        logger.info("ExperienceLearner initialized")

    def set_llm_client(self, llm_client):
        self._llm_client = llm_client

    async def learn_from_interaction(
        self,
        interaction: Dict,
        outcome: str = "success"
    ) -> Dict[str, Any]:
        """从交互中学习

        Args:
            interaction: 交互数据
            outcome: 交互结果 (success/failure)

        Returns:
            学习结果
        """
        if not self._llm_client:
            return self._learn_with_rules(interaction, outcome)

        return await self._learn_with_llm(interaction, outcome)

    async def _learn_with_llm(
        self,
        interaction: Dict,
        outcome: str
    ) -> Dict[str, Any]:
        """使用 LLM 学习"""
        try:
            import json
            prompt = f"""分析以下交互记录，提取可复用的模式和经验：

交互内容：{json.dumps(interaction, ensure_ascii=False)}
交互结果：{outcome}

请返回：
{{
    "patterns": ["模式1", "模式2"],
    "knowledge": {{"key": "value"}},
    "suggestions": ["建议1", "建议2"]
}}

只返回 JSON。"""

            result = self._llm_client.chat([
                {"role": "system", "content": "你是一个经验学习专家，善于从交互中提取模式"},
                {"role": "user", "content": prompt}
            ], temperature=0.3)

            if result.get("success"):
                data = json.loads(result.get("content", "{}"))
                return data

        except Exception as e:
            logger.warning(f"LLM learning failed: {e}")

        return self._learn_with_rules(interaction, outcome)

    def _learn_with_rules(
        self,
        interaction: Dict,
        outcome: str
    ) -> Dict[str, Any]:
        """使用规则学习"""
        intent = interaction.get("intent", "unknown")
        if intent not in self._patterns:
            self._patterns[intent] = []
        self._patterns[intent].append({
            "outcome": outcome,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "patterns": [f"{intent} 交互模式"],
            "knowledge": {"learned": True},
            "suggestions": ["继续学习更多模式"]
        }

    def get_patterns(self, intent: str = None) -> List[Dict]:
        """获取模式"""
        if intent:
            return self._patterns.get(intent, [])
        return self._patterns

    def get_knowledge(self, topic: str = None) -> Any:
        """获取知识"""
        if topic:
            return self._knowledge_base.get(topic)
        return self._knowledge_base

    def add_knowledge(self, topic: str, knowledge: Any):
        """添加知识"""
        self._knowledge_base[topic] = knowledge
        logger.info(f"Added knowledge: {topic}")


class ReflectionScheduler:
    """反思调度器

    特性：
    - 定时反思
    - 事件触发
    - 周期性回顾
    """

    def __init__(self, reflector: SelfReflector = None):
        self._reflector = reflector or self_reflector
        self._scheduled_reflections: Dict[str, Dict] = {}
        logger.info("ReflectionScheduler initialized")

    def schedule_reflection(
        self,
        trigger: str,
        interval: int = 60,
        conditions: Dict = None
    ) -> str:
        """安排反思

        Args:
            trigger: 触发器名称
            interval: 间隔(分钟)
            conditions: 触发条件

        Returns:
            调度ID
        """
        schedule_id = f"schedule_{len(self._scheduled_reflections)}"
        self._scheduled_reflections[schedule_id] = {
            "trigger": trigger,
            "interval": interval,
            "conditions": conditions or {},
            "last_run": None,
            "enabled": True
        }
        logger.info(f"Scheduled reflection: {schedule_id}")
        return schedule_id

    def cancel_schedule(self, schedule_id: str):
        """取消调度"""
        if schedule_id in self._scheduled_reflections:
            self._scheduled_reflections[schedule_id]["enabled"] = False
            logger.info(f"Cancelled reflection schedule: {schedule_id}")

    def get_pending_schedules(self) -> List[Dict]:
        """获取待执行的调度"""
        pending = []
        for sid, schedule in self._scheduled_reflections.items():
            if schedule.get("enabled"):
                pending.append({
                    "schedule_id": sid,
                    "trigger": schedule["trigger"],
                    "interval": schedule["interval"]
                })
        return pending
