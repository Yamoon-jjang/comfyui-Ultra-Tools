# -*- coding: utf-8 -*-
"""
Ultra Image Watermark - practical compact version

Practical goals:
- Keep the node much simpler than the text watermark node.
- Still include a few real-world controls that are often needed:
  * scale by percentage OR by target pixel width
  * position + shared margin + X/Y fine adjustment
  * tile mode with selectable axis: screen-aligned or rotation-aligned grid spacing
  * optional color inversion for light/dark logo reuse
  * one-knob edge softness
  * color tint — replace watermark RGB with a single color
  * stroke / outline — add colored outline around watermark
  * drop shadow — gaussian-blurred shadow behind watermark
  * blend modes — multiply, screen, overlay, soft light
  * mask output — alpha mask of the composited watermark region
"""

from __future__ import annotations

from typing import Optional, Tuple
import math
import os

import numpy as np
import torch
from PIL import Image, ImageChops, ImageFilter, ImageOps

try:
    import folder_paths
except Exception:  # Allows syntax/unit checks outside ComfyUI.
    folder_paths = None

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
    RESAMPLE_BICUBIC = Image.Resampling.BICUBIC
except AttributeError:  # Pillow < 9.1 compatibility
    RESAMPLE_LANCZOS = Image.LANCZOS
    RESAMPLE_BICUBIC = Image.BICUBIC


POSITION_OPTIONS = [
    "center",
    "top left", "top center", "top right",
    "bottom left", "bottom center", "bottom right",
]
SIZE_MODE_OPTIONS = ["percentage", "pixels"]
TILE_MODE_OPTIONS = ["off", "full", "diagonal"]
TILE_AXIS_MODE_OPTIONS = ["angle aligned", "screen aligned"]
MASK_MODE_OPTIONS = ["load image mask (invert)", "normal mask (white visible)"]
BLEND_MODE_OPTIONS = ["normal", "multiply", "screen", "overlay", "soft light"]
COLOR_PRESET_OPTIONS = [
    "custom hex",
    "white", "black", "red", "green", "blue", "yellow", "cyan", "magenta",
    "orange", "purple", "pink", "brown", "gray", "navy", "teal", "maroon",
]
COLOR_PRESET_MAPPING = {
    "white": (255, 255, 255), "black": (0, 0, 0), "red": (255, 0, 0),
    "green": (0, 255, 0), "blue": (0, 0, 255), "yellow": (255, 255, 0),
    "cyan": (0, 255, 255), "magenta": (255, 0, 255), "orange": (255, 165, 0),
    "purple": (128, 0, 128), "pink": (255, 192, 203), "brown": (165, 42, 42),
    "gray": (128, 128, 128), "navy": (0, 0, 128), "teal": (0, 128, 128),
    "maroon": (128, 0, 0),
}

# Safety limits for angle-aligned tile rendering.
# The angle-aligned mode intentionally builds a larger temporary canvas, rotates
# the whole tile grid, and crops back to the final image.  That preserves the
# intended diagonal alignment, but extreme watermark size + tile settings can
# create impractically large temporary canvases.  These guards reject only those
# pathological combinations before the expensive allocation/loop begins.
MAX_ANGLE_TILE_CANVAS_PIXELS = 80_000_000
MAX_TILE_COMPOSITE_WORK_PIXELS = 2_000_000_000
MAX_PREPARED_WATERMARK_PIXELS = 32_000_000
MAX_TORCH_BLEND_PIXELS_PER_CHUNK = 48_000_000
NEGATIVE_TILE_MIN_STEP_RATIO = 0.01
SCREEN_ALIGNED_ROTATED_BBOX_MIN_RATIO = 0.25
MASK_MODE_OPTIONS_NORM = {str(v).lower().strip() for v in MASK_MODE_OPTIONS}
TILE_AXIS_MODE_OPTIONS_NORM = {str(v).lower().strip() for v in TILE_AXIS_MODE_OPTIONS}


def _prepare_rotation_for_tile(tile_mode: str, tile_axis_mode: str, rotation: float) -> float:
    """Return the per-watermark rotation needed before final placement.

    Angle-aligned tiles rotate the whole tile grid later, so the prepared
    watermark itself must stay unrotated.  Single placement and screen-aligned
    tiles rotate the watermark during preparation.
    """
    return float(rotation) if (str(tile_mode).lower() == "off" or str(tile_axis_mode).lower().strip() == "screen aligned") else 0.0


def _parse_hex_color(s: str, fallback: Tuple[int, int, int] = (0, 0, 0)) -> Tuple[int, int, int]:
    """Parse a '#RRGGBB' or 'RRGGBB' string into an (R, G, B) tuple."""
    s = str(s).strip().lstrip("#")
    if len(s) == 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            pass
    return fallback


def _resolve_preset_or_hex_color(
    preset: str, hex_value: str, fallback: Tuple[int, int, int]
) -> Tuple[int, int, int]:
    """Resolve a color from a preset dropdown, falling back to the hex input.

    The default preset is 'custom hex' so existing workflows keep using their
    saved #RRGGBB values.  If a preset color is selected, it intentionally
    overrides the hex string for convenience and to avoid typo-sensitive input.
    """
    key = str(preset or "custom hex").strip().lower()
    if key in COLOR_PRESET_MAPPING:
        return COLOR_PRESET_MAPPING[key]
    return _parse_hex_color(hex_value, fallback)


def _float_to_uint8_l(arr: np.ndarray) -> Image.Image:
    """Convert a float luminance array to uint8 with clipping and rounding.

    Premultiplied-alpha resize/rotate paths are sensitive at translucent edges.
    Rounding is slightly more faithful than truncation and avoids a systematic
    one-level dark bias in half-alpha colors.
    """
    return Image.fromarray(np.clip(np.rint(arr), 0, 255).astype(np.uint8))


# ─────────────────────────────────────────────
# Tensor ↔ PIL
# ─────────────────────────────────────────────
def tensor2pil(image: torch.Tensor) -> Image.Image:
    """Convert a ComfyUI IMAGE/MASK tensor frame to a PIL image.

    Avoid a blanket squeeze(): if height or width is 1, squeezing all singleton
    dimensions can turn an HWC image into a malformed array and corrupt output
    shapes.  Only remove a leading batch/channel singleton when it is actually
    present.
    """
    arr = image.detach().cpu().numpy()

    # Accept accidental single-item batches while preserving 1-pixel H/W axes.
    if arr.ndim == 4 and arr.shape[0] == 1:
        arr = arr[0]

    # MASK tensors may arrive as 1xHxW; convert to HxW grayscale.
    if arr.ndim == 3 and arr.shape[0] == 1 and arr.shape[-1] not in (3, 4):
        arr = arr[0]

    # HxWx1 grayscale is valid data but PIL expects HxW for mode L.
    if arr.ndim == 3 and arr.shape[-1] == 1:
        arr = arr[:, :, 0]

    return Image.fromarray(np.clip(255.0 * arr, 0, 255).astype(np.uint8))


def pil2tensor(img: Image.Image) -> torch.Tensor:
    return torch.from_numpy(np.array(img.convert("RGB")).astype(np.float32) / 255.0)


def _empty_mask_like_image(image: Optional[torch.Tensor]) -> Optional[torch.Tensor]:
    """Return an all-black MASK matching an IMAGE batch, when possible.

    This keeps the node safe as a no-op/pass-through when no watermark source is
    selected. Returning None for a declared MASK output can break downstream
    nodes or ComfyUI execution, so the normal no-watermark case returns a valid
    empty mask instead.
    """
    if image is None:
        return None
    try:
        if image.ndim >= 4:
            batch = int(image.shape[0])
            height = int(image.shape[1])
            width = int(image.shape[2])
        elif image.ndim == 3:
            batch = 1
            height = int(image.shape[0])
            width = int(image.shape[1])
        else:
            return None
        return torch.zeros((batch, height, width), dtype=torch.float32, device=image.device)
    except Exception:
        return None


