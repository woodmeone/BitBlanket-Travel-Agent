"""
对话策略管理器

提供对话动作选择、意图澄清判断、对话状态管理和闲聊触发功能。
支持基于规则和 LLM 的智能对话策略。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class DialogueAction(Enum):
    """对话动作"""
    RESPOND = "respond"           # 直接回复
    CLARIFY = "clarify"           # 澄清意图
    CONFIRM = "confirm"            # 确认信息
    ASK_MORE = "ask_more"          # 询问更多信息
    CHITCHAT = "chitchat"          # 闲聊
    END_SESSION = "end_session"    # 结束会话


class DialogueState(Enum):
    """对话状态"""
    INITIAL = "initial"           # 初始
    UNDERSTANDING = "understanding" # 理解中
    EXECUTING = "executing"       # 执行中
    RESPONDING = "responding"     # 回复中
    WAITING_CLARIFICATION = "waiting_clarification"  # 等待澄清
    COMPLETED = "completed"        # 完成


@dataclass
class ClarificationRequest:
    """澄清请求"""
    param_name: str
    question: str
    options: List[str] = field(default_factory=list)
    required: bool = True


@dataclass
class DialogueContext:
    """对话上下文"""
    session_id: str
    user_id: str
    state: DialogueState = DialogueState.INITIAL
    current_intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    missing_params: List[str] = field(default_factory=list)
    clarifications: List[ClarificationRequest] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DialoguePolicy:
    """对话策略管理器

    特性：
    - 动作选择策略
    - 意图澄清判断
    - 对话状态管理
    - 闲聊触发
    - LLM 增强的意图澄清
    """

    # 闲聊触发关键词
    CHITCHAT_TRIGGERS = {
        "你好", "hello", "hi", "在吗",
        "天气", "今天", "最近", "怎么样",
        "谢谢", "再见", "bye", "886"
    }

    # 需要澄清的意图及必填参数
    INTENT_REQUIRES_CLARIFICATION = {
        "plan_trip": ["destination", "dates"],
        "book_hotel": ["checkin", "checkout"],
        "find_restaurant": ["cuisine", "budget"],
        "travel_planning": ["city", "days"],
        "route_planning": ["city", "days"],
    }

    def __init__(self, llm_client: Any = None):
        """
        初始化对话策略管理器

        Args:
            llm_client: 可选的 LLM 客户端，用于智能澄清
        """
        self._contexts: Dict[str, DialogueContext] = {}
        self._llm_client = llm_client
        logger.info("DialoguePolicy initialized")

    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self._llm_client = llm_client

    def get_context(self, session_id: str, user_id: str = "") -> DialogueContext:
        """获取对话上下文

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            对话上下文
        """
        if session_id not in self._contexts:
            self._contexts[session_id] = DialogueContext(
                session_id=session_id,
                user_id=user_id
            )
        else:
            # 更新 user_id
            if user_id:
                self._contexts[session_id].user_id = user_id

        return self._contexts[session_id]

    def select_action(
        self,
        context: DialogueContext,
        intent: Optional[str] = None,
        entities: Optional[Dict] = None
    ) -> DialogueAction:
        """选择对话动作

        Args:
            context: 对话上下文
            intent: 识别的意图
            entities: 实体信息

        Returns:
            选择的动作
        """
        # 更新上下文
        if intent:
            context.current_intent = intent
        if entities:
            context.entities.update(entities)

        # 检查是否需要澄清
        if intent in self.INTENT_REQUIRES_CLARIFICATION:
            required_params = self.INTENT_REQUIRES_CLARIFICATION[intent]
            missing = [p for p in required_params if p not in context.entities]
            if missing:
                context.missing_params = missing
                context.state = DialogueState.WAITING_CLARIFICATION
                return DialogueAction.CLARIFY

        # 检查是否需要确认
        if self._should_confirm(context):
            return DialogueAction.CONFIRM

        # 检查是否闲聊
        if self.should_chitchat(context):
            return DialogueAction.CHITCHAT

        # 检查是否需要更多信息
        if self._needs_more_info(context):
            return DialogueAction.ASK_MORE

        # 默认直接回复
        context.state = DialogueState.RESPONDING
        return DialogueAction.RESPOND

    def select_action_with_llm(
        self,
        context: DialogueContext,
        intent: Optional[str] = None,
        entities: Optional[Dict] = None,
        user_query: str = ""
    ) -> DialogueAction:
        """使用 LLM 选择对话动作

        Args:
            context: 对话上下文
            intent: 识别的意图
            entities: 实体信息
            user_query: 用户原始查询

        Returns:
            选择的动作
        """
        # 如果没有 LLM，回退到规则
        if not self._llm_client:
            return self.select_action(context, intent, entities)

        try:
            # 构建上下文信息
            context_info = {
                "current_intent": intent,
                "entities": entities,
                "missing_params": context.missing_params,
                "history_length": len(context.history),
                "current_state": context.state.value
            }

            system_prompt = """你是一个智能对话策略专家。根据对话上下文，判断应该采取什么动作。

