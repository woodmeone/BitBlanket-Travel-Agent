"""
================================================================================
LangChain Agent 测试脚本
================================================================================

测试 LangChain + LangGraph Agent 的各项功能。

使用:
```bash
cd agent
PYTHONPATH=src python application/test_langchain.py
```

================================================================================
"""

import asyncio
import os
import sys

# 添加路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'agent', 'src'))


async def test_llm():
    """测试 LLM 适配器"""
    print("\n" + "=" * 50)
    print("测试 1: LLM 适配器")
    print("=" * 50)

    from llm.langchain_adapter import create_from_yaml_config

    config_path = os.path.join(project_root, 'config', 'llm_config.yaml')
    llm_adapter = create_from_yaml_config(config_path)
    llm = llm_adapter.chat_model

    print(f"LLM: {llm_adapter.config.get('name')}")

    # 测试调用
    from langchain_core.messages import HumanMessage

    response = llm.invoke([HumanMessage(content="你好，请用一句话介绍自己")])
    print(f"\n响应: {response.content}")

    return llm


async def test_tools():
    """测试工具"""
    print("\n" + "=" * 50)
    print("测试 2: LangChain 工具")
    print("=" * 50)

    from tools.travel_tools import get_travel_tools

    tools = get_travel_tools()
    print(f"加载了 {len(tools)} 个工具")

    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")

    # 测试工具调用
    print("\n测试 search_cities 工具:")
    result = tools[0].invoke({"query": "北京"})
    print(result[:200] + "..." if len(result) > 200 else result)

    return tools


async def test_agent(llm, tools):
    """测试 Agent"""
    print("\n" + "=" * 50)
    print("测试 3: LangGraph Agent")
    print("=" * 50)

    from graph import build_travel_agent, run_travel_agent

    test_cases = [
        "推荐一个周末短途旅行目的地",
        "北京三日游怎么安排？",
        "去三亚旅游需要注意什么？",
    ]

    for i, user_input in enumerate(test_cases, 1):
        print(f"\n--- 测试 {i}: {user_input} ---")

        result = await run_travel_agent(
            user_message=user_input,
            llm=llm,
            tools=tools,
            session_id="test"
        )

        print(f"意图: {result['intent']}")
        print(f"工具: {result['tools_used']}")
        print(f"\n回答:\n{result['answer'][:300]}...")


async def test_streaming(llm, tools):
    """测试流式输出"""
    print("\n" + "=" * 50)
    print("测试 4: 流式输出")
    print("=" * 50)

    from graph import build_travel_agent, create_initial_state

    agent = build_travel_agent(llm, tools)

    initial_state = create_initial_state(
        user_message="推荐一个海边旅游目的地",
        session_id="stream_test"
    )

    print("\n流式响应:")
    async for chunk in agent.astream(initial_state):
        if "answer" in chunk and chunk["answer"]:
            print(chunk["answer"], end="", flush=True)
    print("\n")


async def test_memory():
    """测试 Memory"""
    print("\n" + "=" * 50)
    print("测试 5: 会话历史 Memory")
    print("=" * 50)

    from memory.chat_history import ChatHistoryManager

    manager = ChatHistoryManager()

    # 创建会话
    history = manager.get_or_create("test_session")
    history.add_user_message("我想去北京旅游")
    history.add_ai_message("北京是个很好的选择！")

    # 获取消息
    messages = history.get_messages()
    print(f"会话消息数: {len(messages)}")
    for msg in messages:
        print(f"  {type(msg).__name__}: {msg.content[:30]}...")


async def main():
    """主函数"""
    print("=" * 50)
    print("LangChain + LangGraph Agent 测试")
    print("=" * 50)

    try:
        # 测试 LLM
        llm = await test_llm()

        # 测试工具
        tools = await test_tools()

        # 测试 Agent
        await test_agent(llm, tools)

        # 测试流式
        await test_streaming(llm, tools)

        # 测试 Memory
        await test_memory()

        print("\n" + "=" * 50)
        print("所有测试完成!")
        print("=" * 50)

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
