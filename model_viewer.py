"""
ComfyUI Ultra Model Viewer - Optimized + Backslash-safe Version

- 기능 변경 없음 (API/출력 구조 동일)
- Windows 백슬래시 이스케이프 문제를 원천 차단하기 위해 문자열 리터럴에 "\" 를 직접 쓰지 않음
"""

import os
import re
import json
import time
import asyncio
import threading
import logging
from aiohttp import web
import folder_paths
import server

# ---- constants (no functional change) ----
MODEL_EXTENSIONS = (
    ".safetensors", ".ckpt", ".pt", ".pth", ".bin",
    ".gguf", ".nunchaku", ".onnx", ".sft", ".pt2", ".engine"
)
MODEL_EXT_LOWER = tuple(e.lower() for e in MODEL_EXTENSIONS)

# Exact model-value keys. Avoid substring matching such as profile_name,
# modeling_notes, filename_label, or model_version_label because those are
# usually UI/metadata labels in non-model nodes.
MODEL_VALUE_KEYS = {
    "model", "model_name", "model_path", "model_file",
    "checkpoint", "checkpoint_name", "checkpoint_path", "ckpt", "ckpt_name",
    "unet", "unet_name", "diffusion_model", "diffusion_model_name",
    "vae", "vae_name", "vae_path",
    "clip", "clip_name", "clip_l", "clip_g", "clip_path",
    "clip_vision", "clip_vision_name",
    "text_encoder", "text_encoder_name", "text_encoders", "text_encoders_name",
    "lora", "lora_name", "lora_path", "lora_file",
    "embedding", "embedding_name", "ti", "ti_name",
    "hypernet", "hypernet_name", "hypernetwork", "hypernetwork_name",
    "controlnet", "controlnet_name", "control_net", "control_net_name",
    "ipadapter", "ipadapter_name", "ipadapter_model", "ipadapter_model_name",
    "upscale_model", "upscale_model_name", "upscale_model_path",
    "latent_upscale_model", "latent_upscale_model_name",
    "filename", "file_name", "path",
    "engine", "engine_name", "gguf", "gguf_name",
}
# Generic "name" is intentionally not a model key. Only exact typed model keys
# such as model_name, ckpt_name, lora_name, filename, and path may open
# model-value context.
POSSIBLE_MODEL_KEYS = tuple(sorted(MODEL_VALUE_KEYS))

KEY_TAG_TYPES = {
    "lora": "lora", "lora_name": "lora", "lora_path": "lora", "lora_file": "lora",
    "embedding": "embedding", "embedding_name": "embedding", "ti": "embedding", "ti_name": "embedding",
    "hypernet": "hypernet", "hypernet_name": "hypernet",
    "hypernetwork": "hypernet", "hypernetwork_name": "hypernet",
}

# Windows backslash char without using "\" literal
_BS = chr(92)
logger = logging.getLogger(__name__)


def _to_posix(path_str: str) -> str:
    """OS 경로 구분자를 '/'로 통일 (표시용)."""
    if not path_str:
        return path_str
    return path_str.replace(os.sep, "/")


def _normalize_rel(value: str) -> str:
    """위젯에서 얻은 경로 문자열을 현재 OS 구분자로 정규화."""
    if not value:
        return value
    return value.replace("/", os.sep).replace(_BS, os.sep)


_MODEL_EXT_PATTERN = "|".join(re.escape(ext) for ext in MODEL_EXT_LOWER)
_MODEL_REF_RE = re.compile(
    r"(?<![\w.\-])"
    r"(?P<ref>(?:[A-Za-z]:[\\/])?(?:[^\s\"'<>\[\]{}|;,:]+[\\/])*[^\s\"'<>\[\]{}|;,:]+(?:" + _MODEL_EXT_PATTERN + r"))"
    r"(?=$|[\s\"'<>\[\]{}|;,):])",
    re.IGNORECASE,
)
_LORA_TAG_RE = re.compile(
    r"<\s*(?P<tag>lora|lyco|locon|loha|hypernet|embedding|ti)\s*:\s*"
    r"(?P<ref>[^<>:\n\r]+?(?:" + _MODEL_EXT_PATTERN + r"))"
    r"(?:\s*[:>])",
    re.IGNORECASE,
)

_LORA_TAG_ANY_RE = re.compile(
    r"<\s*(?P<tag>lora|lyco|locon|loha|hypernet|embedding|ti)\s*:\s*"
    r"(?P<ref>[^<>:\n\r]+?)"
    r"(?:\s*[:>])",
    re.IGNORECASE,
)
_JSON_KEY_VALUE_RE = re.compile(
    r"(?<![A-Za-z0-9_])[\"\']?(?P<key>" + "|".join(re.escape(k) for k in POSSIBLE_MODEL_KEYS) + r")[\"\']?\s*:\s*"
    r"(?P<value>\"[^\"<>\n\r]+\"|'[^'<>\n\r]+'|[^,}\]<>\n\r]+)",
    re.IGNORECASE,
)
MODEL_LOOSE_NODE_EXACT = {
    "checkpointloadersimple", "checkpointloader", "checkpointloaderadvanced", "checkpointloadernf4",
    "unetloader", "unetloadergguf", "unetloadernunchaku", "diffusionmodelloader", "unetloaderfloat",
    "vaeloader", "vaeloadergguf", "vaeloadernunchaku",
    "cliploader", "dualcliploader", "triplecliploader", "clipvisionloader",
    "loraloader", "loraloadermodelonly", "loraloaderloraonly", "loraloadertags",
    "powerloraloader", "lorastack", "lorastacker",
    "controlnetloader", "controlnetloaderadvanced",
    "ipadaptermodelloader", "ipadapterloader",
    "upscalemodelloader", "upscalemodelloaderadvanced", "latentupscalemodelloader",
    "textencoderloader", "textencoderloadersimple", "textencodersloader",
    "llmloader", "llmmodelloader", "ggufloader", "modelloader",
    "tensorrtloader", "tensorrtengineloader", "engineloader",
}
MODEL_LOOSE_ACTION_HINTS = ("loader", "load", "stack")
MODEL_LOOSE_DOMAIN_HINTS = (
    "model", "checkpoint", "ckpt", "unet", "diffusion", "vae", "clip",
    "lora", "lyco", "controlnet", "ipadapter", "upscale", "textencoder",
    "textencoders", "gguf", "nunchaku", "onnx", "engine", "tensorrt", "bbox", "segm", "ultralytics",
    "insightface", "facedetection", "facerestore", "photomaker", "animatediff",
    "motionmodule", "cogvideo", "seedvr", "promptexpander", "blip", "sams", "grounding",
)
NON_MODEL_NODE_EXACT = {"note", "notes", "notenode", "notesnode", "reroute", "reroutenode", "primitive", "primitivenode"}
NON_LOOSE_NODE_HINTS = (
    "cliptextencode", "vaeencode", "vaedecode", "ksampler", "sampler",
    "scheduler", "preview", "saveimage", "display", "showtext",
)
TEXT_ENCODE_NON_LOOSE_RE = re.compile(r"textencode(?!r)")
EXTENSIONLESS_STOPWORDS = {
    "default", "none", "null", "true", "false", "auto", "cpu", "cuda", "gpu",
    "fast", "slow", "normal", "high", "low", "best", "base", "main",
    "model", "checkpoint", "clip", "vae", "lora", "unet", "text", "encoder",
}
MAX_SCAN_TEXT = 4096
MAX_JSON_SCAN_TEXT = 65536

# ComfyUI graph input descriptors often use these fields as slot metadata, not model values.
INPUT_DESCRIPTOR_META_KEYS = {
    "name", "type", "link", "label", "localized_name", "slot_index", "index",
    "shape", "widget", "optional", "isoptional", "control_after_generate",
}

# In non-model nodes these property keys usually describe UI labels, not model files.
NON_LOOSE_PROPERTY_META_KEYS = {"name", "label", "title"}


