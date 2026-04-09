# Harness Engineering Runtime Source Roadmap (2026-03-28)

> Status: 已关闭的路线图执行稿。本文保留为运行时治理演进记录，不作为当前实现真相源。
> 当前维护请优先看 [../README.md](../README.md)、[system-architecture.md](system-architecture.md)、[infrastructure-foundations.md](infrastructure-foundations.md)、[data-storage.md](data-storage.md)。

## 当前维护者速查

这份已关闭路线图的当前价值可以压成 4 条：

| 主题 | 历史结论 |
| --- | --- |
| Runtime seam | `AgentRuntime -> runtime_driver -> runtime_flow -> runtime_sources / runtime_event_emitters` 已成为稳定主链，`runtime_contract_audit` 是这条 seam 的执行门禁。 |
| Ops contracts | `runtime_doctor`、support bundle、release manifest、release harness scorecard 已共享 typed ops contract，不再各自拼装 loose dict。 |
| Delivery bundle | `artifact + execution receipt + html content + share metadata` 已收口成统一 delivery bundle，并有 replay / snapshot 保护。 |
| 治理闭环 | 运行时演进已经纳入本地脚本、CI、release evidence 同一治理面，不再依赖口头约定。 |

## 历史执行摘要

这轮路线图的历史完成项主要是：

1. 给 runtime seam 补上 `runtime_contract_audit`，并接入本地与 CI。
2. 把 memory-aware source state 和 normalized event assembly 分别下沉到 `runtime_sources.py` 与 `runtime_event_emitters.py`。
3. 把 runtime doctor、support bundle、release evidence 统一到 `scripts/runtime_ops_contracts.py`。
4. 把 share / replay / snapshot 收口到 delivery bundle contract。

## 当前阅读建议

- 如果你现在在维护运行时主链，请优先看 [system-architecture.md](system-architecture.md)、[infrastructure-foundations.md](infrastructure-foundations.md)、[data-storage.md](data-storage.md)。
- 如果你只是想知道“这份历史稿最后沉淀了什么”，看完上面的两节就够了。
- 下面不再追加新的执行清单；后续运行时治理以当前 reference / architecture 文档为准。
