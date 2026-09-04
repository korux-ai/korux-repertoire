# alibaba/wanx-edit — Vault credential

Bind tool name **`alibaba/wanx-edit`**.

Calls Alibaba **DashScope / Model Studio** Wanxiang multimodal image edit (default sync `wan2.6-image`).

## Prerequisites

1. Alibaba Cloud Bailian / DashScope API Key: https://help.aliyun.com/zh/model-studio/
2. Enable Wanxiang image generation/edit models for the account
3. Docs: https://help.aliyun.com/zh/model-studio/wan-image-generation-and-editing-api-reference

## Vault JSON

```json
{
  "api_key": "sk-xxxxxxxx",
  "base_url": "https://dashscope.aliyuncs.com/api/v1",
  "model": "wan2.6-image"
}
```

- `base_url` optional (default China DashScope). For intl use `https://dashscope-intl.aliyuncs.com/api/v1`, or a Model Studio workspace host when your account requires it.
- `model` optional; args.model overrides Vault default.

## Agent binding

1. Vault → secret kind `alibaba-dashscope`
2. Bind `tool_name`: **`alibaba/wanx-edit`**
3. Prefer `image_file_id` + Korux `context.image` (public_url or bytes→data URI)

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`.
