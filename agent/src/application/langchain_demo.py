"""
================================================================================
LangChain Agent 使用示例
================================================================================

演示如何使用基于 LangChain + LangGraph 的新 Agent 系统。

使用方法:
```bash
cd agent
PYTHONPATH=src python application/langchain_demo.py
```

================================================================================
"""

import asyncio
import os
import sys

# 添加 src 目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, 'agent', 'src'))


async def main():
    """主函数"""
    print("=" * 60)
    print("LangChain + LangGraph 旅游 Agent 演示")
    print("=" * 60)

    # 1. 导入模块
    from llm.langchain_adapter import create_from_yaml_config
    from tools.travel_tools import get_travel_tools
    from graph import build_travel_agent, run_travel_agent, create_initial_state
    from langchain_core.messages import HumanMessage

    # 2. 创建 LLM
    print("\n[1] 初始化 LLM...")
    config_path = os.path.join(project_root, 'config', 'llm_config.yaml')
    llm_adapter = create_from_yaml_config(config_path)
    llm = llm_adapter.chat_model
    print(f"    LLM 创建成功: {llm_adapter.config.get('name', 'unknown')}")

    # 3. 获取工具
    print("\n[2] 加载工具...")
    tools = get_travel_tools()
    print(f"    加载了 {len(tools)} 个工具:")
    for tool in tools:
        print(f"      - {tool.name}")

    # 4. 构建 Agent
    print("\n[3] 构建 LangGraph Agent...")
    agent = build_travel_agent(llm, tools)
    print("    Agent 构建成功!")

    # 5. 测试用例
    test_cases = [
        "推荐一个周末短途旅行目的地",
        "北京三日游怎么安排？",
        "去三亚旅游需要注意什么？",
        "帮我计算一下去上海3天的预算"
    ]

    for i, user_input in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"测试 {i}: {user_input}")
        print("=" * 60)

        # 方式1: 使用 run_travel_agent 便捷函数
        result = await run_travel_agent(
            user_message=user_input,
            llm=llm,
            tools=tools,
            session_id="demo"
        )

        print(f"\n意图: {result['intent']}")
        print(f"使用工具: {result['tools_used']}")
        print(f"\n回答:\n{result['answer']}")

        print(f"\n[推理过程]: {result['reasoning']}")

        # 每次测试间隔
        await asyncio.sleep(1)

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
