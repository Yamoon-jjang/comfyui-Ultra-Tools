# comfyui-Ultra-Tools · Translator module
# ComfyUI custom node for lightweight text translation.
# Primary service: shared Google Cloud Translation API key when configured,
# with the existing free Google web routes and MyMemory as fallbacks.

from __future__ import annotations

import html
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


COMMON_LANGUAGES = [
    "auto",
    "english",
    "korean",
    "japanese",
    "chinese (simplified)",
    "chinese (traditional)",
    "spanish",
    "french",
    "german",
    "italian",
    "portuguese",
    "russian",
    "ukrainian",
    "vietnamese",
    "thai",
    "indonesian",
    "hindi",
    "arabic",
    "turkish",
    "dutch",
    "polish",
]

TARGET_LANGUAGES = [lang for lang in COMMON_LANGUAGES if lang != "auto"]


_GOOGLE_LANGUAGE_CODES = {
    "auto": "auto",
    "english": "en",
    "korean": "ko",
    "japanese": "ja",
    "chinese (simplified)": "zh-CN",
    "chinese (traditional)": "zh-TW",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "russian": "ru",
    "ukrainian": "uk",
    "vietnamese": "vi",
    "thai": "th",
    "indonesian": "id",
    "hindi": "hi",
    "arabic": "ar",
    "turkish": "tr",
    "dutch": "nl",
    "polish": "pl",
}

# MyMemory uses locale-style codes for many languages.  Its API also accepts
# source="auto"; auto-detection is weaker than Google's but is useful as a
# genuinely independent emergency fallback when Google is temporarily limited.
_MYMEMORY_LANGUAGE_CODES = {
    "auto": "auto",
    "english": "en-GB",
    "korean": "ko-KR",
    "japanese": "ja-JP",
    "chinese (simplified)": "zh-CN",
    "chinese (traditional)": "zh-TW",
    "spanish": "es-ES",
    "french": "fr-FR",
    "german": "de-DE",
    "italian": "it-IT",
    "portuguese": "pt-PT",
    "russian": "ru-RU",
    "ukrainian": "uk-UA",
    "vietnamese": "vi-VN",
    "thai": "th-TH",
    "indonesian": "id-ID",
    "hindi": "hi-IN",
    "arabic": "ar-SA",
    "turkish": "tr-TR",
    "dutch": "nl-NL",
    "polish": "pl-PL",
}


class _TranslationRouteUnavailableError(RuntimeError):
    """A configured online route could not be reached or used."""


class _TranslationRouteRateLimitedError(_TranslationRouteUnavailableError):
    """The provider explicitly rate-limited this process/IP."""


class _TranslationRouteConfigurationError(_TranslationRouteUnavailableError):
    """An explicitly configured official translation route needs attention."""


class _TranslationRouteCoolingDownError(_TranslationRouteUnavailableError):
    """A provider is intentionally skipped while a recent 429 cools down."""


class _TranslationRouteUnusableResultError(RuntimeError):
    """A reachable route returned no safe usable translation."""


_PROVIDER_LOCK = threading.Lock()
_GOOGLE_CLOUD_LAST_REQUEST_AT = 0.0
_GOOGLE_CLOUD_COOLDOWN_UNTIL = 0.0
_GOOGLE_LAST_REQUEST_AT = 0.0
_GOOGLE_COOLDOWN_UNTIL = 0.0
_MYMEMORY_LAST_REQUEST_AT = 0.0
_MYMEMORY_COOLDOWN_UNTIL = 0.0

# Do not hammer free/no-key services.  More important than the exact interval is
# the provider-wide cooldown: after one 429, later lines/nodes temporarily use
# the independent fallback instead of immediately repeating the same failure.
_GOOGLE_CLOUD_MIN_REQUEST_INTERVAL_SECONDS = 0.05
_GOOGLE_MIN_REQUEST_INTERVAL_SECONDS = 0.65
_MYMEMORY_MIN_REQUEST_INTERVAL_SECONDS = 0.30
_GOOGLE_CLOUD_DEFAULT_429_COOLDOWN_SECONDS = 30.0
_GOOGLE_DEFAULT_429_COOLDOWN_SECONDS = 30.0
_MYMEMORY_DEFAULT_429_COOLDOWN_SECONDS = 20.0
_MAX_RETRY_AFTER_SECONDS = 120.0
_TRANSIENT_RETRY_DELAY_SECONDS = 0.9

# MyMemory's public endpoint is intentionally kept under its documented short
# text envelope.  Long input is split on natural boundaries only for this route.
_MYMEMORY_CHUNK_LIMIT_BYTES = 480

# Small success cache avoids re-requesting identical text across repeated queue
# runs.  It is deliberately bounded and stores only successful translations.
_CACHE_LOCK = threading.Lock()
_TRANSLATION_CACHE: Dict[Tuple[str, str, str, str, bool], str] = {}
_TRANSLATION_CACHE_ORDER: List[Tuple[str, str, str, str, bool]] = []
_TRANSLATION_CACHE_LIMIT = 192

