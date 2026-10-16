"""Core-compatible image loader with an optional thumbnail browser frontend."""

import asyncio
import hashlib
import json
import os
import time
import uuid
from io import BytesIO
from urllib.parse import quote

import nodes

try:
    import folder_paths  # type: ignore
except Exception:  # pragma: no cover - always available inside ComfyUI
    folder_paths = None


# ---------------------------------------------------------------------------
# Recursive input listing
#
# Core's LoadImage.INPUT_TYPES() only lists files sitting directly in the
# input folder (os.listdir + os.path.isfile, no recursion), so anything in a
# subfolder never even reaches the combo's value list — the browse dialog's
# folder dropdown had nothing to show because the underlying data never
# included subfolder files at all. This walks the input directory
# recursively instead and reports "subfolder/name.ext" style relative paths,
# which core's own get_annotated_filepath()/LoadImage.load_image() already
# know how to resolve (it just does a plain path join, subfolders included).
# A short-lived cache avoids re-walking the whole tree on every object_info
# request (ComfyUI queries it fairly often), while still picking up new
# files within a couple of seconds or immediately via the dialog's Refresh
# button.
# ---------------------------------------------------------------------------

_EXCLUDED_DIR_NAMES = {"clipspace"}  # ComfyUI's internal mask-editor scratch folder
_MAX_SCANNED_FILES = 20000
_LIST_CACHE_TTL = 2.0
_scan_cache = {}  # cache_key -> {"time": float, "entries": [...]}


def _scan_dir_images(base_dir, cache_key):
    """Walk base_dir once and cache {path, mtime, size} per file for a couple
    of seconds, keyed by cache_key so the input folder and every registered
    external root each get their own short-lived cache. Both INPUT_TYPES
    (needs just the paths) and the /list route (needs mtime for the "date
    modified" sort) read from this same cache so a browse-dialog open only
    costs one directory walk per source, not two."""
    now = time.monotonic()
    try:
        directory_mtime_ns = os.stat(base_dir).st_mtime_ns if base_dir else None
    except OSError:
        directory_mtime_ns = None
    cached = _scan_cache.get(cache_key)
    if (
        cached is not None
        and (now - cached["time"]) < _LIST_CACHE_TTL
        and cached.get("directory_mtime_ns") == directory_mtime_ns
    ):
        return cached["entries"]

    entries = []
    if base_dir and os.path.isdir(base_dir):
        done = False
        for root, dirs, names in os.walk(base_dir, followlinks=False):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in _EXCLUDED_DIR_NAMES]
            rel_root = os.path.relpath(root, base_dir)
            for name in names:
                if name.startswith("."):
                    continue
                rel_path = name if rel_root in (".", "") else f"{rel_root}/{name}"
                rel_path = rel_path.replace(os.sep, "/")
                try:
                    stat = os.stat(os.path.join(root, name))
                except OSError:
                    continue
                entries.append({"path": rel_path, "mtime": stat.st_mtime, "size": stat.st_size})
                if len(entries) >= _MAX_SCANNED_FILES:
                    done = True
                    break
            if done:
                break

        try:
            keep = set(folder_paths.filter_files_content_types([e["path"] for e in entries], ["image"]))
            entries = [e for e in entries if e["path"] in keep]
        except Exception:
            pass  # older ComfyUI versions without this helper: keep the full list
        entries.sort(key=lambda e: e["path"])

    _scan_cache[cache_key] = {
        "time": now,
        "directory_mtime_ns": directory_mtime_ns,
        "entries": entries,
    }
    return entries


def _scan_input_images():
    try:
        input_dir = folder_paths.get_input_directory() if folder_paths else None
    except Exception:
        input_dir = None
    return _scan_dir_images(input_dir, "__input__")


def _list_input_images_recursive():
    return [entry["path"] for entry in _scan_input_images()]


# ---------------------------------------------------------------------------
# External roots (drives/folders outside the ComfyUI input directory)
#
# Core's node-loading pipeline (INPUT_TYPES combo, get_annotated_filepath,
# the /view endpoint) all assume "input", "output" or "temp" — there is no
# concept of an arbitrary folder elsewhere on disk. Rather than touch any of
# that shared machinery (which every other LoadImage-derived node in this
# ComfyUI install also relies on), this node keeps its own small persisted
# registry of user-approved external folders and represents a file from one
# of them with a self-describing combo value: "ext:<root_id>:<rel/path>".
# Everything that needs to resolve one of these values — the thumbnail
# route, load_image(), IS_CHANGED(), VALIDATE_INPUTS() — goes through
# _resolve_external_path(), which re-validates the value against the
# *current* registry and refuses anything that resolves outside the
# registered root, the same containment check core's own /view uses for
# input/output/temp.
# ---------------------------------------------------------------------------

