# korux-repertoire

本仓发 catalog 快照；Korux 通过 GitHub Release zip 消费；信任分级与评审见 Korux [contributor-guide](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md)。

## 目录

```text
korux-repertoire/
  packages/              # 能力包（含 _template 脚手架；_template 不进 release catalog）
  schemas/               # 可选：manifest / governor JSON Schema
  scripts/               # 校验与打包
  .github/workflows/     # CI 与 Release
  CONTRIBUTING.md
  README.md
```

## 消费方式

1. 从 [Releases](https://github.com/korux-ai/korux-repertoire/releases) 下载 `korux-repertoire-vX.Y.Z.zip`。
2. 校验后解压到 Korux 工作区 `.data/capability/repertoire-vX.Y.Z/`。
3. Workflow / Run 以 `repertoire_ref`（`builtin` 或 `vX.Y.Z`）钉扎；未导入远程版时回退主仓 builtin `packages/`。

公开目录为超集；主仓 `packages/` 为可离线启动的 first-party 子集。从 builtin 升到某 tag 须显式导入并切换 pin，不静默替换。

## 贡献

见 [CONTRIBUTING.md](./CONTRIBUTING.md)。