# Shared official Google Cloud Translation Basic v2 key.  Ultra Translator uses
# the same ComfyUI-user-local config file as Ultra MiniMax H3 Prompt so either
# node can use one key without placing the secret in a workflow.
_SHARED_API_CONFIG_SCHEMA_VERSION = 1
_SHARED_API_KEY_MAX_LENGTH = 512
_SHARED_API_CONFIG_LOCK = threading.Lock()


def _shared_translation_state_dir(create: bool = False) -> Optional[Path]:
    try:
        import folder_paths  # type: ignore

        get_user_directory = getattr(folder_paths, "get_user_directory", None)
        if not callable(get_user_directory):
            return None
        root = Path(str(get_user_directory())).expanduser() / "ultra_minimax_h3_prompt"
        if create:
            root.mkdir(parents=True, exist_ok=True)
        return root
    except Exception:
        return None


def _shared_translation_api_config_path(create: bool = False) -> Optional[Path]:
    root = _shared_translation_state_dir(create=create)
    return (root / "translation_api_config_v1.json") if root is not None else None


def _normalize_google_cloud_translation_api_key(value: Any) -> str:
    key = str(value or "").strip()
    if not key:
        return ""
    if len(key) > _SHARED_API_KEY_MAX_LENGTH:
        raise ValueError("Google Cloud Translation API key is too long.")
    if len(key) < 20 or not re.fullmatch(r"[A-Za-z0-9_-]+", key):
        raise ValueError("Google Cloud Translation API key format is invalid.")
    return key


def _google_cloud_translation_api_key() -> str:
    """Read the shared key from disk each time so H3-side changes are immediate."""
    path = _shared_translation_api_config_path(create=False)
    if path is None or not path.is_file():
        return ""
    try:
        if path.stat().st_size > 64 * 1024:
            return ""
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("schema", 0)) != _SHARED_API_CONFIG_SCHEMA_VERSION:
            return ""
        return _normalize_google_cloud_translation_api_key(
            payload.get("google_cloud_translation_api_key", "")
        )
    except Exception:
        return ""


