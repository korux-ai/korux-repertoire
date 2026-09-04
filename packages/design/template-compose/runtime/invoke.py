"""Compose product photo + logo + headline into one social card. Pillow preferred."""

from __future__ import annotations

import base64
import io
import os
import re
from typing import Any

MAX_HEADLINE = 80
MAX_CAPTION = 2000
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
LAYOUTS = {
    "xhs_portrait": (1080, 1440),
    "square": (1080, 1080),
    "landscape": (1440, 1080),
}
HEX_RE = re.compile(r"^#?[0-9A-Fa-f]{6}$")


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    return os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip() in {"1", "true", "TRUE", "yes"}


def _parse_hex(raw: str) -> tuple[int, int, int]:
    text = (raw or "").strip()
    if not text:
        return (196, 30, 58)  # brand-ish red default
    if not HEX_RE.match(text):
        return (196, 30, 58)
    if not text.startswith("#"):
        text = "#" + text
    value = int(text[1:], 16)
    return ((value >> 16) & 255, (value >> 8) & 255, value & 255)


def _load_pil():
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except ImportError:
        return None
    return Image, ImageDraw, ImageFont


def _bytes_from_slot(slot: Any, *, max_bytes: int) -> dict[str, Any]:
    if not isinstance(slot, dict):
        return _fail("VALIDATION", "image context slot missing")
    raw = slot.get("bytes")
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        return _fail("VALIDATION", "image bytes missing in context")
    data = bytes(raw)
    if len(data) > max_bytes:
        return _fail("VALIDATION", f"image exceeds {max_bytes} bytes")
    return {"ok": True, "bytes": data}


def _fit_contain(Image: Any, img: Any, box: tuple[int, int]) -> Any:
    tw, th = box
    img = img.convert("RGBA")
    src_w, src_h = img.size
    scale = min(tw / src_w, th / src_h)
    nw, nh = max(1, int(src_w * scale)), max(1, int(src_h * scale))
    resized = img.resize((nw, nh), resample=Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2), resized)
    return canvas


