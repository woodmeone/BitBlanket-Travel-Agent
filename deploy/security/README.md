# Security Ops Assets

这里存放仓库的安全扫描与 secret-scan 配置，避免安全资产继续散落在根目录。

当前已收口：

- [`gitleaks.toml`](./gitleaks.toml)
  - CI 与本地 `gitleaks` 扫描共用的 allowlist / example-token 例外规则

当前 CI 使用方式：

```bash
docker run --rm \
  -v "$PWD:/repo" \
  zricethezav/gitleaks:v8.24.2 \
  dir /repo --config /repo/ops/security/gitleaks.toml --no-banner --redact
```

维护约定：

1. 只在确有必要时增加 allowlist。
2. 每条 allowlist 都应尽量限定到明确路径或明确 placeholder token。
3. 如果扫描策略有变化，需同步更新 `README.md`、`docs/architecture/infrastructure-foundations.md` 和 `docs/reference/project-structure.md`。