def _input_image_file_list():
    """Return image files under ComfyUI/input for the watermark dropdown.

    ComfyUI's model-folder helper, get_filename_list("input"), is not reliable
    for the user input directory in all builds.  The stock Load Image node reads
    folder_paths.get_input_directory() directly, so this node follows that
    behavior and also keeps subfolder-relative names such as "logos/logo.png".

    This helper must never raise during INPUT_TYPES(), because an exception
    there can prevent the whole node from appearing in ComfyUI's node list.
    """
    if folder_paths is None:
        return [""]

    try:
        input_dir = folder_paths.get_input_directory()
    except Exception as e:
        print(f"[Ultra Image Watermark] Warning: cannot resolve ComfyUI input folder: {e}")
        return [""]

    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
    files = []
    try:
        for root, _dirs, names in os.walk(input_dir):
            rel_root = os.path.relpath(root, input_dir)
            for name in names:
                if name.startswith("."):
                    continue
                if os.path.splitext(name)[1].lower() not in image_exts:
                    continue
                rel = name if rel_root == "." else os.path.join(rel_root, name)
                files.append(rel.replace(os.sep, "/"))
    except Exception as e:
        print(f"[Ultra Image Watermark] Warning: cannot scan ComfyUI input folder: {e}")
        return [""]

    return [""] + sorted(set(files), key=str.lower)


def _load_watermark_file_as_tensors(filename: str) -> Tuple[torch.Tensor, torch.Tensor]:
    """Load a watermark image from ComfyUI's input folder.

    The returned mask follows ComfyUI Load Image's convention for alpha images:
    black means visible and white means transparent.  The node's default
    Mask_Mode, "load image mask (invert)", converts it back to normal alpha.
    Therefore a transparent PNG/WebP selected in this node behaves the same as
    connecting Load Image IMAGE + MASK manually.
    """
    if folder_paths is None:
        raise Exception(
            "[Ultra Image Watermark] ComfyUI folder_paths is unavailable. "
            "Run inside ComfyUI, or connect watermark_image manually."
        )

    filename = str(filename or "").strip()
    if not filename:
        raise Exception(
            "[Ultra Image Watermark] Select a watermark image in the watermark widget, "
            "or connect watermark_image manually."
        )

    try:
        image_path = folder_paths.get_annotated_filepath(filename)
    except Exception as e:
        raise Exception(f"[Ultra Image Watermark] Cannot resolve watermark file '{filename}': {e}")

    try:
        with Image.open(image_path) as src:
            src = ImageOps.exif_transpose(src)
            rgba = src.convert("RGBA")
    except Exception as e:
        raise Exception(f"[Ultra Image Watermark] Cannot load watermark image '{filename}': {e}")

    rgb_np = np.array(rgba.convert("RGB"), dtype=np.float32) / 255.0
    alpha_np = np.array(rgba.getchannel("A"), dtype=np.float32) / 255.0

    load_image_style_mask = 1.0 - alpha_np

    return (
        torch.from_numpy(rgb_np).unsqueeze(0),
        torch.from_numpy(load_image_style_mask).unsqueeze(0),
    )


# ─────────────────────────────────────────────
# Alpha helpers
# ─────────────────────────────────────────────
def reduce_opacity_rgba(img_rgba: Image.Image, opacity: float) -> Image.Image:
    opacity = float(max(0.0, min(1.0, opacity)))
    if opacity >= 0.999:
        return img_rgba
    if opacity <= 0.0:
        return Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    out = img_rgba.copy()
    a = out.split()[3]
    out.putalpha(a.point(lambda p: int(p * opacity)))
    return out


def alpha_bbox_threshold(
    img_rgba: Image.Image, threshold: int
) -> Optional[Tuple[int, int, int, int]]:
    threshold = int(max(0, min(255, threshold)))
    if threshold <= 0:
        return img_rgba.getbbox()
    a = img_rgba.split()[3]
    a2 = a.point(lambda v: 255 if v >= threshold else 0)
    return a2.getbbox()


def expand_bbox(
    bb: Tuple[int, int, int, int], pad: int, max_w: int, max_h: int
) -> Tuple[int, int, int, int]:
    x0, y0, x1, y1 = bb
    p = int(max(0, pad))
    return (
        max(0, x0 - p),
        max(0, y0 - p),
        min(max_w, x1 + p),
        min(max_h, y1 + p),
    )