def _strip_ref(ref: str):
    if not isinstance(ref, str):
        return None
    value = ref.strip().strip("\"'")
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1].strip()
    return value or None


def _canonical_tag_type(tag):
    lower = str(tag or "").strip().lower()
    if lower in ("lora", "lyco", "locon", "loha"):
        return "lora"
    if lower in ("embedding", "ti"):
        return "embedding"
    if lower == "hypernet":
        return "hypernet"
    return lower or None


def _tagged_ref(ref, tag_type):
    cleaned = _strip_ref(ref)
    tag = _canonical_tag_type(tag_type)
    if cleaned and tag:
        return {"ref": cleaned, "tag_type": tag}
    return cleaned


def _candidate_ref(value):
    if isinstance(value, dict):
        ref = value.get("ref")
        return ref if isinstance(ref, str) else None
    return value if isinstance(value, str) else None


def _candidate_tag_type(value):
    if isinstance(value, dict):
        return _canonical_tag_type(value.get("tag_type"))
    return None


def _candidate_key(value):
    ref = _candidate_ref(value)
    if not ref:
        return str(value).lower()
    tag = _candidate_tag_type(value) or ""
    return f"{tag}|{ref.lower()}"


def _is_exact_model_key(key: str) -> bool:
    return str(key or "").lower() in MODEL_VALUE_KEYS


def _tag_type_for_key(key: str):
    return KEY_TAG_TYPES.get(str(key or "").lower())


def _apply_key_hint(refs, tag_type=None):
    if not tag_type:
        return list(refs or [])
    out = []
    for ref in refs or []:
        if _candidate_tag_type(ref):
            out.append(ref)
        else:
            out.append(_tagged_ref(_candidate_ref(ref), tag_type))
    return out


def _refs_from_exact_key_value(key: str, raw_value: str):
    """Parse one exact-key JSON/pseudo-dict value without broad-scanning unknown text.

    Quoted extensionless typed values may contain spaces, e.g.
    {lora_name: "space lora"}. Unquoted extensionless values are kept
    conservative and must be a single token, so incidental text like
    {lora_name: some plain text} does not trigger unnecessary model lookups.
    Extension-bearing filenames remain allowed to contain spaces in exact-key
    contexts.
    """
    key_lower = str(key or "").lower()
    if not _is_exact_model_key(key_lower):
        return []
    raw_text = str(raw_value or "").strip()
    quote_wrapped = len(raw_text) >= 2 and raw_text[0] == raw_text[-1] and raw_text[0] in "\"'"
    cleaned = _strip_ref(raw_text)
    if not cleaned:
        return []
    tag_type = _tag_type_for_key(key_lower)
    refs = []
    if _looks_like_full_model_ref(cleaned):
        refs.append(cleaned)
    elif tag_type in {"lora", "embedding", "hypernet"} and _looks_like_extensionless_lora_tag_ref(cleaned):
        if quote_wrapped or not re.search(r"\s", cleaned):
            refs.append(cleaned)
    return _apply_key_hint(refs, tag_type)


def _is_json_like_text(text: str) -> bool:
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("[")


def _looks_like_extensionless_model_ref(value: str) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip().strip("\"'")
    if not text:
        return False
    lower = text.lower()
    if lower.endswith(MODEL_EXT_LOWER):
        return False
    if lower in EXTENSIONLESS_STOPWORDS:
        return False
    if len(text) < 3 or text.isdigit():
        return False
    if re.search(r"[\s\"'<>\[\]{}|;,:]", text):
        return False
    if any(part in ("", ".", "..") for part in re.split(r"[\\/]+", text)):
        return False
    return bool(re.search(r"[A-Za-z_]", text))


def _looks_like_full_model_ref(value: str) -> bool:
    """True when the whole widget/key value looks like one model file path.

    Unlike the generic regex scanner this accepts spaces inside filenames, but it
    still rejects traversal segments, comma-separated stacks, and prompt-like punctuation.
    It is used only in loader/model-key contexts so normal prompt text remains strict.
    """
    if not isinstance(value, str):
        return False
    text = value.strip().strip("\"'")
    if not text or not text.lower().endswith(MODEL_EXT_LOWER):
        return False
    if any(ch in text for ch in "<>[]{}|;,\n\r\t"):
        return False
    parts = re.split(r"[\\/]+", text)
    if any(part in ("", ".", "..") for part in parts):
        return False
    return True


def _looks_like_extensionless_lora_tag_ref(value: str) -> bool:
    """LoRA tag names may omit extensions and may contain spaces.

    This is intentionally narrower than arbitrary prompt text: it is only used for
    strings already captured from <lora:...:weight>-style tags.
    """
    if not isinstance(value, str):
        return False
    text = value.strip().strip("\"'")
    if not text:
        return False
    lower = text.lower()
    if lower.endswith(MODEL_EXT_LOWER) or lower in EXTENSIONLESS_STOPWORDS:
        return False
    if len(text) > 180 or text.isdigit():
        return False
    if re.search(r"[\"'<>{}\[\]|;,:\n\r\t]", text):
        return False
    if any(part in ("", ".", "..") for part in re.split(r"[\\/]+", text)):
        return False
    return bool(re.search(r"[A-Za-z_]", text))


def _split_loose_model_stack(text: str, *, allow_extensionless: bool = False, allow_plain_extensionless: bool = False):
    """Split comma/newline separated loader stack values without breaking spaced filenames."""
    if not isinstance(text, str):
        return []
    if "," not in text and "\n" not in text and "\r" not in text:
        return []
    refs = []
    for part in re.split(r"[,\n\r]+", text):
        item = part.strip().strip("\"'")
        if not item:
            continue
        if _looks_like_full_model_ref(item):
            refs.append(item)
        elif allow_extensionless and allow_plain_extensionless and (_looks_like_extensionless_model_ref(item) or _looks_like_extensionless_lora_tag_ref(item)):
            refs.append(item)
    return _unique_preserve_order(refs)


