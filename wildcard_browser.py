import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Dict, List, Optional, Sequence, Set, Tuple

import server
from aiohttp import web

try:
    from .request_guard import guard_request, register_token_route
except ImportError:  # pragma: no cover - module loaded outside the package
    from request_guard import guard_request, register_token_route


_SCAN_WORKERS = 2
_SCAN_EXECUTOR = ThreadPoolExecutor(
    max_workers=_SCAN_WORKERS,
    thread_name_prefix="UltraWildcardBrowser",
)
_SCAN_SLOTS = asyncio.Semaphore(_SCAN_WORKERS)


async def _run_filesystem_call(function, *args):
    """Run blocking filesystem work without allowing canceled requests to flood the pool."""
    async with _SCAN_SLOTS:
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(_SCAN_EXECUTOR, partial(function, *args))
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError:
            # OS filesystem calls cannot be force-canceled. Keep the slot occupied until
            # the running call finishes so repeated browser cancellations do not build an
            # unbounded executor queue.
            try:
                await asyncio.shield(future)
            finally:
                raise


class UltraWildcardBrowser:
    """ComfyUI helper node for browsing wildcard folders and copying wildcard calls."""

    DEFAULT_WILDCARDS_PATH = r"F:\models\wildcards"
    ROOT_FOLDER_LABEL = "[Root]"
    LEGACY_ROOT_FOLDER_LABELS = frozenset({"[최상위]"})
    ROOT_FOLDER_ESCAPE_PREFIX = "./"
    SUPPORTED_EXTENSIONS = (".txt", ".yaml", ".yml", ".json")
    EXTENSION_PRIORITY = {ext: index for index, ext in enumerate(SUPPORTED_EXTENSIONS)}
    MAX_ROOT_PATH_LENGTH = 4096
    MAX_FOLDER_VALUE_LENGTH = 2048
    MAX_NAVIGATION_DEPTH = 64
    MAX_ROOT_FOLDERS = 5000
    MAX_VISIBLE_ENTRIES = 10000
    MAX_SCANNED_ENTRIES = 50000

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wildcards_path": ("STRING", {"default": cls.DEFAULT_WILDCARDS_PATH}),
                "folder": ([cls.ROOT_FOLDER_LABEL], {"default": cls.ROOT_FOLDER_LABEL}),
                "file_list": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, folder):
        # The frontend populates this combo dynamically.
        return True

    RETURN_TYPES = ()
    FUNCTION = "execute"
    CATEGORY = "Ultra Tools"

    def execute(self, wildcards_path, folder, file_list):
        # UI-only node: never fail an unrelated prompt run because a drive is offline.
        return ()

    @classmethod
    def _resolve_wildcards_path(cls, wildcards_path=None) -> Tuple[str, bool]:
        raw = "" if wildcards_path is None else str(wildcards_path).strip().strip('"').strip("'")
        if "\x00" in raw:
            raise ValueError("[Ultra Tools Wildcard Browser] 경로에 NUL 문자를 사용할 수 없습니다.")
        if len(raw) > cls.MAX_ROOT_PATH_LENGTH:
            raise ValueError("[Ultra Tools Wildcard Browser] 와일드카드 루트 경로가 너무 깁니다.")

        defaulted = not raw
        if defaulted:
            raw = cls.DEFAULT_WILDCARDS_PATH
        return os.path.normpath(os.path.expandvars(os.path.expanduser(raw))), defaulted

    @classmethod
    def _decode_folder_value(cls, folder_name) -> str:
        raw = str(folder_name or "").strip()
        if "\x00" in raw:
            raise ValueError("[Ultra Tools Wildcard Browser] 폴더 경로에 NUL 문자를 사용할 수 없습니다.")
        if len(raw) > cls.MAX_FOLDER_VALUE_LENGTH:
            raise ValueError("[Ultra Tools Wildcard Browser] 폴더 경로가 너무 깁니다.")

        if raw.startswith(cls.ROOT_FOLDER_ESCAPE_PREFIX):
            return raw[len(cls.ROOT_FOLDER_ESCAPE_PREFIX):]
        root_labels = {cls.ROOT_FOLDER_LABEL, *cls.LEGACY_ROOT_FOLDER_LABELS}
        return "" if raw in root_labels else raw

    @classmethod
    def _encode_folder_value(cls, normalized_folder: str) -> str:
        root_labels = {cls.ROOT_FOLDER_LABEL, *cls.LEGACY_ROOT_FOLDER_LABELS}
        if normalized_folder in root_labels:
            return f"{cls.ROOT_FOLDER_ESCAPE_PREFIX}{normalized_folder}"
        return normalized_folder or cls.ROOT_FOLDER_LABEL

    @classmethod
    def _normalize_folder_parts(cls, folder_name) -> Tuple[str, List[str]]:
        raw_folder = cls._decode_folder_value(folder_name)
        drive, _tail = os.path.splitdrive(raw_folder)
        if drive or os.path.isabs(raw_folder):
            raise ValueError("[Ultra Tools Wildcard Browser] 폴더에는 상대 경로만 사용할 수 있습니다.")

        normalized = raw_folder.replace("\\", "/").strip("/")
        parts = [part for part in normalized.split("/") if part and part != "."]
        if any(part == ".." for part in parts):
            raise ValueError("[Ultra Tools Wildcard Browser] 상위 폴더 경로('..')는 사용할 수 없습니다.")
        if len(parts) > cls.MAX_NAVIGATION_DEPTH:
            raise ValueError("[Ultra Tools Wildcard Browser] 폴더 탐색 깊이 제한을 초과했습니다.")
        return "/".join(parts), parts

    @classmethod
    def _walk_realpaths(cls, base_abs: str, parts: Sequence[str]) -> Set[str]:
        """Return ancestor real paths and reject a path that revisits one of them."""
        seen = {os.path.normcase(os.path.realpath(base_abs))}
        current = base_abs

        for part in parts:
            current = os.path.join(current, part)
            if not os.path.lexists(current):
                break
            current_real = os.path.normcase(os.path.realpath(current))
            if current_real in seen:
                raise ValueError("[Ultra Tools Wildcard Browser] 순환 심볼릭 링크 경로는 열 수 없습니다.")
            seen.add(current_real)
        return seen

    @classmethod
    def _resolve_folder_context(
        cls, folder_name, wildcards_path=None
    ) -> Tuple[str, str, Set[str]]:
        """Resolve a lexical child path while allowing external symlinks/junctions."""
        base_path, _defaulted = cls._resolve_wildcards_path(wildcards_path)
        normalized, parts = cls._normalize_folder_parts(folder_name)
        base_abs = os.path.abspath(base_path)
        folder_path = os.path.abspath(os.path.join(base_abs, *parts))

        try:
            common = os.path.commonpath([base_abs, folder_path])
        except ValueError as exc:
            raise ValueError("[Ultra Tools Wildcard Browser] 올바르지 않은 폴더 경로입니다.") from exc
        if os.path.normcase(common) != os.path.normcase(base_abs):
            raise ValueError("[Ultra Tools Wildcard Browser] 와일드카드 루트 밖의 경로는 사용할 수 없습니다.")

        return normalized, folder_path, cls._walk_realpaths(base_abs, parts)

    @classmethod
    def get_folders_info(cls, wildcards_path=None) -> Dict[str, object]:
        base_path, defaulted = cls._resolve_wildcards_path(wildcards_path)
        result: Dict[str, object] = {
            "ok": True,
            "folders": [cls.ROOT_FOLDER_LABEL],
            "path_defaulted": defaulted,
            "default_path": cls.DEFAULT_WILDCARDS_PATH,
            "error": None,
            "warning": None,
        }

        if not os.path.isdir(base_path):
            result.update(ok=False, error="Wildcards folder not found")
            return result

        names: List[str] = []
        try:
            base_real = os.path.normcase(os.path.realpath(base_path))
            with os.scandir(base_path) as scan:
                for scanned_entries, entry in enumerate(scan, start=1):
                    if scanned_entries > cls.MAX_SCANNED_ENTRIES:
                        result["warning"] = (
                            f"루트 폴더 항목이 너무 많아 {cls.MAX_SCANNED_ENTRIES:,}개를 "
                            "검사한 뒤 중단했습니다."
                        )
                        break
                    try:
                        if "\n" in entry.name or "\r" in entry.name:
                            continue
                        if not entry.is_dir(follow_symlinks=True):
                            continue
                        if os.path.normcase(os.path.realpath(entry.path)) == base_real:
                            continue
                        if len(names) >= cls.MAX_ROOT_FOLDERS:
                            result["warning"] = (
                                f"루트 드롭다운은 최대 {cls.MAX_ROOT_FOLDERS:,}개 폴더만 표시합니다."
                            )
                            break
                        names.append(entry.name)
                    except OSError:
                        continue
        except OSError as exc:
            result.update(ok=False, error=str(exc))
            return result

        names.sort(key=str.casefold)
        result["folders"] = [cls.ROOT_FOLDER_LABEL, *(
            cls._encode_folder_value(name) for name in names
        )]
        return result

    @classmethod
    def _parent_entry(cls, normalized_folder: str) -> Optional[Dict[str, str]]:
        if not normalized_folder:
            return None
        parent = normalized_folder.rsplit("/", 1)[0] if "/" in normalized_folder else ""
        return {
            "type": "parent",
            "path": cls._encode_folder_value(parent),
            "display": "📁 ..",
        }

    @classmethod
    def _get_entries_for_folder(cls, folder_name, wildcards_path=None) -> List[Dict[str, str]]:
        """Return only immediate folders and supported wildcard files."""
        entries: List[Dict[str, str]] = []

        try:
            normalized_folder, _parts = cls._normalize_folder_parts(folder_name)
            parent_entry = cls._parent_entry(normalized_folder)
            if parent_entry:
                entries.append(parent_entry)

            normalized_folder, folder_path, ancestor_realpaths = cls._resolve_folder_context(
                folder_name, wildcards_path
            )
            if not os.path.isdir(folder_path):
                entries.append({
                    "type": "status",
                    "display": "Error: 선택한 폴더를 찾을 수 없습니다.",
                })
                return entries

            folder_rows: List[Tuple[str, Dict[str, str]]] = []
            file_candidates: Dict[str, Tuple[int, str]] = {}
            visible_entries = 0
            truncated_by_scan = False
            truncated_by_display = False

            with os.scandir(folder_path) as scan:
                for scanned_entries, entry in enumerate(scan, start=1):
                    if scanned_entries > cls.MAX_SCANNED_ENTRIES:
                        truncated_by_scan = True
                        break

                    name = entry.name
                    if "\n" in name or "\r" in name:
                        continue

                    try:
                        if entry.is_dir(follow_symlinks=True):
                            if visible_entries >= cls.MAX_VISIBLE_ENTRIES:
                                truncated_by_display = True
                                break

                            relative_path = f"{normalized_folder}/{name}" if normalized_folder else name
                            child_real = os.path.normcase(os.path.realpath(entry.path))
                            if child_real in ancestor_realpaths:
                                row = {
                                    "type": "cycle",
                                    "display": f"📁 {name} [순환 링크]",
                                }
                            else:
                                row = {
                                    "type": "folder",
                                    "path": cls._encode_folder_value(relative_path.replace("\\", "/")),
                                    "display": f"📁 {name}",
                                }
                            folder_rows.append((name.casefold(), row))
                            visible_entries += 1
                            continue

                        if not entry.is_file(follow_symlinks=True):
                            continue
                    except OSError:
                        continue

                    stem, extension = os.path.splitext(name)
                    if not stem:
                        continue
                    extension = extension.casefold()
                    priority = cls.EXTENSION_PRIORITY.get(extension)
                    if priority is None:
                        continue

                    wildcard_name = (
                        f"{normalized_folder}/{stem}" if normalized_folder else stem
                    ).replace("\\", "/")
                    key = os.path.normcase(wildcard_name)
                    previous = file_candidates.get(key)
                    if previous is None:
                        if visible_entries >= cls.MAX_VISIBLE_ENTRIES:
                            truncated_by_display = True
                            break
                        visible_entries += 1
                    if previous is None or priority < previous[0]:
                        file_candidates[key] = (priority, wildcard_name)

            folder_rows.sort(key=lambda item: item[0])
            entries.extend(row for _sort_key, row in folder_rows)

            for _priority, wildcard_name in sorted(
                file_candidates.values(), key=lambda item: item[1].casefold()
            ):
                wildcard_text = f"__{wildcard_name}__"
                entries.append({
                    "type": "file",
                    "display": wildcard_text,
                })

            if truncated_by_display:
                entries.append({
                    "type": "status",
                    "display": (
                        f"목록 제한: 현재 폴더는 최대 {cls.MAX_VISIBLE_ENTRIES:,}개 항목까지만 "
                        "표시합니다."
                    ),
                })
            elif truncated_by_scan:
                entries.append({
                    "type": "status",
                    "display": (
                        f"목록 제한: 항목이 너무 많아 {cls.MAX_SCANNED_ENTRIES:,}개를 검사한 뒤 "
                        "중단했습니다."
                    ),
                })

            if not entries:
                entries.append({"type": "status", "display": "No files or folders found"})
        except Exception as exc:
            entries.append({"type": "status", "display": f"Error: {str(exc)}"})

        return entries


