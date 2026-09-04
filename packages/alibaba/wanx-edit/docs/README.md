# alibaba/wanx-edit

First-party connector: Alibaba Wanxiang (万相) **prompt-based image edit**.

## Behavior

- `POST .../services/aigc/multimodal-generation/generation`
- Input: edit `prompt` + one product image (URL or base64 data URI)
- Default model `wan2.6-image`, size `1K`, `n=1`
- Human gate; real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: video, group sequential storytelling, Model Studio console OAuth.

Binding: [credential.md](credential.md).
