"""OAuth 1.0a User Context signing (stdlib only)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import parse_qsl, quote, urlsplit


def percent_encode(value: str) -> str:
    return quote(str(value), safe="~")


def _param_string(params: dict[str, str]) -> str:
    items = [(percent_encode(k), percent_encode(v)) for k, v in params.items()]
    items.sort()
    return "&".join(f"{k}={v}" for k, v in items)


def oauth_authorization(
    method: str,
    url: str,
    *,
    api_key: str,
    api_secret: str,
    access_token: str,
    access_token_secret: str,
    extra_params: dict[str, str] | None = None,
) -> str:
    parts = urlsplit(url)
    base_url = f"{parts.scheme}://{parts.netloc}{parts.path}"
    oauth: dict[str, str] = {
        "oauth_consumer_key": api_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }
    sign_params = dict(oauth)
    sign_params.update(dict(parse_qsl(parts.query, keep_blank_values=True)))
    if extra_params:
        sign_params.update(extra_params)
    base = "&".join(
        [
            method.upper(),
            percent_encode(base_url),
            percent_encode(_param_string(sign_params)),
        ]
    )
    key = f"{percent_encode(api_secret)}&{percent_encode(access_token_secret)}".encode("ascii")
    digest = hmac.new(key, base.encode("utf-8"), hashlib.sha1).digest()
    oauth["oauth_signature"] = base64.b64encode(digest).decode("ascii")
    header = ", ".join(
        f'{percent_encode(k)}="{percent_encode(v)}"' for k, v in sorted(oauth.items())
    )
    return f"OAuth {header}"
