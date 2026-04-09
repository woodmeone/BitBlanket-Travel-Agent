# Skills Market Onboarding

这份清单用来约束新 `skill` 接入 `moyuan-travel-agent` 的最低工程标准。

目标不是让接入变慢，而是避免新 skill 再退回到“只有一个工具包装 + 一段 prompt”的松散状态。

## 什么时候要走这份清单

满足下面任一条件时，就应该补这份材料：

- 新增一个会进入 `SkillRegistry` 的领域能力
- 让已有 skill 改变输入上下文、输出 artifact、freshness 或 fallback 规则
- 让某个 subagent 开始依赖新的 skill contract

## 四件套门槛

新 skill 合入前，至少要补齐下面四件套：

1. `schema`
   - 在 [agent/travel_agent/contracts/skills.py](../../agent/travel_agent/contracts/skills.py) 对应的 `SkillContract` 中补齐：
     - `name`
     - `allowed_subagents`
     - `input_contract.required_context`
     - `output_contract.artifact`
     - `output_contract.fields`
     - `evidence_required`
     - `freshness_policy`
     - `fallback_policy`
     - `market_metadata.owner / version / docs_path / prompt_asset / eval_fixture`
     - `market_metadata.test_fixture`
     - `selection_policy.priority / intent_signals / preferred_context / notes`
2. `tests`
   - 至少补一条 registry 级单测，落在 [tests/test_skill_registry_unit.py](../../tests/test_skill_registry_unit.py)
   - 如果 skill 会影响 subagent 路由、selection policy、artifact patch 或 diagnostics，再补对应 runtime / stream 测试
3. `docs`
   - 更新 [docs/reference/skills-market-catalog.md](../reference/skills-market-catalog.md)
   - 如果会改变架构边界，再同步 [docs/architecture/agent-subagent-skills-architecture-roadmap.md](../architecture/agent-subagent-skills-architecture-roadmap.md)
4. `eval`
   - 在 `market_metadata.eval_fixture` 里挂上至少一个可追溯的验证入口
   - 默认优先复用 registry / runtime 单测；高风险 skill 再追加 benchmark 或 golden eval

当前这份清单已经有对应门禁：

- `python scripts/skills_market_audit.py --strict`
- `python scripts/dev.py infra-check`

## 推荐接入步骤

1. 在 [agent/travel_agent/skills/registry.py](../../agent/travel_agent/skills/registry.py) 注册新 skill，并补齐元数据。
2. 如果需要新增 tool provider、改 selection policy，或更换 evidence/fallback 逻辑，先补对应 contract，再改 subagent 消费方。
3. 把 skill 写入 [docs/reference/skills-market-catalog.md](../reference/skills-market-catalog.md)，说明 owner、输入输出、证据要求和失败回退。
4. 运行最小回归：
   - `uv run --offline --with pytest --with pytest-asyncio python -m pytest tests/test_skill_registry_unit.py -q`
   - `uv run --offline --with pytest --with pytest-asyncio python -m pytest tests/test_agent_subagent_phase2_unit.py -q`
   - `python scripts/docstring_audit.py --strict`
   - `python scripts/complexity_budget.py --strict`

## Review 清单

- skill 是否真的表达“领域能力”，而不是单次 tool call
- 输入上下文是否足够窄，避免让 prompt 隐式推断太多前提
- 输出 artifact 是否能被前端或 runtime 直接消费
- evidence / freshness / fallback 是否写成了稳定 contract，而不是散落在 prompt 里
- selection policy 是否足够显式，避免 subagent 继续靠 prompt 猜测该优先用哪个 skill
- `owner`、`docs_path`、`eval_fixture` 是否可追溯
- `test_fixture` 是否真实覆盖当前 skill contract，而不是只保留一个空字段

## 当前基线

当前默认 catalog 已经把研究、规划、预算相关 skill 收口成显式 schema，见：

- [agent/travel_agent/skills/registry.py](../../agent/travel_agent/skills/registry.py)
- [docs/reference/skills-market-catalog.md](../reference/skills-market-catalog.md)
- [tests/test_skill_registry_unit.py](../../tests/test_skill_registry_unit.py)
