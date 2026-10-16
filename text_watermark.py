# -*- coding: utf-8 -*-
"""
Ultra Text Watermark

핵심
- First/Second 텍스트 블록 (각각 폰트/사이즈/색/정렬/스타일)
- First/Second 아웃라인(색/두께/Enabled) 각각 따로 ✅
- Glow는 Text 1/Text 2 적용 여부만 독립 제어, 옵션값은 공통, 선택된 블록 마스크 합산 기준 1회 적용 ✅
- Rotation: +rotation => CCW ✅
- Faux Italic: traditional italic (/) right-lean ✅
- 폰트 드롭다운 UI 폭 줄이기: 표시용 파일명은 …(ellipsis) 처리, 내부 로딩은 원본 파일명 매핑 ✅
- 섹션 헤더 4개: "가로줄 + 아이콘 + 종류명 + 가로줄" (Section/숫자 없음) ✅
"""

import os
import sys
import math
import numpy as np
import torch
from collections import OrderedDict
from threading import Lock
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
    RESAMPLE_BICUBIC = Image.Resampling.BICUBIC
except AttributeError:  # Pillow < 9.1 compatibility
    RESAMPLE_LANCZOS = Image.LANCZOS
    RESAMPLE_BICUBIC = Image.BICUBIC

try:
    TRANSFORM_AFFINE = Image.Transform.AFFINE
except AttributeError:  # Pillow < 9.1 compatibility
    TRANSFORM_AFFINE = Image.AFFINE

SUPPORTED_FONT_EXTS = (".ttf", ".otf", ".ttc", ".otc")

COLORS = [
    "white", "black", "red", "green", "blue", "yellow", "cyan", "magenta",
    "orange", "purple", "pink", "brown", "gray", "navy", "teal", "maroon"
]

ALIGN_OPTIONS = [
    "center", "top left", "top center", "top right",
    "bottom left", "bottom center", "bottom right"
]

TEXT_ALIGN_OPTIONS = ["left", "center", "right"]
LAYOUT_DIRECTION_OPTIONS = ["vertical", "horizontal"]
HEIGHT_ALIGN_MODE_OPTIONS = ["top", "middle", "bottom"]

COLOR_MAPPING = {
    "white": (255, 255, 255), "black": (0, 0, 0), "red": (255, 0, 0),
    "green": (0, 255, 0), "blue": (0, 0, 255), "yellow": (255, 255, 0),
    "cyan": (0, 255, 255), "magenta": (255, 0, 255), "orange": (255, 165, 0),
    "purple": (128, 0, 128), "pink": (255, 192, 203), "brown": (165, 42, 42),
    "gray": (128, 128, 128), "navy": (0, 0, 128), "teal": (0, 128, 128),
    "maroon": (128, 0, 0),
}

DEFAULT_LINE_SPACING = 0
ROTATION_STEP = 15

# Additional constants for magic numbers
MAX_GLOW_BLUR_RADIUS = 30
MAX_SPACING_COMPENSATION = 12
MIN_LINE_SPACING = -5
MAX_LINE_SPACING = 40
MAX_ALIGN_OFFSET = 2048
MIN_ALIGN_OFFSET = -2048
UNDERLINE_THICKNESS_RATIO = 18.0
UNDERLINE_GAP_RATIO = 14.0
FAUXBOLD_STRENGTH_RATIO = 22.0

STYLE_PRESETS = [
    "None",
    "Bold",
    "Italic",
    "Bold + Italic",
    "Underline",
    "Bold + Underline",
    "Italic + Underline",
    "Bold + Italic + Underline",
]

# UI 폭 줄이기용: 드롭다운 표시명 최대 길이
FONT_DISPLAY_MAX_LEN = 28


# -------------------------
# Constants (document magic numbers)
# -------------------------
# Extra padding to prevent glow/outline clipping at extreme settings.
MARGIN_SAFETY_PADDING = 24

# Extra bbox margin when measuring multiline text to avoid tight cropping.
TEXT_BBOX_MARGIN = 20

# Standard italic shear factor for faux-italic rendering (right-lean).
DEFAULT_ITALIC_SHEAR = 0.30


# -------------------------
# Helper functions for config extraction
# -------------------------
def _extract_spacing_params(config: dict, prefix: str) -> dict:
    """Extract multiline spacing parameters from watermark config.
    
    Args:
        config: Watermark configuration dictionary
        prefix: "First" or "Second" to select text block
        
    Returns:
        Dict with keys: user_spacing, outline_enabled, outline_width,
                       glow_enabled, glow_thickness, glow_blur
    """
    return {
        'user_spacing': int(config.get(f"{prefix}_Line_Spacing", DEFAULT_LINE_SPACING)),
        'outline_enabled': bool(config.get(f"{prefix}_Outline_Enabled", False)),
        'outline_width': int(config.get(f"{prefix}_Outline_Width", 0)),
        'glow_enabled': bool(config.get(f"{prefix}_Glow_Enabled", config.get("Glow_Enabled", False))),
        'glow_thickness': int(config.get("Glow_Thickness", 0)),
        'glow_blur': int(config.get("Glow_Blur", 0))
    }


def _get_color_safe(config: dict, key: str, default: tuple = (255, 255, 255)) -> tuple:
    """Safely extract RGB color from config with fallback.
    
    Args:
        config: Configuration dictionary
        key: Color key name (e.g., "First_Font_Color")
        default: Default RGB tuple if key not found or invalid
        
    Returns:
        RGB tuple (r, g, b) with values 0-255
    """
    color_name = config.get(key)
    if not color_name:
        return default
    return COLOR_MAPPING.get(color_name, default)


# -------------------------
# Tensor/PIL helpers
# -------------------------
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

    # MASK-like tensors may arrive as 1xHxW; convert to HxW grayscale.
    if arr.ndim == 3 and arr.shape[0] == 1 and arr.shape[-1] not in (3, 4):
        arr = arr[0]

    # HxWx1 grayscale is valid data but PIL expects HxW for mode L.
    if arr.ndim == 3 and arr.shape[-1] == 1:
        arr = arr[:, :, 0]

    return Image.fromarray(np.clip(255.0 * arr, 0, 255).astype(np.uint8))