_EXTERNAL_ROOTS_FILENAME = "ultra_tools_image_load_roots.json"


def _external_roots_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), _EXTERNAL_ROOTS_FILENAME)


def _load_external_roots():
    path = _external_roots_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    roots = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        root_id = str(entry.get("id") or "").strip()
        root_path = str(entry.get("path") or "").strip()
        if not root_id or not root_path:
            continue
        label = str(entry.get("label") or "").strip() or os.path.basename(root_path.rstrip("/\\")) or root_path
        roots.append({"id": root_id, "path": root_path, "label": label})
    return roots


def _save_external_roots(roots):
    path = _external_roots_path()
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(roots, fh, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _external_root_by_id(root_id):
    for entry in _load_external_roots():
        if entry["id"] == root_id:
            return entry
    return None


def _add_external_root(raw_path, label):
    if not raw_path or not isinstance(raw_path, str):
        return None, "경로를 입력해 주세요."
    candidate = os.path.abspath(raw_path.strip())
    if not os.path.isdir(candidate):
        return None, f"폴더를 찾을 수 없습니다: {candidate}"
    roots = _load_external_roots()
    for entry in roots:
        try:
            same = os.path.normcase(os.path.abspath(entry["path"])) == os.path.normcase(candidate)
        except Exception:
            same = entry["path"] == candidate
        if same:
            return entry, None  # already registered — treat as success, no duplicate
    entry = {
        "id": uuid.uuid4().hex[:10],
        "path": candidate,
        "label": (label or "").strip() or os.path.basename(candidate.rstrip("/\\")) or candidate,
    }
    roots.append(entry)
    if not _save_external_roots(roots):
        return None, "설정 저장에 실패했습니다."
    _scan_cache.pop(entry["id"], None)
    return entry, None


def _remove_external_root(root_id):
    roots = _load_external_roots()
    remaining = [entry for entry in roots if entry["id"] != root_id]
    if len(remaining) == len(roots):
        return False
    if not _save_external_roots(remaining):
        return False
    _scan_cache.pop(root_id, None)
    return True


def _scan_external_images(root_entry):
    return _scan_dir_images(root_entry["path"], root_entry["id"])


def _external_combo_values():
    """Self-describing 'ext:<root_id>:<rel/path>' combo values for every
    image under every registered external root.

    IMPORTANT: this must stay a flat list of strings, not a {value: label}
    dict. ComfyUI's frontend only recognises a combo widget when
    INPUT_TYPES()'s type field is a plain Array — handing it a dict there
    (even though our own browse-dialog JS is happy to read one) makes the
    frontend fall back to treating "image" as an unrecognised input type,
    which drops the widget (and this node's browse button with it) entirely
    and leaves just a bare input socket. Friendly "RootLabel/relpath"
    display text is instead built client-side in ultra_image_load.js from
    the separate /ultra_tools/image_load/roots list, purely for the browse
    dialog's own UI — it never needs to touch the combo value itself."""
    return [
        f"ext:{root_entry['id']}:{item['path']}"
        for root_entry in _load_external_roots()
        for item in _scan_external_images(root_entry)
    ]


def _resolve_external_path(value):
    """Parse 'ext:<root_id>:<rel/path>', re-validate it against the current
    registry, and return an absolute path — or None if the value isn't an
    external reference, the root is no longer registered, or the resolved
    path would escape the registered root directory."""
    if not isinstance(value, str) or not value.startswith("ext:"):
        return None
    rest = value[len("ext:"):]
    root_id, sep, rel_path = rest.partition(":")
    if not sep or not root_id or not rel_path:
        return None
    root_entry = _external_root_by_id(root_id)
    if not root_entry:
        return None
    root_dir = os.path.abspath(root_entry["path"])
    rel_path = rel_path.replace("\\", "/")
    segments = [seg for seg in rel_path.split("/") if seg not in ("", ".")]
    if not segments or ".." in segments:
        return None
    full_path = os.path.abspath(os.path.join(root_dir, *segments))
    try:
        if os.path.commonpath((full_path, root_dir)) != root_dir:
            return None
    except ValueError:  # e.g. different drive letters on Windows
        return None
    return full_path


class _ExternalPathContext:
    """Lets core's own LoadImage.load_image() / IS_CHANGED() /
    VALIDATE_INPUTS() run completely unmodified against an external file, by
    momentarily teaching folder_paths how to resolve this one combo value.
    A normal input-relative value resolves to None here and the two
    folder_paths functions are left untouched, so nothing changes for the
    existing input-folder behaviour. The patch only ever lives for the
    duration of a single call (the `with` block), then core's real
    functions are restored immediately — no other node or request can
    observe it."""

    def __init__(self, value):
        self._path = _resolve_external_path(value) if isinstance(value, str) else None
        self._orig_get = None
        self._orig_exists = None

    def __enter__(self):
        if self._path is None or not folder_paths:
            return self
        self._orig_get = folder_paths.get_annotated_filepath
        self._orig_exists = folder_paths.exists_annotated_filepath
        path = self._path
        folder_paths.get_annotated_filepath = lambda *_a, **_k: path
        folder_paths.exists_annotated_filepath = lambda *_a, **_k: os.path.isfile(path)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._orig_get is not None:
            folder_paths.get_annotated_filepath = self._orig_get
        if self._orig_exists is not None:
            folder_paths.exists_annotated_filepath = self._orig_exists
        return False


class UltraToolsImageLoad(nodes.LoadImage):
    """Use ComfyUI's installed LoadImage implementation, except INPUT_TYPES is
    overridden to list the input folder recursively (subfolders included)
    plus any registered external folders, and load_image()/IS_CHANGED()/
    VALIDATE_INPUTS() are overridden just enough to resolve an external
    combo value before handing off to core's own implementation."""

    CATEGORY = "Ultra Tools"
    # Core LoadImage declares ESSENTIALS_CATEGORY = "Basics". ComfyUI 0.40 sends
    # that to the frontend, which would then list this custom node as a Comfy
    # Core "Essentials" node instead of under the Ultra Tools pack. Override the
    # inherited value so the node is classified as a normal custom node again.
    ESSENTIALS_CATEGORY = None
    SEARCH_ALIASES = [
        *getattr(nodes.LoadImage, "SEARCH_ALIASES", []),
        "ultra tools image load",
        "browse input images",
        "thumbnail image loader",
        "input image browser",
        "이미지 로드",
        "input 이미지",
        "이미지 썸네일",
    ]

    @classmethod
    def INPUT_TYPES(cls):
        # Plain array (see _external_combo_values' docstring for why this
        # can't be a {value: label} dict): input-folder paths first, then
        # any registered external-folder paths appended after.
        values = _list_input_images_recursive() + _external_combo_values()
        if not values:
            # Input dir couldn't be resolved for some reason — fall back to
            # core's own (flat) behaviour rather than an empty combo.
            return super().INPUT_TYPES()
        return {"required": {"image": (values, {"image_upload": True})}}

    def load_image(self, image):
        with _ExternalPathContext(image):
            return super().load_image(image)

    @classmethod
    def IS_CHANGED(cls, image):
        base = getattr(super(), "IS_CHANGED", None)
        with _ExternalPathContext(image):
            return base(image) if base else image

    @classmethod
    def VALIDATE_INPUTS(cls, image):
        base = getattr(super(), "VALIDATE_INPUTS", None)
        with _ExternalPathContext(image):
            return base(image) if base else True


NODE_CLASS_MAPPINGS = {
    "UltraToolsImageLoad": UltraToolsImageLoad,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UltraToolsImageLoad": "Ultra Tools Image Load",
}


# ---------------------------------------------------------------------------
# Thumbnail API
#
# ComfyUI core's "/view" endpoint has no resize/thumbnail option: every request
# decodes the *original* file and (optionally) re-encodes it, still at full
# resolution, even when the caller only wants a ~150px browser tile. The
# browse dialog used to call "/view" directly for every tile, so opening it
# with a large input folder (or a folder with big/high-res files) meant dozens
# of full-resolution PIL decodes firing at once, which is slow both to
# receive (large payloads) and to generate (server-side CPU-bound work).
# This route generates a small, disk-cached WEBP preview instead, and reports
# the source image's real dimensions via a response header so the frontend
# doesn't need a second full-resolution request just to show "1920 x 1080".
# ---------------------------------------------------------------------------

_THUMB_CACHE_ENTRY_LIMIT = 600
_THUMB_MAX_DIMENSION_CAP = 1600


def _is_direct_image_navigation(request):
    """Return whether a thumbnail URL is opening as a browser page.

    Thumbnail tiles deliberately use a small cached WEBP. Browser commands
    such as "Open image in new tab" reuse that URL but request it as a
    top-level navigation, which lets the route return the untouched source
    file without slowing ordinary thumbnail loading.
    """
    headers = getattr(request, "headers", {})
    destination = str(headers.get("Sec-Fetch-Dest", "")).strip().lower()
    mode = str(headers.get("Sec-Fetch-Mode", "")).strip().lower()
    accept = str(headers.get("Accept", "")).lower()
    return destination == "document" or mode == "navigate" or "text/html" in accept


def _original_content_disposition(source_path, download=False):
    if not download:
        return "inline"
    filename = os.path.basename(source_path)
    ascii_name = "".join(
        char if 32 <= ord(char) < 127 and char not in {'"', "\\"} else "_"
        for char in filename
    ) or "image"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def _guess_content_type(path):
    import mimetypes
    content_type, _ = mimetypes.guess_type(path, strict=False)
    return content_type or "application/octet-stream"


def _is_dangerous_content_type(content_type):
    """Mirror core's /view hardening (folder_paths.is_dangerous_content_type):
    types a browser may execute/render as a document (SVG, HTML, XML...) are
    never served inline."""
    try:
        checker = getattr(folder_paths, "is_dangerous_content_type", None) if folder_paths else None
        if callable(checker):
            return bool(checker(content_type))
    except Exception:
        pass
    normalized = str(content_type or "").split(";", 1)[0].strip().lower()
    return (
        normalized in {"text/html", "application/xhtml+xml", "image/svg+xml", "text/javascript",
                       "application/javascript", "text/css", "application/xml", "text/xml"}
        or normalized.endswith("+xml") or normalized.endswith("/xml")
    )


def _is_safe_raster_image(path):
    content_type = _guess_content_type(path)
    return content_type.startswith("image/") and not _is_dangerous_content_type(content_type)


def _file_response(web, source_path, disposition, extra_headers=None):
    """FileResponse that never lets an executable/document type render inline."""
    headers = {
        "Cache-Control": "private, max-age=0",
        "X-Content-Type-Options": "nosniff",
    }
    if extra_headers:
        headers.update(extra_headers)
    content_type = _guess_content_type(source_path)
    if _is_dangerous_content_type(content_type):
        headers["Content-Disposition"] = _original_content_disposition(source_path, True)
        headers["Content-Type"] = "application/octet-stream"
    else:
        headers["Content-Disposition"] = disposition
    return web.FileResponse(path=source_path, headers=headers)


def _thumbnail_cache_dir():
    base = None
    try:
        if folder_paths:
            base = folder_paths.get_temp_directory()
    except Exception:
        base = None
    base = base or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
    path = os.path.join(base, "ultra_tools_image_load_thumbs")
    os.makedirs(path, exist_ok=True)
    return path


def _resolve_source_path(filename, subfolder, type_, root_id=None, raw_path=None):
    """Mirrors core's /view path validation so we only ever read from a
    recognised ComfyUI directory (input/output/temp), a registered external
    root, or — for the folder-browse preview only — an exact file the
    person can already see listed via /browse_dirs itself."""
    if type_ == "path":
        # Folder-browse preview: the caller already saw this exact path in
        # a /browse_dirs listing (that route is a full local directory
        # browser by design), so showing its thumbnail here exposes
        # nothing new — this just confirms it resolves to a real file, not
        # a symlink pointing somewhere unexpected.
        if not raw_path:
            return None
        candidate = os.path.abspath(raw_path)
        # Only raster image files may be read this way (this route backs the
        # folder-browse image preview, nothing else). Without this check any
        # file on disk could be downloaded through ?type=path&path=...
        if not os.path.isfile(candidate) or not _is_safe_raster_image(candidate):
            return None
        return candidate

    if not filename:
        return None
    if filename.startswith("/") or ".." in filename:
        return None

    if type_ == "external":
        root_entry = _external_root_by_id(root_id) if root_id else None
        if not root_entry:
            return None
        rel_path = f"{subfolder}/{filename}" if subfolder else filename
        return _resolve_external_path(f"ext:{root_entry['id']}:{rel_path}")

    if not folder_paths:
        return None
    try:
        base_dir = folder_paths.get_directory_by_type(type_ or "input")
    except Exception:
        base_dir = None
    if not base_dir:
        return None
    base_dir = os.path.abspath(base_dir)
    filename = os.path.basename(filename)
    full_dir = os.path.abspath(os.path.join(base_dir, subfolder) if subfolder else base_dir)
    try:
        if os.path.commonpath((full_dir, base_dir)) != base_dir:
            return None
    except ValueError:
        return None
    return os.path.join(full_dir, filename)


def _resolve_deletable_image_value(value):
    """Resolve a listed input or registered-external image for deletion."""
    if not isinstance(value, str):
        return None
    raw = value.strip().replace("\\", "/")
    if not raw:
        return None
    if raw.startswith("ext:"):
        path = _resolve_external_path(raw)
        return path if path and os.path.isfile(path) else None
    type_ = "input"
    lowered = raw.lower()
    for annotated_type in ("input", "output", "temp"):
        suffix = f" [{annotated_type}]"
        if lowered.endswith(suffix):
            type_ = annotated_type
            raw = raw[: -len(suffix)].strip()
            break
    if type_ != "input" or not raw or raw.startswith("/"):
        return None
    parts = [part for part in raw.split("/") if part not in ("", ".")]
    if not parts or ".." in parts:
        return None
    filename = parts[-1]
    subfolder = "/".join(parts[:-1])
    return _resolve_source_path(filename, subfolder, "input")


def _evict_old_cache_entries(cache_dir):
    try:
        names = os.listdir(cache_dir)
    except Exception:
        return
    # Two files per cached thumbnail (.webp + .meta); keep roughly the
    # newest _THUMB_CACHE_ENTRY_LIMIT thumbnails and drop the rest.
    if len(names) <= _THUMB_CACHE_ENTRY_LIMIT * 2:
        return
    paths = [os.path.join(cache_dir, name) for name in names]
    try:
        paths.sort(key=lambda p: os.path.getmtime(p))
    except Exception:
        return
    for path in paths[: len(paths) - _THUMB_CACHE_ENTRY_LIMIT * 2]:
        try:
            os.remove(path)
        except OSError:
            pass


def _read_cached_thumbnail(cache_path, meta_path):
    """Pure/sync: cache hit path. Returns (data, width, height) or None."""
    if not (os.path.isfile(cache_path) and os.path.isfile(meta_path)):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            orig_w, orig_h = fh.read().strip().split("x")
        with open(cache_path, "rb") as fh:
            data = fh.read()
        return data, orig_w, orig_h
    except Exception:
        return None  # fall through and regenerate


def _generate_thumbnail(source_path, max_dim, cache_dir, cache_path, meta_path):
    """Pure/sync: PIL decode + resize + encode + disk-cache write. This is the
    CPU-bound part, meant to be run off the event loop via run_in_executor —
    doing this inline in an async route handler would stall every other
    request ComfyUI is serving (queue status, websocket, etc.) for as long as
    the decode takes."""
    from PIL import Image  # imported lazily so module import never needs PIL

    with Image.open(source_path) as img:
        orig_w, orig_h = img.width, img.height
        # For JPEG (and a few other formats), draft() tells libjpeg to decode
        # directly at a reduced DCT scale (1/2, 1/4, 1/8) instead of decoding
        # the full original resolution just to immediately shrink it — much
        # less CPU and peak memory for large source photos. No-op for
        # formats that don't support it (e.g. PNG), and img.load() below
        # still produces a correctly-sized/decoded image either way.
        try:
            img.draft("RGB", (max_dim, max_dim))
        except Exception:
            pass
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
        # No extra .copy() here: `img` is a local we don't reuse afterward,
        # so thumbnail() can safely resize it in place instead of shrinking
        # a second full-resolution duplicate first.
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="WEBP", quality=80, method=4)
        data = buf.getvalue()

    try:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_path, "wb") as fh:
            fh.write(data)
        with open(meta_path, "w", encoding="utf-8") as fh:
            fh.write(f"{orig_w}x{orig_h}")
        _evict_old_cache_entries(cache_dir)
    except Exception:
        pass

    return data, str(orig_w), str(orig_h)


