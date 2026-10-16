"""Ultra Tools Image + PiD.

Compact ComfyUI text-to-image node for Krea 2, Z-Image, Anima, and Qwen
Image. It accepts a STRING prompt, loads the selected diffusion
model/text encoder/VAE, applies an ordered dynamic stack of model-only
LoRAs, samples once, and returns the original generated IMAGE and a PiD IMAGE output. When PiD is on, the PiD output is the upscaled result; when PiD is off, the PiD output mirrors the original image for convenient single-output downstream use. An optional integrated
PiD stage can upscale the sampled latent while keeping CFG fixed at 1.0 and exposing
PiD sampler, scheduler, steps, degrade sigma, and final 1(x4)/0.5(x2) output scale.
PiD output is automatically color-matched to the original with ComfyUI Transfer
Color-equivalent reinhard_lab/per_frame/1.0 processing; no UI control or separate
color-match custom node is required.
An optional SageAttention toggle can internally apply KJNodes Patch Sage Attention
KJ to the main generation MODEL only. OFF keeps the existing execution path and
does not touch KJNodes or SageAttention at runtime. The PiD model is internally
patched with Context Windows (Manual) using the tested 2048/512 standard-static
pyramid setup; spatial dim is automatic (landscape=3, portrait/square=2) and is
intentionally not exposed in the UI.
"""

import inspect
import math
import re
from typing import Optional, Tuple

import folder_paths
import nodes
import comfy.samplers


MAX_RESOLUTION = 16384
MAX_SEED = 0xFFFFFFFFFFFFFFFF
MAX_LORA_STRENGTH = 100.0
MODEL_FAMILIES = ("Krea 2", "Z-Image", "Anima", "Qwen Image")
NEGATIVE_MODES = ("zero positive conditioning", "encode negative text")
PID_UPSCALE_OFF = "off"
PID_UPSCALE_ON = "on"
DEFAULT_WEIGHT_DTYPE = "default"
DEFAULT_TEXT_ENCODER_DEVICE = "default"
_CALL_SIGNATURE_CACHE = {}
_MODERN_NODE_CLASS_CACHE = {}
_MODERN_SIGNATURE_CACHE = {}
_SIGNATURE_CACHE_MISS = object()

# ---------------------------------------------------------------------------
# Latent space registry (single source of truth for PiD compatibility)
#
# PiD is bound to a *latent space*, not to the model that produced the latent.
# Every model family declares which latent space it samples in
# (MODEL_CONTRACTS[...]["latent_space"]), and each latent space declares which
# PiD checkpoint / PiDConditioning latent_format serves it. A value of None means "no PiD for this space yet".
#
# Mirror of the PiD part lives in web/ultra_image_pid.js
# (FAMILY_LATENT_SPACE / LATENT_SPACE_PID). Keep both in sync.
#
# How to enable Qwen Image 2.1 later:
#   1) LATENT_SPACES["qwen21"]: fill pid_checkpoint_token / pid_latent_format
#      with the officially published values.
#   2) Add "Qwen Image 2.1" to MODEL_FAMILIES and MODEL_CONTRACTS with
#      latent_space="qwen21" and verified text_encode / latent / sampling values.
#   3) Mirror the family and PiD token in web/ultra_image_pid.js.
# ---------------------------------------------------------------------------
LATENT_SPACES = {
    "wan21": {
        "label": "Qwen-Image / Wan 2.1 latent (16ch / 8x)",
        "pid_checkpoint_token": "qwenimage",
        "pid_latent_format": "qwenimage",
        # Future Qwen-Image 2.1 PiD files may also contain "qwenimage"; never
        # let them match the 16ch Wan 2.1 space by substring.
        "pid_checkpoint_exclude": (
            re.compile(r"qwen[-_ ]?image[-_ .]?2[._-]?1(?!\d)", re.IGNORECASE),
        ),
    },
    "flux1": {
        "label": "Flux.1 latent (16ch / 8x)",
        "pid_checkpoint_token": "flux1",
        "pid_latent_format": "flux",
        "pid_checkpoint_exclude": (),
    },
    "qwen21": {
        "label": "Qwen-Image 2.1 latent (64ch / 16x)",
        # No family uses this space yet and no PiD checkpoint exists for it.
        "pid_checkpoint_token": None,
        "pid_latent_format": None,
        "pid_checkpoint_exclude": (),
    },
}

PID_OUTPUT_SCALE_HALF = "0.5(x2)"
PID_OUTPUT_SCALE_FULL = "1(x4)"
PID_OUTPUT_SCALES = (PID_OUTPUT_SCALE_FULL, PID_OUTPUT_SCALE_HALF)
PID_MODEL_PLACEHOLDER = "<auto PiD model>"
PID_CFG = 1.0
PID_DENOISE = 1.0
PID_PIXEL_SPACE_VAE = "pixel_space"
PID_CONTEXT_LENGTH = 2048
PID_CONTEXT_OVERLAP = 512
PID_CONTEXT_SCHEDULE = "standard_static"
PID_CONTEXT_STRIDE = 1
PID_CONTEXT_CLOSED_LOOP = False
PID_CONTEXT_FUSE_METHOD = "pyramid"
PID_CONTEXT_FREENOISE = False
PID_CONTEXT_COND_RETAIN = ""
PID_CONTEXT_SPLIT_CONDS = False
PID_CONTEXT_LATENT_RETAIN = ""
PID_CONTEXT_CAUSAL_WINDOW_FIX = False
PID_COLOR_TRANSFER_METHOD = "reinhard_lab"
PID_COLOR_TRANSFER_SOURCE_STATS = "per_frame"
PID_COLOR_TRANSFER_STRENGTH = 1.0
PID_CHECKPOINT_TOKEN_RE = re.compile(
    r"(?:^|[\/._\-\s])(?P<token>pid|pixeldit)",
    re.IGNORECASE,
)
PID_CONCAT_SUFFIXES = ("upscale", "upscaler", "flux1", "qwenimage", "model", "xl")
LORA_ORDER_MISSING = 2**31 - 1

PID_CLIP_PREFERRED = (
    "gemma_2_2b_it_elm_fp8_scaled.safetensors",
    "gemma_2_2b_it_elm_bf16.safetensors",
)

SAGE_ATTENTION_MODE = "auto"
SAGE_ATTENTION_ALLOW_COMPILE = False
SAGE_ATTENTION_NODE_CANDIDATES = (
    "PathchSageAttentionKJ",  # Current KJNodes registration spelling.
    "PatchSageAttentionKJ",  # Defensive alias if KJNodes corrects the typo later.
)


class _AnyType(str):
    """ComfyUI wildcard type used only for dynamic LoRA widget inputs."""

    def __ne__(self, other: object) -> bool:
        return False


class _FlexibleOptionalInputs(dict):
    """Accept dynamic optional widget names while keeping server validation."""

    def __init__(self, value_type: str, initial: Optional[dict] = None):
        super().__init__(initial or {})
        self.value_type = value_type
        self.initial = initial or {}

    def __getitem__(self, key):
        if key in self.initial:
            return self.initial[key]
        return (self.value_type,)

    def __contains__(self, key):
        return True


ANY_TYPE = _AnyType("*")


def _file_choices(folder_name: str, empty_label: str) -> Tuple[str, ...]:
    values = tuple(folder_paths.get_filename_list(folder_name))
    return values if values else (empty_label,)


