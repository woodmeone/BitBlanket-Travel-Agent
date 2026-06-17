# Skills Market Catalog

这份文档记录当前默认 `skills market` 的稳定元数据视图。

代码真相源仍然在 [agent/travel_agent/skills/registry.py](../../agent/travel_agent/skills/registry.py)，这里的目标是让维护者和 reviewer 能快速看到：

- 哪些 skill 已经进入默认 catalog
- 它们分别归谁负责
- 输入输出契约是什么
- 是否要求证据、freshness 和 fallback

## 统一 metadata schema

默认 `SkillContract` 当前包含这些治理字段：

- `name`
- `description`
- `allowed_subagents`
- `tool_names`
- `input_contract.required_context`
- `input_contract.optional_context`
- `output_contract.artifact`
- `output_contract.fields`
- `evidence_required`
- `freshness_policy`
- `fallback_policy`
- `market_metadata.owner`
- `market_metadata.version`
- `market_metadata.docs_path`
- `market_metadata.test_fixture`
- `market_metadata.prompt_asset`
- `market_metadata.eval_fixture`
- `market_metadata.onboarding_requirements`
- `selection_policy.priority`
- `selection_policy.intent_signals`
- `selection_policy.preferred_context`
- `selection_policy.notes`

## 当前默认 catalog

| Skill | Owner | Subagents | Tools | Artifact | Evidence | Freshness | Fallback |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `CityResearchSkill` | `research-subagent` | `research` | `search_cities` | `ResearchDossier` | No | `best_effort` | `graceful_degrade` |
| `AttractionResearchSkill` | `research-subagent` | `research` | `query_attractions` | `ResearchDossier` | No | `prefer_recent` | `graceful_degrade` |
| `WeatherLookupSkill` | `research-subagent` | `research / planning / verification` | `get_weather` | `ResearchDossier` | No | `must_refresh_if_stale` | `graceful_degrade` |
| `HotelQuoteSkill` | `budget-subagent` | `budget / planning` | `query_hotels` | `BudgetReport` | Yes | `must_refresh_if_stale` | `graceful_degrade` |
| `BudgetAggregationSkill` | `budget-subagent` | `budget` | `calculate_budget` | `BudgetReport` | Yes | `best_effort` | `graceful_degrade` |
| `PlanSynthesisSkill` | `planning-subagent` | `planning` | `plan_itinerary` | `ItineraryDraft` | No | `best_effort` | `graceful_degrade` |
| `TravelTipsSkill` | `verification-subagent` | `research / verification` | `get_travel_tips` | `ResearchDossier` | No | `best_effort` | `graceful_degrade` |

## 当前 subagent selection policy 基线

- `research`
  - `CityResearchSkill` 优先建立候选城市，再按 `AttractionResearchSkill` 补齐 POI 证据，天气与提示类能力交给 `WeatherLookupSkill / TravelTipsSkill` 作为条件补充
- `planning`
  - `PlanSynthesisSkill` 是默认主技能；当上下文中出现住宿预算或路线约束时，再把 `HotelQuoteSkill / WeatherLookupSkill` 作为补强技能加入
- `budget`
  - `HotelQuoteSkill` 先补齐 quote 级输入，`BudgetAggregationSkill` 再汇总 `hotel_quotes / transport_estimates / activity_estimates`
- `verification`
  - `TravelTipsSkill` 当前作为提醒与政策检查技能，只有在目的地上下文已满足且意图需要补充提醒时才进入 `ready`

这层 policy 现在已经从 subagent prompt 里抽成代码契约，可通过：

- [agent/travel_agent/subagents/base.py](../../agent/travel_agent/subagents/base.py)
- [agent/travel_agent/subagents/registry.py](../../agent/travel_agent/subagents/registry.py)
- [agent/travel_agent/runtime/agent_runtime.py](../../agent/travel_agent/runtime/agent_runtime.py)

读取 `selection_policy()`、`selection_plan()` 和 `subagent_skill_policies` diagnostics。

## 当前治理门禁

默认 catalog 当前会额外经过：

- `python scripts/skills_market_audit.py --strict`

这条门禁会检查：

- onboarding requirements 是否包含 `schema + tests + docs + eval`
- `docs_path / test_fixture / eval_fixture / onboarding_doc` 是否存在
- `input_contract.required_context / output_contract.artifact / output_contract.fields` 是否完整

## 当前配套入口

- Registry 代码：[agent/travel_agent/skills/registry.py](../../agent/travel_agent/skills/registry.py)
- Contract 模型：[agent/travel_agent/contracts/skills.py](../../agent/travel_agent/contracts/skills.py)
- Onboarding 清单：[docs/governance/skills-market-onboarding.md](../governance/skills-market-onboarding.md)
- 回归测试：[tests/test_skill_registry_unit.py](../../tests/test_skill_registry_unit.py)

## 当前限制

这轮先解决的是“有稳定 schema、ownership、selection policy 和 onboarding 入口”。

还没有完全做完的部分：

- `research / planning / budget / verification` 的 scorecard 还没有按 skill 维度稳定落地
- 还没有单独的 skill benchmark 数据集
