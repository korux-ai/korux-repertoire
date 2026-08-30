# Example capability package

贡献者脚手架。生产公开目录使用等价 `manifest.yaml` / `governor.yaml`；本目录以 JSON 供 `scripts/validate_capability_package.py` 零依赖校验。

规范见 Korux `docs/spec/capability-package/`。本目录不进 Release catalog。

## Runtime 签名（first-party 包内实现）

`runtime.entry` 为包相对路径时固定：

```text
async def invoke(args: dict, secret: dict, context: dict) -> dict
```

- 标准库 HTTPS；不 import `korux.*`；不声明 pip 依赖
- 返回扁平 dict（`ok` / `stub` / 供应商 id）；平台再包装 runtime-contract 信封
- `KORUX_CAPABILITY_HTTP_MOCK=1` 供无密钥 CI；生产默认关

