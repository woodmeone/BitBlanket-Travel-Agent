# ADR-0002 Versioned Release Images

## Status

Status: accepted

## Context

- 当前项目已经进入持续维护阶段，发布镜像需要能被明确追踪、回滚和复盘。
- 旧的 release workflow 允许发布 `latest` 标签，这会让“某次发布到底对应哪个镜像”变得不确定。
- release manifest 之前只有镜像仓库地址，没有精确到可直接拉取的版本化引用。

## Decision

- 发布镜像禁止使用 `latest` 标签。
- 所有 release 都必须带明确的 `release_tag`。
  - tag 触发时直接使用 Git tag
  - 手动触发时必须显式输入 `release_tag`
- release workflow 默认发布两类标签：
  - 业务发布标签，例如 `v3.3.0`
  - 溯源标签，例如 `sha-abc1234`
- release manifest 必须记录：
  - `image`
  - `image_tag`
  - `image_ref`
- `latest` 只允许存在于本地临时概念里，例如 `local`、`local-compose`，不得进入正式发布链路。

## Consequences

- 好处：
  - 发版、回滚、排障和 support bundle 里的版本追溯会更确定。
  - release manifest 可以直接作为发布镜像坐标来源使用。
- 成本：
  - 手动 release 需要额外维护版本命名纪律。
  - 文档、脚本和交付清单都需要统一使用明确版本标签。
- 后续事项：
  - 补 staging / production 的环境提升规则
  - 评估是否继续把镜像 digest 也写入 release manifest
