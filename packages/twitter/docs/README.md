# twitter

First-party connector：发一条 X（Twitter）推文。文案必填；可选一张 JPEG/PNG。

## 行为

- 无图：`POST /2/tweets`
- 有图：先 `POST upload.twitter.com/1.1/media/upload.json`，再发推并带 `media_ids`
- `writes_external`：默认人审；空正文 reject
- 图只接受平台注入的 `context.image`（由 `image_file_id` 解析），不拉公网 URL、不收 base64

## invoke

`runtime.entry` = `runtime.invoke`

```text
async def invoke(args, secret, context) -> dict
```

- `args.content` 必填；`args.image_file_id` 可选
- `secret`：`api_key` / `api_secret` / `access_token` / `access_token_secret`
- 成功扁平结果：`ok`、`stub`、`tweet_id`、`content` / `summary`
- `KORUX_CAPABILITY_HTTP_MOCK=1` 时不打外网，返回 `stub: true`

不包含：多图、GIF/视频、线程、回复、删帖、读时间线、读/回评论。

绑定与申请步骤见 [credential.md](credential.md)。
