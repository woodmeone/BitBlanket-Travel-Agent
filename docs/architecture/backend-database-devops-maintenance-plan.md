# Backend / Database / DevOps Maintenance Plan

这份文档专门回答一个长期维护问题：当前后端已经做了哪些基础建设，还缺什么，接下来应该按什么顺序补齐。

## 1. 当前已经具备的基线

### 1.1 后端接口

- 已有明确的 FastAPI 路由边界：
  - `chat / session / artifact / share / city / map / health / model`
- 已有对外接口文档与契约快照：
  - `docs/reference/api-reference.md`
  - `docs/reference/openapi.snapshot.json`
  - `docs/reference/sse-contract.snapshot.json`
- 已有运行时观测：
  - `request_id / trace_id`
  - `/api/health`、`/api/ready`、`/api/metrics`
  - SSE 事件统计、超时统计、限流统计
- 已有维护脚本与测试：
  - `runtime_doctor`
  - `support bundle`
  - OpenAPI / SSE snapshot export
  - `unit / local / integration / quality` 分层测试

### 1.2 数据与持久化

- Session 当前由 `FileSessionRepository` 落到 `data/sessions/sessions.json`
- Share link 当前落到 `data/share_links.json`
- Agent memory 当前落到 `data/agent_memory.json`，并带 `.bak` 热备
- LangGraph checkpoint 当前落到 `data/langgraph_checkpoints.sqlite3`
- 已有 `backup / restore / prune / doctor` 维护脚本

### 1.3 发版与运维

- 已有 `deploy/docker/backend.Dockerfile`、`deploy/docker/frontend.Dockerfile`、`deploy/compose/compose.yaml`
- 已有 CI 的 `container-validate`
- 已有 `release manifest`、`release harness scorecard`
- 已有 Grafana / Prometheus 资产
- 已有 build metadata 注入到后端 `/` 与 `/api/health`

## 2. 目前仍需补齐的重点

### 2.1 接口治理

当前接口“可用”，但还没完全达到“长期稳定演进”的治理强度，主要缺口有：

- 请求模型校验偏薄。
  - 例如 `ChatRequest.mode` 还不是显式枚举，`session/name/model` 相关字段缺少长度和格式约束。
- 错误码虽然已经存在，但还没有形成统一目录和兼容策略。
  - 目前是 route 内零散维护 `SESSION_NOT_FOUND`、`INVALID_ARGUMENT`、`MAP_ROUTE_ERROR` 等。
- 还没有正式的接口版本化 / 废弃策略。
  - 当前只有快照，没有“哪个字段可改、哪个字段只能追加”的明确规则。
- 写接口还没有幂等性、审计字段和 ownership 语义。
  - 例如分享、清空会话、删除会话等操作更像单机应用接口，而不是长期演进的服务接口。
- 还没有认证、租户隔离和权限边界。
  - 这对单用户本地运行没问题，但会限制后续多人协作或线上部署。

### 2.2 数据库能力

当前存储“可恢复”，但仍然是典型单机运行态模型，主要缺口有：

- Session / Share / Memory / Checkpoint 分散在 JSON + SQLite，多份状态没有统一事务边界。
- 还没有仓储层级别的 schema version、migration、backfill 机制。
- 当前文件存储和进程内单例更适合单实例，不适合多实例并发写入。
- 限流也是内存滑动窗口，天然不是分布式方案。
- 还没有 PostgreSQL 目标模型、索引设计、归档 / TTL / 清理计划。
- 还没有数据分级策略。
  - 哪些字段可长期留存、哪些属于运行态缓存、哪些需要脱敏或删除，目前没有正式规则。

### 2.3 发版与 DevOps

当前发布链路已经能构建、推送、产出 manifest，但长期维护仍缺这些确定性资产：

- 发布镜像过去仍保留 `latest` 语义，回滚和问题定位不够确定。
  - 本轮已改成“必须使用明确 `release_tag`，不再发布 `latest`”。
- release manifest 过去只有镜像仓库坐标，没有精确镜像引用。
  - 本轮已补 `image_tag` 和 `image_ref`。
- 还没有 staging / production 的环境提升规则和上线后 smoke checklist。
- 还没有正式的回滚 runbook、变更窗口和故障升级路径。
- 还没有部署编排资产。
  - 当前只有 Compose，没有 K8s / Helm / 云环境部署清单。
- 还没有容器安全闭环。
  - 目前有 `pip-audit`、`gitleaks`，但还缺镜像扫描、SBOM、签名或 provenance。

## 3. 建议执行顺序

### P0：先把规则固定住

目标：先解决“发版不确定、文档不集中、边界不清楚”。

- 固化发布规则：
  - 禁止 `latest`
  - 手动 release 必须显式提供 `release_tag`
  - release manifest 必须记录 `image_tag / image_ref`
- 把总规划落到 `docs/architecture/`
- 把发布规则落到 `docs/governance/adr/`
- 在 `backend-maintainer-playbook / infrastructure / data-storage` 中补交叉链接

### P1：把后端治理变成可检查资产

目标：让接口、数据库、发布不再只靠经验维护。

- 接口侧补齐：
  - 请求/响应模型约束
  - 错误码目录
  - 字段兼容性规则
  - 废弃策略
- 数据侧补齐：
  - schema version
  - migration script
  - PostgreSQL 目标模型设计
  - retention / archive 规则
- DevOps 侧补齐：
  - release runbook
  - rollback checklist
  - staging / production smoke checklist

### P2：进入生产化能力

目标：从“单机可维护”升级到“多环境可维护”。

- 引入 PostgreSQL 持久化主路径
- 明确 Redis 是否承担缓存 / 限流 / 会话加速
- 引入部署清单和环境提升流程
- 补容器安全与供应链治理
- 视业务阶段补认证、租户隔离和权限模型

## 4. 文档落点约定

后续这三类内容建议固定维护到这些目录，不再散落：

- 接口治理：
  - `docs/reference/api-reference.md`
  - `docs/reference/openapi.snapshot.json`
  - `docs/reference/sse-contract.snapshot.json`
  - `docs/reference/backend-maintainer-playbook.md`
- 数据库与存储：
  - `docs/architecture/data-storage.md`
  - 本文档
  - `docs/governance/rfcs/RFC-0001-postgresql-migration-baseline.md`
  - `docs/governance/rfcs/RFC-0002-checkpoint-sql-boundary.md`
- 发版与 DevOps：
  - `docs/architecture/infrastructure-foundations.md`
  - `docs/governance/adr/ADR-0002-versioned-release-images.md`
  - `extend/observability/README.md`

## 5. 当前结论

如果只回答“后端还缺什么”，结论是这 5 件事优先级最高：

1. 接口版本与错误码治理
2. 请求模型约束和写接口幂等性
3. 数据 schema version / migration / PostgreSQL 目标模型
4. release versioning、回滚和环境提升规则
5. 多实例场景下的认证、限流、缓存与一致性方案
