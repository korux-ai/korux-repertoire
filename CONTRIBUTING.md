# Contributing to korux-repertoire

本仓收 **Capability Package**：manifest、governor、docs；first-party 写外联包还须含可执行 `runtime/`。Korux 消费锁定 Release zip。权威规则在 Korux 规范，本文件只作入口。

## 本地校验

```bash
./scripts/validate_all.sh
# 或单包：
python3 scripts/validate_capability_package.py packages/<id>
```

`packages/_template` 不进 catalog / Release，不当生产包校验。`runtime.entry` 为 `runtime.invoke` 时须存在 `runtime/invoke.py` 并定义 `invoke`；`korux.modules.*` 入口不要求包内 `runtime/`。

打包（不提交 `dist/`）：

```bash
./scripts/package_release.sh v0.2.0
```

## 写外联与 Governor

PR 必须过 Korux 评审清单（本仓不另写一套规则）：

- [PR 评审清单](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#4-pr-评审清单)
  - [Manifest：`writes_external` / `default_gate`](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#41-manifest-与-schema)
  - [Governor 非空、不可放宽硬底线](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#43-governor)
- [安全红线](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#5-安全红线)
- [governor 规则语法](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/governor-rules.md)

写外联包（发帖、发信、写 Notion 等）硬性要求：`writes_external=true`、governor 非空、`default_gate=require_human`（书面例外除外）。社区包不得默认 `writes_external` + `auto` 且无 governor。禁止密钥、token、真实 PII 进入本仓。

## 新增包

1. 复制 `packages/_template/` 为 `packages/<kebab-id>/`。
2. 填写 `manifest.json`：`id`、`version`、I/O 外联标志、schema、auth、`params`、`default_gate`。first-party 发帖包 `runtime.entry=runtime.invoke`。
3. `writes_external=true` 时编写 governor；`auth.required=true` 时编写 `docs/credential.md`。
4. 实现 `runtime/invoke.py`（标准库 HTTPS；不 import `korux.*`）。
5. 本地校验通过后提交 PR，附 invoke 示例与 CHANGELOG。

完整步骤见 [新增能力流程](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#2-新增能力流程)。若必须改 Korux 内核接口，另开主仓 RFC，与本仓能力包 PR 分离。

## 许可与 DCO

本仓为 Apache-2.0。提交即视为 **inbound = outbound**：贡献按同一许可证授权，不附加额外条款（除非事先另有书面约定）。

每个 commit 须含 Developer Certificate of Origin 署名，例如：

```text
Signed-off-by: Your Name <you@example.com>
```

Git 可用 `git commit -s`。禁止提交密钥、token、真实 PII。许可证不含 Korux 商标。

## 发版

维护者推送不可变 tag `vX.Y.Z`。GitHub Actions `release.yml` 会校验、打 `korux-repertoire-vX.Y.Z.zip` 并挂到 Release（附 `SHA256SUMS`）。生产禁止依赖浮动 `latest`。
