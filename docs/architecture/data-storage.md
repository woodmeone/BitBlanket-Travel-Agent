# Data Storage

## 当前策略

- 会话数据默认采用文件存储
- 文件 session repository 位于 [`backend/moyuan_web/repositories/file_session_repository.py`](../../backend/moyuan_web/repositories/file_session_repository.py)
- `web` bootstrap 现在支持 `file | postgres` 双后端切换
- SQL 实现位于 `backend/moyuan_web/persistence/` 和 `backend/moyuan_web/repositories/*postgres*.py`
- 运行数据位于 `data/`（已被 `.gitignore` 忽略）
- Agent memory 独立持久化到 `data/agent_memory.json`
- Agent memory 已启用原子写入（临时文件 + `os.replace`）并保留 `data/agent_memory.json.bak` 热备
- LangGraph checkpoint 默认持久化到 `data/langgraph_checkpoints.sqlite3`
- checkpoint backend 现在支持 `sqlite | postgres` 切换，但默认仍保留 SQLite

## 当前核心实体

- Session: 会话元信息 + 消息列表
- Message: 角色、内容、时间戳等
- Memory Session: 摘要 + 最近消息 + 用户偏好画像（budget/days/interests 等）
- Share Link: 分享标题、正文和创建时间
- Runtime Failure Cluster: 失败聚类和故障时间戳

## 当前关键运行文件

默认重点文件包括：

- `data/sessions/sessions.json`
- `data/sessions/sessions.json.bak`
- `data/agent_memory.json`
- `data/agent_memory.json.bak`
- `data/langgraph_checkpoints.sqlite3`
- `data/share_links.json`
- `data/share_links.json.bak`
- `data/runtime_failure_clusters.jsonl`

这些文件现在已经被 `runtime_*` 维护脚本统一纳管。

## Agent Memory 持久化细节

1. 写入路径
   - 主文件：`data/agent_memory.json`
   - 备份：`data/agent_memory.json.bak`
2. 写入流程
   - 先写同目录临时文件
   - `flush + fsync` 确保内容写入磁盘缓冲
   - `os.replace` 原子替换主文件
   - 同样流程写入 `.bak`
3. 读取恢复流程
   - 先尝试读取主文件
   - 主文件损坏时自动回退读取 `.bak`
   - 若从 `.bak` 恢复成功，自动回写主文件
4. 目的
   - 降低进程中断导致 JSON 半写入损坏的概率
   - 提升启动恢复成功率与 memory 可用性

更多细节见 [agent-memory-mechanisms.md](agent-memory-mechanisms.md)。

## Runtime 维护脚本

### 1. 创建备份

```bash
python scripts/dev.py runtime-backup
python scripts/dev.py runtime-backup --backup-label before-upgrade
```

默认输出目录：

- `artifacts/runtime_backups/`

输出内容：

- `runtime_backup_<timestamp>.zip`
- 压缩包内的 `manifest.json`

当前 `manifest.json` 重点会记录：

- 归档的运行文件列表与校验摘要
- `checkpoint_runtime.backend`
- `checkpoint_runtime.target`
- `checkpoint_runtime.restore_strategy`
- `restore_instructions`

checkpoint 相关规则：

- `sqlite` backend
  - 如果 checkpoint 文件位于项目目录内，archive 会直接包含该 SQLite 文件
  - 如果 checkpoint 文件位于项目目录外，archive 只记录 metadata，不自动打包外部文件
- `postgres` backend
  - archive 只记录 redacted DSN / backend metadata
  - 不会把 PostgreSQL checkpoint 表导出进 zip
  - 恢复时仍需要独立的数据库快照或逻辑备份

### 2. 从备份恢复

```bash
python scripts/dev.py runtime-restore --restore-archive artifacts/runtime_backups/runtime_backup_20260315T120000Z.zip
```

默认行为：

- 先创建一次 `pre-restore` 安全备份
- 再把归档中的运行文件恢复回项目目录
- 最后根据 `manifest.json` 打印 checkpoint 恢复说明

恢复语义：

- `sqlite` backend 且 archive 内含 checkpoint 文件
  - `python scripts/dev.py runtime-restore ...` 会把该文件恢复回记录的相对路径
- `postgres` backend
  - `python scripts/dev.py runtime-restore ...` 只恢复 zip 内的文件型运行态数据
  - checkpoint 仍需先恢复外部 PostgreSQL checkpoint 表，再把 runtime 切回 postgres

排障侧约定：

- `python scripts/dev.py runtime-doctor --runtime-doctor-json`
  - 会输出 `checks.checkpoint_runtime.details`
- `python scripts/dev.py support-bundle`
  - 会把同一份视图写入 `checkpoint-runtime.json`
  - `manifest.json.runtime_health` 里会再摘要 `checkpoint_backend / checkpoint_restore_strategy / checkpoint_requires_external_snapshot`

### 3. 清理旧数据

