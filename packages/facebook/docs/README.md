# facebook

First-party connector：向 **Facebook Page** 发一条帖。文案必填；可选一张 JPEG/PNG。

## 行为

- 无图：Graph `v21.0` `POST /{page-id}/feed`
- 有图：`POST /{page-id}/photos`（`caption` = 文案）
- `writes_external`：默认人审；空正文 reject
- 图只接受平台注入的 `context.image`，不拉公网 URL、不收 base64
- 凭证必须是 **长期 Page token**，禁止用 User token 发帖

## invoke

`runtime.entry` = `runtime.invoke`

```text
async def invoke(args, secret, context) -> dict
```

- `args.message` 必填；`args.image_file_id` 可选
- `secret`：`page_id` / `page_access_token`
- 成功扁平结果：`ok`、`stub`、`post_id`、`content` / `summary`
- `KORUX_CAPABILITY_HTTP_MOCK=1` 时不打外网，返回 `stub: true`

不包含：个人墙、多图/相册、视频、评论、广告、Instagram。

绑定与申请步骤见 [credential.md](credential.md)。
