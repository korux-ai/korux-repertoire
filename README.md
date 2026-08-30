# korux-repertoire

官方 Korux 能力目录。本仓发布 **catalog 快照**（manifest、governor、凭证说明，以及 first-party 包内 `runtime/`）；Korux 只消费 **锁定的 GitHub Release zip**，不依赖浮动 `latest`。

SPDX-License-Identifier: Apache-2.0

信任分级、PR 评审与安全红线以 Korux [contributor-guide](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md) 为准。包字段见 [package-manifest](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/package-manifest.md)。

## 目录

```text
korux-repertoire/
  packages/              # 能力包；_template 为脚手架，不进 release catalog
    send-email/          # builtin 路径仍指向 Korux 模块
    web-research/
    twitter/             # 含 runtime.invoke
    facebook/
    _template/
  schemas/               # 可选：manifest / governor JSON Schema
  scripts/               # validate_all.sh · package_release.sh
  .github/workflows/     # CI（PR/push）与 tag Release
  CONTRIBUTING.md
  LICENSE
  README.md
```

`send-email` / `web-research` 的 `runtime.entry` 仍为 `korux.modules.*`。`twitter` / `facebook` 等 first-party 发帖包在目录内提供可执行 `runtime/`。

## 消费方式

1. 从 [Releases](https://github.com/korux-ai/korux-repertoire/releases) 下载 `korux-repertoire-vX.Y.Z.zip`。
2. 校验后解压到 Korux 工作区 `.data/capability/repertoire-vX.Y.Z/`。
3. Workflow / Run 以 `repertoire_ref`（`builtin` 或 `vX.Y.Z`）钉扎；未导入远程版时回退 Korux 主仓 builtin `packages/`。

公开目录为超集；主仓 `packages/` 为可离线启动的 first-party 子集。从 builtin 升到某 tag 须显式导入并切换 pin，不静默替换。旧 Workflow 保持原 ref；新建流继承工作区默认 pin。

目录内有包不等于可 invoke：仍须 catalog enabled、员工 Vault 绑定、以及 trust 分级。包内 `runtime/` 须由 Korux 按 `runtime.entry` 加载（仅 first-party）。

## 校验与发版

```bash
./scripts/validate_all.sh
./scripts/package_release.sh v0.2.0
```

推送 tag `vX.Y.Z` 后，Actions 上传 zip 到 [Releases](https://github.com/korux-ai/korux-repertoire/releases)。

## 贡献

见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 许可

本仓库以 [Apache License 2.0](./LICENSE) 授权（SPDX: `Apache-2.0`）。本许可证 **不** 授予 Korux 名称、商标或标识的使用权。官方 `trust: first-party` 发版与审核仍由 Korux 维护者执行；合并进本仓不等于默认可在生产 invoke。