def soften_rgba_edges(img_rgba: Image.Image, softness: int) -> Image.Image:
    """Feather the edges of an RGBA watermark image.

    Works on both transparent logos (existing alpha edges) and fully
    opaque images (no alpha variation).  For opaque images the function
    creates a distance-based alpha ramp from the image border inward so
    the watermark blends smoothly into the background.

    softness 0: no change
    softness 1~2: subtle feather
    softness 3~5: clearly visible soft edges
    """
    s = int(max(0, min(5, softness)))
    if s <= 0:
        return img_rgba

    # Inward margin (px) and blur sigma per level.
    margin  = [0, 3, 6, 12, 20, 30][s]
    blur_s  = [0.0, 1.5, 3.0, 5.0, 8.0, 12.0][s]

    w, h = img_rgba.size
    r, g, b, a = img_rgba.split()

    # Build a distance-from-edge mask: white in the centre, fading to
    # black at the borders over *margin* pixels.  This is multiplied
    # with the existing alpha so transparent logos also benefit.
    if margin > 0 and w > 2 and h > 2:
        margin = min(margin, min(w, h) // 2)

        edge_mask = np.ones((h, w), dtype=np.float32)
        for i in range(margin):
            t = (i + 1) / margin          # 0→1 as we move inward
            edge_mask[i, :]      = np.minimum(edge_mask[i, :],      t)
            edge_mask[h-1-i, :]  = np.minimum(edge_mask[h-1-i, :],  t)
            edge_mask[:, i]      = np.minimum(edge_mask[:, i],      t)
            edge_mask[:, w-1-i]  = np.minimum(edge_mask[:, w-1-i],  t)

        # Blur the mask only — smooths the ramp transition without
        # affecting the fully-opaque interior.
        mask_pil = Image.fromarray((edge_mask * 255.0).clip(0, 255).astype(np.uint8), "L")
        if blur_s > 1e-6:
            mask_pil = mask_pil.filter(ImageFilter.GaussianBlur(blur_s))
        edge_mask = np.array(mask_pil, dtype=np.float32) / 255.0

        a_np = np.array(a, dtype=np.float32) / 255.0
        a_np *= edge_mask
        a = Image.fromarray((a_np * 255.0).clip(0, 255).astype(np.uint8), "L")

    return Image.merge("RGBA", (r, g, b, a))



def invert_rgba_colors(img_rgba: Image.Image) -> Image.Image:
    """Invert RGB channels while preserving alpha."""
    r, g, b, a = img_rgba.split()
    rgb = Image.merge("RGB", (r, g, b))
    inv = ImageChops.invert(rgb)
    rr, gg, bb = inv.split()
    return Image.merge("RGBA", (rr, gg, bb, a))


# ─────────────────────────────────────────────
# ③ Color tint — replace RGB with a solid color, keep alpha
# ─────────────────────────────────────────────
def tint_rgba_colors(
    img_rgba: Image.Image, color: Tuple[int, int, int]
) -> Image.Image:
    """Replace all RGB values with *color* while preserving the alpha channel.

    Useful for turning a logo into a single-color silhouette (white, black,
    or any brand color) without needing a separate image file.
    """
    r, g, b, a = img_rgba.split()
    tinted = Image.new("RGBA", img_rgba.size, (*color, 255))
    tinted.putalpha(a)
    return tinted


# ─────────────────────────────────────────────
# ④ Stroke / outline around the watermark
# ─────────────────────────────────────────────
def add_stroke_rgba(
    img_rgba: Image.Image,
    stroke_width: int,
    stroke_color: Tuple[int, int, int],
) -> Image.Image:
    """Add a colored outline around visible pixels of an RGBA image.

    Algorithm:
    1. Dilate the alpha channel by *stroke_width* using MaxFilter.
    2. Create a solid-color image with the dilated alpha (= outline + fill).
    3. Paste the original on top so the outline only shows around the edges.

    The returned image is larger by 2×stroke_width in each direction so
    the outline is never clipped.
    """
    sw = int(max(0, min(20, stroke_width)))
    if sw <= 0:
        return img_rgba

    pad = sw + 1
    w, h = img_rgba.size
    padded = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    padded.paste(img_rgba, (pad, pad))

    a = padded.split()[3]
    # MaxFilter with very large kernels can be slow.  Apply iteratively
    # with smaller kernels to keep the same visual result at lower cost.
    remaining = sw
    dilated_a = a
    while remaining > 0:
        step = min(remaining, 7)
        kernel_size = step * 2 + 1
        dilated_a = dilated_a.filter(ImageFilter.MaxFilter(kernel_size))
        remaining -= step

    stroke_layer = Image.new("RGBA", padded.size, (*stroke_color, 255))
    stroke_layer.putalpha(dilated_a)

    stroke_layer.paste(padded, (0, 0), padded)
    return stroke_layer


# ─────────────────────────────────────────────
# ① Drop shadow — baked into the watermark image
# ─────────────────────────────────────────────
def add_shadow_rgba(
    img_rgba: Image.Image,
    shadow_color: Tuple[int, int, int],
    shadow_opacity: float,
    offset_x: int,
    offset_y: int,
    blur_radius: float,
) -> Tuple[Image.Image, int]:
    """Bake a drop shadow into the watermark RGBA image.

    The shadow is created from the watermark's alpha channel, blurred,
    tinted, and placed *behind* the original.  The returned image is
    enlarged to accommodate the offset + blur without clipping.

    Always returns (image, extra_padding) — even when shadow is skipped.
    """
    shadow_opacity = float(max(0.0, min(1.0, shadow_opacity)))
    if shadow_opacity <= 0.0:
        return img_rgba, 0

    ox, oy = int(offset_x), int(offset_y)
    blur_r = max(0.0, float(blur_radius))

    extra = int(math.ceil(blur_r * 2.5)) + max(abs(ox), abs(oy)) + 4
    w, h = img_rgba.size
    canvas_w = w + extra * 2
    canvas_h = h + extra * 2

    a = img_rgba.split()[3]
    a_np = np.array(a, dtype=np.float32) / 255.0
    a_np = (a_np * shadow_opacity * 255.0).clip(0, 255).astype(np.uint8)
    shadow_a = Image.fromarray(a_np, "L")

    if blur_r > 0.5:
        shadow_a = shadow_a.filter(ImageFilter.GaussianBlur(blur_r))

    shadow_img = Image.new("RGBA", (w, h), (*shadow_color, 255))
    shadow_img.putalpha(shadow_a)

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    shadow_x = extra + ox
    shadow_y = extra + oy
    canvas.paste(shadow_img, (shadow_x, shadow_y), shadow_img)
    canvas.paste(img_rgba, (extra, extra), img_rgba)

    return canvas, extra


# ─────────────────────────────────────────────
# ② Blend mode compositing
# ─────────────────────────────────────────────
def blend_images(
    base_rgba: Image.Image,
    overlay_rgba: Image.Image,
    mode: str,
) -> Image.Image:
    """Composite *overlay_rgba* onto *base_rgba* using the given blend mode.

    Both images must be the same size and RGBA.  The overlay's alpha
    channel controls how much of the blended result replaces the base.

    Supported modes: normal, multiply, screen, overlay, soft light.

    For 'normal' this falls back to PIL's alpha_composite for speed.
    """
    mode = str(mode).lower().strip()
    if mode == "normal":
        return Image.alpha_composite(base_rgba, overlay_rgba)

    base_np = np.array(base_rgba, dtype=np.float32) / 255.0
    over_np = np.array(overlay_rgba, dtype=np.float32) / 255.0

    b_rgb = base_np[:, :, :3]
    o_rgb = over_np[:, :, :3]
    o_a = over_np[:, :, 3:4]

    # Clean overlay RGB in fully-transparent regions to avoid garbage
    # values leaking into blend formulas (e.g. sqrt in soft-light).
    o_rgb = np.where(o_a > 0, o_rgb, 0.0)

    if mode == "multiply":
        blended = b_rgb * o_rgb
    elif mode == "screen":
        blended = 1.0 - (1.0 - b_rgb) * (1.0 - o_rgb)
    elif mode == "overlay":
        low = 2.0 * b_rgb * o_rgb
        high = 1.0 - 2.0 * (1.0 - b_rgb) * (1.0 - o_rgb)
        blended = np.where(b_rgb < 0.5, low, high)
    elif mode == "soft light":
        blended = np.where(
            o_rgb <= 0.5,
            b_rgb - (1.0 - 2.0 * o_rgb) * b_rgb * (1.0 - b_rgb),
            b_rgb + (2.0 * o_rgb - 1.0) * (np.sqrt(b_rgb) - b_rgb),
        )
    else:
        return Image.alpha_composite(base_rgba, overlay_rgba)

    b_a = base_np[:, :, 3:4]

    # For ordinary ComfyUI RGB images b_a is 1, so this is identical to the
    # old formula.  If an RGBA tensor enters from another custom node, blend
    # toward normal source-over as the backdrop alpha approaches 0 so hidden or
    # garbage RGB in transparent regions does not darken the watermark.
    effective_blend_rgb = blended * b_a + o_rgb * (1.0 - b_a)
    result_a = b_a + o_a * (1.0 - b_a)
    premul_rgb = b_rgb * b_a * (1.0 - o_a) + effective_blend_rgb * o_a
    result_rgb = np.where(result_a > 1e-6, premul_rgb / result_a, 0.0)

    result = np.dstack([result_rgb, result_a])
    result = (result * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(result, "RGBA")



def _quantize_tensor_like_pil(x: torch.Tensor) -> torch.Tensor:
    """Quantize float image values to the 8-bit grid used by the PIL path."""
    return torch.floor(torch.clamp(x, 0.0, 1.0) * 255.0 + 1e-6) / 255.0


def blend_tensor_batch_with_static_overlay(
    image_batch: torch.Tensor,
    overlay_rgba: Image.Image,
    mode: str,
    max_pixels_per_chunk: int = MAX_TORCH_BLEND_PIXELS_PER_CHUNK,
) -> Optional[Tuple[torch.Tensor, torch.Tensor]]:
    """Blend one static RGBA overlay over an entire IMAGE batch with PyTorch.

    This fast path is intentionally narrow and conservative:
    - overlay creation, positioning, stroke, shadow, tile geometry, and mask output
      still use the existing PIL path, so placement/shape do not change;
    - only standard ComfyUI RGB IMAGE batches (B,H,W,3) use this path;
    - dynamic per-frame watermark/mask inputs fall back to the existing loop.

    The input is quantized to the same 8-bit grid as tensor2pil()/pil2tensor()
    so visual output stays close to the established PIL path while avoiding
    per-frame PIL round-trips for static video/batch watermarks.
    """
    try:
        if not isinstance(image_batch, torch.Tensor):
            return None
        if image_batch.ndim != 4 or int(image_batch.shape[-1]) != 3:
            return None
        b, h, w, _ = image_batch.shape
        if b < 1 or overlay_rgba.size != (int(w), int(h)):
            return None

        mode = str(mode).lower().strip()
        if mode not in BLEND_MODE_OPTIONS:
            mode = "normal"

        over_np = np.array(overlay_rgba.convert("RGBA"), dtype=np.float32) / 255.0
        device = image_batch.device
        over = torch.from_numpy(over_np).to(device=device, dtype=torch.float32)
        o_rgb = over[:, :, :3].unsqueeze(0)
        o_a = over[:, :, 3:4].unsqueeze(0)
        o_rgb = torch.where(o_a > 0, o_rgb, torch.zeros_like(o_rgb))

        pixels_per_frame = max(1, int(h) * int(w))
        chunk = max(1, int(max_pixels_per_chunk) // pixels_per_frame)
        outputs = []

        for start in range(0, int(b), chunk):
            end = min(int(b), start + chunk)
            b_rgb = image_batch[start:end, :, :, :3].to(dtype=torch.float32).clamp(0.0, 1.0)
            b_rgb = _quantize_tensor_like_pil(b_rgb)

            if mode == "normal":
                result_rgb = b_rgb * (1.0 - o_a) + o_rgb * o_a
            elif mode == "multiply":
                blended = b_rgb * o_rgb
                result_rgb = b_rgb * (1.0 - o_a) + blended * o_a
            elif mode == "screen":
                blended = 1.0 - (1.0 - b_rgb) * (1.0 - o_rgb)
                result_rgb = b_rgb * (1.0 - o_a) + blended * o_a
            elif mode == "overlay":
                low = 2.0 * b_rgb * o_rgb
                high = 1.0 - 2.0 * (1.0 - b_rgb) * (1.0 - o_rgb)
                blended = torch.where(b_rgb < 0.5, low, high)
                result_rgb = b_rgb * (1.0 - o_a) + blended * o_a
            elif mode == "soft light":
                blended = torch.where(
                    o_rgb <= 0.5,
                    b_rgb - (1.0 - 2.0 * o_rgb) * b_rgb * (1.0 - b_rgb),
                    b_rgb + (2.0 * o_rgb - 1.0) * (torch.sqrt(torch.clamp(b_rgb, 0.0, 1.0)) - b_rgb),
                )
                result_rgb = b_rgb * (1.0 - o_a) + blended * o_a
            else:
                result_rgb = b_rgb * (1.0 - o_a) + o_rgb * o_a

            outputs.append(_quantize_tensor_like_pil(result_rgb).to(dtype=torch.float32))

        result = torch.cat(outputs, dim=0)
        mask_2d = over[:, :, 3].to(dtype=torch.float32)
        masks = mask_2d.unsqueeze(0).expand(int(b), -1, -1).contiguous()
        return result, masks
    except Exception:
        # A fast path must never make the node less reliable.  Any unexpected
        # tensor/device issue falls back to the proven PIL loop.
        return None

def alpha_composite_clipped(
    dst_rgba: Image.Image, src_rgba: Image.Image, dest_xy: Tuple[int, int]
) -> None:
    x, y = int(dest_xy[0]), int(dest_xy[1])
    sw, sh = src_rgba.size
    dw, dh = dst_rgba.size

    ix0, iy0 = max(0, x), max(0, y)
    ix1, iy1 = min(dw, x + sw), min(dh, y + sh)
    if ix1 <= ix0 or iy1 <= iy0:
        return

    sx0, sy0 = ix0 - x, iy0 - y
    sx1, sy1 = sx0 + (ix1 - ix0), sy0 + (iy1 - iy0)
    dst_rgba.alpha_composite(src_rgba.crop((sx0, sy0, sx1, sy1)), (ix0, iy0))


def limit_tile_steps_for_safety(
    step_x: int, step_y: int, span_x: int, span_y: int, max_tiles: int = 40_000
) -> Tuple[int, int]:
    """Prevent pathological tile counts from extreme negative spacing.

    Normal positive/zero spacing is left untouched.  Very large negative
    spacing can otherwise collapse the step to 1 px and create millions of
    alpha-composite operations on large images.  This keeps the visual result
    densely overlapped while avoiding a practical ComfyUI slowdown/freeze.
    """
    step_x = max(1, int(step_x))
    step_y = max(1, int(step_y))
    span_x = max(1, int(span_x))
    span_y = max(1, int(span_y))
    max_tiles = max(1, int(max_tiles))

    nx = max(1, math.ceil(span_x / step_x))
    ny = max(1, math.ceil(span_y / step_y))
    total = nx * ny
    if total <= max_tiles:
        return step_x, step_y

    factor = math.sqrt(total / max_tiles)
    return max(1, int(math.ceil(step_x * factor))), max(1, int(math.ceil(step_y * factor)))


def estimate_tile_count(step_x: int, step_y: int, span_x: int, span_y: int) -> int:
    """Estimate how many tile paste operations a loop will perform."""
    step_x = max(1, int(step_x))
    step_y = max(1, int(step_y))
    span_x = max(1, int(span_x))
    span_y = max(1, int(span_y))
    return max(1, math.ceil(span_x / step_x)) * max(1, math.ceil(span_y / step_y))


def guard_angle_tile_resources(
    *,
    ext_w: int,
    ext_h: int,
    wm_w: int,
    wm_h: int,
    step_x: int,
    step_y: int,
    span_x: int,
    span_y: int,
) -> None:
    """Reject angle-aligned tile settings that are likely to freeze/OOM.

    Angle-aligned tiling must keep its large-canvas rotation design to preserve
    diagonal alignment.  This guard does not auto-scale or alter the visual
    result; it only stops combinations that would allocate an excessive
    temporary canvas or require an excessive amount of compositing work.
    """
    ext_w = max(1, int(ext_w))
    ext_h = max(1, int(ext_h))
    canvas_pixels = ext_w * ext_h
    if canvas_pixels > MAX_ANGLE_TILE_CANVAS_PIXELS:
        approx_rgba_mb = canvas_pixels * 4 / (1024 * 1024)
        raise Exception(
            "[Ultra Image Watermark] Angle-aligned tile settings are too large.\n"
            f"Temporary tile canvas would be {ext_w}x{ext_h} "
            f"({canvas_pixels:,} pixels, about {approx_rgba_mb:.0f} MB for one RGBA layer).\n"
            "This mode rotates the whole tile grid to preserve diagonal alignment, "
            "so very large watermark size, stroke/shadow, or negative spacing can freeze ComfyUI.\n"
            "Reduce Pixel_Width/Scale_Percent, Stroke/Shadow size, or use screen aligned tiling."
        )

    tile_count = estimate_tile_count(step_x, step_y, span_x, span_y)
    composite_work = tile_count * max(1, int(wm_w)) * max(1, int(wm_h))
    if composite_work > MAX_TILE_COMPOSITE_WORK_PIXELS:
        raise Exception(
            "[Ultra Image Watermark] Tile compositing workload is too large.\n"
            f"Estimated paste operations: {tile_count:,}; watermark size: {int(wm_w)}x{int(wm_h)}; "
            f"estimated work pixels: {composite_work:,}.\n"
            "Increase Tile_Spacing, reduce watermark size, reduce Stroke/Shadow size, "
            "or switch to screen aligned tiling."
        )


# ─────────────────────────────────────────────
# Premultiplied-alpha resize / rotate
# ─────────────────────────────────────────────
def resize_rgba_premultiply(
    img_rgba: Image.Image, size: Tuple[int, int], resample=RESAMPLE_LANCZOS
) -> Image.Image:
    w, h = size
    if w <= 0 or h <= 0:
        return img_rgba

    r, g, b, a = img_rgba.split()
    a_np = np.array(a, dtype=np.float32) / 255.0

    channels_pm = []
    for ch in (r, g, b):
        ch_np = np.array(ch, dtype=np.float32) * a_np
        channels_pm.append(_float_to_uint8_l(ch_np))

    pm = Image.merge("RGBA", (*channels_pm, a))
    pm_resized = pm.resize((w, h), resample)

    rr, gg, bb, aa = pm_resized.split()
    aa_np = np.array(aa, dtype=np.float32)
    safe_div = np.where(aa_np > 0, aa_np / 255.0, 1.0)

    result_channels = []
    for ch in (rr, gg, bb):
        ch_np = np.array(ch, dtype=np.float32) / safe_div
        result_channels.append(_float_to_uint8_l(ch_np))

    return Image.merge("RGBA", (*result_channels, aa))


def rotate_rgba_safe(img_rgba: Image.Image, angle: float) -> Image.Image:
    if abs(float(angle)) < 1e-6:
        return img_rgba

    r, g, b, a = img_rgba.split()
    a_np = np.array(a, dtype=np.float32) / 255.0

    channels_pm = []
    for ch in (r, g, b):
        ch_np = np.array(ch, dtype=np.float32) * a_np
        channels_pm.append(_float_to_uint8_l(ch_np))

    pm = Image.merge("RGBA", (*channels_pm, a))
    pm_rot = pm.rotate(float(angle), expand=True, resample=RESAMPLE_BICUBIC)

    rr, gg, bb, aa = pm_rot.split()
    aa_np = np.array(aa, dtype=np.float32)
    safe_div = np.where(aa_np > 0, aa_np / 255.0, 1.0)

    result_channels = []
    for ch in (rr, gg, bb):
        ch_np = np.array(ch, dtype=np.float32) / safe_div
        result_channels.append(_float_to_uint8_l(ch_np))

    return Image.merge("RGBA", (*result_channels, aa))



def rotate_rgba_canvas(img_rgba: Image.Image, angle: float) -> Image.Image:
    """Rotate an RGBA canvas around its center without changing canvas size.

    Used for tile mode: build a straight tile grid on a large temporary canvas,
    rotate the whole grid, then crop the center back to the original image size.
    """
    if abs(float(angle)) < 1e-6:
        return img_rgba

    r, g, b, a = img_rgba.split()
    a_np = np.array(a, dtype=np.float32) / 255.0

    channels_pm = []
    for ch in (r, g, b):
        ch_np = np.array(ch, dtype=np.float32) * a_np
        channels_pm.append(_float_to_uint8_l(ch_np))

    pm = Image.merge("RGBA", (*channels_pm, a))
    pm_rot = pm.rotate(float(angle), expand=False, resample=RESAMPLE_BICUBIC)

    rr, gg, bb, aa = pm_rot.split()
    aa_np = np.array(aa, dtype=np.float32)
    safe_div = np.where(aa_np > 0, aa_np / 255.0, 1.0)

    result_channels = []
    for ch in (rr, gg, bb):
        ch_np = np.array(ch, dtype=np.float32) / safe_div
        result_channels.append(_float_to_uint8_l(ch_np))

    return Image.merge("RGBA", (*result_channels, aa))


# ─────────────────────────────────────────────
# Main node
# ─────────────────────────────────────────────
class UltraImageWatermark:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                # Keep this as a plain dropdown.  The custom frontend button
                # below handles OS file selection/upload.  Adding ComfyUI's
                # image_upload=True here creates a second upload button.
                "watermark": (_input_image_file_list(), {"default": ""}),

                # ── 소스 이미지 크기·색상 ──
                "── 🖼️ Watermark Image ──": ("STRING", {"multiline": False, "default": ""}),
                "Size_Mode": (SIZE_MODE_OPTIONS, {"default": "percentage"}),
                "Scale_Percent": ("FLOAT", {
                    "default": 15.0, "min": 0.5, "max": 100.0, "step": 0.5,
                }),
                "Pixel_Width": ("INT", {
                    "default": 200, "min": 1, "max": 8192,
                }),
                "Invert_Colors": ("BOOLEAN", {"default": False}),
                "Color_Tint": ("BOOLEAN", {"default": False}),
                "Tint_Color_Preset": (COLOR_PRESET_OPTIONS, {"default": "custom hex"}),
                "Tint_Color": ("STRING", {"multiline": False, "default": "#FFFFFF"}),
                "Mask_Mode": (MASK_MODE_OPTIONS, {"default": "load image mask (invert)"}),

                # ── 외곽선 ──
                "── ✏️ Stroke ──": ("STRING", {"multiline": False, "default": ""}),
                "Stroke_Width": ("INT", {"default": 0, "min": 0, "max": 20}),
                "Stroke_Color_Preset": (COLOR_PRESET_OPTIONS, {"default": "custom hex"}),
                "Stroke_Color": ("STRING", {"multiline": False, "default": "#000000"}),

                # ── 그림자 ──
                "── 🌑 Shadow ──": ("STRING", {"multiline": False, "default": ""}),
                "Shadow_Enabled": ("BOOLEAN", {"default": False}),
                "Shadow_Color_Preset": (COLOR_PRESET_OPTIONS, {"default": "custom hex"}),
                "Shadow_Color": ("STRING", {"multiline": False, "default": "#000000"}),
                "Shadow_Opacity": ("FLOAT", {
                    "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05,
                }),
                "Shadow_Offset_X": ("INT", {"default": 4, "min": -100, "max": 100}),
                "Shadow_Offset_Y": ("INT", {"default": 4, "min": -100, "max": 100}),
                "Shadow_Blur": ("FLOAT", {
                    "default": 6.0, "min": 0.0, "max": 50.0, "step": 0.5,
                }),

                # ── 타일 ──
                "── 🔲 Tile ──": ("STRING", {"multiline": False, "default": ""}),
                "Tile_Mode": (TILE_MODE_OPTIONS, {"default": "off"}),
                "Tile_Axis_Mode": (TILE_AXIS_MODE_OPTIONS, {"default": "angle aligned"}),
                "Tile_Spacing": ("INT", {"default": 100, "min": -2000, "max": 2000}),

                # ── 배치·합성 ──
                "── 🎛️ Adjust ──": ("STRING", {"multiline": False, "default": ""}),
                "Opacity": ("FLOAT", {
                    "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01,
                }),
                "Blend_Mode": (BLEND_MODE_OPTIONS, {"default": "normal"}),
                "Position": (POSITION_OPTIONS, {"default": "bottom right"}),
                "Margin": ("INT", {"default": 20, "min": 0, "max": 2048}),
                "Margin_X": ("INT", {"default": 0, "min": -2048, "max": 2048}),
                "Margin_Y": ("INT", {"default": 0, "min": -2048, "max": 2048}),
                "Edge_Softness": ("INT", {"default": 0, "min": 0, "max": 5}),
                "Rotation": ("FLOAT", {
                    "default": 0.0, "min": -180.0, "max": 180.0, "step": 1.0,
                }),
            },
            "optional": {
                "watermark_image": ("IMAGE",),
                "mask": ("MASK",),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("IMAGE", "MASK")
    FUNCTION = "add_image_watermark"
    CATEGORY = "Ultra Tools"

    def _prepare_watermark(
        self,
        wm_frame: torch.Tensor,
        base_w: int,
        base_h: int,
        mask_frame: Optional[torch.Tensor],
        mask_mode: str,
        size_mode: str,
        scale_percent: float,
        pixel_width: int,
        edge_softness: int,
        opacity: float,
        invert_colors: bool,
        rotation: float,
        color_tint: bool = False,
        tint_color: Tuple[int, int, int] = (255, 255, 255),
        stroke_width: int = 0,
        stroke_color: Tuple[int, int, int] = (0, 0, 0),
        shadow_enabled: bool = False,
        shadow_color: Tuple[int, int, int] = (0, 0, 0),
        shadow_opacity: float = 0.5,
        shadow_offset_x: int = 4,
        shadow_offset_y: int = 4,
        shadow_blur: float = 6.0,
    ) -> Optional[Tuple[Image.Image, Tuple[int, int, int, int], Tuple[int, int]]]:
        wm = tensor2pil(wm_frame).convert("RGBA")
        if wm.width < 1 or wm.height < 1:
            return None

        # Mask source convention is selectable:
        # - Load Image MASK is inverted relative to normal alpha, so invert it.
        # - Normal mask nodes usually use white=visible and black=transparent.
        if mask_frame is not None:
            m = tensor2pil(mask_frame)
            m = m.convert("L").resize(wm.size, RESAMPLE_LANCZOS)
            if str(mask_mode or "load image mask (invert)").lower().strip() == "load image mask (invert)":
                m = ImageChops.invert(m)
            wm.putalpha(m)

        # Measure the actually visible region (alpha > 0) so that
        # transparent padding around a logo does not inflate the size
        # calculation.  Fall back to full canvas if fully opaque.
        vis_bb = wm.getbbox()          # (x0, y0, x1, y1) or None
        if vis_bb:
            vis_w = max(1, vis_bb[2] - vis_bb[0])
            vis_h = max(1, vis_bb[3] - vis_bb[1])
        else:
            vis_w, vis_h = wm.width, wm.height

        size_mode = str(size_mode).lower()
        if size_mode == "pixels":
            # Target the longest visible side to match the given pixel value.
            vis_long = max(vis_w, vis_h)
            ratio = max(1, int(pixel_width)) / max(1, vis_long)
        else:
            # Scale so the visible area's longest side equals pct% of the
            # base image's shortest side.  This keeps the perceived size
            # consistent regardless of the watermark's aspect ratio or
            # any surrounding transparent padding.
            pct = float(max(0.5, min(100.0, scale_percent))) / 100.0
            ref = min(base_w, base_h)
            target_long = max(1, int(ref * pct))
            vis_long = max(vis_w, vis_h)
            ratio = target_long / max(1, vis_long)

        target_w = max(1, int(wm.width * ratio))
        target_h = max(1, int(wm.height * ratio))
        target_pixels = target_w * target_h
        if target_pixels > MAX_PREPARED_WATERMARK_PIXELS:
            approx_rgba_mb = target_pixels * 4 / (1024 * 1024)
            raise Exception(
                "[Ultra Image Watermark] Watermark render size is too large.\n"
                f"Prepared watermark would be {target_w}x{target_h} "
                f"({target_pixels:,} pixels, about {approx_rgba_mb:.0f} MB for one RGBA layer).\n"
                "Reduce Pixel_Width/Scale_Percent or use a smaller watermark source. "
                "Large Stroke/Shadow settings can add even more memory after resize."
            )
        wm = resize_rgba_premultiply(wm, (target_w, target_h), RESAMPLE_LANCZOS)

        if bool(invert_colors) and not bool(color_tint):
            # Skip invert when tint is active — tint replaces all RGB anyway.
            wm = invert_rgba_colors(wm)

        # ③ Color tint — after invert, before stroke/soften
        if bool(color_tint):
            wm = tint_rgba_colors(wm, tint_color)

        # ④ Stroke — after tint, before soften (so soften feathers the outline too)
        if int(stroke_width) > 0:
            wm = add_stroke_rgba(wm, stroke_width, stroke_color)

        wm = soften_rgba_edges(wm, edge_softness)

        # ① Drop shadow — baked BEFORE opacity so the shadow alpha is derived
        #    from the full-strength watermark, not the already-faded version.
        #    shadow_opacity alone controls how dark the shadow is.
        if bool(shadow_enabled) and shadow_opacity > 0:
            wm, _ = add_shadow_rgba(
                wm, shadow_color, shadow_opacity,
                shadow_offset_x, shadow_offset_y, shadow_blur,
            )

        # Opacity applied after shadow — reduces watermark + shadow together.
        wm = reduce_opacity_rgba(wm, opacity)

        # Keep a pre-rotation visible pitch for screen-aligned tiling.
        # When only each watermark image is rotated, using the rotated bounding
        # box as the tile pitch can create large empty gaps around long/thin logos.
        # This pitch is only a spacing hint; the actual pasted image and mask still
        # use the rotated/cropped watermark below.
        pre_crop_th = 1 if int(edge_softness) <= 0 else min(32, 3 + int(edge_softness) * 4)
        pre_bb = alpha_bbox_threshold(wm, pre_crop_th) or wm.getbbox()
        if pre_bb:
            tile_pitch = (
                max(1, int(pre_bb[2] - pre_bb[0])),
                max(1, int(pre_bb[3] - pre_bb[1])),
            )
        else:
            tile_pitch = (max(1, wm.width), max(1, wm.height))

        wm = rotate_rgba_safe(wm, rotation)

        crop_th = pre_crop_th
        bb = alpha_bbox_threshold(wm, crop_th) or wm.getbbox()
        if not bb:
            return None

        # Pad must be large enough to preserve the feathered gradient.
        # margin + blur defines the visible soft zone; pad keeps it intact.
        # Stroke and shadow already enlarged the canvas, so alpha_bbox_threshold
        # already accounts for them — no extra pad needed for those.
        _margin_lut = [0, 3, 6, 12, 20, 30]
        _blur_lut   = [0.0, 1.5, 3.0, 5.0, 8.0, 12.0]
        s = int(max(0, min(5, edge_softness)))
        pad = 1 if s <= 0 else max(2, _margin_lut[s] + int(math.ceil(_blur_lut[s] * 2)))
        crop_bb = expand_bbox(bb, pad, wm.width, wm.height)
        wm = wm.crop(crop_bb)

        ax0, ay0, ax1, ay1 = bb
        cx0, cy0, _, _ = crop_bb
        align_bb = (ax0 - cx0, ay0 - cy0, ax1 - cx0, ay1 - cy0)

        return wm, align_bb, tile_pitch

    def _calc_position(
        self,
        base_w: int,
        base_h: int,
        align_bb: Tuple[int, int, int, int],
        position: str,
        margin: int,
        margin_x: int,
        margin_y: int,
    ) -> Tuple[int, int]:
        ax0, ay0, ax1, ay1 = align_bb
        aw, ah = ax1 - ax0, ay1 - ay0
        margin = int(max(0, margin))
        margin_x = int(margin_x)
        margin_y = int(margin_y)
        position = str(position)

        if "left" in position:
            x = margin - ax0 + margin_x
        elif "right" in position:
            x = base_w - margin - ax1 - margin_x
        else:
            x = (base_w - aw) // 2 - ax0 + margin_x

        if "top" in position:
            y = margin - ay0 + margin_y
        elif "bottom" in position:
            y = base_h - margin - ay1 - margin_y
        else:
            y = (base_h - ah) // 2 - ay0 + margin_y

        return int(x), int(y)

    def _screen_tile_steps(
        self,
        align_bb: Tuple[int, int, int, int],
        spacing: int,
        tile_pitch: Optional[Tuple[int, int]] = None,
    ) -> Tuple[int, int]:
        ax0, ay0, ax1, ay1 = align_bb
        visible_w = max(1, int(ax1 - ax0))
        visible_h = max(1, int(ay1 - ay0))

        if tile_pitch is not None:
            pitch_w = max(1, int(tile_pitch[0]))
            pitch_h = max(1, int(tile_pitch[1]))
            # Use the pre-rotation visible size to avoid excessive gaps, but keep
            # a mild lower bound from the rotated bbox to prevent extreme overlap.
            pitch_w = max(pitch_w, max(1, int(round(visible_w * SCREEN_ALIGNED_ROTATED_BBOX_MIN_RATIO))))
            pitch_h = max(pitch_h, max(1, int(round(visible_h * SCREEN_ALIGNED_ROTATED_BBOX_MIN_RATIO))))
        else:
            pitch_w, pitch_h = visible_w, visible_h

        gap = int(spacing)
        step_x = max(1, pitch_w + gap)
        step_y = max(1, pitch_h + gap)

        if gap < 0:
            step_x = max(step_x, max(1, int(round(pitch_w * NEGATIVE_TILE_MIN_STEP_RATIO))))
            step_y = max(step_y, max(1, int(round(pitch_h * NEGATIVE_TILE_MIN_STEP_RATIO))))


        return int(step_x), int(step_y)

    def _build_screen_aligned_tile_layer(
        self,
        wm: Image.Image,
        align_bb: Tuple[int, int, int, int],
        base_w: int,
        base_h: int,
        tile_mode: str,
        spacing: int,
        tile_pitch: Optional[Tuple[int, int]] = None,
    ) -> Image.Image:
        if wm.width < 1 or wm.height < 1:
            return Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))

        ax0, ay0, ax1, ay1 = align_bb
        visible_w = max(1, int(ax1 - ax0))
        visible_h = max(1, int(ay1 - ay0))
        step_x, step_y = self._screen_tile_steps(align_bb, spacing, tile_pitch)

        layer = Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))
        tile_mode = str(tile_mode).lower()

        start_x = -step_x * 3
        start_y = -step_y * 3
        end_x = base_w + step_x * 3
        end_y = base_h + step_y * 3
        step_x, step_y = limit_tile_steps_for_safety(
            step_x, step_y, end_x - start_x, end_y - start_y
        )
        start_x = -step_x * 3
        start_y = -step_y * 3
        end_x = base_w + step_x * 3
        end_y = base_h + step_y * 3

        # Center the rotated visible bbox inside each logical tile cell.
        # This is the best-looking compromise for screen-aligned grids: the
        # screen rows/columns stay regular, while rotated watermark images do
        # not get pushed apart solely by transparent bbox corners.
        center_off_x = (ax0 + ax1) / 2.0
        center_off_y = (ay0 + ay1) / 2.0

        if tile_mode == "diagonal":
            row = 0
            for y in range(start_y, end_y, step_y):
                dx = (row * (step_x // 2)) % step_x
                for x in range(start_x, end_x, step_x):
                    px = int(round(x + dx + step_x / 2.0 - center_off_x))
                    py = int(round(y + step_y / 2.0 - center_off_y))
                    alpha_composite_clipped(layer, wm, (px, py))
                row += 1
        else:
            for y in range(start_y, end_y, step_y):
                for x in range(start_x, end_x, step_x):
                    px = int(round(x + step_x / 2.0 - center_off_x))
                    py = int(round(y + step_y / 2.0 - center_off_y))
                    alpha_composite_clipped(layer, wm, (px, py))

        return layer

    def _build_tile_layer(
        self,
        wm: Image.Image,
        align_bb: Tuple[int, int, int, int],
        base_w: int,
        base_h: int,
        tile_mode: str,
        spacing: int,
        tile_rotation: float,
        tile_axis_mode: str = "angle aligned",
        tile_pitch: Optional[Tuple[int, int]] = None,
    ) -> Image.Image:
        if wm.width < 1 or wm.height < 1:
            return Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))

        tile_axis_mode = str(tile_axis_mode or "angle aligned").lower().strip()
        if tile_axis_mode == "screen aligned":
            return self._build_screen_aligned_tile_layer(
                wm, align_bb, base_w, base_h, tile_mode, spacing, tile_pitch
            )

        # Tile spacing is defined as the gap between visible watermark boxes,
        # not as canvas margin.  Negative values mean overlap.
        ax0, ay0, ax1, ay1 = align_bb
        visible_w = max(1, int(ax1 - ax0))
        visible_h = max(1, int(ay1 - ay0))
        gap = int(spacing)

        step_x = max(1, visible_w + gap)
        step_y = max(1, visible_h + gap)

        if gap < 0:
            # Negative spacing means overlap, but a very negative value should
            # not collapse either axis into a near-1px stride.  Keep the
            # overlap strong while preserving practical render speed.
            step_x = max(step_x, max(1, int(round(visible_w * NEGATIVE_TILE_MIN_STEP_RATIO))))
            step_y = max(step_y, max(1, int(round(visible_h * NEGATIVE_TILE_MIN_STEP_RATIO))))


        # Build a larger temporary canvas, tile on straight axes, rotate the
        # whole grid, then crop the center.  This makes the tile layout itself
        # follow Rotation instead of placing rotated images on horizontal rows.
        # Keep this structure: drawing only inside the final image can leave
        # empty corners when the entire tile grid is rotated.
        diag = int(math.ceil(math.sqrt(base_w * base_w + base_h * base_h)))
        safety = int(max(step_x, step_y, wm.width, wm.height) * 3 + 16)
        ext_w = max(base_w, diag + safety * 2)
        ext_h = max(base_h, diag + safety * 2)

        tile_mode = str(tile_mode).lower()

        start_x = -step_x * 3
        start_y = -step_y * 3
        end_x = ext_w + step_x * 3
        end_y = ext_h + step_y * 3

        # Extreme negative spacing can intentionally overlap marks, but it
        # should not collapse into a 1-pixel step on large images.  The guard
        # only affects pathological tile counts and preserves ordinary spacing.
        step_x, step_y = limit_tile_steps_for_safety(
            step_x, step_y, end_x - start_x, end_y - start_y
        )
        start_x = -step_x * 3
        start_y = -step_y * 3
        end_x = ext_w + step_x * 3
        end_y = ext_h + step_y * 3

        # Guard after the step limiter so normal dense/overlap cases remain
        # supported, but extreme canvas/workload combinations fail clearly
        # before allocating/rotating a huge tile layer.
        guard_angle_tile_resources(
            ext_w=ext_w, ext_h=ext_h,
            wm_w=wm.width, wm_h=wm.height,
            step_x=step_x, step_y=step_y,
            span_x=end_x - start_x, span_y=end_y - start_y,
        )

        layer = Image.new("RGBA", (ext_w, ext_h), (0, 0, 0, 0))

        if tile_mode == "diagonal":
            row = 0
            for y in range(start_y, end_y, step_y):
                dx = (row * (step_x // 2)) % step_x
                for x in range(start_x, end_x, step_x):
                    alpha_composite_clipped(layer, wm, (x + dx - ax0, y - ay0))
                row += 1
        else:
            for y in range(start_y, end_y, step_y):
                for x in range(start_x, end_x, step_x):
                    alpha_composite_clipped(layer, wm, (x - ax0, y - ay0))

        layer = rotate_rgba_canvas(layer, tile_rotation)

        left = (ext_w - base_w) // 2
        top = (ext_h - base_h) // 2
        return layer.crop((left, top, left + base_w, top + base_h))

    def add_image_watermark(self, image, watermark="", watermark_image=None, mask=None, **w):
        size_mode = w.get("Size_Mode", "percentage")
        scale_percent = float(w.get("Scale_Percent", 15.0))
        pixel_width = int(w.get("Pixel_Width", 200))
        opacity = float(w.get("Opacity", 1.0))
        blend_mode = str(w.get("Blend_Mode", "normal")).lower().strip()
        invert_colors = bool(w.get("Invert_Colors", False))
        color_tint = bool(w.get("Color_Tint", False))
        tint_color = _resolve_preset_or_hex_color(
            w.get("Tint_Color_Preset", "custom hex"),
            w.get("Tint_Color", "#FFFFFF"),
            (255, 255, 255),
        )
        mask_mode = str(w.get("Mask_Mode", "load image mask (invert)")).lower().strip()
        if mask_mode not in MASK_MODE_OPTIONS_NORM:
            mask_mode = "load image mask (invert)"

        if image is None:
            return (image, _empty_mask_like_image(image))

        # Watermark source priority:
        # 1) connected IMAGE input, preserving existing Load Image workflows
        # 2) built-in watermark dropdown/upload button, using the same alpha-mask convention
        #    as ComfyUI's Load Image node
        #
        # If neither source is provided, treat the node as a safe no-op. This
        # allows workflows to keep Ultra Image Watermark connected while using
        # only the optional external watermark_image path in some branches, or
        # while leaving the watermark intentionally disabled.
        if watermark_image is None:
            watermark_name = str(watermark or "").strip()
            if watermark_name:
                watermark_image, file_mask = _load_watermark_file_as_tensors(watermark_name)
                if mask is None:
                    mask = file_mask
            else:
                return (image, _empty_mask_like_image(image))

        if watermark_image is None:
            return (image, _empty_mask_like_image(image))

        position = str(w.get("Position", "bottom right"))
        margin = int(w.get("Margin", 20))
        margin_x = int(w.get("Margin_X", 0))
        margin_y = int(w.get("Margin_Y", 0))
        rotation = float(w.get("Rotation", 0.0))
        tile_mode = str(w.get("Tile_Mode", "off")).lower()
        tile_axis_mode = str(w.get("Tile_Axis_Mode", "angle aligned")).lower().strip()
        if tile_axis_mode not in TILE_AXIS_MODE_OPTIONS_NORM:
            tile_axis_mode = "angle aligned"
        tile_spacing = int(w.get("Tile_Spacing", 100))
        edge_softness = int(w.get("Edge_Softness", 0))
        stroke_width = int(w.get("Stroke_Width", 0))
        stroke_color = _resolve_preset_or_hex_color(
            w.get("Stroke_Color_Preset", "custom hex"),
            w.get("Stroke_Color", "#000000"),
            (0, 0, 0),
        )
        shadow_enabled = bool(w.get("Shadow_Enabled", False))
        shadow_color = _resolve_preset_or_hex_color(
            w.get("Shadow_Color_Preset", "custom hex"),
            w.get("Shadow_Color", "#000000"),
            (0, 0, 0),
        )
        shadow_opacity = float(w.get("Shadow_Opacity", 0.5))
        shadow_offset_x = int(w.get("Shadow_Offset_X", 4))
        shadow_offset_y = int(w.get("Shadow_Offset_Y", 4))
        shadow_blur = float(w.get("Shadow_Blur", 6.0))

        results = []
        masks = []
        prepared_cache = {}
        overlay_cache = {}
        image_batch = int(getattr(image, "shape", [1])[0])
        watermark_batch = int(getattr(watermark_image, "shape", [1])[0])

        def _mask_is_per_frame() -> bool:
            if mask is None or image_batch <= 1:
                return False
            try:
                return bool(mask.dim() >= 3 and int(mask.shape[0]) == image_batch)
            except Exception:
                return False

        dynamic_wm = bool(image_batch > 1 and watermark_batch == image_batch)
        dynamic_mask = _mask_is_per_frame()
        static_overlay_candidate = bool(image_batch > 1 and (not dynamic_wm) and (not dynamic_mask))

        def _select_mask_frame(frame_i: int):
            if mask is None:
                return None, None
            try:
                if mask.dim() >= 3 and int(mask.shape[0]) == image_batch:
                    return mask[frame_i], frame_i
                if mask.dim() >= 3:
                    return mask[0], 0
                return mask, "single"
            except Exception:
                return mask, "single"

        def _make_prepared(wm_frame, bw, bh, mask_frame, prepare_rotation):
            return self._prepare_watermark(
                wm_frame,
                bw,
                bh,
                mask_frame,
                mask_mode,
                size_mode,
                scale_percent,
                pixel_width,
                edge_softness,
                opacity,
                invert_colors,
                prepare_rotation,
                color_tint=color_tint,
                tint_color=tint_color,
                stroke_width=stroke_width,
                stroke_color=stroke_color,
                shadow_enabled=shadow_enabled,
                shadow_color=shadow_color,
                shadow_opacity=shadow_opacity,
                shadow_offset_x=shadow_offset_x,
                shadow_offset_y=shadow_offset_y,
                shadow_blur=shadow_blur,
            )

        def _make_overlay(base_size, prepared):
            bw, bh = base_size
            wm, align_bb, tile_pitch = prepared
            if tile_mode != "off":
                return self._build_tile_layer(
                    wm, align_bb, bw, bh, tile_mode, tile_spacing, rotation,
                    tile_axis_mode=tile_axis_mode,
                    tile_pitch=tile_pitch,
                )
            x, y = self._calc_position(
                bw, bh, align_bb, position, margin, margin_x, margin_y
            )
            overlay_img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            alpha_composite_clipped(overlay_img, wm, (x, y))
            return overlay_img

        # Fast path for video/batch workflows with a static watermark/mask.
        # Geometry and overlay generation remain PIL-based, so placement and tile
        # shape are unchanged; only the final blend over the batch is vectorized.
        if static_overlay_candidate:
            try:
                if image.ndim == 4 and int(image.shape[-1]) == 3:
                    bh = int(image.shape[1])
                    bw = int(image.shape[2])
                    prepare_rotation = _prepare_rotation_for_tile(tile_mode, tile_axis_mode, rotation)
                    mask_frame, _mask_idx = _select_mask_frame(0)
                    prepared = _make_prepared(watermark_image[0], bw, bh, mask_frame, prepare_rotation)
                    if prepared is None:
                        out = _quantize_tensor_like_pil(image[:, :, :, :3].to(dtype=torch.float32))
                        zero_masks = torch.zeros((image_batch, bh, bw), dtype=torch.float32, device=image.device)
                        return (out, zero_masks)
                    overlay = _make_overlay((bw, bh), prepared)
                    fast = blend_tensor_batch_with_static_overlay(image, overlay, blend_mode)
                    if fast is not None:
                        return fast
            except Exception:
                # Preserve reliability: if the fast path cannot be used, the
                # established per-frame PIL path below handles the same request.
                pass

        # Cache only when the selected watermark/mask can be reused.  For dynamic
        # per-frame watermark or mask batches, storing every unique 4K overlay can
        # retain many gigabytes until the node finishes, so dynamic cases render
        # directly and release per-frame objects naturally.
        use_cache = bool((not dynamic_wm) and (not dynamic_mask))

        for i in range(image_batch):
            base = tensor2pil(image[i]).convert("RGBA")
            bw, bh = base.size

            # Batch-aware watermark/mask selection:
            # - if watermark_image has the same batch length as image, use per-frame watermark
            # - otherwise reuse the first watermark for all output frames
            wm_idx = i if watermark_batch == image_batch else 0
            wm_frame = watermark_image[wm_idx]
            mask_frame, mask_idx = _select_mask_frame(i)

            # Angle-aligned tiling rotates the whole tile grid after placement,
            # so the individual watermark image must stay unrotated here.
            # Screen-aligned tiling keeps the grid horizontal/vertical and rotates
            # each watermark image before placement.
            prepare_rotation = _prepare_rotation_for_tile(tile_mode, tile_axis_mode, rotation)

            prepared_key = (wm_idx, mask_idx, bw, bh, prepare_rotation, mask_mode)
            if use_cache:
                prepared = prepared_cache.get(prepared_key)
            else:
                prepared = None
            if prepared is None:
                prepared = _make_prepared(wm_frame, bw, bh, mask_frame, prepare_rotation)
                if use_cache and prepared is not None:
                    prepared_cache[prepared_key] = prepared

            if prepared is None:
                results.append(pil2tensor(base).unsqueeze(0))
                masks.append(torch.zeros(1, bh, bw, dtype=torch.float32))
                continue

            if tile_mode != "off":
                overlay_key = (prepared_key, tile_mode, tile_axis_mode, tile_spacing, rotation)
                if use_cache:
                    overlay = overlay_cache.get(overlay_key)
                else:
                    overlay = None
                if overlay is None:
                    overlay = _make_overlay((bw, bh), prepared)
                    if use_cache:
                        overlay_cache[overlay_key] = overlay
            else:
                overlay = _make_overlay((bw, bh), prepared)

            # ⑤ Mask output — extract overlay alpha before compositing.
            overlay_a = np.array(overlay.split()[3], dtype=np.float32) / 255.0
            masks.append(torch.from_numpy(overlay_a).unsqueeze(0))

            # ② Blend mode compositing — replaces Image.alpha_composite.
            out = blend_images(base, overlay, blend_mode)

            results.append(pil2tensor(out).unsqueeze(0))

        return (torch.cat(results, dim=0), torch.cat(masks, dim=0))
