"""
Agent 协作协议

定义多 Agent 之间的通信和协作规范。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型"""
    REQUEST = "request"       # 请求
    RESPONSE = "response"     # 响应
    BROADCAST = "broadcast"   # 广播
    EVENT = "event"          # 事件


@dataclass
class AgentMessage:
    """Agent 消息"""
    message_id: str
    sender_id: str
    receiver_id: str
    message_type: MessageType
    content: Dict
    timestamp: str = ""


class CollaborationProtocol:
    """协作协议"""

    def __init__(self):
        self._agents: Dict[str, Any] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._message_queue: List[AgentMessage] = []
        logger.info("CollaborationProtocol initialized")

    def register_agent(self, agent_id: str, agent: Any):
        """注册 Agent"""
        self._agents[agent_id] = agent
        logger.info(f"Registered agent: {agent_id}")

    def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        content: Dict,
        message_type: MessageType = MessageType.REQUEST
    ) -> AgentMessage:
        """发送消息"""
        if sender_id not in self._agents:
            raise ValueError(f"Unknown sender: {sender_id}")
        if receiver_id not in self._agents:
            raise ValueError(f"Unknown receiver: {receiver_id}")

        message = AgentMessage(
            message_id=f"msg_{datetime.now().timestamp()}",
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            timestamp=datetime.now().isoformat()
        )

        self._message_queue.append(message)

        # 处理消息
        self._process_message(message)

        return message

    def broadcast(self, sender_id: str, content: Dict):
        """广播消息"""
        for agent_id in self._agents:
            if agent_id != sender_id:
                self.send_message(sender_id, agent_id, content, MessageType.BROADCAST)

    def _process_message(self, message: AgentMessage):
        """处理消息"""
        receiver = self._agents.get(message.receiver_id)
        if not receiver:
            return

        # 简单处理：调用 receive 方法
        if hasattr(receiver, "receive_message"):
            try:
                receiver.receive_message(message)
            except Exception as e:
                logger.error(f"Message processing error: {e}")

    def get_messages(self, agent_id: str) -> List[AgentMessage]:
        """获取 Agent 的消息"""
        return [m for m in self._message_queue if m.receiver_id == agent_id]


class SkillDependencyResolver:
    """技能依赖解析器"""

    def __init__(self):
        self._graph: Dict[str, List[str]] = {}
        logger.info("SkillDependencyResolver initialized")

    def add_dependency(self, skill_id: str, depends_on: List[str]):
        """添加依赖"""
        self._graph[skill_id] = depends_on

    def resolve_order(self) -> List[List[str]]:
        """解析执行顺序（分层）"""
        visited = set()
        layers = []

        def visit(skill_id: str, current_layer: set):
            if skill_id in visited:
                return
            visited.add(skill_id)
            current_layer.add(skill_id)

            for dep in self._graph.get(skill_id, []):
                if dep in current_layer:
                    logger.warning(f"Circular dependency detected: {skill_id} -> {dep}")
                visit(dep, current_layer.copy())

        for skill_id in self._graph:
            if skill_id not in visited:
                layer = set()
                visit(skill_id, layer)
                if layer:
                    layers.append(list(layer))

        return layers


class AgentMetrics:
    """Agent 指标收集器"""

    def __init__(self):
        self._metrics: Dict[str, Dict] = {}
        logger.info("AgentMetrics initialized")

    def record_request(self, agent_id: str, duration: float, success: bool):
        """记录请求"""
        if agent_id not in self._metrics:
            self._metrics[agent_id] = {
                "requests": 0,
                "success": 0,
                "failure": 0,
                "total_duration": 0.0
            }

        m = self._metrics[agent_id]
        m["requests"] += 1
        m["total_duration"] += duration
        if success:
            m["success"] += 1
        else:
            m["failure"] += 1

    def get_metrics(self, agent_id: str) -> Dict:
        """获取指标"""
        m = self._metrics.get(agent_id, {})
        if not m:
            return {}

        requests = m.get("requests", 0)
        return {
            "requests": requests,
            "success_rate": m.get("success", 0) / requests if requests > 0 else 0,
            "avg_duration": m.get("total_duration", 0) / requests if requests > 0 else 0
        }


class TemplateEngine:
    """Agent 模板引擎"""

    def __init__(self):
        self._templates: Dict[str, Dict] = {}
        self._init_builtin_templates()
        logger.info("TemplateEngine initialized")

    def _init_builtin_templates(self):
        """初始化内置模板"""
        self.register_template("travel_expert", {
            "name": "旅游专家",
            "description": "专业的旅游助手",
            "skills": ["city_recommend", "route_plan", "budget_calc"],
            "config": {"max_results": 5}
        })

    def register_template(self, template_id: str, template: Dict):
        """注册模板"""
        self._templates[template_id] = template
        logger.info(f"Registered template: {template_id}")

    def create_from_template(self, template_id: str, **kwargs) -> Dict:
        """从模板创建"""
        template = self._templates.get(template_id, {})
        return {**template, **kwargs}

    def list_templates(self) -> List[str]:
        """列出模板"""
        return list(self._templates.keys())
