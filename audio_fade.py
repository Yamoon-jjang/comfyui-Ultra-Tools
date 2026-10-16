import math

import torch


_CURVES = ("smooth", "linear", "equal_power", "exponential")
_MAX_FADE_SECONDS = 10.0


def _safe_seconds(value):
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(seconds):
        return 0.0
    return min(max(seconds, 0.0), _MAX_FADE_SECONDS)




def _fit_fade_lengths(total_samples, fade_in_samples, fade_out_samples):
    """Fit two requested fades into the clip without allowing them to overlap."""
    total_samples = max(0, int(total_samples))
    fade_in_samples = max(0, min(total_samples, int(fade_in_samples)))
    fade_out_samples = max(0, min(total_samples, int(fade_out_samples)))

    requested_total = fade_in_samples + fade_out_samples
    if requested_total <= total_samples or requested_total <= 0:
        return fade_in_samples, fade_out_samples

    # Preserve the requested in/out proportion while making the two regions
    # exactly fill the available clip. When both fades were requested and the
    # clip has at least two samples, retain at least one sample for each side.
    fitted_in = int(round(total_samples * (fade_in_samples / requested_total)))
    if fade_in_samples > 0 and fade_out_samples > 0 and total_samples >= 2:
        fitted_in = min(max(fitted_in, 1), total_samples - 1)
    else:
        fitted_in = min(max(fitted_in, 0), total_samples)
    fitted_out = total_samples - fitted_in
    return fitted_in, fitted_out


def _fade_ramp(length, *, device, dtype, curve):
    """Create a 0..1 gain ramp without changing audio length or sample rate."""
    if length <= 0:
        return torch.empty((0,), device=device, dtype=dtype)
    if length == 1:
        return torch.zeros((1,), device=device, dtype=dtype)

    t = torch.linspace(0.0, 1.0, steps=length, device=device, dtype=dtype)

    if curve == "linear":
        return t
    if curve == "equal_power":
        return torch.sin(t * (math.pi / 2.0))
    if curve == "exponential":
        # Slow start, stronger suppression near the beginning of a fade-in.
        strength = 5.0
        return torch.expm1(t * strength) / math.expm1(strength)

    # Default: half-cosine / raised-cosine ramp. It begins and ends with a
    # zero slope, avoiding an abrupt derivative change at the fade boundary.
    return 0.5 - 0.5 * torch.cos(t * math.pi)


class UltraAudioFade:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "fade_in_seconds": (
                    "FLOAT",
                    {
                        "default": 0.15,
                        "min": 0.0,
                        "max": _MAX_FADE_SECONDS,
                        "step": 0.01,
                    },
                ),
                "fade_out_seconds": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": 0.0,
                        "max": _MAX_FADE_SECONDS,
                        "step": 0.01,
                    },
                ),
                "curve": (list(_CURVES), {"default": "smooth"}),
            }
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "apply_fade"
    CATEGORY = "Ultra Tools"
    DESCRIPTION = (
        "Applies non-destructive fade-in/fade-out gain ramps to ComfyUI AUDIO. "
        "Audio duration, sample rate, and sync are preserved."
    )

    def apply_fade(
        self,
        audio,
        fade_in_seconds=0.15,
        fade_out_seconds=0.0,
        curve="smooth",
    ):
        if not isinstance(audio, dict):
            raise ValueError("Ultra Tools Audio Fade expected an AUDIO dictionary.")

        waveform = audio.get("waveform")
        sample_rate = audio.get("sample_rate")

        if not isinstance(waveform, torch.Tensor):
            raise ValueError("Ultra Tools Audio Fade could not find a valid AUDIO waveform tensor.")
        if waveform.ndim < 1:
            raise ValueError("Ultra Tools Audio Fade received an invalid waveform shape.")

        try:
            sample_rate = int(sample_rate)
        except (TypeError, ValueError):
            raise ValueError("Ultra Tools Audio Fade received an invalid sample rate.") from None
        if sample_rate <= 0:
            raise ValueError("Ultra Tools Audio Fade requires a positive sample rate.")

        total_samples = int(waveform.shape[-1])
        if total_samples <= 0:
            result = dict(audio)
            result["waveform"] = waveform.clone()
            return (result,)

        # ComfyUI AUDIO waveforms are floating-point tensors. Be defensive if a
        # third-party node supplies an integer tensor so gain multiplication does
        # not silently quantize the envelope.
        work = waveform.clone()
        if not torch.is_floating_point(work):
            work = work.to(torch.float32)

        fade_in_seconds = _safe_seconds(fade_in_seconds)
        fade_out_seconds = _safe_seconds(fade_out_seconds)
        curve = curve if curve in _CURVES else "smooth"

        fade_in_samples = min(total_samples, int(round(fade_in_seconds * sample_rate)))
        fade_out_samples = min(total_samples, int(round(fade_out_seconds * sample_rate)))
        fade_in_samples, fade_out_samples = _fit_fade_lengths(
            total_samples,
            fade_in_samples,
            fade_out_samples,
        )

        if fade_in_samples > 0:
            ramp_in = _fade_ramp(
                fade_in_samples,
                device=work.device,
                dtype=work.dtype,
                curve=curve,
            )
            work[..., :fade_in_samples] *= ramp_in

        if fade_out_samples > 0:
            ramp_out = _fade_ramp(
                fade_out_samples,
                device=work.device,
                dtype=work.dtype,
                curve=curve,
            ).flip(0)
            work[..., -fade_out_samples:] *= ramp_out

        result = dict(audio)
        result["waveform"] = work
        result["sample_rate"] = sample_rate
        return (result,)


NODE_CLASS_MAPPINGS = {
    "UltraAudioFade": UltraAudioFade,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UltraAudioFade": "Ultra Tools Audio Fade",
}
