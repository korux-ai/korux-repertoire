# 阶段 5：twitter / facebook 可 invoke 能力包

**Status:** Ready（本仓清单可开工；跨仓真实发帖仍依赖下文「主仓配套」）  
**范围：** 仅 `packages/twitter` 与 `packages/facebook`；含可被 Korux 调用的包内 `runtime/`。  
**发版：** 本阶段完成后打不可变 tag `v0.2.0`（在 `v0.1.0` 两包之上追加 twitter / facebook）。LinkedIn、Instagram 发帖放到后续 `v0.3.0`，不进本阶段完成标准。  
**主仓对照：** Korux `docs/implementation/capability-repertoire/plan.md` 阶段 5 只保留跨仓验收；实现清单以本文为准。

---

## 目标

1. 官方目录提供两条写外联发帖能力：`twitter`（X）、`facebook`（Page 发帖）；每条帖可为纯文本，或文案 + **可选 1 张图**（JPEG/PNG）。
2. 包内含 manifest、governor、凭证文档、CHANGELOG、以及可执行的 `runtime/`（真实调用供应商 HTTP API）。
3. Korux 导入 `v0.2.0` 后，新建 Workflow 在 enabled ∩ Vault 绑定 ∩ 人审通过后可 invoke，且 `stub: false`。

---

## 前提与现状

- 本仓 `v0.1.0` 仅含 `send-email`、`web-research`；无社媒包。
- Korux seed 已有 `twitter` / `x`：catalog 与 governor 存在，**invoke 为 stub**（校验 Vault 后返回 `stub: true`，不打 X API）。
- Korux **无** `facebook` seed / connector / Vault 模板。
- Korux `connectors/proxy.py` 按工具名硬编码分支，**尚不能**按 `runtime.entry` 加载导入快照中的 `runtime/`。包内 runtime 要可跑，主仓须提供通用加载（见下文「主仓配套」）。本仓不实现 Korux 内核。

---

## 能力边界（本阶段只做这些）

| 包 id | 动作 | 不包含 |
|-------|------|--------|
| `twitter` | 发一条推文：文案必填（≤280 字）；可选 1 张 JPEG/PNG。无图：`POST /2/tweets`。有图：先 media upload，再 `POST /2/tweets` 带 `media_ids` | 多图、GIF/视频、线程、回复、删帖、读时间线、读/回评论 |
| `facebook` | 发一条 Page 帖：文案必填；可选 1 张 JPEG/PNG。无图：Graph `v21.0` `POST /{page-id}/feed`。有图：`POST /{page-id}/photos`（caption = 文案） | 多图/相册、视频、个人墙、评论、广告、Instagram |

图只来自 Korux 工作区文件：`args` 可选 `image_file_id`。平台在 invoke 前解析文件，经 `context` 传入字节（及 `filename` / `content_type`）；包内 **不** 按公网 URL 拉取、**不** 收 base64。无 `image_file_id` 时走纯文本路径。非 JPEG/PNG 或超过供应商限制则 fail-closed。

`trust`: `first-party`。`writes_external: true`，`default_gate: require_human`。`aliases`：`twitter` 保留 `x`，与主仓 seed 一致。读评论、回评论等 Marketing 互动能力不在本阶段，后续独立能力包。

---

## Runtime 策略：包内 `runtime/`（策略 A）

`runtime.entry` 固定为相对包根的模块路径：`runtime.invoke`。`transport`: `in_process`。`idempotent: false`。

禁止把入口写成 `korux.modules.connectors.proxy._twitter_invoke`（那是主仓 stub，且违背「目录即实现」）。

### 调用约定（供主仓加载器实现）

平台在 Governor 放行且 Vault 已解析后调用。签名钉死为：

```text
async def invoke(args: dict, secret: dict, context: dict) -> dict
```

包内用标准库同步发 HTTPS（可在该 coroutine 内直接调用）。成功/失败均返回**扁平 dict**（对齐现有 `proxy` 结果，**不是** runtime-contract 外层信封）。平台负责把该 dict 包装进 `{ok, result, side_effect, audit}`。

| 参数 | 内容 |
|------|------|
| `args` | 已通过 `input_schema`；twitter 必填 `content`；facebook 必填 `message`；可选 `image_file_id` |
| `secret` | Vault JSON 明文（仅本次调用传入，包内不得写入日志或审计明文） |
| `context` | `workspace_id` / `agent_id` / `execution_id` / `capability_version`；有图时含已解析的 `image`（`bytes` / `filename` / `content_type`），供审计字段回填 |