# Per-process token handed to the Ultra Tools frontend (see request_guard).
register_token_route()


@server.PromptServer.instance.routes.post("/Ultra-wildcard_browser/folders")
async def post_folders(request):
    denied = guard_request(request, web)
    if denied is not None:
        return denied
    try:
        data = await request.json()
        wildcards_path = data.get("wildcards_path") or data.get("path") or None
        result = await _run_filesystem_call(UltraWildcardBrowser.get_folders_info, wildcards_path)
        return web.json_response(result)
    except Exception as exc:
        return web.json_response({
            "ok": False,
            "folders": [UltraWildcardBrowser.ROOT_FOLDER_LABEL],
            "default_path": UltraWildcardBrowser.DEFAULT_WILDCARDS_PATH,
            "error": str(exc),
        }, status=400)


# Compatibility for older cached frontend files. The current frontend uses POST.
@server.PromptServer.instance.routes.get("/Ultra-wildcard_browser/folders")
async def get_folders(request):
    denied = guard_request(request, web)
    if denied is not None:
        return denied
    try:
        wildcards_path = request.query.get("wildcards_path") or request.query.get("path") or None
        result = await _run_filesystem_call(UltraWildcardBrowser.get_folders_info, wildcards_path)
        return web.json_response(result)
    except Exception as exc:
        return web.json_response({
            "ok": False,
            "folders": [UltraWildcardBrowser.ROOT_FOLDER_LABEL],
            "default_path": UltraWildcardBrowser.DEFAULT_WILDCARDS_PATH,
            "error": str(exc),
        }, status=400)


@server.PromptServer.instance.routes.post("/Ultra-wildcard_browser/get_files")
async def get_files(request):
    denied = guard_request(request, web)
    if denied is not None:
        return denied
    try:
        data = await request.json()
        folder = data.get("folder", UltraWildcardBrowser.ROOT_FOLDER_LABEL)
        wildcards_path = data.get("wildcards_path") or data.get("path") or None
        entries = await _run_filesystem_call(
            UltraWildcardBrowser._get_entries_for_folder, folder, wildcards_path
        )
        return web.json_response({"ok": True, "entries": entries})
    except Exception as exc:
        return web.json_response({"ok": False, "entries": [], "error": str(exc)}, status=400)