def _extract_model_refs_from_string(value: str, *, loose: bool = False, allow_extensionless: bool = False, allow_standalone: bool = True, allow_plain_extensionless: bool = False):
    """문자열 하나에서 모델 참조를 0개 이상 추출한다.

    strict 모드: standalone 모델 경로, JSON/JSON-like 모델 키만 허용해 Notes/프롬프트 오탐을 줄인다.
    loose 모드: 모델 로더 계열 노드에서 <lora:name:weight>, 쉼표 구분 스택 등도 허용한다.
    """
    refs = []
    if not isinstance(value, str):
        return refs
    text = value.strip()
    if not text:
        return refs

    # JSON 문자열이면 실제 구조로 먼저 해석한다. 실패해도 JSON-like key regex를 아래에서 보조 적용한다.
    json_like_text = text[:1] in ("{", "[")
    if json_like_text:
        if len(text) > MAX_JSON_SCAN_TEXT:
            return refs
        try:
            parsed = json.loads(text)
            return _collect_model_refs(
                parsed,
                loose=loose,
                allow_extensionless=allow_extensionless,
                allow_standalone=allow_standalone,
            )
        except Exception:
            pass
    elif len(text) > MAX_SCAN_TEXT:
        return refs

    # JSON 조각/문자열화된 dict의 모델 관련 key는 strict 모드에서도 허용한다.
    # A single key/value parser handles both extension-bearing and extensionless
    # exact-key values, avoiding duplicate processing of quoted filename values.

    # Pseudo JSON/dict can store extensionless typed names in exact keys such as
    # {lora_name: "space lora"} or {embedding_name: "my_style"}. Keep this structural and key-scoped; never
    # broad-scan unknown keys such as {name: "false.safetensors"}.
    for match in _JSON_KEY_VALUE_RE.finditer(text):
        refs.extend(_refs_from_exact_key_value(match.group("key"), match.group("value")))

    # Pseudo JSON/dict text is structural metadata. After exact-key extraction,
    # do not run broad loose regex over unknown keys such as {name: "..."}.
    if json_like_text:
        return _unique_preserve_order(refs)

    stripped = text.strip().strip("\"'")
    full_model_ref = _looks_like_full_model_ref(stripped)

    tag_spans = []
    # Explicit <lora:...>, <embedding:...>, and <hypernet:...> tags are
    # structural model references even inside otherwise non-model text nodes.
    for match in _LORA_TAG_RE.finditer(text):
        candidate = _tagged_ref(match.group("ref"), match.group("tag"))
        if candidate:
            refs.append(candidate)
            if loose:
                tag_spans.append(match.span())

    if allow_extensionless:
        for match in _LORA_TAG_ANY_RE.finditer(text):
            raw_ref = match.group("ref")
            cleaned = _strip_ref(raw_ref)
            if cleaned and (_looks_like_extensionless_model_ref(cleaned) or _looks_like_extensionless_lora_tag_ref(cleaned)):
                refs.append(_tagged_ref(cleaned, match.group("tag")))
                if loose:
                    tag_spans.append(match.span())

    # 일반 텍스트 오탐 방지: strict 모드에서는 명시적 태그와 공백 없는 전체 모델 경로 하나만 허용한다.
    if not loose:
        if allow_standalone:
            if full_model_ref and not re.search(r"\s", stripped):
                refs.append(stripped)
                return _unique_preserve_order(refs)
            match = _MODEL_REF_RE.search(stripped)
            if match and match.start("ref") == 0 and match.end("ref") == len(stripped):
                cleaned = _strip_ref(match.group("ref"))
                if cleaned:
                    refs.append(cleaned)
        return _unique_preserve_order(refs)

    # 모델 로더/모델 관련 key에서는 위에서 수집한 explicit tags 외에
    # 스택형/일반 파일명 문자열도 느슨하게 추출한다.
    # Comma/newline stacks may contain both plain refs and tags. Do not return
    # early after the stack split, otherwise values such as
    # "a.safetensors, <lora:b:1>" lose the tagged item.
    stack_refs = _split_loose_model_stack(text, allow_extensionless=allow_extensionless, allow_plain_extensionless=allow_plain_extensionless)
    if stack_refs:
        refs.extend(stack_refs)

    if full_model_ref:
        refs.append(stripped)

    def _inside_tag_span(pos: int) -> bool:
        return any(start <= pos < end for start, end in tag_spans)

    for match in _MODEL_REF_RE.finditer(text):
        if _inside_tag_span(match.start("ref")):
            continue
        cleaned = _strip_ref(match.group("ref"))
        if cleaned:
            refs.append(cleaned)

    if allow_extensionless and allow_plain_extensionless and (
        _looks_like_extensionless_model_ref(stripped) or _looks_like_extensionless_lora_tag_ref(stripped)
    ):
        refs.append(stripped)

    return _unique_preserve_order(refs)


def _clean_model_ref(value: str):
    """하위 호환용: 첫 번째 모델 참조만 반환."""
    refs = _extract_model_refs_from_string(value, loose=True)
    return _candidate_ref(refs[0]) if refs else None


def _compact_node_type(node_type: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(node_type or "").lower())


def _is_model_related_node_type(node_type: str) -> bool:
    compact = _compact_node_type(node_type)
    if not compact:
        return False
    # Explicit model loader whitelist wins first. This lets custom loader names
    # such as NoteModelLoader remain detectable instead of being blocked by a
    # broad substring like "note".
    if compact in MODEL_LOOSE_NODE_EXACT:
        return True
    # Only exact non-model node types are excluded here. Broad text/sampler
    # exclusions stay below and are evaluated on compact structural tokens.
    if compact in NON_MODEL_NODE_EXACT:
        return False
    # Unknown text encoders/samplers/display nodes are not loose model parsers.
    if TEXT_ENCODE_NON_LOOSE_RE.search(compact):
        return False
    if any(token in compact for token in NON_LOOSE_NODE_HINTS):
        return False
    has_action = any(token in compact for token in MODEL_LOOSE_ACTION_HINTS)
    has_domain = any(token in compact for token in MODEL_LOOSE_DOMAIN_HINTS)
    return has_action and has_domain


def _collect_model_refs(value, out=None, *, loose: bool = False, model_key_context: bool = False, allow_extensionless: bool = False, allow_standalone: bool = True):
    """Collect typed model candidates from strings/lists/dicts.

    Fundamental rule: unknown dict keys in non-model contexts are not treated as
    model values merely because they contain substrings such as name/file/model.
    Only exact allowlisted keys open model-key context. Unknown scalar values are
    ignored except for JSON-like strings that may contain exact model keys.
    """
    if out is None:
        out = []

    if isinstance(value, str):
        out.extend(_extract_model_refs_from_string(
            value,
            loose=(loose or model_key_context),
            allow_extensionless=allow_extensionless,
            allow_standalone=allow_standalone,
            allow_plain_extensionless=(allow_extensionless and model_key_context),
        ))
        return out

    if isinstance(value, dict):
        for key, child in value.items():
            key_lower = str(key).lower()
            child_is_model_key = _is_exact_model_key(key_lower)
            key_tag_type = _tag_type_for_key(key_lower) if child_is_model_key else None
            if child_is_model_key:
                temp = []
                _collect_model_refs(
                    child,
                    temp,
                    loose=loose,
                    model_key_context=True,
                    allow_extensionless=allow_extensionless,
                    allow_standalone=True,
                )
                out.extend(_apply_key_hint(temp, key_tag_type))
            elif isinstance(child, str):
                if _is_json_like_text(child):
                    _collect_model_refs(
                        child,
                        out,
                        loose=False,
                        model_key_context=False,
                        allow_extensionless=False,
                        allow_standalone=False,
                    )
                # Plain scalar under an unknown key is metadata/text, not a model.
            elif isinstance(child, (dict, list, tuple)):
                _collect_model_refs(
                    child,
                    out,
                    loose=loose,
                    model_key_context=False,
                    allow_extensionless=allow_extensionless,
                    allow_standalone=False,
                )
        return out

    if isinstance(value, (list, tuple)):
        for child in value:
            _collect_model_refs(
                child,
                out,
                loose=loose,
                model_key_context=model_key_context,
                allow_extensionless=allow_extensionless,
                allow_standalone=allow_standalone,
            )
        return out

    return out


def _collect_model_refs_from_inputs(value, out=None, *, loose: bool = False, model_key_context: bool = False, allow_extensionless: bool = False, allow_standalone: bool = True):
    """Collect model refs from serialized ComfyUI inputs without treating slot metadata names as model values."""
    if out is None:
        out = []

    if isinstance(value, str):
        out.extend(_extract_model_refs_from_string(
            value,
            loose=(loose or model_key_context),
            allow_extensionless=allow_extensionless,
            allow_standalone=allow_standalone,
            allow_plain_extensionless=(allow_extensionless and model_key_context),
        ))
        return out

    if isinstance(value, dict):
        for key, child in value.items():
            key_lower = str(key).lower()
            if key_lower in INPUT_DESCRIPTOR_META_KEYS:
                continue
            child_is_model_key = _is_exact_model_key(key_lower)
            key_tag_type = _tag_type_for_key(key_lower) if child_is_model_key else None
            if child_is_model_key:
                temp = []
                _collect_model_refs_from_inputs(
                    child,
                    temp,
                    loose=loose,
                    model_key_context=True,
                    allow_extensionless=allow_extensionless,
                    allow_standalone=True,
                )
                out.extend(_apply_key_hint(temp, key_tag_type))
            elif isinstance(child, str):
                if _is_json_like_text(child):
                    _collect_model_refs_from_inputs(
                        child,
                        out,
                        loose=False,
                        model_key_context=False,
                        allow_extensionless=False,
                        allow_standalone=False,
                    )
            elif isinstance(child, (dict, list, tuple)):
                _collect_model_refs_from_inputs(
                    child,
                    out,
                    loose=loose,
                    model_key_context=False,
                    allow_extensionless=allow_extensionless,
                    allow_standalone=False,
                )
        return out

    if isinstance(value, (list, tuple)):
        for child in value:
            _collect_model_refs_from_inputs(
                child,
                out,
                loose=loose,
                model_key_context=model_key_context,
                allow_extensionless=allow_extensionless,
                allow_standalone=allow_standalone,
            )
        return out

    return out