def _write_shared_translation_api_key(key: str) -> bool:
    path = _shared_translation_api_config_path(create=True)
    if path is None:
        return False
    tmp = path.with_name(path.name + ".tmp")
    payload = {
        "schema": _SHARED_API_CONFIG_SCHEMA_VERSION,
        "google_cloud_translation_api_key": key,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except Exception:
            pass
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass
        return True
    except Exception:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        return False


def _loaded_h3_prompt_module():
    """Best-effort bridge so saving here also refreshes H3's in-memory key."""
    for module in list(sys.modules.values()):
        if module is None:
            continue
        try:
            filename = Path(str(getattr(module, "__file__", ""))).name
        except Exception:
            filename = ""
        if filename != "ultra_minimax_h3_prompt.py":
            continue
        if callable(getattr(module, "_google_cloud_translation_api_key", None)):
            return module
    return None


def _save_google_cloud_translation_api_key(value: Any) -> bool:
    key = _normalize_google_cloud_translation_api_key(value)
    if not key:
        raise ValueError("Google Cloud Translation API key is empty.")
    with _SHARED_API_CONFIG_LOCK:
        h3 = _loaded_h3_prompt_module()
        save = getattr(h3, "_save_google_cloud_translation_api_key", None) if h3 is not None else None
        if callable(save):
            try:
                if bool(save(key)):
                    return True
            except Exception:
                pass
        return _write_shared_translation_api_key(key)


def _clear_google_cloud_translation_api_key() -> bool:
    with _SHARED_API_CONFIG_LOCK:
        h3 = _loaded_h3_prompt_module()
        clear = getattr(h3, "_clear_google_cloud_translation_api_key", None) if h3 is not None else None
        if callable(clear):
            try:
                if bool(clear()):
                    return True
            except Exception:
                pass
        path = _shared_translation_api_config_path(create=False)
        try:
            if path is not None and path.exists():
                path.unlink()
            return True
        except Exception:
            return False


def _google_cloud_translation_api_status() -> Dict[str, Any]:
    return {
        "configured": bool(_google_cloud_translation_api_key()),
        "provider": "google_cloud_translation_v2",
        "workflow_exposed": False,
        "shared_with_ultra_minimax_h3_prompt": True,
    }


def _sleep(seconds: float) -> None:
    time.sleep(max(0.0, float(seconds)))


def _language_code(mapping: Dict[str, str], language: str, provider: str) -> str:
    key = (language or "").strip().lower()
    try:
        return mapping[key]
    except KeyError as exc:
        raise ValueError(f"Unsupported {provider} language: {language}") from exc


def _mymemory_source_code(source: str, text: str) -> str:
    """Resolve MyMemory source code without relying on unsupported auto detection.

    Explicit user selections always win.  For ``auto`` we only use lightweight
    script detection where it is reasonably strong, then preserve the legacy
    Latin-text fallback to English.  Users translating another Latin-script
    language can select that source explicitly.
    """
    key = (source or "auto").strip().lower()
    if key != "auto":
        return _language_code(_MYMEMORY_LANGUAGE_CODES, key, "MyMemory")

    probe = text or ""
    if re.search(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7a3]", probe):
        return _MYMEMORY_LANGUAGE_CODES["korean"]
    if re.search(r"[\u3040-\u30ff]", probe):
        return _MYMEMORY_LANGUAGE_CODES["japanese"]
    if re.search(r"[\u0e00-\u0e7f]", probe):
        return _MYMEMORY_LANGUAGE_CODES["thai"]
    if re.search(r"[\u0600-\u06ff]", probe):
        return _MYMEMORY_LANGUAGE_CODES["arabic"]
    if re.search(r"[\u0900-\u097f]", probe):
        return _MYMEMORY_LANGUAGE_CODES["hindi"]
    if re.search(r"[\u0400-\u04ff]", probe):
        return _MYMEMORY_LANGUAGE_CODES["russian"]
    if re.search(r"[\u3400-\u9fff]", probe):
        return _MYMEMORY_LANGUAGE_CODES["chinese (simplified)"]
    return _MYMEMORY_LANGUAGE_CODES["english"]


def _retry_after_seconds(headers) -> Optional[float]:
    try:
        value = headers.get("Retry-After") if headers is not None else None
    except Exception:
        value = None
    if not value:
        return None

    value = str(value).strip()
    try:
        seconds = float(value)
        if seconds >= 0:
            return min(seconds, _MAX_RETRY_AFTER_SECONDS)
    except Exception:
        pass

    try:
        retry_at = parsedate_to_datetime(value)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        seconds = (retry_at - datetime.now(timezone.utc)).total_seconds()
        if seconds >= 0:
            return min(seconds, _MAX_RETRY_AFTER_SECONDS)
    except Exception:
        pass
    return None


def _provider_wait(provider: str) -> None:
    global _GOOGLE_CLOUD_LAST_REQUEST_AT, _GOOGLE_LAST_REQUEST_AT, _MYMEMORY_LAST_REQUEST_AT

    while True:
        with _PROVIDER_LOCK:
            now = time.monotonic()
            if provider == "google_cloud":
                if now < _GOOGLE_CLOUD_COOLDOWN_UNTIL:
                    remaining = max(0.0, _GOOGLE_CLOUD_COOLDOWN_UNTIL - now)
                    raise _TranslationRouteCoolingDownError(
                        f"Google Cloud Translation is cooling down after a recent HTTP 429 ({remaining:.1f}s remaining)"
                    )
                wait_for = _GOOGLE_CLOUD_MIN_REQUEST_INTERVAL_SECONDS - (now - _GOOGLE_CLOUD_LAST_REQUEST_AT)
                if wait_for <= 0:
                    _GOOGLE_CLOUD_LAST_REQUEST_AT = now
                    return
            elif provider == "google":
                if now < _GOOGLE_COOLDOWN_UNTIL:
                    remaining = max(0.0, _GOOGLE_COOLDOWN_UNTIL - now)
                    raise _TranslationRouteCoolingDownError(
                        f"Google translation is cooling down after a recent HTTP 429 ({remaining:.1f}s remaining)"
                    )
                wait_for = _GOOGLE_MIN_REQUEST_INTERVAL_SECONDS - (now - _GOOGLE_LAST_REQUEST_AT)
                if wait_for <= 0:
                    _GOOGLE_LAST_REQUEST_AT = now
                    return
            elif provider == "mymemory":
                if now < _MYMEMORY_COOLDOWN_UNTIL:
                    remaining = max(0.0, _MYMEMORY_COOLDOWN_UNTIL - now)
                    raise _TranslationRouteCoolingDownError(
                        f"MyMemory translation is cooling down after a recent HTTP 429 ({remaining:.1f}s remaining)"
                    )
                wait_for = _MYMEMORY_MIN_REQUEST_INTERVAL_SECONDS - (now - _MYMEMORY_LAST_REQUEST_AT)
                if wait_for <= 0:
                    _MYMEMORY_LAST_REQUEST_AT = now
                    return
            else:
                return
        _sleep(wait_for)


def _provider_note_429(provider: str, headers=None) -> None:
    global _GOOGLE_CLOUD_COOLDOWN_UNTIL, _GOOGLE_COOLDOWN_UNTIL, _MYMEMORY_COOLDOWN_UNTIL

    now = time.monotonic()
    retry_after = _retry_after_seconds(headers)
    with _PROVIDER_LOCK:
        if provider == "google_cloud":
            cooldown = max(5.0, retry_after) if retry_after is not None else _GOOGLE_CLOUD_DEFAULT_429_COOLDOWN_SECONDS
            _GOOGLE_CLOUD_COOLDOWN_UNTIL = max(_GOOGLE_CLOUD_COOLDOWN_UNTIL, now + cooldown)
        elif provider == "google":
            cooldown = max(5.0, retry_after) if retry_after is not None else _GOOGLE_DEFAULT_429_COOLDOWN_SECONDS
            _GOOGLE_COOLDOWN_UNTIL = max(_GOOGLE_COOLDOWN_UNTIL, now + cooldown)
        elif provider == "mymemory":
            cooldown = max(3.0, retry_after) if retry_after is not None else _MYMEMORY_DEFAULT_429_COOLDOWN_SECONDS
            _MYMEMORY_COOLDOWN_UNTIL = max(_MYMEMORY_COOLDOWN_UNTIL, now + cooldown)


def _looks_like_provider_error_page(text: str) -> bool:
    probe = re.sub(r"\s+", " ", (text or "")).strip().lower()
    if not probe:
        return True
    if re.search(r"\berror\s+[45]\d\d\b", probe):
        return True
    markers = (
        "too many requests",
        "server error",
        "service unavailable",
        "that's an error",
        "that’s an error",
        "there was an error",
        "please try again later",
        "unusual traffic",
        "our systems have detected",
        "<html",
        "<!doctype html",
    )
    return any(marker in probe for marker in markers)


def _exception_has_http_status(exc: BaseException, wanted: int) -> bool:
    seen = set()
    current: Optional[BaseException] = exc
    for _ in range(8):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        code = getattr(current, "code", None)
        if isinstance(code, int) and code == wanted:
            return True
        response = getattr(current, "response", None)
        status = getattr(response, "status_code", None) if response is not None else None
        if isinstance(status, int) and status == wanted:
            return True
        current = current.__cause__ or current.__context__
    return False


def _translation_exception_diagnostic(exc: BaseException) -> str:
    """Prompt-safe structural diagnostics; never stringify URLs/source text."""
    parts: List[str] = []
    seen = set()
    current: Optional[BaseException] = exc

    for _ in range(6):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))

        name = type(current).__name__
        meta: List[str] = []
        code = getattr(current, "code", None)
        response = getattr(current, "response", None)
        status = getattr(response, "status_code", None) if response is not None else None
        if not isinstance(status, int) and isinstance(code, int):
            status = code
        if isinstance(status, int):
            meta.append(f"HTTP {status}")
        if "timeout" in name.lower():
            meta.append("timeout")
        reason = getattr(current, "reason", None)
        if reason is not None and not isinstance(reason, (str, bytes)):
            reason_name = type(reason).__name__
            if reason_name and reason_name != name:
                meta.append(f"reason={reason_name}")
            if "timeout" in reason_name.lower() and "timeout" not in meta:
                meta.append("timeout")
        parts.append(f"{name}[{','.join(meta)}]" if meta else name)
        current = current.__cause__ or current.__context__

    return ">".join(parts) if parts else type(exc).__name__


