# Error Code Reference

这份文档记录 Backend API 当前对外暴露的稳定错误码，以及它们的使用边界。

## 错误响应格式

所有业务错误和请求校验错误都统一返回：

```json
{
  "detail": {
    "success": false,
    "error": "Request validation failed.",
    "code": "REQUEST_VALIDATION_FAILED",
    "details": [
      {
        "field": "body.mode",
        "message": "Input should be 'direct', 'react' or 'plan'",
        "issueType": "literal_error"
      }
    ]
  }
}
```

说明：

- `error`: 面向调用方的可读错误描述
- `code`: 稳定错误码，供前端、脚本和告警规则匹配
- `details`: 可选补充信息
  - 请求校验失败时是 issue 列表
  - 业务错误时通常是结构化字典

## 稳定性规则

1. 已对外暴露的错误码只允许追加，不允许复用语义。
2. 同一类失败场景应持续返回同一错误码。
3. 请求模型、Query、Path 校验失败统一使用 `REQUEST_VALIDATION_FAILED`。
4. 业务语义错误优先返回显式业务码，不回退到泛化字符串。

## 当前错误码

- `REQUEST_VALIDATION_FAILED`
  - 请求体、Query、Path 不满足 contract
- `INVALID_ARGUMENT`
  - 参数语义存在问题，但不属于静态 schema 校验
- `SESSION_NOT_FOUND`
  - 会话不存在或关联数据不存在
- `MODEL_NOT_FOUND`
  - 模型不存在或不在当前可用目录中
- `CITY_NOT_FOUND`
  - 城市标识不存在
- `SHARE_INVALID`
  - 分享请求内容不合法
- `SHARE_NOT_FOUND`
  - 分享短链不存在
- `MAP_ROUTE_INVALID`
  - 路线预览参数不合法
- `MAP_ROUTE_ERROR`
  - 路线服务调用失败
- `METRICS_DISABLED`
  - metrics 端点被配置关闭
- `HTTP_ERROR`
  - 非业务化的通用 HTTP 异常兜底码

## 当前治理边界

当前错误码治理主要覆盖：

- `chat`
- `session`
- `model`
- `artifact`
- `share`
- `city`
- `map`
- `metrics`

如果未来新增 API，默认也应复用这套错误响应格式，并先补本文档再上线。
