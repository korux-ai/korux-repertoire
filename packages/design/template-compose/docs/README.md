# design/template-compose

Internal compose connector: product photo + optional logo + headline → one JPEG card and a `social_post` artifact (`kind`, `title`, `caption`, `image_base64`).

## Behavior

- Layouts: `xhs_portrait` (default 1080×1440), `square`, `landscape`
- Reads `context.product_image` or `context.image`, and `context.logo` when `logo_file_id` is set
- On-image text uses system fonts when available; caption is always returned for publish steps
- **Requires Pillow** on the Korux runtime host (`pip install Pillow`)
- `KORUX_CAPABILITY_HTTP_MOCK=1` → stub artifact

## Downstream

Map `title` / `caption` / composed image into `xiaohongshu/publish` or other social connectors via workflow upstream fields (artifact contract, not producer id).

No Vault binding.