def _translation_routes_diagnostic(errors: List[Tuple[str, Exception]]) -> str:
    return "; ".join(
        f"{label}={_translation_exception_diagnostic(exc)}"
        for label, exc in errors
    )


def _cache_get(key: Tuple[str, str, str, str, bool]) -> Optional[str]:
    with _CACHE_LOCK:
        value = _TRANSLATION_CACHE.get(key)
        if value is None:
            return None
        try:
            _TRANSLATION_CACHE_ORDER.remove(key)
        except ValueError:
            pass
        _TRANSLATION_CACHE_ORDER.append(key)
        return value


def _cache_put(key: Tuple[str, str, str, str, bool], value: str) -> None:
    with _CACHE_LOCK:
        _TRANSLATION_CACHE[key] = value
        try:
            _TRANSLATION_CACHE_ORDER.remove(key)
        except ValueError:
            pass
        _TRANSLATION_CACHE_ORDER.append(key)
        while len(_TRANSLATION_CACHE_ORDER) > _TRANSLATION_CACHE_LIMIT:
            old_key = _TRANSLATION_CACHE_ORDER.pop(0)
            _TRANSLATION_CACHE.pop(old_key, None)


def _decode_http_body(response, raw: bytes) -> str:
    charset = None
    try:
        charset = response.headers.get_content_charset()
    except Exception:
        charset = None
    return raw.decode(charset or "utf-8", errors="replace")