def _collect_model_refs_from_properties(value, out=None, *, loose: bool = False, model_key_context: bool = False, allow_extensionless: bool = False, allow_standalone: bool = True):
    """Collect refs from node properties while avoiding UI label/name false positives."""
    if out is None:
        out = []

    if isinstance(value, str):
        out.extend(_extract_model_refs_from_string(
            value,
            loose=(loose or model_key_context),
            allow_extensionless=allow_extensionless,
            allow_standalone=allow_standalone,
            allow_plain_extensionless=(allow_extensionless and model_key_context),
        ))
        return out

    if isinstance(value, dict):
        for key, child in value.items():
            key_lower = str(key).lower()
            if not loose and not model_key_context and key_lower in NON_LOOSE_PROPERTY_META_KEYS:
                continue
            child_is_model_key = _is_exact_model_key(key_lower)
            key_tag_type = _tag_type_for_key(key_lower) if child_is_model_key else None
            if child_is_model_key:
                temp = []
                _collect_model_refs_from_properties(
                    child,
                    temp,
                    loose=loose,
                    model_key_context=True,
                    allow_extensionless=allow_extensionless,
                    allow_standalone=True,
                )
                out.extend(_apply_key_hint(temp, key_tag_type))
            elif isinstance(child, str):
                if _is_json_like_text(child):
                    _collect_model_refs_from_properties(
                        child,
                        out,
                        loose=False,
                        model_key_context=False,
                        allow_extensionless=False,
                        allow_standalone=False,
                    )
            elif isinstance(child, (dict, list, tuple)):
                _collect_model_refs_from_properties(
                    child,
                    out,
                    loose=loose,
                    model_key_context=False,
                    allow_extensionless=allow_extensionless,
                    allow_standalone=False,
                )
        return out

    if isinstance(value, (list, tuple)):
        for child in value:
            _collect_model_refs_from_properties(
                child,
                out,
                loose=loose,
                model_key_context=model_key_context,
                allow_extensionless=allow_extensionless,
                allow_standalone=allow_standalone,
            )
        return out

    return out


def _unique_preserve_order(values):
    seen = set()
    out = []
    for value in values:
        key = _candidate_key(value)
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _pretty_category_from_folder_key(folder_key: str) -> str:
    explicit = {
        "clip_vision": "CLIP_Vision",
        "latent_upscale_models": "Latent_Upscale",
        "model_patches": "Model_Patches",
        "vae_approx": "VAE_Approx",
        "background_removal": "Background_Removal",
        "frame_interpolation": "Frame_Interpolation",
        "geometry_estimation": "Geometry_Estimation",
        "optical_flow": "Optical_Flow",
        "detection": "Detection",
        "prompt_expander": "Prompt_Expander",
        "audio_encoders": "Audio_Encoders",
        "style_models": "Style_Models",
        "grounding-dino": "GroundingDINO",
        "text_encoders": "Text_Encoders",
        "custom_nodes": "Custom",
        "facerestore_models": "Facerestore",
        "llm": "LLM",
    }
    if folder_key in explicit:
        return explicit[folder_key]

    normalized = str(folder_key or "").strip().replace("-", "_").replace("/", "_")
    if not normalized:
        return "Custom"
    parts = [part for part in normalized.split("_") if part]
    if not parts:
        return "Custom"
    return "_".join(part.upper() if part.isupper() else part[:1].upper() + part[1:] for part in parts)


# ComfyUI 최신 map_legacy 동작으로 clip / text_encoders가 같은 경로 묶음을 반환할 수 있어
# 중복 집계가 발생하지 않도록 스캔용 실제 경로를 정규화해서 dedupe한다.
def _get_folder_paths_dedup(folder_key: str, *, prefer_default_only: bool = False):
    paths = []
    seen = set()

    def add_path(path):
        if not path:
            return
        norm = os.path.normcase(os.path.realpath(path))
        if norm in seen:
            return
        seen.add(norm)
        paths.append(path)

    default_models_path = None
    try:
        if hasattr(folder_paths, "base_path"):
            default_models_path = os.path.join(folder_paths.base_path, "models", folder_key)
    except Exception:
        default_models_path = None

    # ComfyUI 최신 map_legacy()가 clip -> text_encoders 를 합쳐 반환할 수 있으므로,
    # 이 두 키는 raw registry를 우선 사용해 카테고리 혼선을 줄인다.
    if folder_key in ("clip", "text_encoders"):
        raw_map_available = False
        try:
            raw_map = getattr(folder_paths, "folder_names_and_paths", None)
            raw_map_available = isinstance(raw_map, dict)
            folder_info = raw_map.get(folder_key) if raw_map_available else None
            if folder_info:
                for path in list(folder_info[0] or []):
                    add_path(path)
            elif folder_key == "clip" and raw_map_available:
                # 최신 환경에서 clip 키가 없어도 text_encoders 등록 안에 models/clip 경로가 섞여 있을 수 있다.
                text_info = raw_map.get("text_encoders")
                if text_info:
                    for path in list(text_info[0] or []):
                        if os.path.basename(os.path.normpath(path)).lower() == "clip":
                            add_path(path)
        except Exception:
            raw_map_available = False
        if default_models_path and os.path.exists(default_models_path):
            add_path(default_models_path)
        if paths:
            return paths
        # raw registry가 있는데 clip이 없으면 text_encoders 전체 리다이렉트 fallback을 타지 않는다.
        if raw_map_available and folder_key == "clip":
            return paths
        # raw registry를 못 쓰는 구환경만 get_folder_paths fallback

    if prefer_default_only and default_models_path and os.path.exists(default_models_path):
        add_path(default_models_path)
        return paths

    try:
        for path in list(folder_paths.get_folder_paths(folder_key) or []):
            add_path(path)
    except Exception:
        pass

    if default_models_path and os.path.exists(default_models_path):
        add_path(default_models_path)
    return paths


def _category_for_scanned_base(folder_key: str, category_name: str, base_path: str) -> str:
    base_name = os.path.basename(os.path.normpath(base_path)).lower()
    # text_encoders가 models/clip 경로를 함께 들고 오는 환경에서는 파일별 표시 라벨을 보정한다.
    if category_name == "Text_Encoders" and base_name == "clip":
        return "CLIP"
    if category_name == "CLIP" and base_name == "text_encoders":
        return "Text_Encoders"
    return category_name