def _build_thumbnail(source_path, source_mtime, max_dim):
    """Pure/sync: the full cache-hit-or-generate flow for one thumbnail
    request. Runs entirely inside a worker thread (see register routes
    below) so PIL work and cache-file I/O never block the event loop."""
    cache_dir = _thumbnail_cache_dir()
    cache_key = hashlib.sha1(f"{source_path}|{source_mtime}|{max_dim}".encode("utf-8")).hexdigest()
    cache_path = os.path.join(cache_dir, f"{cache_key}.webp")
    meta_path = cache_path + ".meta"

    cached = _read_cached_thumbnail(cache_path, meta_path)
    if cached is not None:
        return cached
    return _generate_thumbnail(source_path, max_dim, cache_dir, cache_path, meta_path)


def _list_drives():
    """Top-level entries for the folder browser when no path has been
    navigated into yet: drive letters on Windows, or the filesystem root
    plus the user's home and common mount points elsewhere. This is the
    "하드 드라이브 리스트" starting point the browse UI opens on."""
    import platform
    import string

    if platform.system() == "Windows":
        drives = []
        try:
            import ctypes

            bitmask = ctypes.windll.kernel32.GetLogicalDrives()  # type: ignore[attr-defined]
            for index, letter in enumerate(string.ascii_uppercase):
                if bitmask & (1 << index):
                    drive = f"{letter}:\\"
                    drives.append({"name": drive, "path": drive})
        except Exception:
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append({"name": drive, "path": drive})
        return drives

    entries = [{"name": "/", "path": "/"}]
    home = os.path.expanduser("~")
    if home and os.path.isdir(home) and home != "/":
        entries.append({"name": f"Home ({home})", "path": home})
    for mount_root in ("/mnt", "/media", "/Volumes"):
        if not os.path.isdir(mount_root):
            continue
        try:
            for name in sorted(os.listdir(mount_root), key=str.casefold):
                full = os.path.join(mount_root, name)
                if os.path.isdir(full):
                    entries.append({"name": full, "path": full})
        except Exception:
            pass
    return entries