扁平成功响应须含 `ok: true`、`stub: false`、供应商返回的 id（如 `tweet_id` / `post_id`）、以及 `content` 或 `summary` 供下游。失败抛出或返回 `ok: false` + 稳定错误码（校验 / 凭证 / 供应商 4xx/5xx）。

实现约束：

- 仅用 Python 标准库（`urllib` 等）发 HTTPS，**不**在包内声明 pip 依赖，Release zip 不含 venv。
- 不 import `korux.*`。凭证解析、绑定、人审均在平台侧完成。
- 可选：环境变量 `KORUX_CAPABILITY_HTTP_MOCK=1` 时走本地假响应（`stub: true` 且不打外网），供无密钥 CI；**生产路径默认关 mock**。

### twitter 凭证（OAuth 1.0a User Context）

发推需要用户上下文，不用 App-only Bearer。Vault JSON 字段：

- `api_key` / `api_secret`（Consumer）
- `access_token` / `access_token_secret`

`docs/credential.md` 写明：X Developer Portal 申请、User Token 权限含 tweet.write 与 media.write、Vault 绑定 `tool_name=twitter`。

### facebook 凭证（Page）

- `page_id`
- `page_access_token`（长期 Page token；文档说明从 User token 换 Page token，禁止把 User token 当发帖凭证）

`binding_tool` / `invoke_tool`: `facebook`。

---

## 包目录（每个能力）

```text
packages/twitter/
  manifest.json
  governor.json
  runtime/
    __init__.py          # 导出 invoke
    invoke.py            # HTTP 实现（纯文本或先上传再发帖）
    oauth1.py            # twitter 签名（仅该包）
  docs/
    README.md
    credential.md
  CHANGELOG.md
```

`facebook` 同结构，无 `oauth1.py`。`packages/_template` 本阶段可补一节「runtime 签名」说明，不把示例当成可发版包。

Governor 硬底线（Owner **不可**关掉）：空正文 reject；`writes_external` → intercept + `require_human`。`editable_fields` 为 `content` / `message`，以及可选 `image_file_id`。人审卡须展示文案；有图时展示文件名（及平台已有的预览，若有）。

每日发帖上限、静默时段不放在本能力 governor（属 Workflow `per_window`）。必带 hashtag、法律免责声明、PII/LLM 审核不在本阶段。

### Owner 可配（`editable_governor_config`）

两包均声明下列字段；空列表 / 未填表示该项不额外收紧。求值用 `$owner.*`，命中则 **reject**（不调用供应商）。配置只可加严，不可放宽硬底线。

| 字段 | 类型 | 默认 | 规则 |
|------|------|------|------|
| `blocked_keywords` | string[] | `[]` | 文案（`content` / `message`）含子串（大小写不敏感）则 reject |
| `blocked_url_hosts` | string[] | `[]` | 从文案解析 `http(s)` URL；host 小写后若在列表中则 reject |
| `max_chars` | integer | twitter `280`；facebook `5000` | 文案长度超过则 reject；默认不超过平台上限（X 280） |

可选（本阶段写入 manifest，默认不收紧）：

| 字段 | 类型 | 默认 | 规则 |
|------|------|------|------|
| `max_mentions` | integer | 不限制（字段缺省或 `null`） | 文案中 `@` 次数超过则 reject |
| `require_image` | boolean | `false` | `true` 且无有效 `image_file_id` / `context.image` 则 reject |

主仓 invoke 前把绑定上的 `owner_config` 传入能力 governor（与 `web-research` 禁搜词同一路径）。

---

## 本仓任务清单

- [x] 从 `_template` 建立 `packages/twitter`、`packages/facebook`
- [x] 填写 manifest（I/O、schema、auth、params、`editable_governor_config`、`runtime.entry=runtime.invoke`、trust）
- [x] 写 governor（硬底线 + `$owner` 禁词 / 禁域名 / 字数；可选 mentions / 须带图）+ `docs/credential.md` + README + CHANGELOG
- [x] 实现 `runtime/`（纯文本发帖、单图上传+发帖、可选 HTTP mock）
- [x] `validate_all.sh` 绿。仅当 `runtime.entry` 为包相对路径（本阶段固定 `runtime.invoke`）时，要求存在 `runtime/invoke.py` 且导出 `invoke`；`send-email` / `web-research` 的 `korux.modules.*` 入口不要求包内 `runtime/`
- [x] 更新 README / CONTRIBUTING：本仓发版含 first-party `runtime/`，不再写「只收 manifest+governor」
- [ ] merge 后打 tag `v0.2.0`，确认 zip 含四包：`send-email`、`web-research`、`twitter`、`facebook`（无 `_template`）

