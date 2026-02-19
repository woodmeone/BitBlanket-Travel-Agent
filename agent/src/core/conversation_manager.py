"""
对话管理器

管理多会话对话，支持会话切换和历史管理。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """会话"""
    session_id: str
    user_id: str
    created_at: str
    last_active: str = ""
    context: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


class ConversationManager:
    """对话管理器

    特性：
    - 多会话管理
    - 会话切换
    - 会话归档
    - 历史检索
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._active_sessions: Dict[str, str] = {}  # user_id -> session_id
        logger.info("ConversationManager initialized")

    def create_session(self, user_id: str, session_id: str = None) -> Session:
        """创建会话"""
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.now().isoformat(),
            last_active=datetime.now().isoformat()
        )

        self._sessions[session_id] = session
        self._active_sessions[user_id] = session_id

        logger.info(f"Created session {session_id} for user {user_id}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self._sessions.get(session_id)

    def get_active_session(self, user_id: str) -> Optional[Session]:
        """获取活跃会话"""
        session_id = self._active_sessions.get(user_id)
        if session_id:
            return self._sessions.get(session_id)
        return None

    def switch_session(self, user_id: str, session_id: str) -> bool:
        """切换会话"""
        if session_id not in self._sessions:
            return False

        self._active_sessions[user_id] = session_id
        return True

    def archive_session(self, session_id: str):
        """归档会话"""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.metadata["archived"] = True
            session.metadata["archived_at"] = datetime.now().isoformat()
            logger.info(f"Archived session {session_id}")

    def list_sessions(self, user_id: str = None) -> List[Session]:
        """列出会话"""
        sessions = list(self._sessions.values())
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        return sorted(sessions, key=lambda s: s.last_active, reverse=True)


class IntentClarifier:
    """意图澄清器 - LLM 增强"""

    def __init__(self, llm_client: Any = None):
        self._llm_client = llm_client
        logger.info("IntentClarifier initialized")

    def set_llm_client(self, llm_client):
        self._llm_client = llm_client

    async def generate_clarification_question(
        self,
        intent: str,
        missing_params: List[str],
        context: Dict = None
    ) -> str:
        """生成澄清问题"""
        if not self._llm_client:
            return self._generate_simple_question(intent, missing_params)

        # LLM 增强的澄清问题生成
        import json
        prompt = f"""用户意图: {intent}
缺少参数: {missing_params}
上下文: {context}

生成一个自然的澄清问题，帮助用户补充必要信息。"""

        result = self._llm_client.chat([
            {"role": "system", "content": "你是对话助手，擅长生成自然的澄清问题"},
            {"role": "user", "content": prompt}
        ])

        if result.get("success"):
            return result.get("content", "").strip()

        return self._generate_simple_question(intent, missing_params)

    def _generate_simple_question(self, intent: str, missing_params: List[str]) -> str:
        """简单的澄清问题"""
        questions = {
            "destination": "您想去哪个城市呢?",
            "days": "您计划玩几天?",
            "budget": "您的预算是多少?",
            "date": "您计划什么时候出发?"
        }

        for param in missing_params:
            if param in questions:
                return questions[param]

        return "请提供更多信息"


class DialogueStyleAdapter:
    """对话风格适配器"""

    def __init__(self, llm_client: Any = None):
        self._llm_client = llm_client
        self._user_styles: Dict[str, str] = {}
        logger.info("DialogueStyleAdapter initialized")

    def adapt_response(self, response: str, user_id: str = None, style: str = "default") -> str:
        """适配响应风格"""
        if style == "default" or not self._llm_client:
            return response

        # 简化实现
        return response

    def learn_style(self, user_id: str, messages: List[Dict]):
        """学习用户风格"""
        # 简化实现：记录用户偏好
        self._user_styles[user_id] = "adaptive"
        logger.info(f"Learned style for user {user_id}")
