# Data Storage

## 当前策略

- 会话数据默认采用文件存储
- 存储实现位于 [`web/moyuan_web/storage/session_storage.py`](/D:/moyuan/moyuan-travel-agent/web/moyuan_web/storage/session_storage.py)
- 运行数据位于 `data/`（已被 `.gitignore` 忽略）
- Agent memory 独立持久化到 `data/agent_memory.json`
- Agent memory 已启用原子写入（临时文件 + `os.replace`）并保留 `data/agent_memory.json.bak` 热备
- LangGraph checkpoint 持久化到 `data/langgraph_checkpoints.sqlite3`

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
python scripts/runtime_backup.py
python scripts/runtime_backup.py --label before-upgrade
```

默认输出目录：

- `artifacts/runtime_backups/`

输出内容：

- `runtime_backup_<timestamp>.zip`
- 压缩包内的 `manifest.json`

### 2. 从备份恢复

```bash
python scripts/runtime_restore.py --archive artifacts/runtime_backups/runtime_backup_20260315T120000Z.zip
```

默认行为：

- 先创建一次 `pre-restore` 安全备份
- 再把归档中的运行文件恢复回项目目录

### 3. 清理旧数据

```bash
python scripts/runtime_prune.py --keep-latest-backups 10 --max-backup-age-days 14
python scripts/runtime_prune.py --max-session-age-seconds 2592000 --max-failure-age-days 30 --vacuum-checkpoints
```

当前支持：

- 旧备份归档清理
- 过期 session 清理
- 旧 failure-cluster 记录清理
- checkpoint SQLite `VACUUM`

## 推荐保留策略

开发环境建议：

- backup archive：保留最近 `10` 个
- session：保留最近 `30` 天活跃数据
- failure clusters：保留最近 `30` 天

联调或演示环境建议：

- 大改前先执行一次 `runtime_backup.py`
- 回放完成后定期执行 `runtime_prune.py`

## 恢复建议

如果遇到以下情况，优先考虑恢复：

- `sessions.json` 损坏
- `agent_memory.json` 读不出来
- checkpoint 文件误删或被覆盖
- 升级后需要快速回滚运行态

推荐顺序：

1. 先执行一次当前状态安全备份
2. 再执行 `runtime_restore.py`
3. 恢复后检查：
   - `/api/health`
   - `/api/ready`
   - `/api/metrics`
4. 必要时再用 `agent_replay.py` 验证关键会话

## 扩展建议

1. 开发环境可继续使用文件存储
2. 生产环境建议迁移 PostgreSQL
3. 高并发下可增加 Redis 做会话缓存
4. Session 与 Memory 建议统一落同一数据库事务边界，降低双写不一致风险
5. 如果未来进入多用户或多实例阶段，优先增加：
   - schema version
   - migration script
   - backup integrity check