可能的动作：
- respond: 直接回复用户
- clarify: 需要澄清用户意图
- confirm: 需要确认信息
- ask_more: 需要获取更多信息
- chitchat: 闲聊/寒暄
- end_session: 结束会话"""

            user_prompt = f"""用户查询：{user_query}
当前上下文：{json.dumps(context_info, ensure_ascii=False)}

请以 JSON 格式返回你的决策：
{{
    "action": "动作名称",
    "reason": "决策原因",
    "clarification_question": "如果需要澄清，给出问题"
}}

只返回 JSON。"""

            result = self._llm_client.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.3)

            if result.get("success"):
                content = result.get("content", "")
                try:
                    data = json.loads(content)
                    action_str = data.get("action", "respond")
                    # 解析动作
                    for action in DialogueAction:
                        if action.value == action_str:
                            # 如果需要澄清，更新上下文
                            if action == DialogueAction.CLARIFY:
                                question = data.get("clarification_question", "")
                                if question:
                                    context.clarifications = [
                                        ClarificationRequest(
                                            param_name="unknown",
                                            question=question
                                        )
                                    ]
                            return action
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM dialogue policy response")

        except Exception as e:
            logger.warning(f"LLM dialogue policy failed: {e}")

        # LLM 失败，回退到规则
        return self.select_action(context, intent, entities)

    def should_clarify(
        self,
        intent: str,
        entities: Dict[str, Any]
    ) -> List[ClarificationRequest]:
        """判断是否需要澄清

        Args:
            intent: 意图
            entities: 已提取的实体

        Returns:
            澄清请求列表
        """
        if intent not in self.INTENT_REQUIRES_CLARIFICATION:
            return []

        required = self.INTENT_REQUIRES_CLARIFICATION[intent]
        clarifications = []

        for param in required:
            if param not in entities:
                question = self._generate_clarification_question(intent, param)
                clarifications.append(ClarificationRequest(
                    param_name=param,
                    question=question,
                    required=True
                ))

        return clarifications

    def should_chitchat(self, context: DialogueContext) -> bool:
        """判断是否闲聊

        Args:
            context: 对话上下文

        Returns:
            是否闲聊
        """
        # 基于历史对话密度
        if len(context.history) < 2:
            return False

        # 基于用户输入
        last_user_input = ""
        for msg in reversed(context.history):
            if msg.get("role") == "user":
                last_user_input = msg.get("content", "").lower()
                break

        # 检查触发词
        for trigger in self.CHITCHAT_TRIGGERS:
            if trigger in last_user_input:
                return True

        return False

    def _should_confirm(self, context: DialogueContext) -> bool:
        """判断是否需要确认"""
        # 高价值操作需要确认
        high_value_actions = {"book", "reserve", "payment", "order"}
        intent = context.current_intent or ""

        return any(action in intent.lower() for action in high_value_actions)

    def _needs_more_info(self, context: DialogueContext) -> bool:
        """判断是否需要更多信息"""
        # 如果有未澄清的参数
        if context.missing_params:
            return True

        # 如果实体信息不完整
        if context.current_intent:
            required = self.INTENT_REQUIRES_CLARIFICATION.get(context.current_intent, [])
            provided = list(context.entities.keys())
            missing = [p for p in required if p not in provided]
            return len(missing) > 2  # 缺少超过2个参数

        return False

    def _generate_clarification_question(
        self,
        intent: str,
        param: str
    ) -> str:
        """生成澄清问题"""
        questions = {
            ("plan_trip", "destination"): "您想去哪个城市旅游呢?",
            ("plan_trip", "dates"): "您计划什么时候出发，呆几天?",
            ("book_hotel", "checkin"): "您计划什么时候入住?",
            ("book_hotel", "checkout"): "您计划什么时候退房?",
            ("find_restaurant", "cuisine"): "您想吃什么类型的菜呢?",
            ("find_restaurant", "budget"): "您的预算是多少?",
            ("travel_planning", "city"): "您想去哪个城市游玩?",
            ("travel_planning", "days"): "您计划玩几天?",
            ("route_planning", "city"): "您想去哪个城市?",
            ("route_planning", "days"): "您有几天时间?",
        }
        return questions.get((intent, param), f"请提供您的{param}")

    def update_state(self, session_id: str, state: DialogueState):
        """更新对话状态"""
        context = self.get_context(session_id)
        context.state = state

    def add_history(self, session_id: str, role: str, content: str):
        """添加历史记录"""
        context = self.get_context(session_id)
        context.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def clear_context(self, session_id: str):
        """清除对话上下文"""
        if session_id in self._contexts:
            del self._contexts[session_id]

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "active_sessions": len(self._contexts),
            "states": {
                state.value: sum(1 for c in self._contexts.values() if c.state == state)
                for state in DialogueState
            }
        }


# 全局单例
dialogue_policy = DialoguePolicy()