def _translate_google_cloud_v2_request(
    text: str,
    source: str,
    target: str,
    *,
    api_key: Optional[str] = None,
    use_provider_guard: bool = True,
) -> str:
    """Official Google Cloud Translation Basic v2 route using the shared H3 key."""
    key = _normalize_google_cloud_translation_api_key(
        api_key if api_key is not None else _google_cloud_translation_api_key()
    )
    if not key:
        raise _TranslationRouteConfigurationError(
            "Google Cloud Translation API key is not configured."
        )

    source_code = _language_code(_GOOGLE_LANGUAGE_CODES, source, "Google")
    target_code = _language_code(_GOOGLE_LANGUAGE_CODES, target, "Google")
    body_payload: Dict[str, Any] = {
        "q": text,
        "target": target_code,
        "format": "text",
    }
    if source_code != "auto":
        body_payload["source"] = source_code

    if use_provider_guard:
        _provider_wait("google_cloud")

    request = Request(
        "https://translation.googleapis.com/language/translate/v2",
        data=json.dumps(body_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "x-goog-api-key": key,
            "User-Agent": "Ultra-Translator/1.0",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read(2_000_000)
            body = _decode_http_body(response, raw)
    except HTTPError as exc:
        error_text = ""
        if exc.code in (400, 401, 403, 429):
            try:
                error_text = exc.read(200_000).decode("utf-8", errors="replace").lower()
            except Exception:
                error_text = ""
        quota_limited_403 = exc.code == 403 and any(
            token in error_text
            for token in (
                "quota", "rate limit", "ratelimit", "resource_exhausted",
                "daily limit", "user rate limit", "limit exceeded",
            )
        )
        if exc.code == 429 or quota_limited_403:
            if use_provider_guard:
                _provider_note_429("google_cloud", exc.headers)
            raise _TranslationRouteRateLimitedError(
                f"Google Cloud Translation API was rate/quota limited (HTTP {exc.code})"
            ) from exc
        if exc.code in (400, 401, 403):
            raise _TranslationRouteConfigurationError(
                "Google Cloud Translation API rejected the configured key/project settings"
            ) from exc
        raise _TranslationRouteUnavailableError(
            f"Google Cloud Translation API request failed (HTTP {exc.code})"
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise _TranslationRouteUnavailableError(
            "Google Cloud Translation API request failed"
        ) from exc

    try:
        payload = json.loads(body)
        translations = ((payload.get("data") or {}).get("translations") or [])
        translated = ""
        if translations and isinstance(translations[0], dict):
            translated = html.unescape(str(translations[0].get("translatedText") or "")).strip()
    except Exception as exc:
        raise _TranslationRouteUnusableResultError(
            "Google Cloud Translation API returned an unexpected response"
        ) from exc

    if not translated or _looks_like_provider_error_page(translated):
        raise _TranslationRouteUnusableResultError(
            "Google Cloud Translation API returned no usable translation"
        )
    return translated


def _translate_google_json_request(text: str, source: str, target: str) -> str:
    """Primary no-key Google JSON route with one bounded retry for transient 5xx/network errors."""
    params = urlencode(
        {
            "client": "gtx",
            "sl": _language_code(_GOOGLE_LANGUAGE_CODES, source, "Google"),
            "tl": _language_code(_GOOGLE_LANGUAGE_CODES, target, "Google"),
            "dt": "t",
            "ie": "UTF-8",
            "oe": "UTF-8",
            "q": text,
        }
    )
    url = f"https://translate.googleapis.com/translate_a/single?{params}"

    last_error: Optional[Exception] = None
    for attempt in range(2):
        _provider_wait("google")
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read(2_000_000)
        except HTTPError as exc:
            last_error = exc
            if exc.code == 429:
                _provider_note_429("google", exc.headers)
                raise _TranslationRouteRateLimitedError(
                    "Google JSON translation was rate-limited (HTTP 429)"
                ) from exc
            if exc.code in (500, 502, 503, 504) and attempt == 0:
                _sleep(_TRANSIENT_RETRY_DELAY_SECONDS)
                continue
            raise _TranslationRouteUnavailableError(
                f"Google JSON translation request failed (HTTP {exc.code})"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == 0:
                _sleep(_TRANSIENT_RETRY_DELAY_SECONDS)
                continue
            raise _TranslationRouteUnavailableError(
                "Google JSON translation request failed"
            ) from exc

        try:
            payload = json.loads(_decode_http_body(response, raw))
            segments = payload[0]
            translated = "".join(
                segment[0]
                for segment in segments
                if isinstance(segment, list) and segment and isinstance(segment[0], str)
            ).strip()
        except Exception as exc:
            raise _TranslationRouteUnusableResultError(
                "Google JSON translation returned an unexpected response"
            ) from exc

        if not translated or _looks_like_provider_error_page(translated):
            raise _TranslationRouteUnusableResultError(
                "Google JSON translation returned no usable translation"
            )
        return translated

    if last_error is not None:
        raise _TranslationRouteUnavailableError("Google JSON translation failed") from last_error
    raise _TranslationRouteUnavailableError("Google JSON translation failed")


def _translate_google_mobile_request(text: str, source: str, target: str) -> str:
    """Secondary Google route. Automatically skipped during a provider 429 cooldown."""
    params = urlencode(
        {
            "sl": _language_code(_GOOGLE_LANGUAGE_CODES, source, "Google"),
            "tl": _language_code(_GOOGLE_LANGUAGE_CODES, target, "Google"),
            "hl": "en",
            "q": text,
        }
    )
    _provider_wait("google")
    request = Request(
        f"https://translate.google.com/m?{params}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read(2_000_000)
            page = _decode_http_body(response, raw)
    except HTTPError as exc:
        if exc.code == 429:
            _provider_note_429("google", exc.headers)
            raise _TranslationRouteRateLimitedError(
                "Google mobile translation was rate-limited (HTTP 429)"
            ) from exc
        raise _TranslationRouteUnavailableError(
            f"Google mobile translation request failed (HTTP {exc.code})"
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise _TranslationRouteUnavailableError(
            "Google mobile translation request failed"
        ) from exc

    try:
        match = re.search(
            r'<div[^>]*class=["\']result-container["\'][^>]*>(.*?)</div>',
            page,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            raise ValueError("result-container not found")
        translated = re.sub(r"<[^>]+>", "", match.group(1))
        translated = html.unescape(translated)
        translated = re.sub(r"\s+", " ", translated).strip()
    except Exception as exc:
        raise _TranslationRouteUnusableResultError(
            "Google mobile translation returned an unexpected response"
        ) from exc

    if not translated or _looks_like_provider_error_page(translated):
        raise _TranslationRouteUnusableResultError(
            "Google mobile translation returned no usable translation"
        )
    return translated


def _split_text_for_mymemory(
    text: str,
    limit_bytes: int = _MYMEMORY_CHUNK_LIMIT_BYTES,
) -> List[str]:
    """Split conservatively by UTF-8 bytes; MyMemory limits q to 500 bytes."""
    if len(text.encode("utf-8")) <= limit_bytes:
        return [text]

    chunks: List[str] = []
    remaining = text
    boundary_pattern = re.compile(r"[.!?。！？]\s+|[,;:]\s+|\s+")
    while remaining:
        if len(remaining.encode("utf-8")) <= limit_bytes:
            chunks.append(remaining)
            break

        used_bytes = 0
        char_limit = 0
        for index, char in enumerate(remaining):
            char_bytes = len(char.encode("utf-8"))
            if used_bytes + char_bytes > limit_bytes:
                break
            used_bytes += char_bytes
            char_limit = index + 1
        if char_limit <= 0:
            char_limit = 1

        candidate = remaining[:char_limit]
        search_floor_bytes = max(1, int(limit_bytes * 0.55))
        cuts: List[int] = []
        for match in boundary_pattern.finditer(candidate):
            if len(candidate[:match.end()].encode("utf-8")) >= search_floor_bytes:
                cuts.append(match.end())
        cut = max(cuts) if cuts else char_limit
        # Preserve newline sentinels as atomic units so the common one-request
        # newline-preservation path does not degrade into many per-line calls.
        token_pattern = re.compile(r"ULTRATRANSLATORBREAK\d{4}X", flags=re.IGNORECASE)
        for token_match in token_pattern.finditer(remaining):
            if token_match.start() < cut < token_match.end():
                before = token_match.start()
                after = token_match.end()
                if before > 0:
                    cut = before
                elif len(remaining[:after].encode("utf-8")) <= limit_bytes:
                    cut = after
                break
        chunk = remaining[:cut].strip()
        if not chunk:
            chunk = remaining[:char_limit]
            cut = char_limit
        chunks.append(chunk)
        remaining = remaining[cut:].lstrip()
    return chunks


def _translate_mymemory_single(text: str, source: str, target: str) -> str:
    _provider_wait("mymemory")
    params = urlencode(
        {
            "q": text,
            "langpair": (
                f"{_mymemory_source_code(source, text)}|"
                f"{_language_code(_MYMEMORY_LANGUAGE_CODES, target, 'MyMemory')}"
            ),
        }
    )
    request = Request(
        f"https://api.mymemory.translated.net/get?{params}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read(2_000_000)
            body = _decode_http_body(response, raw)
    except HTTPError as exc:
        if exc.code == 429:
            _provider_note_429("mymemory", exc.headers)
            raise _TranslationRouteRateLimitedError(
                "MyMemory translation was rate-limited (HTTP 429)"
            ) from exc
        raise _TranslationRouteUnavailableError(
            f"MyMemory translation request failed (HTTP {exc.code})"
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise _TranslationRouteUnavailableError("MyMemory translation request failed") from exc

    try:
        payload = json.loads(body)
        response_data = payload.get("responseData") or {}
        translated = response_data.get("translatedText") or ""
        translated = html.unescape(str(translated)).strip()
        response_status = payload.get("responseStatus")
        try:
            response_status_code = int(response_status) if response_status is not None else 200
        except (TypeError, ValueError):
            response_status_code = 200
        if response_status_code >= 400:
            raise ValueError(f"responseStatus={response_status_code}")
        if not translated:
            matches = payload.get("matches") or []
            for match in matches:
                if isinstance(match, dict) and match.get("translation"):
                    translated = html.unescape(str(match["translation"])).strip()
                    break
    except Exception as exc:
        raise _TranslationRouteUnusableResultError(
            "MyMemory translation returned an unexpected response"
        ) from exc

    if not translated or _looks_like_provider_error_page(translated):
        raise _TranslationRouteUnusableResultError(
            "MyMemory translation returned no usable translation"
        )
    return translated


def _translate_mymemory_request(text: str, source: str, target: str) -> str:
    chunks = _split_text_for_mymemory(text)
    translated_chunks = [_translate_mymemory_single(chunk, source, target) for chunk in chunks]
    return " ".join(part.strip() for part in translated_chunks if part.strip()).strip()


def _translate_google_with_independent_fallback(text: str, source: str, target: str) -> str:
    """Shared official API first, then the existing free Google/MyMemory routes.

    With a shared API key: Google Cloud v2 -> Google JSON -> Google mobile -> MyMemory.
    Without a key the old behavior is unchanged: Google JSON -> Google mobile -> MyMemory.
    """
    errors: List[Tuple[str, Exception]] = []

    if _google_cloud_translation_api_key():
        try:
            return _translate_google_cloud_v2_request(text, source, target)
        except Exception as exc:
            errors.append(("Google Cloud Translation v2", exc))

    try:
        return _translate_google_json_request(text, source, target)
    except Exception as exc:
        errors.append(("Google JSON", exc))

    # If JSON produced a 429, _provider_wait() will reject this route locally
    # without making another Google network request.  That is intentional.
    try:
        return _translate_google_mobile_request(text, source, target)
    except Exception as exc:
        errors.append(("Google mobile", exc))

    try:
        return _translate_mymemory_request(text, source, target)
    except Exception as exc:
        errors.append(("MyMemory fallback", exc))

    diagnostic = _translation_routes_diagnostic(errors)
    try:
        print(f"[Ultra Tools Translator] all translation routes failed: {diagnostic}")
    except Exception:
        pass
    raise RuntimeError(f"Translation failed on all routes ({diagnostic})")



def register_translation_api_routes() -> bool:
    """Register secret-safe settings endpoints for Ultra Translator's shared API key."""
    try:
        from aiohttp import web  # type: ignore
        from server import PromptServer  # type: ignore
    except Exception:
        return False

    try:
        prompt_server = PromptServer.instance
        routes = prompt_server.routes
    except Exception:
        return False

    marker = "_ultra_translator_translation_api_routes_v1"
    if getattr(prompt_server, marker, False):
        return True

    try:
        from .request_guard import guard_request, register_token_route
    except ImportError:  # pragma: no cover - module loaded outside the package
        from request_guard import guard_request, register_token_route

    # Per-process token handed to the Ultra Tools frontend (see request_guard).
    register_token_route()

    def _json_error(message: str, *, status: int = 400, error_type: str = "request_error"):
        return web.json_response(
            {"ok": False, "error": str(message or "Translation API request failed."), "type": error_type},
            status=status,
        )

    @routes.get("/ultra_translator/translation_api")
    async def _status_route(request):
        denied = guard_request(request, web, require_token=False)
        if denied is not None:
            return denied
        return web.json_response({"ok": True, **_google_cloud_translation_api_status()})

    @routes.post("/ultra_translator/translation_api")
    async def _save_route(request):
        denied = guard_request(request, web)
        if denied is not None:
            return denied
        try:
            payload = await request.json()
        except Exception:
            return _json_error("Invalid JSON request.")
        if not isinstance(payload, dict):
            return _json_error("Invalid request body.")
        try:
            key = _normalize_google_cloud_translation_api_key(payload.get("api_key", ""))
        except ValueError as exc:
            return _json_error(str(exc))
        if not key:
            return _json_error("Google Cloud Translation API key is empty.", error_type="missing_key")
        if not _save_google_cloud_translation_api_key(key):
            return _json_error(
                "Could not save the API key in the ComfyUI user directory.",
                status=500,
                error_type="storage_error",
            )
        return web.json_response({"ok": True, **_google_cloud_translation_api_status()})

    @routes.delete("/ultra_translator/translation_api")
    async def _delete_route(request):
        denied = guard_request(request, web)
        if denied is not None:
            return denied
        if not _clear_google_cloud_translation_api_key():
            return _json_error(
                "Could not remove the saved API key from the ComfyUI user directory.",
                status=500,
                error_type="storage_error",
            )
        return web.json_response({"ok": True, **_google_cloud_translation_api_status()})

    @routes.post("/ultra_translator/translation_api/test")
    async def _test_route(request):
        denied = guard_request(request, web)
        if denied is not None:
            return denied
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            return _json_error("Invalid request body.")
        supplied = payload.get("api_key", None)
        try:
            key = (
                _normalize_google_cloud_translation_api_key(supplied)
                if supplied is not None and str(supplied or "").strip()
                else _google_cloud_translation_api_key()
            )
        except ValueError as exc:
            return _json_error(str(exc))
        if not key:
            return _json_error("Enter an API key or save one first.", error_type="missing_key")

        try:
            import asyncio
            translated = await asyncio.to_thread(
                _translate_google_cloud_v2_request,
                "한 여성이 비 오는 거리를 천천히 걷는다.",
                "korean",
                "english",
                api_key=key,
                use_provider_guard=False,
            )
        except _TranslationRouteRateLimitedError:
            return _json_error(
                "Google Cloud Translation returned HTTP 429. Check quota/rate limits and try again later.",
                status=429,
                error_type="rate_limited",
            )
        except _TranslationRouteConfigurationError:
            return _json_error(
                "Google Cloud Translation rejected the key/project settings. Check the API-key restriction, Cloud Translation API activation, and Billing.",
                status=403,
                error_type="configuration_error",
            )
        except Exception:
            return _json_error(
                "Google Cloud Translation test request failed. Check the network and Google Cloud service status.",
                status=502,
                error_type="provider_error",
            )
        return web.json_response({
            "ok": True,
            "provider": "google_cloud_translation_v2",
            "translatedText": translated,
            "configured": bool(_google_cloud_translation_api_key()),
            "shared_with_ultra_minimax_h3_prompt": True,
        })

    try:
        setattr(prompt_server, marker, True)
    except Exception:
        pass
    return True


def _mask_newlines(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    tokens: List[Tuple[str, str]] = []
    parts: List[str] = []
    cursor = 0
    for index, match in enumerate(re.finditer(r"\r\n|\r|\n", text)):
        parts.append(text[cursor:match.start()])
        token = f"ULTRATRANSLATORBREAK{index:04d}X"
        parts.append(token)
        tokens.append((token, match.group(0)))
        cursor = match.end()
    parts.append(text[cursor:])
    return "".join(parts), tokens


def _restore_newlines(text: str, tokens: List[Tuple[str, str]]) -> Optional[str]:
    restored = text
    for token, newline in tokens:
        pattern = re.compile(r"[ \t\f\v]*" + re.escape(token) + r"[ \t\f\v]*", flags=re.IGNORECASE)
        matches = list(pattern.finditer(restored))
        if len(matches) != 1:
            return None
        restored = pattern.sub(lambda _m, newline=newline: newline, restored, count=1)
    if re.search(r"ULTRATRANSLATORBREAK\d{4}X", restored, flags=re.IGNORECASE):
        return None
    return restored


class UltraTranslatorTextNode:
    """Translate plain text, using the shared official Google key when configured."""

    CATEGORY = "Ultra Tools"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("translated_text",)
    FUNCTION = "translate_text"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "dynamicPrompts": False,
                    },
                ),
                "target_language": (TARGET_LANGUAGES, {"default": "korean"}),
                "source_language": (COMMON_LANGUAGES, {"default": "auto"}),
                "translator_service": (["google", "mymemory"], {"default": "google"}),
                "preserve_newlines": ("BOOLEAN", {"default": True}),
                "fallback_to_input_on_error": ("BOOLEAN", {"default": False}),
            }
        }

    def translate_text(
        self,
        text: str,
        target_language: str = "korean",
        source_language: str = "auto",
        translator_service: str = "google",
        preserve_newlines: bool = True,
        fallback_to_input_on_error: bool = False,
    ):
        original_text = text or ""
        if not original_text.strip():
            return ("",)

        try:
            translated = self._translate(
                text=original_text,
                target_language=target_language,
                source_language=source_language,
                translator_service=translator_service,
                preserve_newlines=preserve_newlines,
            )
            return (translated,)
        except Exception as exc:
            # All route errors reaching here are already prompt-safe wrappers.
            message = f"[Ultra Tools Translator] Translation failed: {exc}"
            print(message)
            if fallback_to_input_on_error:
                return (original_text,)
            return (message,)

    def _translate(
        self,
        text: str,
        target_language: str,
        source_language: str,
        translator_service: str,
        preserve_newlines: bool,
    ) -> str:
        service = (translator_service or "google").strip().lower()
        source = (source_language or "auto").strip().lower()
        target = (target_language or "korean").strip().lower()

        if source == target and source != "auto":
            return text

        cache_key = (service, source, target, text, bool(preserve_newlines))
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        if preserve_newlines and re.search(r"\r\n|\r|\n", text):
            masked, tokens = _mask_newlines(text)
            translated_masked = self._translate_unit(masked, source, target, service)
            restored = _restore_newlines(translated_masked, tokens)
            if restored is not None:
                _cache_put(cache_key, restored)
                return restored

            # Extremely conservative compatibility fallback for a provider that
            # mutates a sentinel: only then revert to the old line-by-line path.
            translated = self._translate_preserving_newlines_per_line(text, source, target, service)
            _cache_put(cache_key, translated)
            return translated

        translated = self._translate_unit(text, source, target, service)
        _cache_put(cache_key, translated)
        return translated

    @staticmethod
    def _translate_unit(text: str, source: str, target: str, service: str) -> str:
        if service == "google":
            return _translate_google_with_independent_fallback(text, source, target)
        if service == "mymemory":
            return _translate_mymemory_request(text, source, target)
        raise ValueError(f"Unsupported translator_service: {service}")

    @staticmethod
    def _translate_preserving_newlines_per_line(
        text: str,
        source: str,
        target: str,
        service: str,
    ) -> str:
        lines: List[str] = text.splitlines(keepends=True)
        output: List[str] = []
        for line in lines:
            newline = ""
            body = line
            if line.endswith("\r\n"):
                body = line[:-2]
                newline = "\r\n"
            elif line.endswith("\n") or line.endswith("\r"):
                body = line[:-1]
                newline = line[-1]

            if body.strip():
                output.append(
                    UltraTranslatorTextNode._translate_unit(body, source, target, service)
                    + newline
                )
            else:
                output.append(line)
        return "".join(output)
