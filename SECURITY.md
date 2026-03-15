# Security Policy

## Supported Branch

当前默认维护分支为：

- `main`

如果你发现安全问题，请默认以 `main` 为参考版本描述复现方式、影响范围和修复建议。

## Reporting a Vulnerability

如果你发现了潜在的安全问题，请不要直接公开提交包含利用细节的 issue。

建议按下面方式报告：

1. 准备最小复现信息
   - 影响模块
   - 触发条件
   - 影响范围
   - 是否涉及凭据、共享链接、数据泄露、提权或远程执行
2. 通过私密渠道联系维护者，并提供：
   - 问题描述
   - 复现步骤
   - 影响评估
   - 建议修复方式
3. 在修复和发布完成前，不公开利用细节

## Current Security Focus

当前仓库优先关注这些安全面：

- LLM / provider 密钥管理
- `config/*.yaml` 与 `.env` 中的敏感配置保护
- SSE / REST 接口的输入校验与错误降级
- share link 的最小暴露面
- 依赖漏洞与供应链更新
- 运行时数据目录 `data/` 的备份与恢复

## Security Baseline in Repository

当前仓库已经具备这些基础安全资产：

- [`.github/workflows/ci.yml`](/D:/projects/shuai/ShuaiTravelAgent/.github/workflows/ci.yml)
  - 基础测试与质量门禁
- [`.github/dependabot.yml`](/D:/projects/shuai/ShuaiTravelAgent/.github/dependabot.yml)
  - Python / npm 依赖更新建议
- [`docs/architecture/infrastructure-foundations.md`](/D:/projects/shuai/ShuaiTravelAgent/docs/architecture/infrastructure-foundations.md)
  - 基础设施与运行治理总览

## Secrets and Local Configuration

不要提交这些文件：

- `config/llm_config.yaml`
- `config/server_config.yaml`
- `.env`

仓库里应只提交模板文件：

- `config/llm_config.yaml.example`
- `config/server_config.yaml.example`
- `.env.example`

## Automated Checks

当前 CI 还会执行：

- `pip-audit -r requirements.txt`
- Dockerized `gitleaks`
- 契约快照校验（OpenAPI / SSE）

本地同步命令：

```bash
python scripts/export_openapi_snapshot.py
python scripts/export_sse_contract_snapshot.py
python scripts/runtime_doctor.py --json
```

## Next Hardening Steps

下一阶段优先建议：

1. 增加依赖审计自动化
2. 为 share link 增加过期或签名策略
3. 增加更清晰的运行时恢复和审计流程
4. 继续补充契约快照和回归检查