def reduce_opacity_rgba(img_rgba: Image.Image, opacity: float) -> Image.Image:
    """Reduce opacity of RGBA image by scaling alpha channel.
    
    Args:
        img_rgba: Source RGBA image
        opacity: Opacity multiplier in range [0.0, 1.0]
        
    Returns:
        New RGBA image with adjusted opacity
    """
    opacity = float(opacity)
    if opacity >= 0.999:
        return img_rgba
    if opacity <= 0.0:
        return Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    out = img_rgba.copy()
    a = out.split()[3]
    a = a.point(lambda p: int(p * opacity))
    out.putalpha(a)
    return out



def alpha_composite_clipped(dst_rgba: Image.Image, src_rgba: Image.Image, dest_xy: Tuple[int, int]) -> None:
    """Alpha-composite src onto dst at dest_xy, safely clipped to dst bounds.

    Pillow's Image.alpha_composite(src, dest=(x,y)) may raise if dest is outside bounds.
    This helper crops the source to the intersection region so any (x,y) is safe.

    Args:
        dst_rgba: Destination RGBA image (modified in-place)
        src_rgba: Source RGBA image
        dest_xy: (x, y) top-left position on dst
    """
    x, y = int(dest_xy[0]), int(dest_xy[1])
    if src_rgba is None:
        return
    sw, sh = src_rgba.size
    dw, dh = dst_rgba.size

    # Intersection of dst rect [0,dw)x[0,dh) and src rect [x,x+sw)x[y,y+sh)
    ix0 = max(0, x)
    iy0 = max(0, y)
    ix1 = min(dw, x + sw)
    iy1 = min(dh, y + sh)

    if ix1 <= ix0 or iy1 <= iy0:
        return  # no overlap

    # Crop corresponding region from src
    sx0 = ix0 - x
    sy0 = iy0 - y
    sx1 = sx0 + (ix1 - ix0)
    sy1 = sy0 + (iy1 - iy0)

    src_crop = src_rgba.crop((sx0, sy0, sx1, sy1))
    dst_rgba.alpha_composite(src_crop, (ix0, iy0))

def list_supported_fonts(font_dir: str) -> List[str]:
    try:
        files = os.listdir(font_dir)
    except (FileNotFoundError, NotADirectoryError):
        # Font directory doesn't exist yet (normal on first run)
        return []
    except (PermissionError, OSError) as e:
        # Log but allow graceful degradation
        print(f"[Ultra Text Watermark] Warning: Cannot access fonts directory: {e}")
        return []
    fonts = [f for f in files if isinstance(f, str) and f.lower().endswith(SUPPORTED_FONT_EXTS)]
    fonts.sort(key=lambda s: s.lower())
    return fonts