def _normalize_pid_upscale_mode(value) -> str:
    if isinstance(value, bool):
        return PID_UPSCALE_ON if value else PID_UPSCALE_OFF
    text = str(value or "").strip().lower()
    if text in {"on", "true", "1", "yes"}:
        return PID_UPSCALE_ON
    if text in {"off", "false", "0", "no", ""}:
        return PID_UPSCALE_OFF
    raise ValueError("Unsupported PiD upscale mode: {}".format(value))


def _normalize_sage_attention_enabled(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"on", "true", "1", "yes"}:
        return True
    if text in {"off", "false", "0", "no", ""}:
        return False
    raise ValueError("Unsupported SageAttention mode: {}".format(value))


def _looks_like_pid_checkpoint(value: str) -> bool:
    """Recognize plausible PiD/PixelDiT checkpoint names without substring traps.

    A token must start at a path/filename boundary. After the token, accept the
    usual separator/digit forms or a small set of known concatenated suffixes
    such as pidflux1 / pidqwenimage / pidmodel / pidupscale. Arbitrary CamelCase
    continuations are intentionally rejected so unrelated names such as PIDNet
    cannot be mistaken for PixelDiT checkpoints.
    """
    normalized = str(value or "").replace("\\", "/")
    for match in PID_CHECKPOINT_TOKEN_RE.finditer(normalized):
        suffix = normalized[match.end():]
        if not suffix:
            return True
        first = suffix[0]
        if first in "/._- " or first.isdigit():
            return True
        lowered = suffix.lower()
        if any(lowered.startswith(prefix) for prefix in PID_CONCAT_SUFFIXES):
            return True
    return False


def _pid_model_choices() -> Tuple[str, ...]:
    values = tuple(
        value
        for value in folder_paths.get_filename_list("diffusion_models")
        if _looks_like_pid_checkpoint(value)
    )
    # Keep one backend-valid sentinel so PiD can remain OFF even when the current
    # model family has no matching PiD checkpoint installed.
    return (PID_MODEL_PLACEHOLDER,) + values


def _is_placeholder(value: str) -> bool:
    return value.startswith("<") and value.endswith(">")


def _normalize_pid_output_scale(value: str) -> str:
    text = str(value or "").strip().lower()
    if text in {"1", "1(x4)", "1 (x4)", "x4"}:
        return PID_OUTPUT_SCALE_FULL
    if text in {"0.5", ".5", "0.5(x2)", "0.5 (x2)", "x2"}:
        return PID_OUTPUT_SCALE_HALF
    raise ValueError("Unsupported PiD output scale: {}".format(value))


MODEL_CONTRACTS = {
    "Krea 2": {
        "clip_type": "krea2",
        "latent_space": "wan21",
        "text_encode": "clip_text_encode",
        "latent_node": "EmptyLatentImage",
        "model_sampling_class": None,
        "model_sampling_shift": None,
    },
    "Z-Image": {
        "clip_type": "lumina2",
        "latent_space": "flux1",
        "text_encode": "clip_text_encode",
        "latent_node": "EmptySD3LatentImage",
        "model_sampling_class": "ModelSamplingAuraFlow",
        "model_sampling_shift": 3.0,
    },
    "Anima": {
        "clip_type": "stable_diffusion",
        "latent_space": "wan21",
        "text_encode": "clip_text_encode",
        "latent_node": "EmptyLatentImage",
        "model_sampling_class": None,
        "model_sampling_shift": None,
    },
    "Qwen Image": {
        "clip_type": "qwen_image",
        "latent_space": "wan21",
        "text_encode": "clip_text_encode",
        "latent_node": "EmptySD3LatentImage",
        "model_sampling_class": "ModelSamplingAuraFlow",
        "model_sampling_shift": 3.1,
    },
}


def _family_contract(model_family: str) -> dict:
    contract = MODEL_CONTRACTS.get(model_family)
    if contract is None:
        raise ValueError("Unsupported model family '{}'".format(model_family))
    return contract


def _node_class(class_name: str):
    cls = nodes.NODE_CLASS_MAPPINGS.get(class_name)
    if cls is None:
        raise RuntimeError(
            "Required ComfyUI core node '{}' is unavailable. Update ComfyUI and restart it.".format(
                class_name
            )
        )
    return cls


def _call_node_instance(instance, **kwargs):
    function_name = getattr(instance.__class__, "FUNCTION", None)
    if not function_name:
        raise RuntimeError(
            "ComfyUI node '{}' has no FUNCTION declaration.".format(instance.__class__.__name__)
        )
    function = getattr(instance, function_name)
    cache_key = (instance.__class__, function_name)
    accepted_names = _CALL_SIGNATURE_CACHE.get(cache_key, _SIGNATURE_CACHE_MISS)
    if accepted_names is _SIGNATURE_CACHE_MISS:
        signature = inspect.signature(function)
        accepts_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )
        accepted_names = None if accepts_kwargs else frozenset(signature.parameters)
        _CALL_SIGNATURE_CACHE[cache_key] = accepted_names
    filtered = (
        kwargs
        if accepted_names is None
        else {key: value for key, value in kwargs.items() if key in accepted_names}
    )
    return function(**filtered)


def _call_core_node(class_name: str, **kwargs):
    return _call_node_instance(_node_class(class_name)(), **kwargs)


def _resolve_sage_attention_node_class() -> Tuple[str, type]:
    for class_name in SAGE_ATTENTION_NODE_CANDIDATES:
        cls = nodes.NODE_CLASS_MAPPINGS.get(class_name)
        if cls is not None:
            return class_name, cls
    raise RuntimeError(
        _error_message(
            "SageAttention 노드 없음",
            [
                "SageAttention을 ON으로 사용하려면 ComfyUI-KJNodes의 Patch Sage Attention KJ 노드가 필요합니다.",
                "KJNodes 또는 SageAttention을 사용할 수 없는 환경에서는 SageAttention을 OFF로 두십시오.",
                "OFF 상태에서는 KJNodes와 SageAttention을 조회하거나 실행하지 않습니다.",
            ],
        )
    )


def _apply_sage_attention_patch(model):
    _, cls = _resolve_sage_attention_node_class()
    try:
        # Match KJNodes Patch Sage Attention KJ: sage_attention=auto and
        # allow_compile=False. The KJ node itself performs the MODEL clone and
        # installs optimized_attention_override. No sageattention import occurs
        # here unless this ON-only path reaches KJ's patch implementation.
        return _call_node_instance(
            cls(),
            model=model,
            sage_attention=SAGE_ATTENTION_MODE,
            allow_compile=SAGE_ATTENTION_ALLOW_COMPILE,
        )[0]
    except Exception as exc:
        raise RuntimeError(
            _error_message(
                "SageAttention 적용 실패",
                [
                    "KJ Patch Sage Attention KJ를 내부 적용하지 못했습니다.",
                    "내부 모드: {}".format(SAGE_ATTENTION_MODE),
                    "allow_compile: {}".format(SAGE_ATTENTION_ALLOW_COMPILE),
                    "SageAttention은 메인 이미지 생성 MODEL에만 적용하며 PiD MODEL에는 적용하지 않습니다.",
                    "SageAttention을 사용할 수 없는 환경에서는 이 옵션을 OFF로 두십시오.",
                ],
                exc,
            )
        ) from exc


def _require_sampler(name: str) -> None:
    if name not in comfy.samplers.KSampler.SAMPLERS:
        raise RuntimeError("Sampler '{}' is not available in this ComfyUI build.".format(name))


