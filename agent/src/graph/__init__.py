"""
================================================================================
LangGraph Agent 模块
================================================================================

基于 LangChain + LangGraph 的旅游 Agent 实现。

导出:
- AgentState: 状态定义
- TravelAgentGraph: Agent 图构建器
- build_travel_agent: 工厂函数
- run_travel_agent: 便捷运行函数
- run_travel_agent_streaming: 带流式回调的运行函数

使用示例:
```python
from graph import build_travel_agent, run_travel_agent
from llm.langchain_adapter import create_from_yaml_config
from tools.travel_tools import get_travel_tools

# 方式1: 使用工厂函数
llm = create_from_yaml_config("config/llm_config.yaml").chat_model
tools = get_travel_tools()
agent = build_travel_agent(llm, tools)

result = agent.invoke({
    "messages": [HumanMessage(content="推荐一个城市")],
    "session_id": "test"
})

# 方式2: 使用便捷函数
result = await run_travel_agent("推荐一个城市", llm, tools)

# 方式3: 使用流式回调
async def on_token(token):
    print(token, end="", flush=True)

result = await run_travel_agent_streaming(
    "推荐一个城市",
    llm,
    tools,
    on_token=on_token
)
```

================================================================================
"""

from .state import AgentState, create_initial_state, TRAVEL_AGENT_SYSTEM_PROMPT
from .nodes import AgentNodes, create_nodes, IntentResult, PlanStep
from .builder import (
    TravelAgentGraph,
    build_travel_agent,
    run_travel_agent,
    run_travel_agent_streaming,
    run_travel_agent_streaming_with_memory,
    run_travel_agent_with_memory
)

__all__ = [
    # 状态
    "AgentState",
    "create_initial_state",
    "TRAVEL_AGENT_SYSTEM_PROMPT",
    # 节点
    "AgentNodes",
    "create_nodes",
    "IntentResult",
    "PlanStep",
    # 构建器
    "TravelAgentGraph",
    "build_travel_agent",
    "run_travel_agent",
    "run_travel_agent_streaming",
    "run_travel_agent_streaming_with_memory",
    "run_travel_agent_with_memory",
]