def list_system_fonts(max_files: int = 1200) -> Tuple[List[str], Dict[str, str]]:
    """Find a bounded set of OS fonts as a no-bundle fallback.

    Local ./fonts files always take priority.  This fallback keeps the node usable
    when Ultra Tools is installed without bundled font binaries.
    """
    roots = []
    if os.name == "nt":
        windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot") or r"C:\\Windows"
        roots.append(os.path.join(windir, "Fonts"))
    elif sys.platform == "darwin":
        roots.extend([
            "/System/Library/Fonts",
            "/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ])
    else:
        roots.extend([
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
            os.path.expanduser("~/.local/share/fonts"),
        ])

    found: Dict[str, str] = {}
    for root in roots:
        if len(found) >= max_files or not os.path.isdir(root):
            continue
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames.sort(key=str.lower)
                for filename in sorted(filenames, key=str.lower):
                    if not filename.lower().endswith(SUPPORTED_FONT_EXTS):
                        continue
                    # Keep the first path for duplicate basenames; local ./fonts
                    # still wins because this map is consulted only as fallback.
                    found.setdefault(filename, os.path.join(dirpath, filename))
                    if len(found) >= max_files:
                        break
                if len(found) >= max_files:
                    break
        except (PermissionError, OSError):
            continue

    names = sorted(found.keys(), key=str.lower)
    return names, found


# -------------------------
# Font display shortening (…)
# -------------------------
def _ellipsis_name(name: str, max_len: int) -> str:
    if not isinstance(name, str):
        return str(name)
    if len(name) <= max_len:
        return name

    base, ext = os.path.splitext(name)
    ext = ext or ""
    budget = max_len - len(ext) - 1  # 1 for …
    if budget <= 6:
        return (name[: max_len - 1] + "…")[:max_len]

    head = max(3, budget // 2)
    tail = max(3, budget - head)
    return f"{base[:head]}…{base[-tail:]}{ext}"


def build_font_choices_and_map(file_list: List[str], max_len: int) -> Tuple[List[str], Dict[str, str], Dict[str, str]]:
    """Build font choices and bidirectional mapping.
    
    Args:
        file_list: List of font filenames
        max_len: Maximum display name length
        
    Returns:
        Tuple of (choices, disp2actual, actual2disp) mappings
    """
    disp2actual = {}
    actual2disp = {}
    used = set()
    choices = []

    for actual in file_list:
        disp = _ellipsis_name(actual, max_len)

        if disp in used and actual2disp.get(actual) != disp:
            n = 2
            while True:
                suffix = f" ({n})"
                disp2 = _ellipsis_name(actual, max_len - len(suffix)) + suffix
                if disp2 not in used:
                    disp = disp2
                    break
                n += 1

        used.add(disp)
        disp2actual[disp] = actual
        actual2disp[actual] = disp
        choices.append(disp)

    return choices, disp2actual, actual2disp


# -------------------------
# Font name parsing
# -------------------------
def _stem_no_ext(filename: str) -> str:
    return os.path.splitext(filename)[0]


def _family_key(filename: str) -> str:
    stem = _stem_no_ext(filename)
    for sep in ("-", "_"):
        if sep in stem:
            return stem.split(sep)[0].strip().lower()
    return stem.strip().lower()


def _name_tokens(filename: str) -> Set[str]:
    stem = _stem_no_ext(filename).lower()
    for ch in ("-", "_"):
        stem = stem.replace(ch, " ")
    return set(stem.split())


def _is_bold_name(filename: str) -> bool:
    s = _stem_no_ext(filename).lower()
    toks = _name_tokens(filename)
    return ("bold" in toks) or ("black" in toks) or ("bold" in s) or ("black" in s)


def _is_italic_name(filename: str) -> bool:
    s = _stem_no_ext(filename).lower()
    toks = _name_tokens(filename)
    return ("italic" in toks) or ("oblique" in toks) or ("italic" in s) or ("oblique" in s)


def _is_bolditalic_name(filename: str) -> bool:
    s = _stem_no_ext(filename).lower().replace("_", "-").replace(" ", "-")
    return ("bolditalic" in s) or ("bold-italic" in s)


def parse_style_preset(preset: str) -> Tuple[bool, bool, bool]:
    s = (preset or "None").lower()
    want_bold = "bold" in s
    want_italic = "italic" in s
    want_underline = "underline" in s
    return want_bold, want_italic, want_underline




# -------------------------
# Mask/FX helpers
# -------------------------
def alpha_bbox_threshold(img_rgba: Image.Image, th: int) -> Optional[Tuple[int, int, int, int]]:
    th = int(max(0, min(255, th)))
    a = img_rgba.split()[3]
    if th <= 0:
        return img_rgba.getbbox()
    a2 = a.point(lambda v: 255 if v >= th else 0)
    return a2.getbbox()


def auto_visible_threshold(glow_enabled: bool, glow_blur: int, glow_thickness: int, eff_opacity: float) -> int:
    """Heuristic threshold for bbox detection on alpha channel.

    Lower thresholds are safer for thin strokes / low-opacity glow (prevents clipping).
    """
    eff = float(max(0.0, min(1.0, eff_opacity)))

    # If glow is effectively off (or thickness 0), keep threshold very low.
    if (not glow_enabled) or (int(glow_thickness) <= 0):
        return 1 if eff >= 0.25 else 0

    b = int(max(0, glow_blur))
    t = int(max(0, glow_thickness))
    base = 8 + int(round(b * 0.75)) + int(round(t * 0.10))
    th = int(round(base * (0.55 + 0.45 * eff)))
    return max(3, min(32, th))



def dilate_mask(mask_l: Image.Image, radius_px: int) -> Image.Image:
    r = int(max(0, radius_px))
    if r <= 0:
        return mask_l
    # Single-pass MaxFilter: kernel size = 2*r + 1 (must be odd)
    return mask_l.filter(ImageFilter.MaxFilter(r * 2 + 1))


def upgraded_glow_mask(outside_mask_l: Image.Image, blur_radius: int) -> Image.Image:
    r = int(max(0, blur_radius))
    if r <= 0:
        return outside_mask_l
    g1 = outside_mask_l.filter(ImageFilter.GaussianBlur(r))
    g2 = outside_mask_l.filter(ImageFilter.GaussianBlur(r * 2))
    return ImageChops.add(g1, g2, scale=1.7, offset=0)


def _compute_multiline_spacing(user_spacing: int,
                              outline_enabled: bool,
                              outline_width: int,
                              glow_enabled: bool,
                              glow_thickness: int,
                              glow_blur: int) -> int:
    """Compute a visually-stable multiline spacing that accounts for outline/glow expansion.
    Keeps the adjustment gentle (prevents 'exploding' gaps) and clamps to the UI range.
    """
    base = int(user_spacing)

    extra = 0
    if outline_enabled:
        extra += int(round(max(0, int(outline_width)) * 0.70))

    # In the renderer, Glow_Thickness=0 means there is no visible glow area.
    # Keep multiline spacing unchanged in that case, even if Glow_Blur is set.
    if glow_enabled and int(glow_thickness) > 0:
        gt = max(0, int(glow_thickness))
        gb = max(0, int(glow_blur))
        # blur affects perceived vertical spread more than thickness, but keep it subtle
        extra += int(round(gt * 0.35))
        extra += int(round(gb * 0.25))

    # Soft cap so it never becomes too large even with huge glow values.
    extra = max(0, min(extra, MAX_SPACING_COMPENSATION))

    # The original helper is useful at 0, but for long poems / memo text it can feel too roomy.
    # Keep some protection at 0, then fade out quickly once the user starts dialing spacing in.
    if base <= 0:
        extra = int(round(extra * 0.50))
    elif base >= 4:
        extra = 0
    else:
        extra = int(round(extra * (4 - base) / 10.0))

    eff = base + extra

    # Respect the UI slider range so behavior matches the user's expectation.
    eff = max(MIN_LINE_SPACING, min(MAX_LINE_SPACING, eff))
    return eff


def underline_params(font: ImageFont.ImageFont) -> Tuple[int, int]:
    """Calculate underline thickness and gap from font size.
    
    Returns:
        Tuple of (thickness, gap) in pixels
    """
    sz = int(getattr(font, "size", 20))
    th = max(1, int(round(sz / UNDERLINE_THICKNESS_RATIO)))
    gap = max(1, int(round(sz / UNDERLINE_GAP_RATIO)))
    return th, gap


def draw_underline(draw: ImageDraw.ImageDraw, bbox: Optional[Tuple[int, int, int, int]], 
                   color: Union[int, Tuple[int, int, int]], thickness: int, gap: int) -> None:
    """Draw underline below text bounding box."""
    if not bbox:
        return
    x0, y0, x1, y1 = bbox
    y = int(math.ceil(y1 + gap))
    x0i = int(math.floor(x0))
    x1i = int(math.ceil(x1))
    for t in range(int(thickness)):
        draw.line([(x0i, y + t), (x1i, y + t)], fill=color, width=1)


def fauxbold_strength(font: ImageFont.ImageFont) -> int:
    """Calculate faux bold rendering strength from font size."""
    sz = int(getattr(font, "size", 20))
    return max(1, int(math.ceil(sz / FAUXBOLD_STRENGTH_RATIO)))




def draw_text_fauxbold(draw: ImageDraw.ImageDraw, pos, text, font, fill, strength_px: int):
    """Draw a single line with faux bold using multi-offset stamping."""
    s = int(max(1, strength_px))
    offsets = [(0, 0)]
    for dx, dy in [(-s, 0), (s, 0), (0, -s), (0, s),
                  (-s, -s), (-s, s), (s, -s), (s, s)]:
        offsets.append((dx, dy))
    if s >= 2:
        offsets += [(-1, 0), (1, 0), (0, -1), (0, 1)]

    x, y = int(pos[0]), int(pos[1])
    for dx, dy in offsets:
        draw.text((x + dx, y + dy), text, font=font, fill=fill)


def measure_multiline_reference_width(text: str, font: ImageFont.ImageFont) -> int:
    """Measure the longest visible line width for multiline text.

    This is used as the common reference width in vertical layout when Text 1 and Text 2 coexist.
    """
    if not text or not str(text).strip():
        return 0

    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dummy)
    longest = 0
    for line in text.splitlines() or [text]:
        bbox = dd.textbbox((0, 0), line if line else " ", font=font)
        x0, y0, x1, y1 = bbox
        longest = max(longest, int(math.ceil(x1 - x0)))
    return max(0, longest)




def shear_affine_italic_right(img: Image.Image, shear_k: float) -> Image.Image:
    k = float(abs(shear_k))
    if k < 1e-6:
        return img
    w, h = img.size
    extra = int(math.ceil(k * h))
    new_w = w + extra
    matrix = (1, +k, -extra, 0, 1, 0)
    return img.transform((new_w, h), TRANSFORM_AFFINE, matrix, resample=RESAMPLE_BICUBIC)


def build_block_assets(
    text: str,
    font: ImageFont.ImageFont,
    color_rgb,
    want_underline: bool,
    faux_bold: bool,
    faux_italic: bool,
    spacing: int = DEFAULT_LINE_SPACING,
    shear_k: float = DEFAULT_ITALIC_SHEAR,
    text_align: str = "left",
    paragraph_width_override: Optional[int] = None,
) -> Tuple[Optional[Image.Image], Optional[Image.Image], int, int, int, int]:
    if not text or not str(text).strip():
        return None, None, 0, 0, 0, 0

    lines = text.splitlines() or [text]
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dummy)

    measured_lines = []
    longest_visible_w = 1
    top_min = 0
    bottom_max = 0
    left_overhang = 0
    right_overhang = 0

    for line in lines:
        line_draw = line if line else " "
        bbox = dd.textbbox((0, 0), line_draw, font=font)
        x0, y0, x1, y1 = bbox
        width = max(0, int(math.ceil(x1 - x0)))
        top_min = min(top_min, int(math.floor(y0)))
        bottom_max = max(bottom_max, int(math.ceil(y1)))
        longest_visible_w = max(longest_visible_w, width)
        left_overhang = max(left_overhang, max(0, -int(math.floor(x0))))
        right_overhang = max(right_overhang, max(0, int(math.ceil(x1)) - width))
        measured_lines.append({
            "text": line,
            "draw_text": line_draw,
            "bbox": bbox,
            "width": width,
        })

    paragraph_w = max(1, int(paragraph_width_override or longest_visible_w))
    line_h = max(1, bottom_max - top_min)
    total_h = line_h * len(measured_lines) + int(spacing) * max(0, len(measured_lines) - 1)

    u_th, u_gap = underline_params(font)
    underline_extra = (u_th + u_gap + 2) if want_underline else 0

    margin = TEXT_BBOX_MARGIN
    content_x0 = int(margin + left_overhang)
    cw = int(paragraph_w + left_overhang + right_overhang + margin * 2)
    ch = int(total_h + underline_extra + margin * 2)

    m = Image.new("L", (cw, ch), 0)
    md = ImageDraw.Draw(m)
    tl = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    td = ImageDraw.Draw(tl)

    bold_strength = fauxbold_strength(font)
    y_cursor = int(margin - top_min)

    for item in measured_lines:
        x0, y0, x1, y1 = item["bbox"]
        line_w = item["width"]

        if text_align == "right":
            line_box_x = content_x0 + (paragraph_w - line_w)
        elif text_align == "center":
            line_box_x = content_x0 + (paragraph_w - line_w) // 2
        else:
            line_box_x = content_x0

        pos = (int(line_box_x - math.floor(x0)), int(y_cursor))
        shifted_bbox = (
            pos[0] + x0,
            pos[1] + y0,
            pos[0] + x1,
            pos[1] + y1,
        )

        if faux_bold:
            draw_text_fauxbold(md, pos, item["draw_text"], font, 255, bold_strength)
            draw_text_fauxbold(td, pos, item["draw_text"], font, color_rgb, bold_strength)
        else:
            md.text(pos, item["draw_text"], font=font, fill=255)
            td.text(pos, item["draw_text"], font=font, fill=color_rgb)

        if want_underline and item["text"].strip():
            draw_underline(md, shifted_bbox, 255, u_th, u_gap)
            draw_underline(td, shifted_bbox, color_rgb, u_th, u_gap)

        y_cursor += line_h + int(spacing)

    if faux_italic:
        m = shear_affine_italic_right(m, shear_k)
        tl = shear_affine_italic_right(tl, shear_k)

    bb = m.getbbox()
    if not bb:
        return None, None, 0, 0, 0, 0

    crop_x0, crop_y0, crop_x1, crop_y1 = bb
    m2 = m.crop(bb)
    tl2 = tl.crop(bb)
    bw, bh = m2.size

    # Horizontal placement shift needed to restore the original content box after tight crop.
    # Positive values mean "the cropped image must be pasted a bit to the right of the content box left edge".
    paste_shift_x = int(crop_x0 - content_x0)

    return m2, tl2, int(bw), int(bh), int(paragraph_w), paste_shift_x



class UltraTextWatermark:
    # Font cache: (absolute_path, size, file_mtime) -> PIL ImageFont (LRU-capped)
    MAX_FONT_CACHE = 96
    _font_cache = OrderedDict()
    _font_cache_lock = Lock()

    # Runtime safety: clamp actual render font size to avoid OOM.
    # 256 keeps large-image watermark use practical while avoiding excessive RGBA layer growth.
    MAX_RENDER_FONT_SIZE = 256

    # Font list cache for INPUT_TYPES (avoid rescanning on every UI refresh)
    _font_list_cache: Optional[List[str]] = None
    _font_list_dir_mtime: Optional[float] = None
    _font_external_paths: Dict[str, str] = {}

    @classmethod
    def INPUT_TYPES(cls):
        font_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fonts")
        os.makedirs(font_dir, exist_ok=True)

        # Cache font list based on directory mtime to avoid repeated scans
        dir_mtime = None
        try:
            dir_mtime = os.path.getmtime(font_dir)
        except OSError as e:
            print(f"[Ultra Text Watermark] Warning: Cannot get mtime for {font_dir}: {e}")
            dir_mtime = None

        cached_list = getattr(cls, "_font_list_cache", None)
        cached_mtime = getattr(cls, "_font_list_dir_mtime", None)
        if isinstance(cached_list, list) and (dir_mtime is not None) and (cached_mtime == dir_mtime):
            file_list = cached_list
        else:
            file_list = list_supported_fonts(font_dir)
            cls._font_external_paths = {}
            if not file_list:
                # Ultra Tools does not require bundled font binaries.  When the
                # local fonts folder is empty, use installed OS fonts as a safe
                # fallback so the node remains immediately usable.
                file_list, cls._font_external_paths = list_system_fonts()
            if not file_list:
                file_list = ["<NO_FONTS_FOUND>"]

            # ✅ 폰트 목록은 대소문자 무시 알파벳 정렬
            file_list = sorted(file_list, key=lambda x: x.lower())
            cls._font_list_cache = file_list
            cls._font_list_dir_mtime = dir_mtime

        font_choices, font_disp2actual, font_actual2disp = build_font_choices_and_map(
            file_list, max_len=FONT_DISPLAY_MAX_LEN
        )
        cls._font_disp2actual = font_disp2actual

        # ✅ 기본 선택 폰트: 스샷 기준으로 Text 1 / Text 2 기본 폰트를 따로 지정
        # - 폰트 파일이 fonts 폴더에 있으면 해당 폰트를 기본값으로 사용
        # - 없으면 기존처럼 정렬된 목록의 첫 번째 폰트로 안전하게 fallback
        def _default_font_choice(preferred_names):
            for _p in preferred_names:
                if _p in file_list:
                    return font_actual2disp.get(_p, font_choices[0])
            return font_choices[0]

        default_first_font_choice = _default_font_choice(["DancingScript-Bold.ttf"])
        default_second_font_choice = _default_font_choice(["행복고흥M.ttf"])

        # Section headers
        H0 = "── 🔤 Fonts & Text ──"
        # 4 headers (no section word / no numbering)
        H1 = "── 🧩 Spacing ──"
        H2 = "── ✨ Glow ──"
        H4 = "── 🎛️ Adjust ──"

        return {
            "required": {
                "image": ("IMAGE",),

                H0: ("STRING", {"multiline": False, "default": ""}),
                # Text 1 (core)
                "First_Text": ("STRING", {"multiline": True, "default": "Created image by"}),
                "First_Font": (font_choices, {"default": default_first_font_choice}),
                "First_Font_Size": ("INT", {"default": 30, "min": 1, "max": cls.MAX_RENDER_FONT_SIZE}),
                "First_Font_Color": (COLORS, {"default": "green"}),
                "First_Align": (TEXT_ALIGN_OPTIONS, {"default": "right"}),
                "First_Style": (STYLE_PRESETS, {"default": "None"}),

                # Text 1 details
                "First_Line_Spacing": ("INT", {"default": DEFAULT_LINE_SPACING, "min": -5, "max": 40}),
                "First_Outline_Enabled": ("BOOLEAN", {"default": True}),
                "First_Outline_Width": ("INT", {"default": 1, "min": 0, "max": 12}),
                "First_Outline_Color": (COLORS, {"default": "black"}),

                # Text 2 (core)
                "Second_Text": ("STRING", {"multiline": True, "default": "너의 이름은"}),
                "Second_Font": (font_choices, {"default": default_second_font_choice}),
                "Second_Font_Size": ("INT", {"default": 50, "min": 1, "max": cls.MAX_RENDER_FONT_SIZE}),
                "Second_Font_Color": (COLORS, {"default": "white"}),
                "Second_Align": (TEXT_ALIGN_OPTIONS, {"default": "right"}),
                "Second_Style": (STYLE_PRESETS, {"default": "None"}),

                # Text 2 details
                "Second_Line_Spacing": ("INT", {"default": DEFAULT_LINE_SPACING, "min": -5, "max": 40}),
                "Second_Outline_Enabled": ("BOOLEAN", {"default": True}),
                "Second_Outline_Width": ("INT", {"default": 1, "min": 0, "max": 12}),
                "Second_Outline_Color": (COLORS, {"default": "blue"}),


                # Spacing between two text blocks (keep near text controls)
                H1: ("STRING", {"multiline": False, "default": ""}),
                "Layout_Direction": (LAYOUT_DIRECTION_OPTIONS, {"default": "vertical"}),
                "Height_Align_Mode": (HEIGHT_ALIGN_MODE_OPTIONS, {"default": "middle"}),
                "Block_Spacing": ("INT", {"default": 10, "min": 0, "max": 600}),

                # Glow (often optional; keep enabled visible, details advanced)
                H2: ("STRING", {"multiline": False, "default": ""}),
                "First_Glow_Enabled": ("BOOLEAN", {"default": True}),
                "Second_Glow_Enabled": ("BOOLEAN", {"default": True}),
                "Glow_Color": (COLORS, {"default": "white"}),
                "Glow_Thickness": ("INT", {"default": 5, "min": 0, "max": 20}),
                "Glow_Blur": ("INT", {"default": 5, "min": 0, "max": 30}),
                "Glow_Opacity": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.05}),

                # Placement + global opacity
                H4: ("STRING", {"multiline": False, "default": ""}),
                "Watermark_Opacity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "Align": (ALIGN_OPTIONS, {"default": "bottom right"}),
                "Align_Offset": ("INT", {"default": 0, "min": 0, "max": 2048}),
                "Align_Offset_X": ("INT", {"default": 0, "min": -2048, "max": 2048}),
                "Align_Offset_Y": ("INT", {"default": 0, "min": -2048, "max": 2048}),
                "Rotation": ("FLOAT", {"default": 0.0, "min": -180.0, "max": 180.0, "step": ROTATION_STEP}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "add_watermark"
    CATEGORY = "Ultra Tools"

    def _ensure_fonts_exist_or_raise(self, font_dir: str):
        if len(list_supported_fonts(font_dir)) == 0 and not getattr(self.__class__, "_font_external_paths", {}):
            # INPUT_TYPES normally populates the system fallback map first, but
            # direct/server-side execution can reach here without a UI refresh.
            _, external = list_system_fonts()
            self.__class__._font_external_paths = external
        if len(list_supported_fonts(font_dir)) == 0 and not getattr(self.__class__, "_font_external_paths", {}):
            raise Exception(
                "[Ultra Text Watermark] No supported fonts were found.\n"
                f"Supported: {', '.join(SUPPORTED_FONT_EXTS)}\n"
                "Add at least one supported font file to ./fonts and restart ComfyUI."
            )

    def _map_font_choice_to_actual(self, choice: str) -> str:
        mp = getattr(self.__class__, "_font_disp2actual", {}) or {}
        return mp.get(choice, choice)

    def _load_font_strict(self, font_dir: str, name_or_choice: str, size: int) -> ImageFont.ImageFont:
        name = self._map_font_choice_to_actual(name_or_choice)

        if (not isinstance(name, str)) or name == "<NO_FONTS_FOUND>":
            raise Exception(
                "[Ultra Text Watermark] Font selection invalid (no fonts installed).\n"
                f"Put font files ({', '.join(SUPPORTED_FONT_EXTS)}) into ./fonts and restart ComfyUI."
            )
        if not name.lower().endswith(SUPPORTED_FONT_EXTS):
            raise Exception(
                f"[Ultra Text Watermark] Unsupported font extension: {name}\n"
                f"Supported: {', '.join(SUPPORTED_FONT_EXTS)}"
            )
        
        # Prefer user fonts in ./fonts.  If absent, use only a path that was
        # discovered by our bounded OS-font scan; arbitrary absolute paths are
        # never accepted from workflow input.
        local_path = os.path.abspath(os.path.join(font_dir, name))
        abs_font_dir = os.path.abspath(font_dir)
        if local_path.startswith(abs_font_dir + os.sep) and os.path.exists(local_path):
            abs_path = local_path
        else:
            external = getattr(self.__class__, "_font_external_paths", {}) or {}
            abs_path = os.path.abspath(external.get(name, "")) if name in external else ""

        if not abs_path or not os.path.isfile(abs_path):
            raise Exception(
                f"[Ultra Text Watermark] Font file not found: {name}\n"
                "Put the font in ./fonts, install it in the operating system, or choose another font."
            )

        try:
            file_mtime = os.path.getmtime(abs_path)
        except OSError:
            file_mtime = None

        key = (abs_path, int(size), file_mtime)
        cache = getattr(self.__class__, "_font_cache", None)
        lock = getattr(self.__class__, "_font_cache_lock", None)

        # Thread-safe cache read (LRU)
        if isinstance(cache, OrderedDict) and lock is not None:
            with lock:
                cached = cache.get(key)
                if cached is not None:
                    cache.move_to_end(key)
                    return cached
        elif isinstance(cache, dict):
            # Best-effort fallback (should not happen unless cache type changed)
            cached = cache.get(key)
            if cached is not None:
                try:
                    cache.move_to_end(key)
                except Exception:
                    pass
                return cached

        # Load outside lock to avoid IO bottleneck
        try:
            font = ImageFont.truetype(abs_path, size=int(size))
        except (IOError, OSError) as e:
            raise Exception(
                f"[Ultra Text Watermark] Failed to load font: {name}\n"
                f"File might be corrupted. Error: {e}\n"
                "Try removing and re-adding the font file."
            )

        # Thread-safe cache write (double-check)
        if isinstance(cache, OrderedDict) and lock is not None:
            with lock:
                cached = cache.get(key)
                if cached is not None:
                    cache.move_to_end(key)
                    return cached

                cache[key] = font
                cache.move_to_end(key)
                max_n = int(getattr(self.__class__, "MAX_FONT_CACHE", 96))
                while len(cache) > max_n:
                    cache.popitem(last=False)
        elif isinstance(cache, dict):
            cache[key] = font
        return font

    def _resolve_font_and_faux(self, font_dir: str, selected_name_or_choice: str, want_bold: bool, want_italic: bool):
        # 폰트 파일 자체의 weight/style(예: Light/SemiBold/Italic)를 '그대로' 존중한다.
        # 스타일 프리셋(Bold/Italic)은 폰트를 다른 파일로 교체하지 않고, 가상(faux) 효과로만 추가 적용한다.
        selected_name = self._map_font_choice_to_actual(selected_name_or_choice)

        real_name = selected_name  # ✅ 항상 사용자가 선택한 파일 그대로 사용

        # ✅ Bold는 선택 폰트의 굵기와 무관하게 "추가 두께"로 faux 적용 (사용자가 Bold를 켠 경우)
        faux_bold = want_bold

        # ✅ Italic은 선택 폰트가 이미 Italic/Oblique라면 중복 기울임을 피하기 위해 faux를 끈다
        already_italic = _is_italic_name(real_name)
        faux_italic = bool(want_italic and (not already_italic))

        return real_name, faux_bold, faux_italic


    def _build_watermark_layer_and_align_bbox(self, w, block1, block2):
        # unpack blocks
        m1, t1, bw1, bh1, refw1, shiftx1 = block1[:6]
        m2, t2, bw2, bh2, refw2, shiftx2 = block2[:6]

        # per-text outline params
        o1_en = bool(w["First_Outline_Enabled"])
        o2_en = bool(w["Second_Outline_Enabled"])
        o1_w = int(w["First_Outline_Width"]) if o1_en else 0
        o2_w = int(w["Second_Outline_Width"]) if o2_en else 0
        o1_rgb = _get_color_safe(w, "First_Outline_Color", (0, 0, 0))
        o2_rgb = _get_color_safe(w, "Second_Outline_Color", (0, 0, 0))

        first_glow_enabled = bool(w.get("First_Glow_Enabled", w.get("Glow_Enabled", False)))
        second_glow_enabled = bool(w.get("Second_Glow_Enabled", w.get("Glow_Enabled", False)))
        glow_enabled = bool(first_glow_enabled or second_glow_enabled)
        glow_t = int(w["Glow_Thickness"]) if glow_enabled else 0
        extra_blur = int(w["Glow_Blur"]) if glow_enabled else 0
        glow_opacity = float(w["Glow_Opacity"])

        block_spacing = int(w["Block_Spacing"])
        watermark_opacity = float(w["Watermark_Opacity"])
        rotation = float(w["Rotation"])

        if glow_t <= 0:
            glow_enabled = False
            glow_t = 0
            extra_blur = 0

        if glow_enabled:
            min_blur = int(math.ceil(glow_t / 2.0))
            glow_b = min(MAX_GLOW_BLUR_RADIUS, max(0, min_blur + max(0, extra_blur)))
        else:
            glow_b = 0

        glow_rgb = _get_color_safe(w, "Glow_Color")
        layout_direction = str(w.get("Layout_Direction", "vertical")).lower()

        # Text 1/Text 2 내부 줄간격은 각 텍스트의 glow 상태를 따르고,
        # 두 블록 사이만 한쪽 glow 적용 시 약하게 보정한다.
        # - 둘 다 ON: 기존과 같은 block_spacing 유지
        # - 둘 다 OFF: 기존과 같은 block_spacing 유지
        # - 한쪽만 ON: glow가 반대쪽 생짜 글씨에 붙는 느낌만 완화
        effective_block_spacing = block_spacing
        if m1 and m2 and glow_enabled and (first_glow_enabled != second_glow_enabled):
            spacing_extra = int(round(max(0, glow_t) * 0.25 + max(0, glow_b) * 0.10))
            effective_block_spacing = max(0, block_spacing + spacing_extra)

        if layout_direction == "horizontal":
            content_w = (refw1 if m1 else 0) + (effective_block_spacing if (m1 and m2) else 0) + (refw2 if m2 else 0)
            content_w = max(1, int(content_w))
            total_h = max(bh1 if m1 else 0, bh2 if m2 else 0, 1)
            height_align_mode = str(w.get("Height_Align_Mode", "middle")).lower()
        else:
            content_w = max(refw1 if m1 else 0, refw2 if m2 else 0, 1)
            total_h = (bh1 if m1 else 0) + (effective_block_spacing if (m1 and m2) else 0) + (bh2 if m2 else 0)
            total_h = max(1, int(total_h))

        render_margin = int(max(o1_w, o2_w) + glow_t + (glow_b * 3) + MARGIN_SAFETY_PADDING)
        canvas_w = int(content_w + render_margin * 2)
        canvas_h = int(total_h + render_margin * 2)

        base_mask1 = Image.new("L", (canvas_w, canvas_h), 0)
        base_mask2 = Image.new("L", (canvas_w, canvas_h), 0)
        text_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        if layout_direction == "horizontal":
            def _aligned_y(block_h: int) -> int:
                if height_align_mode == "top":
                    return int(render_margin)
                if height_align_mode == "bottom":
                    return int(render_margin + (total_h - block_h))
                return int(render_margin + (total_h - block_h) // 2)

            content_x = render_margin
            if m1:
                y1 = _aligned_y(bh1)
                x1 = int(content_x + shiftx1)
                base_mask1.paste(m1, (x1, y1))
                text_layer.alpha_composite(t1, (x1, y1))
                content_x += refw1

            if m1 and m2:
                content_x += effective_block_spacing

            if m2:
                y2 = _aligned_y(bh2)
                x2 = int(content_x + shiftx2)
                base_mask2.paste(m2, (x2, y2))
                text_layer.alpha_composite(t2, (x2, y2))
        else:
            y = render_margin
            if m1:
                x1 = int(render_margin + shiftx1)
                base_mask1.paste(m1, (x1, y))
                text_layer.alpha_composite(t1, (x1, y))
                y += bh1

            if m1 and m2:
                y += effective_block_spacing

            if m2:
                x2 = int(render_margin + shiftx2)
                base_mask2.paste(m2, (x2, y))
                text_layer.alpha_composite(t2, (x2, y))

        outline_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        outline_mask1 = base_mask1
        if o1_en and o1_w > 0:
            outline_mask1 = dilate_mask(base_mask1, o1_w)
            ring1 = ImageChops.subtract(outline_mask1, base_mask1)
            ol1 = Image.new("RGBA", (canvas_w, canvas_h), o1_rgb + (0,))
            ol1.putalpha(ring1)
            outline_layer = Image.alpha_composite(outline_layer, ol1)

        outline_mask2 = base_mask2
        if o2_en and o2_w > 0:
            outline_mask2 = dilate_mask(base_mask2, o2_w)
            ring2 = ImageChops.subtract(outline_mask2, base_mask2)
            ol2 = Image.new("RGBA", (canvas_w, canvas_h), o2_rgb + (0,))
            ol2.putalpha(ring2)
            outline_layer = Image.alpha_composite(outline_layer, ol2)

        combined_glow_mask = Image.new("L", (canvas_w, canvas_h), 0)
        if first_glow_enabled:
            combined_glow_mask = ImageChops.lighter(combined_glow_mask, outline_mask1)
        if second_glow_enabled:
            combined_glow_mask = ImageChops.lighter(combined_glow_mask, outline_mask2)

        wm = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        if glow_enabled:
            expanded = dilate_mask(combined_glow_mask, glow_t)
            outside = ImageChops.subtract(expanded, combined_glow_mask)
            glow_mask = upgraded_glow_mask(outside, glow_b)

            gl = Image.new("RGBA", (canvas_w, canvas_h), glow_rgb + (0,))
            gl.putalpha(glow_mask)
            gl = reduce_opacity_rgba(gl, glow_opacity)
            wm = Image.alpha_composite(wm, gl)

        wm = Image.alpha_composite(wm, text_layer)
        wm = Image.alpha_composite(wm, outline_layer)
        wm = reduce_opacity_rgba(wm, watermark_opacity)

        if abs(rotation) > 1e-6:
            wm = wm.rotate(rotation, expand=True, resample=RESAMPLE_BICUBIC)
            max_dim = 4096
            if max(wm.size) > max_dim:
                ratio = max_dim / float(max(wm.size))
                wm = wm.resize(
                    (max(1, int(wm.width * ratio)), max(1, int(wm.height * ratio))),
                    RESAMPLE_LANCZOS
                )

        full_bb = wm.getbbox()
        if not full_bb:
            return None, None
        wm = wm.crop(full_bb)

        eff = float(max(0.0, min(1.0, glow_opacity * watermark_opacity)))
        th = auto_visible_threshold(glow_enabled, glow_b, glow_t, eff)
        align_bb = alpha_bbox_threshold(wm, th) or wm.getbbox()

        return wm, align_bb


    def add_watermark(self, image, **w):
        font_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fonts")
        self._ensure_fonts_exist_or_raise(font_dir)

        # Runtime safety (no UI change): clamp render font sizes to avoid huge canvases / OOM
        max_sz = int(getattr(self.__class__, "MAX_RENDER_FONT_SIZE", 128))
        try:
            w["First_Font_Size"] = max(1, min(int(w.get("First_Font_Size", 1)), max_sz))
            w["Second_Font_Size"] = max(1, min(int(w.get("Second_Font_Size", 1)), max_sz))
        except Exception:
            # If unexpected types slip in, keep original values (will likely error later with clearer message)
            pass

        f1_bold, f1_italic, f1_underline = parse_style_preset(w["First_Style"])
        f2_bold, f2_italic, f2_underline = parse_style_preset(w["Second_Style"])

        f1_name, f1_faux_bold, f1_faux_italic = self._resolve_font_and_faux(font_dir, w["First_Font"], f1_bold, f1_italic)
        f2_name, f2_faux_bold, f2_faux_italic = self._resolve_font_and_faux(font_dir, w["Second_Font"], f2_bold, f2_italic)

        f1 = self._load_font_strict(font_dir, f1_name, w["First_Font_Size"])
        f2 = self._load_font_strict(font_dir, f2_name, w["Second_Font_Size"])

        c1 = _get_color_safe(w, "First_Font_Color")
        c2 = _get_color_safe(w, "Second_Font_Color")

        layout_direction = str(w.get("Layout_Direction", "vertical")).lower()
        first_text = str(w.get("First_Text", ""))
        second_text = str(w.get("Second_Text", ""))
        first_exists = bool(first_text.strip())
        second_exists = bool(second_text.strip())

        common_ref_width = None
        if layout_direction == "vertical" and first_exists and second_exists:
            ref1 = measure_multiline_reference_width(first_text, f1)
            ref2 = measure_multiline_reference_width(second_text, f2)
            common_ref_width = max(ref1, ref2, 1)

        spacing1_params = _extract_spacing_params(w, "First")
        m1, t1, bw1, bh1, refw1, shiftx1 = build_block_assets(
            first_text, f1, c1,
            want_underline=f1_underline,
            faux_bold=f1_faux_bold,
            faux_italic=f1_faux_italic,
            spacing=_compute_multiline_spacing(**spacing1_params),
            shear_k=DEFAULT_ITALIC_SHEAR,
            text_align=str(w["First_Align"]),
            paragraph_width_override=common_ref_width if first_exists else None,
        )

        spacing2_params = _extract_spacing_params(w, "Second")
        m2, t2, bw2, bh2, refw2, shiftx2 = build_block_assets(
            second_text, f2, c2,
            want_underline=f2_underline,
            faux_bold=f2_faux_bold,
            faux_italic=f2_faux_italic,
            spacing=_compute_multiline_spacing(**spacing2_params),
            shear_k=DEFAULT_ITALIC_SHEAR,
            text_align=str(w["Second_Align"]),
            paragraph_width_override=common_ref_width if second_exists else None,
        )

        wm, align_bb = self._build_watermark_layer_and_align_bbox(
            w,
            (m1, t1, bw1, bh1, refw1, shiftx1),
            (m2, t2, bw2, bh2, refw2, shiftx2)
        )

        results = []
        for img_tensor in image:
            base_img = tensor2pil(img_tensor).convert("RGBA")
            iw, ih = base_img.size

            if wm is None or align_bb is None:
                results.append(torch.from_numpy(np.array(base_img.convert("RGB")).astype(np.float32) / 255.0).unsqueeze(0))
                continue

            ax0, ay0, ax1, ay1 = align_bb
            a_w = ax1 - ax0
            a_h = ay1 - ay0

            align = w["Align"]
            offset = int(w["Align_Offset"])
            offset_x = offset + int(w.get("Align_Offset_X", 0))
            offset_y = offset + int(w.get("Align_Offset_Y", 0))

            if "left" in align:
                px = offset_x - ax0
            elif "right" in align:
                px = (iw - offset_x) - ax1
            else:
                px = (iw - a_w) // 2 - ax0 + int(w.get("Align_Offset_X", 0))

            if "top" in align:
                py = offset_y - ay0
            elif "bottom" in align:
                py = (ih - offset_y) - ay1
            else:
                py = (ih - a_h) // 2 - ay0 + int(w.get("Align_Offset_Y", 0))

            out = base_img.copy()
            # v8: deferred compositing (single, correct alpha blend) — avoids paste()-style color dulling
            overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
            alpha_composite_clipped(overlay, wm, (int(px), int(py)))
            out = Image.alpha_composite(out, overlay)

            results.append(torch.from_numpy(np.array(out.convert("RGB")).astype(np.float32) / 255.0).unsqueeze(0))

        return (torch.cat(results, 0),)