def _require_scheduler(name: str) -> None:
    if name not in comfy.samplers.KSampler.SCHEDULERS:
        raise RuntimeError("Scheduler '{}' is not available in this ComfyUI build.".format(name))


def _core_input_values(class_name: str, input_name: str) -> Tuple[str, ...]:
    cls = _node_class(class_name)
    input_types = getattr(cls, "INPUT_TYPES", None)
    if not callable(input_types):
        return ()
    try:
        spec = input_types()
    except Exception:
        return ()
    input_info = spec.get("required", {}).get(input_name)
    if not input_info:
        return ()
    values = input_info[0]
    if isinstance(values, (tuple, list)):
        return tuple(str(value) for value in values)
    return ()


def _require_clip_type(name: str) -> None:
    available = _core_input_values("CLIPLoader", "type")
    if available and name not in available:
        raise RuntimeError(
            "CLIPLoader does not support clip type '{}' in this ComfyUI build.".format(name)
        )


def _require_available_file(folder_name: str, selected_value: str, label: str) -> None:
    available = tuple(folder_paths.get_filename_list(folder_name))
    if available and selected_value not in available:
        raise RuntimeError(
            "Selected {} '{}' is not in the current ComfyUI model list. Refresh the model list or restart ComfyUI.".format(
                label, selected_value
            )
        )


def _error_message(title: str, lines, exc: Optional[BaseException] = None) -> str:
    message = ["Ultra Tools Image + PiD — {}".format(title)]
    filtered = [str(line) for line in lines if str(line).strip()]
    if filtered:
        message.append("")
        message.extend(filtered)
    if exc is not None:
        message.extend(
            [
                "",
                "ComfyUI 원본 오류:",
                "{}: {}".format(exc.__class__.__name__, exc),
            ]
        )
    return "\n".join(message)


def _normalize_resolution_dimension(value, label: str) -> int:
    """Normalize one width/height input and validate the core latent multiple.

    ComfyUI INT links normally arrive as plain integers, but selector/custom
    nodes can return numeric strings, integer-valued floats, scalar
    tensor/NumPy-like objects, or a one-item container. The upstream node is
    responsible for aspect-ratio selection, but this final execution node
    validates the resulting value itself. Core latent allocation for the
    supported paths uses an 8-pixel spatial divisor, so non-multiples that
    would be silently truncated are rejected before sampling. Individual
    model families may still recommend coarser resolution steps such as 16.
    """
    current = value
    for _ in range(4):
        if isinstance(current, (list, tuple)):
            if len(current) != 1:
                raise ValueError(
                    "{} 입력은 하나의 해상도 값이어야 합니다. 받은 항목 수: {}".format(
                        label, len(current)
                    )
                )
            current = current[0]
            continue

        item = getattr(current, "item", None)
        if callable(item) and not isinstance(current, (str, bytes, bytearray)):
            try:
                extracted = item()
            except Exception:
                extracted = current
            if extracted is not current:
                current = extracted
                continue
        break

    if isinstance(current, bool):
        raise ValueError("{} 입력은 True/False가 아닌 정수여야 합니다.".format(label))

    if isinstance(current, int):
        normalized = int(current)
    elif isinstance(current, float):
        if not math.isfinite(current) or not current.is_integer():
            raise ValueError("{} 입력은 정수여야 합니다: {}".format(label, current))
        normalized = int(current)
    elif isinstance(current, str):
        stripped = current.strip()
        if not stripped:
            raise ValueError("{} 입력이 비어 있습니다.".format(label))
        try:
            normalized = int(stripped, 10)
        except ValueError:
            try:
                numeric = float(stripped)
            except ValueError as exc:
                raise ValueError(
                    "{} 입력을 정수 해상도로 해석할 수 없습니다: {!r}".format(
                        label, current
                    )
                ) from exc
            if not math.isfinite(numeric) or not numeric.is_integer():
                raise ValueError("{} 입력은 정수여야 합니다: {}".format(label, current))
            normalized = int(numeric)
    else:
        try:
            numeric = float(current)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "{} 입력을 정수 해상도로 해석할 수 없습니다: {!r}".format(
                    label, current
                )
            ) from exc
        if not math.isfinite(numeric) or not numeric.is_integer():
            raise ValueError("{} 입력은 정수여야 합니다: {}".format(label, current))
        normalized = int(numeric)

    if normalized < 64 or normalized > MAX_RESOLUTION:
        raise ValueError(
            "{}는 64~{} 범위여야 합니다: {}".format(
                label, MAX_RESOLUTION, normalized
            )
        )
    if normalized % 8 != 0:
        lower = max(64, normalized - (normalized % 8))
        upper = lower + 8
        raise ValueError(
            "{}는 ComfyUI latent 크기와 정확히 맞도록 8의 배수여야 합니다: {} (가까운 값: {} 또는 {})".format(
                label, normalized, lower, upper
            )
        )
    return normalized