_MAX_BROWSE_ENTRIES = 3000
_MAX_BROWSE_IMAGES = 60


def _list_subdirectories(path):
    """One level of the folder browser: immediate subfolders of `path` (to
    navigate further into), up to a handful of the folder's own image files
    so the person can see whether this looks like the right folder before
    committing to "이 폴더 추가", and the parent path for the "위로" button.
    Returns (abs_path, parent_or_None, folders, images) or raises
    ValueError/OSError, which the route below turns into a 400/404
    response."""
    if not path or not os.path.isdir(path):
        raise ValueError("폴더를 찾을 수 없습니다.")
    abs_path = os.path.abspath(path)
    parent = os.path.dirname(abs_path.rstrip("/\\"))
    if not parent or os.path.normcase(parent) == os.path.normcase(abs_path):
        parent = None  # already at a drive root (Windows) or "/" (POSIX)

    folder_names = []
    file_names = []
    with os.scandir(abs_path) as scan:
        for count, entry in enumerate(scan, start=1):
            if count > _MAX_BROWSE_ENTRIES:
                break
            try:
                if entry.name.startswith("."):
                    continue
                if entry.is_dir(follow_symlinks=True):
                    folder_names.append(entry.name)
                elif entry.is_file(follow_symlinks=True):
                    file_names.append(entry.name)
            except OSError:
                continue
    folder_names.sort(key=str.casefold)
    folders = [{"name": name, "path": os.path.join(abs_path, name)} for name in folder_names]

    try:
        keep = set(folder_paths.filter_files_content_types(file_names, ["image"])) if folder_paths else set()
    except Exception:
        keep = set()  # older ComfyUI versions without this helper: skip the preview rather than guess
    image_names = sorted((name for name in file_names if name in keep), key=str.casefold)[:_MAX_BROWSE_IMAGES]
    images = [{"name": name, "path": os.path.join(abs_path, name)} for name in image_names]

    return abs_path, parent, folders, images


