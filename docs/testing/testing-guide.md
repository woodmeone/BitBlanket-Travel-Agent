# Testing Guide

## 测试目录

- `tests/`: API 与集成测试
- `agent/tests/`: Agent 单元/模块测试
- `frontend/tests/`: 前端单元测试

## 运行命令

### API / 集成

```bash
pytest tests/ -v
```

### Agent

```bash
cd agent
set PYTHONPATH=src
python -m pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm run test:run
```

## 失败回放（checkpoint）

用于回放失败会话并生成报告。默认模式会执行真实 replay（调用 Agent + LLM）。

```bash
python scripts/agent_replay.py --session-id <session_id> --db data/langgraph_checkpoints.sqlite3
```

仅导出 checkpoint 快照（不执行 replay）：

```bash
python scripts/agent_replay.py --session-id <session_id> --db data/langgraph_checkpoints.sqlite3 --dry-run
```

默认输出目录：`docs/benchmarks/`，文件名形如：

- `agent_replay_<session>_<timestamp>.json`
- `agent_replay_<session>_<timestamp>.md`

## 常见问题

1. `Connection refused`: 先启动 `python run_api.py`
2. `ModuleNotFoundError`: 检查 Python 环境与依赖
3. SSE 测试失败: 先确认 `/api/chat/stream` 可访问