def _parse_lora_widget(key: str, value) -> Optional[Tuple[int, str, str, float]]:
    """Return sortable dynamic LoRA data or None for a disabled/invalid row."""
    if not str(key).lower().startswith("lora_") or not isinstance(value, dict):
        return None
    if not bool(value.get("on", True)):
        return None

    lora_name = str(value.get("lora", "") or "").strip()
    if not lora_name or lora_name.lower() == "none":
        return None

    try:
        strength = float(value.get("strength", 1.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid LoRA strength for '{}'.".format(lora_name)) from exc
    if not math.isfinite(strength):
        raise ValueError("LoRA strength must be finite for '{}'.".format(lora_name))
    if abs(strength) > MAX_LORA_STRENGTH:
        raise ValueError(
            "LoRA strength for '{}' must be between -{} and {}.".format(
                lora_name, int(MAX_LORA_STRENGTH), int(MAX_LORA_STRENGTH)
            )
        )
    if strength == 0.0:
        return None

    try:
        order = int(value.get("order", LORA_ORDER_MISSING))
    except (TypeError, ValueError):
        order = LORA_ORDER_MISSING
    return order, str(key), lora_name, strength


def _collect_lora_rows(values: dict):
    parsed = []
    for position, (key, value) in enumerate(values.items()):
        item = _parse_lora_widget(key, value)
        if item is not None:
            parsed.append((item, position))

    if len(parsed) <= 1:
        return [item for item, _ in parsed]

    has_explicit_order = [item[0] != LORA_ORDER_MISSING for item, _ in parsed]
    if all(has_explicit_order):
        # Normal frontend path: every dynamic LoRA row carries an explicit
        # visual order, so preserve that exact user-facing order.
        parsed.sort(key=lambda entry: (entry[0][0], entry[1]))
    elif not any(has_explicit_order):
        # API/hand-authored fallback: when every row omits order and all keys
        # use the standard lora_N form, use natural numeric key order. If even
        # one key is non-standard, the caller's insertion order is safer than
        # inventing a partial ordering.
        numeric_keys = []
        for item, _ in parsed:
            match = re.fullmatch(r"lora_(\d+)", item[1], flags=re.IGNORECASE)
            if not match:
                numeric_keys = []
                break
            numeric_keys.append(int(match.group(1)))
        if numeric_keys:
            parsed.sort(key=lambda entry: (int(re.fullmatch(r"lora_(\d+)", entry[0][1], flags=re.IGNORECASE).group(1)), entry[1]))
    # Mixed explicit/missing order is intentionally left in payload insertion
    # order. A partial order is ambiguous and should not silently move rows.
    return [item for item, _ in parsed]


def _latent_space_key_for_family(model_family: str) -> str:
    return str(_family_contract(model_family)["latent_space"])


def _latent_space_for_family(model_family: str) -> dict:
    return LATENT_SPACES[_latent_space_key_for_family(model_family)]


def _pid_model_family_for_family(model_family: str) -> Optional[str]:
    """PiD checkpoint filename token for the family's latent space, or None."""
    return _latent_space_for_family(model_family).get("pid_checkpoint_token")


def _pid_latent_format_for_family(model_family: str) -> Optional[str]:
    """PiDConditioning latent_format for the family's latent space, or None."""
    return _latent_space_for_family(model_family).get("pid_latent_format")


def _pid_model_matches_family(model_name: str, model_family: str) -> bool:
    normalized = str(model_name or "").replace("\\", "/").lower()
    if not normalized or not _looks_like_pid_checkpoint(model_name):
        return False
    space = _latent_space_for_family(model_family)
    target = space.get("pid_checkpoint_token")
    if not target or target not in normalized:
        return False
    for pattern in space.get("pid_checkpoint_exclude", ()):
        if pattern.search(normalized):
            return False
    return True


def _resolve_pid_clip_name() -> str:
    available = tuple(folder_paths.get_filename_list("text_encoders"))
    for preferred in PID_CLIP_PREFERRED:
        for value in available:
            if str(value).replace("\\", "/").split("/")[-1] == preferred:
                return str(value)
    fallback_candidates = sorted(
        str(value)
        for value in available
        if "gemma_2_2b_it_elm" in str(value).replace("\\", "/").lower()
    )
    if fallback_candidates:
        return fallback_candidates[0]
    return ""


def _modern_node_output_values(result):
    if isinstance(result, tuple):
        return result
    args = getattr(result, "args", None)
    if args is not None:
        return tuple(args)
    if isinstance(result, list):
        return tuple(result)
    return (result,)


def _modern_node_class(class_name: str, fallback_module: str, fallback_class: str):
    cache_key = (class_name, fallback_module, fallback_class)
    cached = _MODERN_NODE_CLASS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    # Cache only the lightweight node class object, never MODEL/CLIP/VAE runtime
    # objects. Python already caches imported modules; this avoids repeating
    # registry/import resolution on every PiD execution.
    try:
        module = __import__(fallback_module, fromlist=[fallback_class])
        cls = getattr(module, fallback_class)
        if callable(getattr(cls, "execute", None)):
            _MODERN_NODE_CLASS_CACHE[cache_key] = cls
            return cls
    except Exception as import_exc:
        cls = nodes.NODE_CLASS_MAPPINGS.get(class_name)
        if cls is not None and callable(getattr(cls, "execute", None)):
            _MODERN_NODE_CLASS_CACHE[cache_key] = cls
            return cls
        raise RuntimeError(
            "Required ComfyUI core node '{}' is unavailable. Update ComfyUI and restart it.".format(
                class_name
            )
        ) from import_exc

    cls = nodes.NODE_CLASS_MAPPINGS.get(class_name)
    if cls is not None and callable(getattr(cls, "execute", None)):
        _MODERN_NODE_CLASS_CACHE[cache_key] = cls
        return cls
    raise RuntimeError(
        "Required ComfyUI core node '{}' does not expose the modern execute API.".format(
            class_name
        )
    )


def _call_modern_core_node(class_name: str, fallback_module: str, fallback_class: str, **kwargs):
    cls = _modern_node_class(class_name, fallback_module, fallback_class)
    execute = getattr(cls, "execute", None)
    if not callable(execute):
        raise RuntimeError(
            "Required ComfyUI core node '{}' does not expose the modern execute API.".format(
                class_name
            )
        )

    cache_key = (cls, "execute")
    accepted_names = _MODERN_SIGNATURE_CACHE.get(cache_key, _SIGNATURE_CACHE_MISS)
    if accepted_names is _SIGNATURE_CACHE_MISS:
        signature = inspect.signature(execute)
        accepts_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )
        accepted_names = None if accepts_kwargs else frozenset(signature.parameters)
        _MODERN_SIGNATURE_CACHE[cache_key] = accepted_names
    filtered = kwargs if accepted_names is None else {
        key: value for key, value in kwargs.items() if key in accepted_names
    }
    return _modern_node_output_values(execute(**filtered))


def _pid_context_dim(source_width: int, source_height: int) -> int:
    # User-tested PiD behavior: window over the long spatial axis. Landscape
    # uses width (dim 3); portrait and square use height (dim 2). Keeping this
    # internal avoids exposing a low-level tensor-axis setting in the UI.
    return 3 if int(source_width) > int(source_height) else 2


def _apply_pid_context_windows(model, source_width: int, source_height: int):
    dim = _pid_context_dim(source_width, source_height)
    return _call_modern_core_node(
        "ContextWindowsManual",
        "comfy_extras.nodes_context_windows",
        "ContextWindowsManualNode",
        model=model,
        context_length=PID_CONTEXT_LENGTH,
        context_overlap=PID_CONTEXT_OVERLAP,
        context_schedule=PID_CONTEXT_SCHEDULE,
        context_stride=PID_CONTEXT_STRIDE,
        closed_loop=PID_CONTEXT_CLOSED_LOOP,
        fuse_method=PID_CONTEXT_FUSE_METHOD,
        dim=dim,
        freenoise=PID_CONTEXT_FREENOISE,
        cond_retain_index_list=PID_CONTEXT_COND_RETAIN,
        split_conds_to_windows=PID_CONTEXT_SPLIT_CONDS,
        latent_retain_index_list=PID_CONTEXT_LATENT_RETAIN,
        causal_window_fix=PID_CONTEXT_CAUSAL_WINDOW_FIX,
    )[0]


def _apply_pid_conditioning(positive, sampled_latent, latent_format: str, degrade_sigma: float):
    return _call_modern_core_node(
        "PiDConditioning",
        "comfy_extras.nodes_pid",
        "PiDConditioning",
        positive=positive,
        latent=sampled_latent,
        latent_format=latent_format,
        degrade_sigma=float(degrade_sigma),
    )[0]


def _validate_pid_configuration(
    model_family: str,
    pid_model: str,
    pid_sampler: str,
    pid_scheduler: str,
    pid_steps: int,
    pid_degrade_sigma: float,
    pid_output_scale: str,
) -> str:
    space = _latent_space_for_family(model_family)
    if not space.get("pid_checkpoint_token") or not space.get("pid_latent_format"):
        raise RuntimeError(
            _error_message(
                "PiD 미지원 latent 공간",
                [
                    "선택한 모델 계열: {}".format(model_family),
                    "{}용 PiD 체크포인트가 아직 없습니다. PiD를 OFF로 두십시오.".format(space["label"]),
                ],
            )
        )
    if _is_placeholder(str(pid_model)):
        raise RuntimeError(
            _error_message(
                "PiD 설정 오류",
                [
                    "사용 가능한 PiD 모델을 찾지 못했습니다.",
                    "현재 모델 계열에는 {} PiD 체크포인트가 필요합니다.".format(
                        _pid_model_family_for_family(model_family)
                    ),
                ],
            )
        )
    if not _pid_model_matches_family(pid_model, model_family):
        raise RuntimeError(
            _error_message(
                "PiD 모델 계열 불일치",
                [
                    "선택한 PiD 모델: {}".format(pid_model),
                    "현재 {}에는 {} 계열 PiD 모델이 필요합니다.".format(
                        model_family, _pid_model_family_for_family(model_family)
                    ),
                ],
            )
        )
    _require_available_file("diffusion_models", pid_model, "PiD diffusion model")
    _require_sampler(pid_sampler)
    _require_scheduler(pid_scheduler)
    if int(pid_steps) < 1:
        raise ValueError("PiD steps must be at least 1.")
    if not 0.0 <= float(pid_degrade_sigma) <= 1.0:
        raise ValueError("PiD degrade sigma must be between 0 and 1.")
    pid_output_scale = _normalize_pid_output_scale(pid_output_scale)

    _require_clip_type("pixeldit")
    pid_clip_name = _resolve_pid_clip_name()
    if not pid_clip_name:
        raise RuntimeError(
            _error_message(
                "PiD text encoder 없음",
                [
                    "PiD용 Gemma text encoder를 찾지 못했습니다.",
                    "지원 파일 예: {}".format(", ".join(PID_CLIP_PREFERRED)),
                ],
            )
        )
    _require_available_file("text_encoders", pid_clip_name, "PiD text encoder")

    # These are core PiD building blocks. Context Windows is applied only
    # while PiD is enabled; its tuning stays internal except for the automatic
    # spatial dim selection.
    _node_class("EmptyChromaRadianceLatentImage")
    _node_class("VAELoader")
    _modern_node_class(
        "PiDConditioning",
        "comfy_extras.nodes_pid",
        "PiDConditioning",
    )
    _modern_node_class(
        "ContextWindowsManual",
        "comfy_extras.nodes_context_windows",
        "ContextWindowsManualNode",
    )
    return pid_clip_name


def _run_pid_upscale(
    sampled_latent,
    prompt: str,
    model_family: str,
    pid_model: str,
    pid_sampler: str,
    pid_scheduler: str,
    pid_steps: int,
    pid_degrade_sigma: float,
    pid_output_scale: str,
    seed: int,
    source_width: int,
    source_height: int,
    pid_clip_name: str,
):
    pid_model_object = _call_core_node(
        "UNETLoader",
        unet_name=pid_model,
        weight_dtype=DEFAULT_WEIGHT_DTYPE,
    )[0]
    pid_model_object = _apply_pid_context_windows(
        pid_model_object,
        source_width=source_width,
        source_height=source_height,
    )
    pid_clip = _call_core_node(
        "CLIPLoader",
        clip_name=pid_clip_name,
        type="pixeldit",
        device=DEFAULT_TEXT_ENCODER_DEVICE,
    )[0]
    pid_vae = _call_core_node("VAELoader", vae_name=PID_PIXEL_SPACE_VAE)[0]

    pid_text = _call_core_node("CLIPTextEncode", clip=pid_clip, text=str(prompt or ""))[0]
    # Follow the official PixelDiT PiD graph: positive uses PiDConditioning,
    # while PiD negative is always ConditioningZeroOut of the PiD text encoding.
    # The main node's negative_prompt intentionally affects only base-image
    # generation. With the current fixed PiD CFG=1.0, ComfyUI normally skips the
    # unconditional branch, but keeping this explicit also documents the intended
    # behavior if the sampling implementation changes later.
    pid_negative = _call_core_node("ConditioningZeroOut", conditioning=pid_text)[0]
    pid_positive = _apply_pid_conditioning(
        pid_text,
        sampled_latent,
        _pid_latent_format_for_family(model_family),
        pid_degrade_sigma,
    )

    samples = sampled_latent["samples"]
    batch_size = int(samples.shape[0])
    # In the integrated node the generation dimensions are already known, so the
    # PiD target follows the actual requested image size directly instead of
    # reverse-inferring pixels from latent tensor shape.
    target_width = int(source_width) * 4
    target_height = int(source_height) * 4
    if target_width > MAX_RESOLUTION or target_height > MAX_RESOLUTION:
        raise RuntimeError(
            _error_message(
                "PiD 출력 해상도 초과",
                [
                    "PiD 목표 해상도: {} × {}".format(target_width, target_height),
                    "통합 노드의 최대 한 변은 {}입니다.".format(MAX_RESOLUTION),
                ],
            )
        )

    # PixelDiT PiD uses the same Chroma/Radiance target latent space for the
    # supported Flux/Qwen source families. Source-family differences are handled
    # above by PiDConditioning.latent_format; they do not select a different
    # target-latent node.
    target_latent = _call_core_node(
        "EmptyChromaRadianceLatentImage",
        width=target_width,
        height=target_height,
        batch_size=batch_size,
    )[0]
    pid_sampled = _call_core_node(
        "KSampler",
        model=pid_model_object,
        seed=int(seed),
        steps=int(pid_steps),
        cfg=PID_CFG,
        sampler_name=pid_sampler,
        scheduler=pid_scheduler,
        positive=pid_positive,
        negative=pid_negative,
        latent_image=target_latent,
        denoise=float(PID_DENOISE),
    )[0]
    images = _call_core_node("VAEDecode", vae=pid_vae, samples=pid_sampled)[0]

    pid_output_scale = _normalize_pid_output_scale(pid_output_scale)
    if pid_output_scale == PID_OUTPUT_SCALE_HALF:
        import comfy.utils

        output_height = max(1, round(images.shape[1] * 0.5))
        output_width = max(1, round(images.shape[2] * 0.5))
        images = comfy.utils.common_upscale(
            images.movedim(-1, 1),
            output_width,
            output_height,
            "lanczos",
            "disabled",
        ).movedim(1, -1)
    return images


def _apply_pid_color_transfer(image_target, image_ref):
    """Match each PiD frame to its original with core Transfer Color semantics.

    This is the current ComfyUI Transfer Color configuration best suited to
    retaining PiD's spatial/detail changes: reinhard_lab, per_frame, strength
    1.0.  The implementation is kept local so the integrated node does not
    require a separately placed color-match node.
    """
    if PID_COLOR_TRANSFER_METHOD != "reinhard_lab":
        raise RuntimeError("Unsupported internal PiD color transfer method.")
    if PID_COLOR_TRANSFER_SOURCE_STATS != "per_frame":
        raise RuntimeError("Unsupported internal PiD color transfer statistics mode.")
    if PID_COLOR_TRANSFER_STRENGTH != 1.0:
        raise RuntimeError("Unsupported internal PiD color transfer strength.")
    if image_ref is None:
        return image_target

    import torch
    import kornia
    import comfy.model_management
    import comfy.utils

    if image_target.ndim != 4 or image_ref.ndim != 4:
        raise ValueError("PiD color transfer expects batched IMAGE tensors.")
    if image_target.shape[-1] != 3 or image_ref.shape[-1] != 3:
        raise ValueError("PiD color transfer expects RGB IMAGE tensors.")
    if image_ref.shape[0] < 1:
        raise ValueError("PiD color transfer requires at least one original image.")

    device = comfy.model_management.get_torch_device()
    intermediate_device = comfy.model_management.intermediate_device()
    intermediate_dtype = comfy.model_management.intermediate_dtype()
    eps = 1e-6
    batch, height, width, channels = image_target.shape
    ref_batch = image_ref.shape[0]
    progress = comfy.utils.ProgressBar(batch)
    output = torch.empty(
        batch,
        height,
        width,
        channels,
        device=intermediate_device,
        dtype=intermediate_dtype,
    )

    for index in range(batch):
        ref_index = min(index, ref_batch - 1)
        source_lab = kornia.color.rgb_to_lab(
            image_target[index:index + 1]
            .to(device=device, dtype=torch.float32)
            .permute(0, 3, 1, 2)
        )
        reference_lab = kornia.color.rgb_to_lab(
            image_ref[ref_index:ref_index + 1]
            .to(device=device, dtype=torch.float32)
            .permute(0, 3, 1, 2)
        )

        source_flat = source_lab.reshape(channels, -1)
        reference_flat = reference_lab.reshape(channels, -1)
        source_mean = source_flat.mean(dim=-1, keepdim=True)
        reference_mean = reference_flat.mean(dim=-1, keepdim=True)
        source_std = source_flat.std(dim=-1, keepdim=True, unbiased=False).clamp_min_(eps)
        reference_std = reference_flat.std(dim=-1, keepdim=True, unbiased=False).clamp_min_(eps)
        corrected = (
            (source_flat - source_mean) * (reference_std / source_std)
            + reference_mean
        )

        corrected_rgb = kornia.color.lab_to_rgb(
            corrected.reshape(1, channels, height, width)
        )
        output[index] = (
            corrected_rgb.squeeze(0)
            .permute(1, 2, 0)
            .clamp_(0, 1)
            .to(device=intermediate_device, dtype=intermediate_dtype)
        )
        progress.update(1)

    return output


class UltraImagePiD:
    CATEGORY = "Ultra Tools"
    FUNCTION = "generate"
    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("Original Image", "PiD Image")
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Connect Prompt Generator.output to positive_prompt. Generates with Krea 2, Z-Image, "
        "Anima, or Qwen Image, supports a compact dynamically ordered model-only LoRA stack, "
        "optionally applies KJ SageAttention to the main MODEL and/or an integrated PiD upscale stage, "
        "and returns the original IMAGE plus a PiD IMAGE output. PiD denoise is internally fixed at "
        "1.0; PiD output color matching uses reinhard_lab/per_frame/1.0 automatically."
    )

    def __init__(self):
        # Keep the runtime instance stateless with respect to loaded MODEL/CLIP/VAE
        # objects and LoRA loader nodes. ComfyUI's own loader/model-management path
        # remains responsible for reuse and memory handling, while this node avoids
        # retaining potentially stale heavyweight runtime objects across executions.
        pass

    @classmethod
    def INPUT_TYPES(cls):
        diffusion_models = _file_choices("diffusion_models", "<no diffusion model found>")
        text_encoders = _file_choices("text_encoders", "<no text encoder found>")
        vaes = _file_choices("vae", "<no VAE found>")
        pid_models = _pid_model_choices()
        pid_sampler_default = "lcm" if "lcm" in comfy.samplers.KSampler.SAMPLERS else comfy.samplers.KSampler.SAMPLERS[0]
        pid_scheduler_default = "sgm_uniform" if "sgm_uniform" in comfy.samplers.KSampler.SCHEDULERS else ("simple" if "simple" in comfy.samplers.KSampler.SCHEDULERS else comfy.samplers.KSampler.SCHEDULERS[0])
        return {
            "required": {
                "positive_prompt": (
                    "STRING",
                    {
                        "forceInput": True,
                        "multiline": True,
                        "tooltip": "Connect a STRING here. Blank text is allowed and is encoded as an empty positive prompt without rewriting.",
                    },
                ),
                "model_family": (MODEL_FAMILIES, {"default": "Krea 2"}),
                "diffusion_model": (diffusion_models,),
                "text_encoder": (text_encoders,),
                "vae_name": (vaes,),
                "width": (
                    "INT",
                    {"default": 1152, "min": 64, "max": MAX_RESOLUTION, "step": 16},
                ),
                "height": (
                    "INT",
                    {"default": 896, "min": 64, "max": MAX_RESOLUTION, "step": 16},
                ),
                "batch_size": (
                    "INT",
                    {
                        "default": 1,
                        "min": 1,
                        "max": 16,
                        "step": 1,
                        "tooltip": "PiD ON creates a 4x target for every batch item. Batch 1 is recommended when PiD is enabled to avoid excessive VRAM use.",
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": MAX_SEED,
                        "control_after_generate": True,
                    },
                ),
                "steps": ("INT", {"default": 10, "min": 1, "max": 1000, "step": 1}),
                "cfg": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 100.0, "step": 0.1}),
                "sampler_name": (
                    tuple(comfy.samplers.KSampler.SAMPLERS),
                    {"default": "euler"},
                ),
                "scheduler": (
                    tuple(comfy.samplers.KSampler.SCHEDULERS),
                    {"default": "simple"},
                ),
                "denoise": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "negative_mode": (NEGATIVE_MODES, {"default": NEGATIVE_MODES[0]}),
                "negative_prompt": (
                    "STRING",
                    {"default": "", "multiline": True, "dynamicPrompts": True},
                ),
                "pid_upscale": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "label_on": "ON",
                        "label_off": "OFF",
                        "tooltip": "Enable integrated PiD latent upscale. PiD-only controls are shown in the frontend only when enabled.",
                    },
                ),
                "pid_model": (pid_models,),
                "pid_sampler": (
                    tuple(comfy.samplers.KSampler.SAMPLERS),
                    {"default": pid_sampler_default},
                ),
                "pid_scheduler": (
                    tuple(comfy.samplers.KSampler.SCHEDULERS),
                    {"default": pid_scheduler_default},
                ),
                "pid_steps": ("INT", {"default": 4, "min": 1, "max": 1000, "step": 1}),
                "pid_degrade_sigma": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.01,
                        "tooltip": "0.0 for a normal fully denoised KSampler latent; raise only for partially denoised/noisy input latents.",
                    },
                ),
                "pid_output_scale": (PID_OUTPUT_SCALES, {"default": PID_OUTPUT_SCALE_FULL}),
                "sage_attention": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "label_on": "ON",
                        "label_off": "OFF",
                        "tooltip": "Apply KJ Patch Sage Attention KJ to the main generation MODEL only. OFF has zero KJ/Sage runtime dependency; ON uses auto with allow_compile disabled.",
                    },
                ),
            },
            # The frontend creates lora_<unique id> widgets dynamically. The wildcard
            # validator allows those dictionary values to reach generate(**lora_values).
            "optional": _FlexibleOptionalInputs(ANY_TYPE),
        }

    def _resolve_clip_type(self, contract: dict) -> str:
        return str(contract["clip_type"])

    def _resolve_latent_node(self, contract: dict) -> str:
        return str(contract["latent_node"])

    def _resolve_model_sampling(self, contract: dict) -> Tuple[Optional[str], Optional[float]]:
        sampling_class = contract.get("model_sampling_class")
        if not sampling_class:
            return None, None
        shift = contract.get("model_sampling_shift")
        return str(sampling_class), None if shift is None else float(shift)

    def _validate_configuration(
        self,
        diffusion_model: str,
        text_encoder: str,
        vae_name: str,
        sampler_name: str,
        scheduler: str,
        negative_mode: str,
        latent_node_name: str,
        model_sampling_class: Optional[str],
        lora_rows,
        resolved_clip_type: str,
        sage_attention: bool,
    ) -> None:
        if negative_mode not in NEGATIVE_MODES:
            raise ValueError(
                _error_message(
                    "설정 오류",
                    [
                        "negative_mode 값이 올바르지 않습니다: {}".format(negative_mode),
                        "허용값: {}".format(", ".join(NEGATIVE_MODES)),
                    ],
                )
            )
        required_files = [
            (diffusion_model, "diffusion model"),
            (text_encoder, "text encoder"),
            (vae_name, "VAE"),
        ]
        for value, label in required_files:
            if _is_placeholder(value):
                raise ValueError(
                    _error_message("설정 오류", ["선택 가능한 {} 파일이 없습니다.".format(label)])
                )

        for required_class in (
            "UNETLoader",
            "CLIPLoader",
            "CLIPTextEncode",
            latent_node_name,
            "KSampler",
        ):
            _node_class(required_class)
        _node_class("VAELoader")
        _node_class("VAEDecode")
        if negative_mode == "zero positive conditioning":
            _node_class("ConditioningZeroOut")
        if model_sampling_class:
            _node_class(model_sampling_class)
        if sage_attention:
            _resolve_sage_attention_node_class()

        _require_clip_type(resolved_clip_type)
        _require_available_file("diffusion_models", diffusion_model, "diffusion model")
        _require_available_file("text_encoders", text_encoder, "text encoder")
        _require_available_file("vae", vae_name, "VAE")
        _require_sampler(sampler_name)
        _require_scheduler(scheduler)

        if lora_rows:
            _node_class("LoraLoaderModelOnly")
            available_loras = set(folder_paths.get_filename_list("loras"))
            if available_loras:
                for _, _, lora_name, _ in lora_rows:
                    if lora_name not in available_loras:
                        raise RuntimeError(
                            "Selected LoRA '{}' is not in the current ComfyUI LoRA list. Refresh the model list or restart ComfyUI.".format(
                                lora_name
                            )
                        )

    def _load_assets(
        self,
        model_family: str,
        diffusion_model: str,
        text_encoder: str,
        resolved_clip_type: str,
        vae_name: str,
    ):
        # Always request fresh runtime asset objects for each execution. This node
        # intentionally does not keep a private long-lived cache of MODEL/CLIP/VAE
        # objects because those heavyweight objects may participate in ComfyUI's
        # evolving offload / model-management lifecycle.
        try:
            model = _call_core_node(
                "UNETLoader",
                unet_name=diffusion_model,
                weight_dtype=DEFAULT_WEIGHT_DTYPE,
            )[0]
        except Exception as exc:
            raise RuntimeError(
                _error_message(
                    "확산 모델 로드 실패",
                    [
                        "선택한 모델 계열: {}".format(model_family),
                        "선택한 확산 모델: {}".format(diffusion_model),
                        "model_family와 확산 모델이 같은 계열인지 확인하십시오.",
                    ],
                    exc,
                )
            ) from exc

        try:
            clip = _call_core_node(
                "CLIPLoader",
                clip_name=text_encoder,
                type=resolved_clip_type,
                device=DEFAULT_TEXT_ENCODER_DEVICE,
            )[0]
        except Exception as exc:
            raise RuntimeError(
                _error_message(
                    "텍스트 인코더 로드 실패",
                    [
                        "선택한 모델 계열: {}".format(model_family),
                        "요구 CLIP 형식: {}".format(resolved_clip_type),
                        "선택한 텍스트 인코더: {}".format(text_encoder),
                        "model_family와 텍스트 인코더가 같은 계열인지 확인하십시오.",
                    ],
                    exc,
                )
            ) from exc

        try:
            vae = _call_core_node("VAELoader", vae_name=vae_name)[0]
        except Exception as exc:
            raise RuntimeError(
                _error_message(
                    "VAE 로드 실패",
                    [
                        "선택한 모델 계열: {}".format(model_family),
                        "선택한 VAE: {}".format(vae_name),
                        "model_family와 VAE가 같은 계열인지 확인하십시오.",
                    ],
                    exc,
                )
            ) from exc

        return model, clip, vae

    def _encode_conditioning(
        self,
        contract: dict,
        clip,
        prompt: str,
        negative_mode: str,
        negative_prompt: str,
        model_family: str,
    ):
        """Build (positive, negative) according to the family contract.

        Single extension point for families that need a dedicated encoder
        node (e.g. a future Qwen Image 2.1 family using TextEncodeQwenImage21).
        Add a new text_encode value here and reference it from MODEL_CONTRACTS.
        """
        text_encode = str(contract.get("text_encode") or "clip_text_encode")
        if text_encode != "clip_text_encode":
            raise RuntimeError(
                _error_message(
                    "텍스트 인코딩 방식 미구현",
                    [
                        "선택한 모델 계열: {}".format(model_family),
                        "요구 방식: {}".format(text_encode),
                    ],
                )
            )

        try:
            positive = _call_core_node("CLIPTextEncode", clip=clip, text=prompt)[0]
        except Exception as exc:
            raise RuntimeError(
                _error_message(
                    "프롬프트 인코딩 실패",
                    [
                        "positive_prompt를 텍스트 인코딩하지 못했습니다.",
                        "선택한 모델 계열: {}".format(model_family),
                    ],
                    exc,
                )
            ) from exc

        if negative_mode == "encode negative text":
            try:
                negative = _call_core_node(
                    "CLIPTextEncode",
                    clip=clip,
                    text=str(negative_prompt or "").strip(),
                )[0]
            except Exception as exc:
                raise RuntimeError(
                    _error_message(
                        "네거티브 프롬프트 인코딩 실패",
                        [
                            "negative_mode: encode negative text",
                            "negative_prompt를 텍스트 인코딩하지 못했습니다.",
                        ],
                        exc,
                    )
                ) from exc
        else:
            try:
                negative = _call_core_node("ConditioningZeroOut", conditioning=positive)[0]
            except Exception as exc:
                raise RuntimeError(
                    _error_message(
                        "네거티브 conditioning 생성 실패",
                        [
                            "negative_mode: zero positive conditioning",
                            "positive conditioning을 zero-out negative로 변환하지 못했습니다.",
                        ],
                        exc,
                    )
                ) from exc
        return positive, negative

    def _apply_lora_stack(self, model, parsed):
        if not parsed:
            return model

        loader_class = _node_class("LoraLoaderModelOnly")
        for _, _, lora_name, strength in parsed:
            loader = loader_class()
            model = _call_node_instance(
                loader,
                model=model,
                lora_name=lora_name,
                strength_model=strength,
            )[0]
        return model

    def generate(
        self,
        positive_prompt: str,
        model_family: str,
        diffusion_model: str,
        text_encoder: str,
        vae_name: str,
        width: int,
        height: int,
        batch_size: int,
        seed: int,
        steps: int,
        cfg: float,
        sampler_name: str,
        scheduler: str,
        denoise: float,
        negative_mode: str,
        negative_prompt: str,
        pid_upscale: bool,
        pid_model: str,
        pid_sampler: str,
        pid_scheduler: str,
        pid_steps: int,
        pid_degrade_sigma: float,
        pid_output_scale: str,
        sage_attention: bool,
        **lora_values,
    ):
        prompt = str(positive_prompt or "").strip()
        pid_upscale = _normalize_pid_upscale_mode(pid_upscale)
        pid_enabled = pid_upscale == PID_UPSCALE_ON
        sage_attention = _normalize_sage_attention_enabled(sage_attention)
        try:
            contract = _family_contract(model_family)
            resolved_clip_type = self._resolve_clip_type(contract)
            latent_node_name = self._resolve_latent_node(contract)
            model_sampling_class, model_sampling_shift = self._resolve_model_sampling(contract)
        except Exception as exc:
            if str(exc).startswith("Ultra Tools Image + PiD —"):
                raise
            raise RuntimeError(
                _error_message(
                    "실행 전 설정 검사 실패",
                    [
                        "선택한 model_family 값이 올바른지 확인하십시오: {}".format(model_family),
                    ],
                    exc,
                )
            ) from exc

        try:
            width = _normalize_resolution_dimension(width, "width")
            height = _normalize_resolution_dimension(height, "height")
            lora_rows = _collect_lora_rows(lora_values)
            self._validate_configuration(
                diffusion_model,
                text_encoder,
                vae_name,
                sampler_name,
                scheduler,
                negative_mode,
                latent_node_name,
                model_sampling_class,
                lora_rows,
                resolved_clip_type,
                sage_attention,
            )
        except Exception as exc:
            if str(exc).startswith("Ultra Tools Image + PiD —"):
                raise
            raise RuntimeError(
                _error_message(
                    "실행 전 설정 검사 실패",
                    [
                        "선택한 모델 계열: {}".format(model_family),
                        "확산 모델, 텍스트 인코더, VAE, sampler/scheduler, LoRA 목록을 다시 확인하십시오.",
                    ],
                    exc,
                )
            ) from exc

        pid_clip_name = None
        if pid_enabled:
            try:
                pid_clip_name = _validate_pid_configuration(
                    model_family,
                    pid_model,
                    pid_sampler,
                    pid_scheduler,
                    pid_steps,
                    pid_degrade_sigma,
                    pid_output_scale,
                )
            except Exception as exc:
                if str(exc).startswith("Ultra Tools Image + PiD —"):
                    raise
                raise RuntimeError(
                    _error_message(
                        "PiD 실행 전 설정 검사 실패",
                        ["PiD 모델, sampler, scheduler, steps를 다시 확인하십시오."],
                        exc,
                    )
                ) from exc

        model, clip, vae = self._load_assets(
            model_family,
            diffusion_model,
            text_encoder,
            resolved_clip_type,
            vae_name,
        )

        try:
            model = self._apply_lora_stack(model, lora_rows)
        except Exception as exc:
            raise RuntimeError(
                _error_message(
                    "LoRA 적용 실패",
                    [
                        "선택한 모델 계열: {}".format(model_family),
                        "현재 LoRA와 모델 구조가 호환되는지, LoRA 순서와 강도가 적절한지 확인하십시오.",
                    ],
                    exc,
                )
            ) from exc

        if model_sampling_class:
            try:
                kwargs = {"model": model}
                if model_sampling_shift is not None:
                    kwargs["shift"] = model_sampling_shift
                model = _call_core_node(model_sampling_class, **kwargs)[0]
            except Exception as exc:
                raise RuntimeError(
                    _error_message(
                        "모델 샘플링 설정 실패",
                        [
                            "선택한 모델 계열: {}".format(model_family),
                            "요구 샘플링 노드: {}".format(model_sampling_class),
                            "shift: {}".format(model_sampling_shift),
                        ],
                        exc,
                    )
                ) from exc

        if sage_attention:
            model = _apply_sage_attention_patch(model)

        positive, negative = self._encode_conditioning(
            contract, clip, prompt, negative_mode, negative_prompt, model_family
        )

        try:
            latent = _call_core_node(
                latent_node_name,
                width=width,
                height=height,
                batch_size=batch_size,
            )[0]
        except Exception as exc:
            raise RuntimeError(
                _error_message(
                    "latent 생성 실패",
                    [
                        "선택한 모델 계열: {}".format(model_family),
                        "요구 latent 노드: {}".format(latent_node_name),
                        "해상도: {} × {}".format(width, height),
                        "batch_size: {}".format(batch_size),
                    ],
                    exc,
                )
            ) from exc

        try:
            sampled = _call_core_node(
                "KSampler",
                model=model,
                seed=seed,
                steps=steps,
                cfg=cfg,
                sampler_name=sampler_name,
                scheduler=scheduler,
                positive=positive,
                negative=negative,
                latent_image=latent,
                denoise=denoise,
            )[0]
        except Exception as exc:
            raise RuntimeError(
                _error_message(
                    "KSampler 실행 실패",
                    [
                        "선택한 모델 계열: {}".format(model_family),
                        "sampler: {}".format(sampler_name),
                        "scheduler: {}".format(scheduler),
                        "steps: {}".format(steps),
                        "cfg: {}".format(cfg),
                        "denoise: {}".format(denoise),
                    ],
                    exc,
                )
            ) from exc

        # Once the main sampler has produced the final sampled latent, these
        # graph-stage objects are no longer needed. Releasing the local references
        # early helps ComfyUI's model manager/offload path before a PiD model is
        # loaded, without forcing a global cache clear or affecting other nodes.
        del model, clip, positive, negative, latent

        try:
            original_image = _call_core_node("VAEDecode", vae=vae, samples=sampled)[0]
        except Exception as exc:
            raise RuntimeError(
                _error_message(
                    "VAE 디코딩 실패",
                    [
                        "선택한 모델 계열: {}".format(model_family),
                        "선택한 VAE: {}".format(vae_name),
                    ],
                    exc,
                )
            ) from exc

        if pid_enabled:
            if vae is not None:
                del vae
            try:
                pid_image = _run_pid_upscale(
                    sampled,
                    prompt,
                    model_family,
                    pid_model,
                    pid_sampler,
                    pid_scheduler,
                    pid_steps,
                    pid_degrade_sigma,
                    pid_output_scale,
                    seed,
                    width,
                    height,
                    pid_clip_name,
                )
            except Exception as exc:
                if str(exc).startswith("Ultra Tools Image + PiD —"):
                    raise
                raise RuntimeError(
                    _error_message(
                        "PiD 업스케일 실패",
                        [
                            "PiD 모델: {}".format(pid_model),
                            "sampler / scheduler: {} / {}".format(pid_sampler, pid_scheduler),
                            "steps / denoise: {} / {}".format(pid_steps, PID_DENOISE),
                            "CFG는 내부 1.0 고정입니다.",
                        ],
                        exc,
                    )
                ) from exc
            # PiD has consumed the base sampled latent. Release its outer
            # reference before full-resolution Lab processing starts.
            del sampled
            try:
                pid_image = _apply_pid_color_transfer(pid_image, original_image)
            except Exception as exc:
                raise RuntimeError(
                    _error_message(
                        "PiD 색상·명암 일치 실패",
                        [
                            "내부 방식: {} / {} / strength {}".format(
                                PID_COLOR_TRANSFER_METHOD,
                                PID_COLOR_TRANSFER_SOURCE_STATS,
                                PID_COLOR_TRANSFER_STRENGTH,
                            ),
                            "PiD 업스케일은 완료되었지만 최종 색상·명암 후처리를 완료하지 못했습니다.",
                        ],
                        exc,
                    )
                ) from exc
        else:
            pid_image = original_image
        return (original_image, pid_image)


NODE_CLASS_MAPPINGS = {"UltraImagePiD": UltraImagePiD}
NODE_DISPLAY_NAME_MAPPINGS = {"UltraImagePiD": "Ultra Tools Image + PiD"}