---

## 主仓配套（Korux，不在本仓改代码）

无下列项则导入后 catalog 可见、invoke 仍 404 或继续走 twitter stub。

1. **通用加载：** 仅当 `trust=first-party`（或后续书面允许的 `verified`）且 `runtime.entry` 为包内模块时，从当前 `repertoire_ref` 的 `packages/<id>/` 用 `importlib` 加载 `invoke`。路径限制在 `CAPABILITY_CACHE_DIR` 或 builtin `packages/`。社区包不得执行包内代码。`facebook` 不得要求再向 `proxy.py` 加一条永久硬编码（twitter 现有 stub 分支改为走同一加载器，避免两套实现）。
2. **Connector 表：** 磁盘包 overlay 后 `get_connector("facebook")` 可用（从 catalog 推导 External + requires_secret，避免只认 `BUILTINS`）。
3. **Vault：** `facebook` 模板与 `twitter` 字段与包内 `auth.fields` 一致（当前主仓 Vault 无 twitter 专用模板时一并补）。
4. **文件注入：** 有 `image_file_id` 时从工作区读文件，校验 JPEG/PNG 后把字节放入 `context.image`；缺失或类型不符则 fail-closed，不调用供应商。
5. **Governor 绑定：** overlay 后的 twitter / facebook 暴露 `editable_governor_config`；invoke 前合并 `owner_config` 求值（与 web-research 禁搜词同一路径）。
6. **验收：** 导入 `v0.2.0` → 工作区默认 pin → 启用 + 绑定 → 人审后真实发帖（纯文本与单图各至少一条，或 mock 关时对测试账号）；旧 Spec 仍钉 `v0.1.0` / `builtin`，看不到 facebook。

---

## 非目标

- LinkedIn、Instagram（见下文「后续 `v0.3.0`」，不进本阶段 zip / 验收）
- 多图、GIF/视频、从公网 URL 拉图、invoke 内 base64 图
- 读评论、回评论、线程、删帖（后续独立能力，不塞进发帖包）
- 能力包内做每日发帖上限、静默时段、必带 hashtag、PII/LLM 审核
- 把 twitter/facebook 拷进主仓 git `packages/`（builtin 不强制同步；离线无导入则 facebook 不可用）
- 社区包动态加载任意代码（本阶段仅官方 first-party zip）
- 浮动 `latest`

---

## 后续 `v0.3.0`（不在本阶段实现）

在 `v0.2.0` 发帖链路（包内 runtime、人审、可选单图、`file_id` 注入）验收通过后再开。复用同一发帖 MVP：文案 + 可选 1 张 JPEG/PNG；`trust: first-party`；写外联人审。独立包 id，不与 `facebook` 共用 `invoke_tool`。

| 包 id | 动作 | 不包含 |
|-------|------|--------|
| `linkedin` | **仅 Company Page** 发一条帖（文案必填；可选 1 张 JPEG/PNG） | 个人资料发帖、多图、视频、评论、广告 |
| `instagram` | **仅** 已绑 Facebook Page 的 Instagram 专业号发 Feed（文案 + 可选 1 张 JPEG/PNG；无图时 fail-closed，本能力须带图） | 个人 IG、Stories、Reels、购物标签、评论 |

Instagram 与 Facebook 同属 Meta Graph，Vault 仍拆开：`instagram` 不得与 `facebook` 共用 `binding_tool`。主仓加载器沿用阶段 5 通用路径，不为这两包再写 `proxy.py` 硬编码。

---

## 完成标准

- repertoire Release `v0.2.0` zip 含两社媒包且 CI 校验通过。
- Korux 导入该 tag 后新 Workflow 可选 `twitter` / `facebook`。
- 绑定正确凭证并人审通过后，invoke 打到供应商 API（或文档约定的 mock 开关），响应 `stub: false`（非 mock）；纯文本与单图路径均可。
- 写外联路径仍走 governor 人审；密钥不进 git。
