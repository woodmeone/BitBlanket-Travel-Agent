# Skills Market Catalog

这份文档记录当前默认 `skills market` 的稳定元数据视图。

代码真相源仍然在 [agent/travel_agent/skills/registry.py](/D:/moyuan/moyuan-travel-agent/agent/travel_agent/skills/registry.py)，这里的目标是让维护者和 reviewer 能快速看到：

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
- `market_metadata.prompt_asset`
- `market_metadata.eval_fixture`
- `market_metadata.onboarding_requirements`

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

## 当前配套入口

- Registry 代码：[agent/travel_agent/skills/registry.py](/D:/moyuan/moyuan-travel-agent/agent/travel_agent/skills/registry.py)
- Contract 模型：[agent/travel_agent/contracts/skills.py](/D:/moyuan/moyuan-travel-agent/agent/travel_agent/contracts/skills.py)
- Onboarding 清单：[docs/governance/skills-market-onboarding.md](/D:/moyuan/moyuan-travel-agent/docs/governance/skills-market-onboarding.md)
- 回归测试：[tests/test_skill_registry_unit.py](/D:/moyuan/moyuan-travel-agent/tests/test_skill_registry_unit.py)

## 当前限制

这轮先解决的是“有稳定 schema、ownership 和 onboarding 入口”。

还没有完全做完的部分：

- skill selection policy 还没有从 subagent prompt 中进一步抽离
- `research / planning / budget / verification` 的 scorecard 还没有按 skill 维度稳定落地
- 还没有单独的 skill benchmark 数据集