def _fit_cover(Image: Any, img: Any, box: tuple[int, int]) -> Any:
    tw, th = box
    img = img.convert("RGBA")
    src_w, src_h = img.size
    scale = max(tw / src_w, th / src_h)
    nw, nh = max(1, int(src_w * scale)), max(1, int(src_h * scale))
    resized = img.resize((nw, nh), resample=Image.Resampling.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def _font(ImageFont: Any, size: int) -> Any:
    for name in (
        "PingFang.ttc",
        "PingFangSC-Regular.otf",
        "Songti.ttc",
        "Arial Unicode.ttf",
        "Arial.ttf",
        "DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _compose(
    *,
    product: bytes,
    logo: bytes | None,
    headline: str,
    company_name: str,
    layout: str,
    accent: tuple[int, int, int],
) -> dict[str, Any]:
    loaded = _load_pil()
    if loaded is None:
        return _fail(
            "PROVIDER",
            "Pillow is required for design/template-compose on the Korux host (pip install Pillow)",
        )
    Image, ImageDraw, ImageFont = loaded
    width, height = LAYOUTS[layout]
    band = max(120, height // 6)
    photo_h = height - band

    try:
        product_img = Image.open(io.BytesIO(product))
    except Exception as exc:  # noqa: BLE001 — PIL raises many types
        return _fail("VALIDATION", f"product image unreadable: {exc}")

    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    photo = _fit_cover(Image, product_img, (width, photo_h))
    canvas.paste(photo.convert("RGB"), (0, 0))

    # Accent footer band
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, photo_h, width, height), fill=accent)

    if logo:
        try:
            logo_img = Image.open(io.BytesIO(logo))
        except Exception as exc:  # noqa: BLE001
            return _fail("VALIDATION", f"logo image unreadable: {exc}")
        logo_box = min(band - 32, width // 6)
        logo_fitted = _fit_contain(Image, logo_img, (logo_box, logo_box))
        # white plate behind logo
        plate = Image.new("RGBA", (logo_box + 16, logo_box + 16), (255, 255, 255, 230))
        plate.paste(logo_fitted, (8, 8), logo_fitted)
        canvas.paste(plate.convert("RGB"), (24, photo_h + (band - plate.size[1]) // 2))

    title_font = _font(ImageFont, size=max(28, width // 22))
    small_font = _font(ImageFont, size=max(18, width // 36))
    text_x = 24 + (min(band - 32, width // 6) + 40 if logo else 0)
    text_y = photo_h + band // 2 - 24
    if headline:
        draw.text((text_x, text_y), headline[:MAX_HEADLINE], fill=(255, 255, 255), font=title_font)
    if company_name:
        draw.text(
            (text_x, text_y + 40),
            company_name[:120],
            fill=(255, 255, 255),
            font=small_font,
        )

    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=90, optimize=True)
    return {"ok": True, "jpeg": out.getvalue()}


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = secret
    args = args or {}
    context = context or {}
    product_id = str(args.get("product_image_file_id") or "").strip()
    logo_id = str(args.get("logo_file_id") or "").strip()
    headline = str(args.get("headline") or args.get("title") or "").strip()
    caption = str(args.get("caption") or "").strip()
    company_name = str(args.get("company_name") or "").strip()
    layout = str(args.get("layout") or "xhs_portrait").strip().lower() or "xhs_portrait"
    style = str(args.get("style") or "").strip()
    accent = _parse_hex(str(args.get("accent_color") or ""))

    if not product_id:
        return _fail("VALIDATION", "product_image_file_id is required")
    if layout not in LAYOUTS:
        return _fail("VALIDATION", f"layout must be one of {sorted(LAYOUTS)}")
    if len(headline) > MAX_HEADLINE:
        return _fail("VALIDATION", f"headline exceeds {MAX_HEADLINE} characters")
    if len(caption) > MAX_CAPTION:
        return _fail("VALIDATION", f"caption exceeds {MAX_CAPTION} characters")

    max_bytes = DEFAULT_MAX_BYTES
    gov = context.get("governor") if isinstance(context.get("governor"), dict) else {}
    if gov.get("max_image_bytes") is not None:
        try:
            max_bytes = int(gov["max_image_bytes"])
        except (TypeError, ValueError):
            max_bytes = DEFAULT_MAX_BYTES

    if not caption and headline:
        caption = headline
    if style and caption and style not in caption:
        # keep style as metadata only; do not append unless caption empty
        pass

    if _http_mock():
        # Minimal valid JPEG header-ish stub payload (not a real image decode needed)
        stub = base64.b64encode(b"stub-jpeg").decode("ascii")
        title = headline or company_name or "product"
        return {
            "ok": True,
            "stub": True,
            "kind": "social_post",
            "title": title,
            "caption": caption or title,
            "layout": layout,
            "image_base64": stub,
            "content_type": "image/jpeg",
            "content": caption or title,
            "summary": f"compose stub ({layout})",
        }

    product_slot = context.get("product_image") or context.get("image")
    product = _bytes_from_slot(product_slot, max_bytes=max_bytes)
    if product.get("ok") is False:
        return _fail(
            "VALIDATION",
            "product_image_file_id set but context.product_image/image bytes missing",
        )

    logo_bytes: bytes | None = None
    if logo_id:
        logo_slot = context.get("logo")
        logo = _bytes_from_slot(logo_slot, max_bytes=max_bytes)
        if logo.get("ok") is False:
            return _fail("VALIDATION", "logo_file_id set but context.logo bytes missing")
        logo_bytes = logo["bytes"]

    composed = _compose(
        product=product["bytes"],
        logo=logo_bytes,
        headline=headline,
        company_name=company_name,
        layout=layout,
        accent=accent,
    )
    if composed.get("ok") is False:
        return composed

    title = headline or company_name or "product"
    body = caption or title
    b64 = base64.b64encode(composed["jpeg"]).decode("ascii")
    return {
        "ok": True,
        "stub": False,
        "kind": "social_post",
        "title": title,
        "caption": body,
        "layout": layout,
        "image_base64": b64,
        "content_type": "image/jpeg",
        "content": body,
        "summary": f"composed {layout}: {title}",
    }