def register_image_load_routes():
    """Register the resized/cached thumbnail endpoint used by the browse
    dialog, plus the small routes that let it list/add/remove registered
    external (non-input) folders."""
    try:
        from aiohttp import web  # type: ignore
        from server import PromptServer  # type: ignore
        import PIL  # noqa: F401 - just confirming Pillow is importable
    except Exception:
        return False

    try:
        prompt_server = PromptServer.instance
        routes = prompt_server.routes
    except Exception:
        return False

    marker = "_ultra_tools_image_load_thumb_routes_v3"
    if getattr(prompt_server, marker, False):
        return True

    @routes.get("/ultra_tools/image_load/list")
    async def _list_route(request):
        del request
        # Backs the sort feature (date modified needs mtime, which isn't
        # available anywhere in the plain combo value list). Combines the
        # input folder with every registered external root so the frontend
        # only ever needs this one call, regardless of source.
        files = _scan_input_images() + [
            {"path": f"ext:{root_entry['id']}:{item['path']}", "mtime": item["mtime"], "size": item["size"]}
            for root_entry in _load_external_roots()
            for item in _scan_external_images(root_entry)
        ]
        return web.json_response({"files": files})

    @routes.get("/ultra_tools/image_load/roots")
    async def _roots_list_route(request):
        del request
        return web.json_response({"roots": _load_external_roots()})

    @routes.post("/ultra_tools/image_load/roots")
    async def _roots_add_route(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        entry, error = _add_external_root(body.get("path"), body.get("label"))
        if error:
            return web.json_response({"error": error}, status=400)
        return web.json_response({"root": entry})

    @routes.delete("/ultra_tools/image_load/roots")
    async def _roots_remove_route(request):
        root_id = request.rel_url.query.get("id", "")
        if not root_id or not _remove_external_root(root_id):
            return web.json_response({"error": "폴더를 찾을 수 없습니다."}, status=404)
        return web.json_response({"ok": True})

    @routes.post("/ultra_tools/image_load/delete_images")
    async def _delete_images_route(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        values = body.get("images") if isinstance(body, dict) else None
        if not isinstance(values, list) or not values or len(values) > 500:
            return web.json_response({"error": "삭제할 이미지 목록이 올바르지 않습니다."}, status=400)

        # Re-scan immediately and accept only images currently surfaced by
        # this browser: ComfyUI input plus registered external roots. This
        # prevents an arbitrary local path from being submitted directly.
        _scan_cache.clear()
        allowed = set(_list_input_images_recursive()) | set(_external_combo_values())
        deleted = []
        failed = []
        seen = set()
        for raw_value in values:
            value = str(raw_value or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            if value not in allowed:
                failed.append({"image": value, "reason": "not_deletable"})
                continue
            path = _resolve_deletable_image_value(value)
            if not path or not os.path.isfile(path):
                failed.append({"image": value, "reason": "not_found"})
                continue
            try:
                os.remove(path)
                deleted.append(value)
            except OSError:
                failed.append({"image": value, "reason": "delete_failed"})

        _scan_cache.clear()
        status = 200 if deleted or not failed else 400
        return web.json_response({"deleted": deleted, "failed": failed}, status=status)

    @routes.get("/ultra_tools/image_load/browse_dirs")
    async def _browse_dirs_route(request):
        # Backs the "+ 폴더 추가" folder browser: no path -> the drive/root
        # list; a path -> that folder's immediate subfolders (to navigate
        # further) plus a preview of its own image files, and its parent,
        # so the frontend can click its way down (and back up) a real
        # directory tree — and see whether a folder actually has images in
        # it before committing — entirely through this one route, with no
        # browser file/folder picker involved at any point.
        path = request.rel_url.query.get("path", "").strip()
        if not path:
            return web.json_response({"path": "", "parent": None, "entries": _list_drives(), "images": []})
        try:
            abs_path, parent, entries, images = await asyncio.get_running_loop().run_in_executor(
                None, _list_subdirectories, path
            )
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=404)
        except OSError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        return web.json_response({"path": abs_path, "parent": parent, "entries": entries, "images": images})

    @routes.get("/ultra_tools/image_load/original")
    async def _original_route(request):
        filename = request.rel_url.query.get("filename", "")
        subfolder = request.rel_url.query.get("subfolder", "")
        type_ = request.rel_url.query.get("type", "input")
        root_id = request.rel_url.query.get("root", "")
        raw_path = request.rel_url.query.get("path", "")
        source_path = _resolve_source_path(filename, subfolder, type_, root_id, raw_path)
        if not source_path or not os.path.isfile(source_path):
            return web.Response(status=404)
        download = request.rel_url.query.get("download", "") == "1"
        return _file_response(web, source_path, _original_content_disposition(source_path, download))

    @routes.get("/ultra_tools/image_load/thumbnail")
    async def _thumbnail_route(request):
        filename = request.rel_url.query.get("filename", "")
        subfolder = request.rel_url.query.get("subfolder", "")
        type_ = request.rel_url.query.get("type", "input")
        root_id = request.rel_url.query.get("root", "")
        raw_path = request.rel_url.query.get("path", "")
        try:
            max_dim = int(request.rel_url.query.get("max", 320))
        except (TypeError, ValueError):
            max_dim = 320
        max_dim = max(32, min(max_dim, _THUMB_MAX_DIMENSION_CAP))

        source_path = _resolve_source_path(filename, subfolder, type_, root_id, raw_path)
        if not source_path or not os.path.isfile(source_path):
            return web.Response(status=404)

        # Keep the resized WEBP for embedded tiles, but make the browser's
        # native "Open image in new tab" command show the original-resolution
        # file. FileResponse streams it without a PIL decode/re-encode and also
        # works for files under a registered external folder.
        if _is_direct_image_navigation(request):
            return _file_response(
                web,
                source_path,
                "inline",
                {"Vary": "Sec-Fetch-Dest, Sec-Fetch-Mode, Accept"},
            )

        try:
            source_mtime = os.path.getmtime(source_path)
        except OSError:
            return web.Response(status=404)

        try:
            loop = asyncio.get_running_loop()
            data, orig_w, orig_h = await loop.run_in_executor(
                None, _build_thumbnail, source_path, source_mtime, max_dim
            )
        except Exception as exc:
            return web.Response(status=500, text=f"thumbnail generation failed: {exc}")

        return web.Response(
            body=data,
            content_type="image/webp",
            headers={
                "X-Ultra-Original-Width": orig_w,
                "X-Ultra-Original-Height": orig_h,
                # The URL itself (filename/subfolder/type/max) doesn't change
                # when a file is edited in place — only the disk cache key
                # does, via mtime. A long Cache-Control would let the browser
                # keep serving old bytes for that unchanged URL even after
                # the source file (and our disk cache) has moved on, so this
                # is kept short rather than the usual long-lived value.
                "Cache-Control": "public, max-age=60",
                # A direct visit to the same URL returns the original file;
                # keep that response separate from this cached thumbnail.
                "Vary": "Sec-Fetch-Dest, Sec-Fetch-Mode, Accept",
            },
        )

    _install_external_view_middleware(prompt_server, web)

    setattr(prompt_server, marker, True)
    return True


def _external_value_from_view_query(query):
    """Rebuild the 'ext:<root>:<rel/path>' combo value from the query the
    frontend generates for core's /view endpoint. The frontend splits a combo
    value on '/' into subfolder + filename, so 'ext:abc:dir/a.png' arrives as
    subfolder='ext:abc:dir', filename='a.png' and 'ext:abc:a.png' arrives as
    filename='ext:abc:a.png'."""
    if str(query.get("type", "input") or "input") != "input":
        return None
    filename = str(query.get("filename", "") or "")
    subfolder = str(query.get("subfolder", "") or "").replace("\\", "/").strip("/")
    if subfolder.startswith("ext:"):
        return f"{subfolder}/{filename}" if filename else None
    if filename.startswith("ext:") and not subfolder:
        return filename
    return None


def _install_external_view_middleware(prompt_server, web):
    """Make core's /view endpoint able to show images from registered external
    folders. Nodes 2.0 (and the core upload widget in classic mode after a
    workflow reload) always builds node previews and dropdown thumbnails from
    /view?filename=...&subfolder=...&type=input, which knows nothing about
    'ext:' values and answered 'Image failed to load'. Only requests whose
    filename/subfolder start with 'ext:' are touched; everything else goes
    straight to core unchanged."""
    marker = "_ultra_tools_image_load_view_middleware_v1"
    if getattr(prompt_server, marker, False):
        return
    app = getattr(prompt_server, "app", None)
    middlewares = getattr(app, "middlewares", None)
    if middlewares is None or getattr(middlewares, "frozen", False):
        return

    @web.middleware
    async def _ultra_external_view(request, handler):
        if request.method in ("GET", "HEAD") and request.path in ("/view", "/api/view"):
            value = _external_value_from_view_query(request.rel_url.query)
            if value:
                input_dir = None
                try:
                    input_dir = folder_paths.get_input_directory() if folder_paths else None
                except Exception:
                    input_dir = None
                # A real input file with this literal name keeps core behaviour.
                literal = os.path.join(input_dir, value) if input_dir else None
                if not (literal and os.path.isfile(literal)):
                    path = _resolve_external_path(value)
                    if not path or not os.path.isfile(path) or not _is_safe_raster_image(path):
                        return web.Response(status=404)
                    return _file_response(web, path, "inline")
        return await handler(request)

    try:
        middlewares.append(_ultra_external_view)
        setattr(prompt_server, marker, True)
    except Exception:
        pass