class ModelViewerAPI:
    _path_index_cache = {}
    _path_index_cache_ttl = 10.0
    _path_index_cache_max_entries = 128
    _path_index_cache_lock = threading.RLock()
    _path_index_build_locks = {}
    _path_index_build_locks_max_entries = 128

    @staticmethod
    def format_size(bytes_size: int) -> str:
        if bytes_size == 0:
            return "0 B"
        size = float(bytes_size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    @classmethod
    def scan_category(cls, category: str):
        folder_map = {
            "UNET": ("unet", "diffusion_models"),
            "Checkpoints": "checkpoints",
            "CLIP": "clip",
            "VAE": "vae",
            "LORA": "loras",
            "Text_Encoders": "text_encoders",
            "LLM": ("LLM", "llm"),
            "Upscale": ("upscale_models", "latent_upscale_models"),
            "ControlNet": "controlnet",
        }

        extra_folders = {
            "CLIP_Vision": "clip_vision",
            "SEEDVR2": "seedvr2",
            "Animatediff": "animatediff_models",
            "Motion_Module": "motion_modules",
            "Photomaker": "photomaker",
            "Insightface": "insightface",
            "Facerestore": "facerestore_models",
            "Facedetection": "facedetection",
            "ONNX": "onnx",
            "Diffusers": "diffusers",
            "CogVideo": "CogVideoX",
            "SAMS": "sams",
            "GroundingDINO": "grounding-dino",
            "BBOX": "ultralytics/bbox",
            "Segm": "ultralytics/segm",
            "Audio_Encoders": "audio_encoders",
            "Style_Models": "style_models",
            "Hypernetworks": "hypernetworks",
            "Embeddings": "embeddings",
            "GLigen": "gligen",
            "Ipadapter": "ipadapter",
            "Prompt_Expander": "prompt_expander",
            "Blip": "blip",
            "Model_Patches": "model_patches",
            "VAE_Approx": "vae_approx",
            "Background_Removal": "background_removal",
            "Frame_Interpolation": "frame_interpolation",
            "Geometry_Estimation": "geometry_estimation",
            "Optical_Flow": "optical_flow",
            "Detection": "detection",
            "Custom": "custom_nodes",
        }

        # ComfyUI 최신 map_legacy() 환경에서 clip ↔ text_encoders 경로가 섞이는 경우가 있어
        # All Models 통계는 파일 실경로 기준으로 전역 dedupe한다.
        if category == "All Models":
            all_files = []
            total = 0
            seen_file_keys = set()
            handled_folder_keys = set()
            walked_path_keys = set()

            def add_result(result):
                nonlocal total
                for f in result["files"]:
                    file_key = f.get("_file_key") or f.get("name", "").lower()
                    if file_key in seen_file_keys:
                        continue
                    seen_file_keys.add(file_key)
                    total += f["size"]
                    all_files.append({k: v for k, v in f.items() if not k.startswith("_")})

            main_categories = [
                "UNET", "Checkpoints", "Text_Encoders", "CLIP", "VAE", "LORA",
                "LLM", "Upscale", "ControlNet"
            ]

            for cat in main_categories:
                folder_key = folder_map.get(cat)
                if not folder_key:
                    continue
                folder_keys = folder_key if isinstance(folder_key, (list, tuple)) else (folder_key,)
                for one_folder_key in folder_keys:
                    handled_folder_keys.add(one_folder_key)
                    result = cls._scan_folder(one_folder_key, cat, walked_path_keys=walked_path_keys)
                    add_result(result)

            for cat, folder_key in extra_folders.items():
                handled_folder_keys.add(folder_key)
                result = cls._scan_folder(folder_key, cat, walked_path_keys=walked_path_keys)
                add_result(result)

            # 최신/미래 ComfyUI 폴더까지 누락되지 않도록 등록된 folder_paths 전체를 fallback으로 포함
            try:
                if hasattr(folder_paths, "folder_names_and_paths"):
                    for folder_key in folder_paths.folder_names_and_paths.keys():
                        if folder_key in handled_folder_keys:
                            continue
                        pretty_category = _pretty_category_from_folder_key(folder_key)
                        result = cls._scan_folder(folder_key, pretty_category, walked_path_keys=walked_path_keys)
                        add_result(result)
            except Exception:
                pass

            all_files.sort(key=lambda x: (-x["size"], x["display_name"].lower()))
            return {"files": all_files, "count": len(all_files), "total_size": total}

        folder_key = folder_map.get(category)
        if not folder_key:
            extra_key = extra_folders.get(category)
            if extra_key:
                folder_key = extra_key
            else:
                return {"files": [], "count": 0, "total_size": 0}

        folder_keys = folder_key if isinstance(folder_key, (list, tuple)) else (folder_key,)
        files = []
        total = 0
        seen_file_keys = set()
        walked_path_keys = set()
        for one_folder_key in folder_keys:
            result = cls._scan_folder(one_folder_key, category, walked_path_keys=walked_path_keys)
            for f in result["files"]:
                file_key = f.get("_file_key") or f.get("name", "").lower()
                if file_key in seen_file_keys:
                    continue
                seen_file_keys.add(file_key)
                files.append({k: v for k, v in f.items() if not k.startswith("_")})
                total += f["size"]
        files.sort(key=lambda x: (-x["size"], x["display_name"].lower()))
        result = {"files": files, "count": len(files), "total_size": total}
        if category == "CLIP" and not files:
            result["message"] = "No separate CLIP folder found. In recent ComfyUI setups, CLIP/text encoder files are usually shown under Text_Encoders."
        return result

    @classmethod
    def _scan_folder(cls, folder_key: str, category_name: str, walked_path_keys=None):
        prefer_default_only = folder_key in ("clip", "text_encoders")
        paths = _get_folder_paths_dedup(folder_key, prefer_default_only=prefer_default_only)

        if not paths:
            return {"files": [], "count": 0, "total_size": 0}

        files_list = []
        total_size = 0
        seen_files = set()

        for base_path in paths:
            if not os.path.exists(base_path):
                continue

            base_key = os.path.normcase(os.path.realpath(base_path))
            if walked_path_keys is not None:
                if base_key in walked_path_keys:
                    continue
                walked_path_keys.add(base_key)

            folder_prefix = os.path.basename(os.path.normpath(base_path))
            actual_category = _category_for_scanned_base(folder_key, category_name, base_path)

            try:
                seen_dirs = set()
                for root, dirs, files in os.walk(base_path, followlinks=True):
                    root_key = os.path.normcase(os.path.realpath(root))
                    if root_key in seen_dirs:
                        dirs[:] = []
                        continue
                    seen_dirs.add(root_key)
                    dirs[:] = [
                        d for d in dirs
                        if os.path.normcase(os.path.realpath(os.path.join(root, d))) not in seen_dirs
                    ]
                    for filename in files:
                        filename_lower = filename.lower()
                        if not filename_lower.endswith(MODEL_EXT_LOWER):
                            continue

                        full_path = os.path.join(root, filename)
                        file_key = os.path.normcase(os.path.realpath(full_path))
                        if file_key in seen_files:
                            continue
                        seen_files.add(file_key)

                        try:
                            size = os.path.getsize(full_path)
                        except Exception as exc:
                            logger.warning("Ultra Tools Model Viewer: unable to stat model file %s (%s)", full_path, exc)
                            continue

                        try:
                            rel_path = os.path.relpath(full_path, base_path)
                        except Exception:
                            rel_path = full_path

                        display_name = _to_posix(rel_path)
                        if "/" in display_name:
                            parts = display_name.split("/")
                            if len(parts) > 1:
                                display_name = f"{parts[-2]}/{parts[-1]}"

                        files_list.append({
                            "name": rel_path,
                            "display_name": display_name,
                            "folder_prefix": folder_prefix,
                            "size": size,
                            "size_formatted": cls.format_size(size),
                            "category": actual_category,
                            "_file_key": file_key,
                        })
                        total_size += size
            except Exception as exc:
                logger.warning("Ultra Tools Model Viewer: failed to scan model folder %s (%s)", base_path, exc)

        files_list.sort(key=lambda x: (-x["size"], x["display_name"].lower()))
        return {"files": files_list, "count": len(files_list), "total_size": total_size}

    @classmethod
    def scan_workflow(cls, workflow_data: dict, frontend_candidates=None):
        FOLDER_CATEGORIES = {
            "checkpoints": "Checkpoints",
            "unet": "UNET",
            "diffusion_models": "UNET",
            "text_encoders": "Text_Encoders",
            "clip": "CLIP",
            "clip_vision": "CLIP_Vision",
            "vae": "VAE",
            "loras": "LORA",
            "controlnet": "ControlNet",
            "upscale_models": "Upscale",
            "latent_upscale_models": "Upscale",
            "LLM": "LLM",
            "llm": "LLM",
            "embeddings": "Embeddings",
            "hypernetworks": "Hypernetworks",
            "style_models": "Style_Models",
            "photomaker": "Photomaker",
            "insightface": "Insightface",
            "facerestore_models": "Facerestore",
            "facedetection": "Facedetection",
            "ipadapter": "Ipadapter",
            "gligen": "GLigen",
            "animatediff_models": "Animatediff",
            "motion_modules": "Motion_Module",
            "CogVideoX": "CogVideo",
            "seedvr2": "SEEDVR2",
            "onnx": "ONNX",
            "diffusers": "Diffusers",
            "sams": "SAMS",
            "grounding-dino": "GroundingDINO",
            "ultralytics/bbox": "BBOX",
            "ultralytics/segm": "Segm",
            "audio_encoders": "Audio_Encoders",
            "blip": "Blip",
            "prompt_expander": "Prompt_Expander",
            "model_patches": "Model_Patches",
            "vae_approx": "VAE_Approx",
            "background_removal": "Background_Removal",
            "frame_interpolation": "Frame_Interpolation",
            "geometry_estimation": "Geometry_Estimation",
            "optical_flow": "Optical_Flow",
            "detection": "Detection",
            "custom_nodes": "Custom",
        }

        def ordered_folder_items_for_node(node_type: str, tag_type: str = None):
            compact = _compact_node_type(node_type)
            priority = []
            tag_type = _canonical_tag_type(tag_type)
            if tag_type == "lora":
                priority.extend(["loras"])
            elif tag_type == "embedding":
                priority.extend(["embeddings"])
            elif tag_type == "hypernet":
                priority.extend(["hypernetworks"])
            elif "lora" in compact or any(token in compact for token in ("lyco", "locon", "loha")):
                priority.extend(["loras", "embeddings", "hypernetworks"])
            elif any(token in compact for token in ("unet", "diffusion", "tensorrt", "engine")):
                priority.extend(["diffusion_models", "unet", "checkpoints"])
            elif "vae" in compact:
                priority.extend(["vae"])
            elif "clipvision" in compact:
                priority.extend(["clip_vision", "clip"])
            elif "textencoder" in compact or "textencoders" in compact:
                priority.extend(["text_encoders", "clip"])
            elif "clip" in compact:
                priority.extend(["clip", "text_encoders"])
            elif "checkpoint" in compact or "ckpt" in compact:
                priority.extend(["checkpoints"])
            elif "controlnet" in compact:
                priority.extend(["controlnet"])
            elif "ipadapter" in compact:
                priority.extend(["ipadapter"])
            elif "upscale" in compact:
                priority.extend(["upscale_models", "latent_upscale_models"])
            elif "llm" in compact:
                priority.extend(["LLM", "llm"])

            ordered = []
            seen = set()
            for key in priority:
                if key in FOLDER_CATEGORIES and key not in seen:
                    ordered.append((key, FOLDER_CATEGORIES[key]))
                    seen.add(key)
            # Explicit <lora:...>, <embedding:...>, and <hypernet:...> tags
            # should never fall back to unrelated folders with the same filename.
            # Untagged loader values still use the broad fallback below.
            if tag_type:
                return ordered
            for key, category in FOLDER_CATEGORIES.items():
                if key not in seen:
                    ordered.append((key, category))
            return ordered

        def _active_graph_nodes(nodes):
            active = []
            for node in nodes or []:
                if not isinstance(node, dict):
                    continue
                if node.get("mode", 0) in (2, 4):
                    continue
                active.append(node)
            return active

        def _subgraph_identity_keys(sg):
            keys = set()
            if not isinstance(sg, dict):
                return keys
            # Definition identity should not use type/class_type: those can match
            # ordinary main-node loader types and make unused subgraphs look used.
            for key in ("id", "name", "title"):
                value = sg.get(key)
                if isinstance(value, (str, int, float)) and str(value):
                    keys.add(str(value).lower())
                    keys.add(_compact_node_type(value))
            return {k for k in keys if k}

        def _extract_subgraph_refs_from_value(value, out, depth=0):
            if depth > 4:
                return
            if isinstance(value, (str, int, float)) and str(value):
                out.add(str(value).lower())
                out.add(_compact_node_type(value))
            elif isinstance(value, dict):
                for key in (
                    "id", "name", "title", "subgraph_id", "subgraphId", "subgraph",
                    "subgraph_name", "subgraphName", "definition_id", "definitionId",
                    "graph_id", "graphId",
                ):
                    if key in value:
                        _extract_subgraph_refs_from_value(value.get(key), out, depth + 1)

        def _main_graph_subgraph_usage(main_nodes, subgraph_defs):
            if not subgraph_defs:
                return set(), False, False
            subgraph_key_map = {}
            definition_compact_keys = []
            for index, sg in enumerate(subgraph_defs):
                keys = _subgraph_identity_keys(sg)
                definition_compact_keys.append(keys)
                for key in keys:
                    subgraph_key_map.setdefault(key, set()).add(index)

            used_indexes = set()
            ambiguous_subgraph_instance = False
            any_explicit_subgraph_ref = False
            ref_keys = (
                "subgraph_id", "subgraphId", "subgraph", "subgraph_name", "subgraphName",
                "definition_id", "definitionId", "graph_id", "graphId",
            )
            for node in main_nodes:
                node_refs = set()
                has_explicit_subgraph_ref = False
                for key in ref_keys:
                    if key in node:
                        has_explicit_subgraph_ref = True
                        any_explicit_subgraph_ref = True
                        _extract_subgraph_refs_from_value(node.get(key), node_refs)
                props = node.get("properties")
                if isinstance(props, dict):
                    for key in ref_keys:
                        if key in props:
                            has_explicit_subgraph_ref = True
                            any_explicit_subgraph_ref = True
                            _extract_subgraph_refs_from_value(props.get(key), node_refs)
                node_type = node.get("type") or node.get("class_type") or ""
                compact_type = _compact_node_type(node_type)

                matched = False
                for ref in node_refs:
                    if ref in subgraph_key_map:
                        used_indexes.update(subgraph_key_map[ref])
                        matched = True

                # Some ComfyUI exports encode a subgraph instance as a node whose
                # type/class_type contains the subgraph name/title rather than a
                # stable subgraph_id field. Treat a strong compact-name overlap as
                # a concrete match, but do not compare definition type/class_type.
                if not matched and compact_type:
                    for index, keys in enumerate(definition_compact_keys):
                        for key in keys:
                            if len(key) >= 4 and (key in compact_type or compact_type in key):
                                used_indexes.add(index)
                                matched = True
                                break
                        if matched:
                            break

                # If an explicit serialized reference exists but does not match any
                # definition, do not fall back to scanning unrelated stale definitions.
                # If there is no explicit reference, ComfyUI/LiteGraph may still be
                # using subgraph definitions with runtime-only mapping, so mark this
                # as ambiguous and include definitions conservatively. This prevents
                # real subgraph models from disappearing when the serialized instance
                # does not contain a stable id.
                if not matched and not has_explicit_subgraph_ref and "subgraph" in compact_type:
                    ambiguous_subgraph_instance = True

            # Some real ComfyUI subgraph workflows serialize definitions but do not
            # serialize a stable subgraph_id/name on the active instance node. If no
            # explicit subgraph reference exists anywhere, include definitions
            # conservatively to avoid hiding models used inside subgraphs. If an
            # explicit reference exists but is stale/unmatched, keep the stricter
            # path above and do not pull unrelated definitions.
            if not used_indexes and not ambiguous_subgraph_instance and not any_explicit_subgraph_ref and main_nodes:
                ambiguous_subgraph_instance = True

            return used_indexes, ambiguous_subgraph_instance, any_explicit_subgraph_ref

        raw_main_nodes = []
        main_nodes = []
        if isinstance(workflow_data, dict) and "nodes" in workflow_data:
            raw_nodes = workflow_data.get("nodes") or []
            raw_main_nodes = [node for node in raw_nodes if isinstance(node, dict)] if isinstance(raw_nodes, list) else []
            main_nodes = _active_graph_nodes(raw_main_nodes)

        defs = workflow_data.get("definitions") if isinstance(workflow_data, dict) else None
        subgraphs = (defs or {}).get("subgraphs") if isinstance(defs, dict) else None
        subgraph_defs = [sg for sg in (subgraphs or []) if isinstance(sg, dict) and isinstance(sg.get("nodes"), list)] if isinstance(subgraphs, list) else []

        all_nodes = list(main_nodes)
        if subgraph_defs:
            used_subgraphs, ambiguous_subgraph_instance, any_explicit_subgraph_ref = _main_graph_subgraph_usage(main_nodes, subgraph_defs)
            if not raw_main_nodes:
                # Subgraph-only exported workflows can store their effective graph only
                # in definitions. Include all definitions to avoid false negatives.
                selected_subgraphs = subgraph_defs
            elif not main_nodes:
                # Raw main nodes exist but all are disabled/bypassed. Do not treat
                # that as a subgraph-only workflow.
                selected_subgraphs = []
            elif ambiguous_subgraph_instance:
                selected_subgraphs = subgraph_defs
            elif used_subgraphs:
                selected_subgraphs = [sg for index, sg in enumerate(subgraph_defs) if index in used_subgraphs]
            else:
                selected_subgraphs = []
            for sg in selected_subgraphs:
                all_nodes.extend(_active_graph_nodes(sg.get("nodes") or []))

        folder_paths_cache = {}

        def get_paths_cached(folder_key: str):
            if folder_key in folder_paths_cache:
                return folder_paths_cache[folder_key]
            prefer_default_only = folder_key in ("clip", "text_encoders")
            paths = _get_folder_paths_dedup(folder_key, prefer_default_only=prefer_default_only)
            folder_paths_cache[folder_key] = paths
            return paths

        def is_within_base_path(base_path: str, test_path: str) -> bool:
            try:
                base_abs = os.path.normcase(os.path.abspath(base_path))
                test_abs = os.path.normcase(os.path.abspath(test_path))
                return os.path.commonpath([base_abs, test_abs]) == base_abs
            except Exception:
                return False

        def prune_path_index_cache(now: float):
            if (
                len(cls._path_index_cache) <= cls._path_index_cache_max_entries
                and len(cls._path_index_build_locks) <= cls._path_index_build_locks_max_entries
            ):
                return
            cutoff = now - cls._path_index_cache_ttl
            cls._path_index_cache = {
                key: entry for key, entry in cls._path_index_cache.items()
                if entry.get("time", 0.0) >= cutoff
            }
            if len(cls._path_index_cache) > cls._path_index_cache_max_entries:
                newest_items = sorted(
                    cls._path_index_cache.items(),
                    key=lambda item: item[1].get("time", 0.0),
                    reverse=True,
                )[:cls._path_index_cache_max_entries]
                cls._path_index_cache = dict(newest_items)
            valid_keys = set(cls._path_index_cache.keys())
            if len(cls._path_index_build_locks) > cls._path_index_build_locks_max_entries:
                cls._path_index_build_locks = {
                    key: lock for key, lock in cls._path_index_build_locks.items()
                    if key in valid_keys
                }
                if len(cls._path_index_build_locks) > cls._path_index_build_locks_max_entries:
                    keep = set(list(cls._path_index_build_locks.keys())[-cls._path_index_build_locks_max_entries:])
                    cls._path_index_build_locks = {
                        key: lock for key, lock in cls._path_index_build_locks.items()
                        if key in keep
                    }

        def get_path_index(base_path: str):
            base_key = os.path.normcase(os.path.realpath(base_path))
            now = time.monotonic()
            with cls._path_index_cache_lock:
                prune_path_index_cache(now)
                cached_entry = cls._path_index_cache.get(base_key)
                if cached_entry is not None and (now - cached_entry.get("time", 0.0)) <= cls._path_index_cache_ttl:
                    return cached_entry.get("index", {"exact": {}, "basename": {}})
                build_lock = cls._path_index_build_locks.get(base_key)
                if build_lock is None:
                    build_lock = threading.RLock()
                    cls._path_index_build_locks[base_key] = build_lock

            # Only one thread may build a specific base_path index, but unrelated
            # model folders can still be indexed in parallel.
            with build_lock:
                now = time.monotonic()
                with cls._path_index_cache_lock:
                    prune_path_index_cache(now)
                    cached_entry = cls._path_index_cache.get(base_key)
                    if cached_entry is not None and (now - cached_entry.get("time", 0.0)) <= cls._path_index_cache_ttl:
                        return cached_entry.get("index", {"exact": {}, "basename": {}})

                exact = {}
                basename = {}
                if os.path.exists(base_path):
                    try:
                        seen_dirs = set()
                        for root, dirs, files in os.walk(base_path, followlinks=True):
                            root_key = os.path.normcase(os.path.realpath(root))
                            if root_key in seen_dirs:
                                dirs[:] = []
                                continue
                            seen_dirs.add(root_key)
                            dirs[:] = [
                                d for d in dirs
                                if os.path.normcase(os.path.realpath(os.path.join(root, d))) not in seen_dirs
                            ]
                            for fn in files:
                                if not fn.lower().endswith(MODEL_EXT_LOWER):
                                    continue
                                full_path = os.path.join(root, fn)
                                try:
                                    relp = os.path.relpath(full_path, base_path)
                                except Exception:
                                    relp = full_path
                                rel_key = _normalize_rel(relp).lower()
                                base_name_key = fn.lower()
                                exact.setdefault(rel_key, full_path)
                                basename.setdefault(base_name_key, full_path)
                    except Exception as exc:
                        logger.warning("Ultra Tools Model Viewer: failed to build path index for %s (%s)", base_path, exc)
                cached = {"exact": exact, "basename": basename}
                with cls._path_index_cache_lock:
                    cls._path_index_cache[base_key] = {"time": time.monotonic(), "index": cached}
                    prune_path_index_cache(time.monotonic())
                return cached

        def build_search_values(raw_value: str):
            values = [raw_value]
            lower_value = raw_value.lower()
            if not lower_value.endswith(MODEL_EXT_LOWER) and (
                _looks_like_extensionless_model_ref(raw_value) or _looks_like_extensionless_lora_tag_ref(raw_value)
            ):
                values.extend(raw_value + ext for ext in MODEL_EXTENSIONS)
            return _unique_preserve_order(values)

        def resolve_in_base(base_path: str, search_values):
            if not os.path.exists(base_path):
                return None, None

            normalized_values = []
            for search_value in search_values:
                normalized = _normalize_rel(search_value)
                normalized_values.append((search_value, normalized))
                test_paths = []
                seen_test_paths = set()
                for candidate in (search_value, normalized):
                    test_path = os.path.join(base_path, candidate)
                    test_key = os.path.normcase(os.path.normpath(test_path))
                    if test_key in seen_test_paths:
                        continue
                    seen_test_paths.add(test_key)
                    test_paths.append(test_path)
                for test_path in test_paths:
                    if (
                        is_within_base_path(base_path, test_path)
                        and os.path.isfile(test_path)
                        and test_path.lower().endswith(MODEL_EXT_LOWER)
                    ):
                        return test_path, search_value

            index = get_path_index(base_path)
            for search_value, normalized in normalized_values:
                rel_key = normalized.lower()
                file_path = index["exact"].get(rel_key)
                if file_path and os.path.isfile(file_path) and file_path.lower().endswith(MODEL_EXT_LOWER):
                    return file_path, search_value

                # 단일 파일명 후보는 대소문자 차이만 있는 파일도 basename으로 빠르게 찾는다.
                if os.path.basename(normalized) == normalized:
                    file_path = index["basename"].get(os.path.basename(normalized).lower())
                    if file_path and os.path.isfile(file_path) and file_path.lower().endswith(MODEL_EXT_LOWER):
                        return file_path, search_value

            return None, None

        found_models = {}
        found_file_keys = set()

        def add_found_model(file_path, base_path, matched_value, actual_value, folder_key, category):
            try:
                file_key = os.path.normcase(os.path.realpath(file_path))
                if file_key in found_file_keys:
                    return True

                size = os.path.getsize(file_path)
                try:
                    matched_rel = os.path.relpath(file_path, base_path)
                except Exception:
                    matched_rel = matched_value or actual_value

                display_name = _to_posix(matched_rel)
                if "/" in display_name:
                    parts = display_name.split("/")
                    if len(parts) > 1:
                        display_name = f"{parts[-2]}/{parts[-1]}"

                matched_lower = str(matched_rel or matched_value or actual_value).lower()
                determined_category = _category_for_scanned_base(folder_key, category, base_path)
                if matched_lower.endswith(".gguf"):
                    if determined_category == "UNET":
                        determined_category = "UNET_GGUF"
                    elif determined_category == "CLIP":
                        determined_category = "CLIP_GGUF"
                    elif determined_category == "VAE":
                        determined_category = "VAE_GGUF"
                if matched_lower.endswith(".nunchaku"):
                    if determined_category == "UNET":
                        determined_category = "UNET_Nunchaku"
                    elif determined_category == "VAE":
                        determined_category = "VAE_Nunchaku"

                found_models.setdefault(determined_category, [])
                found_models[determined_category].append({
                    "name": matched_rel,
                    "display_name": display_name,
                    "size": size,
                    "size_formatted": cls.format_size(size),
                    "category": determined_category,
                })
                found_file_keys.add(file_key)
                return True
            except Exception:
                return False

        def resolve_candidates_for_node(node_type, candidates):
            candidates = _unique_preserve_order(candidates)
            if not candidates:
                return

            for raw_value in candidates:
                actual_value = _candidate_ref(raw_value)
                if not actual_value:
                    continue
                tag_type = _candidate_tag_type(raw_value)
                search_values = build_search_values(actual_value)

                found = False
                for folder_key, category in ordered_folder_items_for_node(node_type, tag_type):
                    paths = get_paths_cached(folder_key)
                    if not paths:
                        continue

                    for base_path in paths:
                        file_path, matched_value = resolve_in_base(base_path, search_values)

                        if file_path and os.path.exists(file_path):
                            if add_found_model(file_path, base_path, matched_value, actual_value, folder_key, category):
                                found = True
                                break
                    if found:
                        break

                if not found and not tag_type:
                    try:
                        if hasattr(folder_paths, "folder_names_and_paths"):
                            for folder_name, folder_info in folder_paths.folder_names_and_paths.items():
                                if folder_name in FOLDER_CATEGORIES:
                                    continue
                                for base_path in (folder_info[0] or []):
                                    file_path, matched_value = resolve_in_base(base_path, search_values)
                                    if file_path and os.path.exists(file_path):
                                        if add_found_model(
                                            file_path,
                                            base_path,
                                            matched_value,
                                            actual_value,
                                            folder_name,
                                            _pretty_category_from_folder_key(folder_name),
                                        ):
                                            found = True
                                            break
                                if found:
                                    break
                    except Exception:
                        pass

        for node in all_nodes:
            if not isinstance(node, dict):
                continue

            node_type = node.get("type") or node.get("class_type") or ""
            loose_node = _is_model_related_node_type(node_type)

            candidates = []
            candidates.extend(_collect_model_refs(
                node.get("widgets_values", []),
                loose=loose_node,
                allow_extensionless=True,
                allow_standalone=loose_node,
            ))
            candidates.extend(_collect_model_refs_from_properties(
                node.get("properties", {}),
                loose=loose_node,
                allow_extensionless=True,
                allow_standalone=loose_node,
            ))
            candidates.extend(_collect_model_refs_from_inputs(
                node.get("inputs", []),
                loose=loose_node,
                allow_extensionless=True,
                allow_standalone=loose_node,
            ))
            resolve_candidates_for_node(node_type, candidates)

        if isinstance(frontend_candidates, list):
            for item in frontend_candidates:
                if not isinstance(item, dict):
                    continue
                ref = item.get("ref") or item.get("value") or item.get("filename")
                if not isinstance(ref, str) or not ref.strip():
                    continue
                node_type = item.get("node_type") or item.get("type") or ""
                tag_type = item.get("tag_type")
                candidate = _tagged_ref(ref, tag_type) if tag_type else _strip_ref(ref)
                if candidate:
                    resolve_candidates_for_node(node_type, [candidate])

        result = {"models": {}}
        total_count = 0
        for category, files in found_models.items():
            result["models"][category] = {"files": files, "count": len(files)}
            total_count += len(files)
        result["total_count"] = total_count
        return result


class ModelSizeViewerDetailed:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # ComfyUI가 정상 경로로 위젯을 생성하도록 미리 선언
                # JS에서 동적으로 ComfyWidgets.STRING() 호출 불필요
                "category": (
                    ["All Models", "UNET", "Checkpoints", "Text_Encoders", "CLIP", "CLIP_Vision", "VAE", "LORA",
                     "LLM", "Upscale", "ControlNet",
                     "SEEDVR2", "Animatediff", "Motion_Module", "Photomaker",
                     "Insightface", "Facerestore", "Facedetection", "ONNX",
                     "Diffusers", "CogVideo", "SAMS", "GroundingDINO",
                     "BBOX", "Segm", "Audio_Encoders", "Style_Models",
                     "Hypernetworks", "Embeddings", "GLigen", "Ipadapter",
                     "Prompt_Expander", "Blip", "Model_Patches", "VAE_Approx",
                     "Background_Removal", "Frame_Interpolation", "Geometry_Estimation",
                     "Optical_Flow", "Detection", "Custom"],
                    {"default": "All Models"}
                ),
                "show_top": (
                    ["5","10","15","20","25","30","40","50","75","100"],
                    {"default": "20"}
                ),
                "info": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "execute"
    OUTPUT_NODE = True
    CATEGORY = "Ultra Tools"

    @classmethod
    def VALIDATE_INPUTS(cls, show_top):
        # The frontend rebuilds show_top from the scanned model count
        # (e.g. "3", "7", "45"), so it is not limited to the static list
        # above. Accept any non-negative integer string instead of failing
        # the queued prompt with "Invalid input".
        try:
            return int(str(show_top).strip()) >= 0 or "show_top must be >= 0"
        except (TypeError, ValueError):
            return f"Invalid show_top value: {show_top}"

    def execute(self, category, show_top, info):
        return ()


class ModelSizeViewerWorkflow:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # ComfyUI가 정상 경로로 위젯을 생성하도록 미리 선언
                "models": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "execute"
    OUTPUT_NODE = True
    CATEGORY = "Ultra Tools"

    def execute(self, models):
        return ()


@server.PromptServer.instance.routes.get("/Ultra-model-viewer/scan/{category}")
async def api_scan(request):
    try:
        category = request.match_info.get("category", "LORA")
        result = await asyncio.to_thread(ModelViewerAPI.scan_category, category)
        return web.json_response(result)
    except Exception:
        logger.exception("Ultra Tools Model Viewer: api_scan failed")
        return web.json_response({"files": [], "count": 0, "total_size": 0, "error": "scan failed"})


@server.PromptServer.instance.routes.post("/Ultra-model-viewer/workflow-models")
async def api_workflow(request):
    try:
        data = await request.json()
        workflow = data.get("workflow", {})
        frontend_candidates = data.get("frontend_candidates", [])
        result = await asyncio.to_thread(ModelViewerAPI.scan_workflow, workflow, frontend_candidates)
        return web.json_response(result)
    except Exception:
        logger.exception("Ultra Tools Model Viewer: api_workflow failed")
        return web.json_response({"models": {}, "total_count": 0, "error": "workflow scan failed"})