```bash
python scripts/dev.py runtime-prune --prune-keep-latest-backups 10 --prune-max-backup-age-days 14
python scripts/dev.py runtime-prune --prune-max-session-age-seconds 2592000 --prune-max-failure-age-days 30 --prune-vacuum-checkpoints
python scripts/dev.py runtime-maintenance --prune-keep-latest-backups 10 --prune-max-backup-age-days 14
python scripts/dev.py checkpoint-maintenance --replay-session-id <session_id> --prune-checkpoint-backend postgres --prune-checkpoint-db 'postgresql://user:password@localhost:5432/moyuan'
```

当前支持：

- 旧备份归档清理
- 过期 session 清理
- 旧 failure-cluster 记录清理
- backend-aware checkpoint maintenance
  - `sqlite` backend：compaction + `VACUUM`
  - `postgres` backend：compaction sweep
- 组合维护入口
  - `runtime-maintenance`：固定执行 `backup -> doctor(json) -> prune`
  - `checkpoint-maintenance`：固定执行 `prune(vacuum checkpoints) -> optional replay(dry-run) -> doctor(json)`

如果需要直接维护 PostgreSQL checkpoint：

```bash
python scripts/dev.py runtime-prune \
  --prune-max-session-age-seconds 2592000 \
  --prune-max-failure-age-days 30 \
  --prune-vacuum-checkpoints \
  --prune-checkpoint-backend postgres \
  --prune-checkpoint-db 'postgresql://user:password@localhost:5432/moyuan'
```

### 4. PostgreSQL migration / backfill

```bash
export MOYUAN_POSTGRES_DSN='postgresql://user:password@localhost:5432/moyuan'
alembic -c deploy/migrations/alembic.ini upgrade head
python scripts/runtime_backfill_postgres.py
```

当前基线说明：

- migration 目录：`deploy/migrations/`
- 当前表：`sessions`、`session_messages`、`share_links`、`memory_sessions`
- `sessions.messages` 已降级为兼容 shadow 字段，主读写来源改为 `session_messages`
- checkpoint SQL 表：`agent_checkpoints`、`agent_checkpoint_blobs`、`agent_checkpoint_writes`、`agent_checkpoint_meta`
- repository 切换：`MOYUAN_DB_BACKEND=file|postgres`
- checkpoint backend 切换：`AGENT_CHECKPOINT_BACKEND=sqlite|postgres`
- 回填源：`data/sessions/sessions.json`、`data/share_links.json`、`data/agent_memory.json`
- 回填策略：幂等 upsert，可重复执行

## 推荐保留策略

开发环境建议：

- backup archive：保留最近 `10` 个
- session：保留最近 `30` 天活跃数据
- failure clusters：保留最近 `30` 天

联调或演示环境建议：

- 大改前先执行一次 `runtime_backup.py`
- 回放完成后定期执行 `python scripts/dev.py runtime-prune ...`
- 如果 checkpoint 已切 PostgreSQL，`python scripts/dev.py agent-replay ...` 和 `python scripts/dev.py runtime-prune ...` 都应显式指向同一个 backend / DSN

## 恢复建议

如果遇到以下情况，优先考虑恢复：

- `sessions.json` 损坏
- `agent_memory.json` 读不出来
- checkpoint 文件误删或被覆盖
- 升级后需要快速回滚运行态

推荐顺序：

1. 先执行一次当前状态安全备份
2. 再执行 `python scripts/dev.py runtime-restore --restore-archive ...`
3. 恢复后检查：
   - `/api/health`
   - `/api/ready`
   - `/api/metrics`
4. 必要时再用 `python scripts/dev.py agent-replay ...` 验证关键会话

PostgreSQL checkpoint 回放示例：

```bash
python scripts/dev.py agent-replay \
  --replay-session-id <session_id> \
  --replay-checkpoint-backend postgres \
  --replay-db 'postgresql://user:password@localhost:5432/moyuan'
```

## 扩展建议

1. 开发环境可继续使用文件存储
2. 生产环境建议迁移 PostgreSQL
3. 高并发下可增加 Redis 做会话缓存
4. Session 与 Memory 建议统一落同一数据库事务边界，降低双写不一致风险
5. 如果未来进入多用户或多实例阶段，优先增加：
   - schema version
   - migration script
   - backup integrity check

## 当前长期维护缺口

从“后端长期维护”角度看，当前数据层还需要明确这几件事：

1. `sessions / share_links / agent_memory / checkpoints` 仍分散在 JSON 和 SQLite，没有统一事务边界。
2. 还没有正式的 schema version、migration、backfill 机制。
3. 当前实现更偏单机单实例，不适合作为多实例共享数据库方案直接放大。
4. 还没有 PostgreSQL 目标数据模型、索引与 retention 规则文档。
5. `checkpoint` 仍使用独立的 `sqlite | postgres` backend，不与业务表共用一套数据库基线。

建议把数据层后续治理统一收口到：

- [`backend-database-devops-maintenance-plan.md`](backend-database-devops-maintenance-plan.md)
- [`../governance/rfcs/RFC-0002-checkpoint-sql-boundary.md`](../governance/rfcs/RFC-0002-checkpoint-sql-boundary.md)
