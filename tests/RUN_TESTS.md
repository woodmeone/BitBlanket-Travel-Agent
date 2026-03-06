# ShuaiTravelAgent 测试指南

## 快速运行

```bash
# 激活 conda 环境
conda activate agents

# 终端1: 启动 Web API
python run_api.py

# 终端2: 运行测试
cd tests
pytest -v
```

---

## 测试文件清单

### 1. 集成测试 (tests/)

| 文件 | 测试内容 |
|------|----------|
| `test_api_integration.py` | API 集成测试 (聊天、会话、模型、健康检查) |
| `test_sse_streaming.py` | SSE 流式响应测试 |
| `test_e2e_streaming.py` | 端到端测试 (首 token 延迟、吞吐量) |

### 2. Agent 模块测试 (agent/tests/)

| 文件 | 测试内容 |
|------|----------|
| `test_config_manager.py` | 配置管理器 |
| `test_langchain_graph.py` | LangGraph 图结构 |
| `test_llm_client.py` | LLM 客户端 |

### 3. Agent 应用测试

| 文件 | 位置 | 测试内容 |
|------|------|----------|
| `test_langchain.py` | `agent/src/application/` | LangChain Agent 功能 |

---

## 详细测试说明

### A. API 集成测试

```bash
# 运行所有 API 测试
pytest tests/test_api_integration.py -v

# 测试项:
# - test_health_check: 健康检查
# - test_ready_check: 就绪检查
# - test_live_check: 存活检查
# - test_chat_stream: 聊天流式
# - test_session_persistence: Session 持久化
# - test_create_session: 创建会话
# - test_list_sessions: 列出会话
# - test_delete_session: 删除会话
# - test_list_models: 模型列表
```

### B. SSE 流式测试

```bash
# 运行 SSE 测试
pytest tests/test_sse_streaming.py -v

# 测试项:
# - test_sse_connection: SSE 连接
# - test_sse_response_format: 响应格式
# - test_token_streaming: Token 流式
# - test_session_persistence: Session 持久化
# - test_streaming_completion: 流完成
# - test_answer_start_event: 答案开始事件
```

### C. 端到端测试

```bash
# 运行 E2E 测试
pytest tests/test_e2e_streaming.py -v

# 测试项:
# - test_web_health: Web 健康检查
# - test_full_streaming_pipeline: 完整流式管道
# - test_multiple_sequential_requests: 连续请求
# - test_first_token_latency: 首 token 延迟
# - test_throughput: 吞吐量
```

### D. LangChain Agent 测试

```bash
# 进入 agent 目录
cd agent

# 设置 PYTHONPATH
export PYTHONPATH=src  # Linux/Mac
set PYTHONPATH=src     # Windows

# 运行测试
python src/application/test_langchain.py

# 测试项:
# - LLM 适配器加载
# - LangChain 工具
# - Agent 推理
# - 流式输出
# - 记忆系统
```

---

## 测试环境要求

- Python 3.10+
- conda 环境: `agents`
- Web API 运行在: `http://localhost:38000`
- Frontend 运行在: `http://localhost:33001`

---

## 故障排查

### 问题1: 连接被拒绝

```
httpx.ConnectError: [Errno 111] Connection refused
```

**解决**: 确保 Web API 已启动
```bash
python run_api.py
```

### 问题2: ImportError

```
ModuleNotFoundError: No module named 'langchain'
```

**解决**: 安装依赖
```bash
pip install langchain langchain-core langgraph
```

### 问题3: 配置加载失败

```
FileNotFoundError: config/llm_config.yaml
```

**解决**: 复制配置模板
```bash
cp config/llm_config.yaml.example config/llm_config.yaml
```

---

## v3.x 测试变化

| 对比项 | v2.x | v3.x |
|--------|------|------|
| Agent | 独立 gRPC | 集成到 Web API |
| gRPC 端口 | 50051 | 无需 |
| Redis | 需要 | 内存存储 |
| Milvus | 需要 | 内存 RAG |
| Nacos | 需要 | 本地 YAML |
