import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_CLASS = "UltraToolsImageLoad";
const IMAGE_WIDGET = "image";
const STORE_KEY = "UltraToolsImageLoad.browser.v1";
const STYLE_ID = "ultra-tools-image-load-style";
const BUTTON_MARK = "__ultraImageLoadBrowseButton";
let previewGeneration = 0;
let registeredNodeData = null;

const TEXT = {
    en: {
        browse: "View Input Thumbnails",
        title: "ComfyUI Input Images",
        thumbnails: "Thumbnails",
        list: "List",
        search: "Search filename...",
        inputAll: "All Images",
        refresh: "Refresh",
        thumbSize: "Thumbnail",
        noImages: "No images found.",
        loadMore: "Load more",
        selected: "Selected",
        sizeChecking: "checking resolution...",
        sizeUnavailable: "resolution unavailable",
        close: "Close Browser",
        select: "Select",
        refreshFailed: "Could not refresh the ComfyUI input image list.",
        selectFailed: "Could not apply the selected image.",
        sortBy: "Sort by",
        sortName: "Name",
        sortDate: "Date modified",
        sortExt: "File type",
        sortAsc: "Ascending",
        sortDesc: "Descending",
        manageFolders: "External folders",
        noRegisteredFolders: "No folders registered yet.",
        addRoot: "+ Add folder",
        removeRoot: "Remove folder",
        browseUp: "↑ Up",
        browseDrives: "Drives",
        browseLoading: "Loading…",
        browseFailed: "Could not open that folder.",
        browseEmpty: "No subfolders here.",
        browsePreviewHint: "Pick a drive or folder to preview its images here.",
        browseNoImages: "No images in this folder.",
        openOriginal: "Open original in new tab",
        saveOriginal: "Save original image as…",
        copyOriginal: "Copy original image",
        copyOriginalDone: "Original-resolution image copied.",
        copyOriginalFailed: "Could not copy the original image.",
        menuTarget: "Target image",
        deleteSelected: "Delete selected images",
        deleteTitle: "Delete images",
        deleteMessage: "The following {count} original image file(s) will be permanently deleted from their current folders.",
        deleteCurrentWarning: "The image currently loaded in this node is included. Its selection will be cleared after deletion.",
        deleteConfirm: "Delete",
        deleteCancel: "Cancel",
        deleteFailed: "Could not delete the selected images.",
        deletePartial: "Some images could not be deleted.",
        selectedMany: "{count} images selected · node candidate: {name}",
        browseLabelPlaceholder: "Display name (optional)",
        addRootSelect: "Add this folder",
        addRootCancel: "Cancel",
        addRootFailed: "Could not add that folder.",
        removeRootFailed: "Could not remove that folder.",
    },
    ko: {
        browse: "input 썸네일 보기",
        title: "ComfyUI input 이미지",
        thumbnails: "썸네일 보기",
        list: "리스트 보기",
        search: "파일명 검색...",
        inputAll: "전체 이미지",
        refresh: "새로고침",
        thumbSize: "썸네일",
        noImages: "표시할 이미지가 없습니다.",
        loadMore: "더 보기",
        selected: "선택 후보",
        sizeChecking: "해상도 확인 중...",
        sizeUnavailable: "해상도 확인 불가",
        close: "브라우저 창 닫기",
        select: "선택",
        refreshFailed: "ComfyUI input 이미지 목록을 새로고침하지 못했습니다.",
        selectFailed: "선택한 이미지를 노드에 적용하지 못했습니다.",
        sortBy: "정렬 기준",
        sortName: "이름",
        sortDate: "수정한 날짜",
        sortExt: "파일 형식",
        sortAsc: "오름차순",
        sortDesc: "내림차순",
        manageFolders: "외부 폴더",
        noRegisteredFolders: "등록된 폴더가 없습니다.",
        addRoot: "+ 폴더 추가",
        removeRoot: "폴더 제거",
        browseUp: "↑ 위로",
        browseDrives: "드라이브 목록",
        browseLoading: "불러오는 중…",
        browseFailed: "폴더를 열지 못했습니다.",
        browseEmpty: "하위 폴더가 없습니다.",
        browsePreviewHint: "드라이브나 폴더를 선택하면 여기에 이미지 미리보기가 표시됩니다.",
        browseNoImages: "이 폴더엔 이미지가 없습니다.",
        openOriginal: "원본 이미지를 새 탭에서 열기",
        saveOriginal: "원본 이미지를 다른 이름으로 저장",
        copyOriginal: "원본 이미지 복사",
        copyOriginalDone: "원본 해상도 이미지를 복사했습니다.",
        copyOriginalFailed: "원본 이미지를 복사하지 못했습니다.",
        menuTarget: "대상 이미지",
        deleteSelected: "선택한 이미지 삭제",
        deleteTitle: "이미지 삭제",
        deleteMessage: "다음 {count}개 원본 이미지 파일을 현재 폴더에서 영구 삭제합니다.",
        deleteCurrentWarning: "현재 이 노드에서 불러온 이미지가 포함되어 있습니다. 삭제 후 노드의 이미지 선택이 해제됩니다.",
        deleteConfirm: "삭제",
        deleteCancel: "취소",
        deleteFailed: "선택한 이미지를 삭제하지 못했습니다.",
        deletePartial: "일부 이미지를 삭제하지 못했습니다.",
        selectedMany: "{count}개 선택 · 노드 적용 후보: {name}",
        browseLabelPlaceholder: "표시 이름 (선택)",
        addRootSelect: "이 폴더 추가",
        addRootCancel: "취소",
        addRootFailed: "폴더를 추가하지 못했습니다.",
        removeRootFailed: "폴더를 제거하지 못했습니다.",
    },
};

function classifyLocale(value) {
    if (value == null) return null;
    const raw = String(value).trim().toLowerCase();
    if (!raw) return null;
    if (raw === "ko" || raw.startsWith("ko-") || raw.includes("korean") || raw.includes("한국")) return "ko";
    if (raw === "en" || raw.startsWith("en-") || raw.includes("english")) return "en";
    return null;
}

function readSetting(key) {
    try {
        return app?.ui?.settings?.getSettingValue?.(key) ?? null;
    } catch (_) {
        return null;
    }
}

function currentLocale() {
    const candidates = [
        app?.extensionManager?.locale,
        readSetting("Comfy.Locale"),
        readSetting("Comfy.Language"),
        readSetting("ComfyUI.Locale"),
        readSetting("ComfyUI.Language"),
        document?.documentElement?.lang,
    ];
    for (const candidate of candidates) {
        const locale = classifyLocale(candidate);
        if (locale) return locale;
    }
    return "en";
}

function tr(key) {
    const locale = currentLocale();
    return TEXT[locale]?.[key] || TEXT.en[key] || key;
}

function trf(key, values = {}) {
    return Object.entries(values).reduce(
        (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
        tr(key),
    );
}

const SORT_FIELDS = ["name", "date", "ext"];

function loadPrefs() {
    const fallback = { view: "thumbs", thumb: 150, width: 900, height: 650, sortField: "name", sortDir: "asc" };
    try {
        const parsed = JSON.parse(localStorage.getItem(STORE_KEY) || "{}");
        return {
            view: parsed.view === "list" ? "list" : "thumbs",
            thumb: Math.min(260, Math.max(90, Number(parsed.thumb) || fallback.thumb)),
            width: Math.max(560, Number(parsed.width) || fallback.width),
            height: Math.max(420, Number(parsed.height) || fallback.height),
            sortField: SORT_FIELDS.includes(parsed.sortField) ? parsed.sortField : fallback.sortField,
            sortDir: parsed.sortDir === "desc" ? "desc" : "asc",
        };
    } catch (_) {
        return fallback;
    }
}

function savePrefs(prefs) {
    try {
        localStorage.setItem(STORE_KEY, JSON.stringify(prefs));
    } catch (_) {
        // Private browsing or storage policy may disable persistence.
    }
}

function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
.ultra-image-load-backdrop{position:fixed;inset:0;z-index:100000;background:rgba(0,0,0,.58);display:flex;align-items:center;justify-content:center;padding:18px}
.ultra-image-load-dialog{--uil-thumb:150px;--uil-font-size:14px;--uil-font-family:Arial,sans-serif;box-sizing:border-box;width:900px;height:650px;min-width:560px;min-height:420px;max-width:calc(100vw - 36px);max-height:calc(100vh - 36px);resize:both;overflow:hidden;display:flex;flex-direction:column;background:#24272b;color:#f1f3f5;border:1px solid #101214;border-radius:9px;box-shadow:0 18px 58px rgba(0,0,0,.55);font-family:var(--uil-font-family);font-size:var(--uil-font-size);line-height:1.35}
.ultra-image-load-dialog *{box-sizing:border-box}
.ultra-image-load-head,.ultra-image-load-foot{display:flex;align-items:center;gap:.55em;padding:.7em .8em;flex:none}
.ultra-image-load-head{justify-content:space-between;border-bottom:1px solid #454b54}.ultra-image-load-head strong{font-weight:600}
.ultra-image-load-title-wrap{display:flex;align-items:baseline;gap:.45em;min-width:0;overflow:hidden}
.ultra-image-load-title-wrap strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ultra-image-load-title-count{color:#9aa2ab;font-size:.85em;white-space:nowrap;flex:none}
.ultra-image-load-close{border:0!important;background:transparent!important;font-size:1.45em!important;padding:.05em .35em!important;min-width:0!important}
.ultra-image-load-toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:.5em;padding:.65em .8em;border-bottom:1px solid #454b54;flex:none}
.ultra-image-load-dialog button,.ultra-image-load-dialog select,.ultra-image-load-dialog input{font:inherit;color:#f1f3f5;background:#31353a;border:1px solid #4b525b;border-radius:5px;padding:.48em .65em}
.ultra-image-load-dialog button{cursor:pointer}.ultra-image-load-dialog button:hover:not(:disabled){filter:brightness(1.14)}.ultra-image-load-dialog button:disabled{opacity:.45;cursor:default}
.ultra-image-load-search{min-width:13em;flex:1}.ultra-image-load-folder{max-width:15em}
.ultra-image-load-manage-row{display:flex;flex-direction:column;gap:.55em;padding:.65em .8em;border-bottom:1px solid #454b54;background:#1c1f22}
.ultra-image-load-manage-row[hidden]{display:none}
.ultra-image-load-chips{display:flex;flex-wrap:wrap;gap:.4em;align-items:center}
.ultra-image-load-chip{display:inline-flex!important;align-items:center;gap:.4em;background:#31353a;border:1px solid #4b525b;border-radius:999px;padding:.3em .35em .3em .7em!important;font-size:.9em;width:auto!important}
.ultra-image-load-chip-remove{display:inline-flex;align-items:center;justify-content:center;width:1.35em;height:1.35em;border-radius:50%;background:#454b54!important;border:0!important;padding:0!important;font-size:.85em;line-height:1;min-width:0!important}
.ultra-image-load-chip-remove:hover{background:#5a626d!important}
.ultra-image-load-chips-empty{color:#9aa2ab;font-size:.9em}
.ultra-image-load-addroot-row{display:flex;flex-direction:column;gap:.5em;padding:.6em;border:1px solid #3a3f46;border-radius:6px;background:#17191c}
.ultra-image-load-addroot-row[hidden]{display:none}
.ultra-image-load-addroot-nav{display:flex;align-items:center;gap:.5em;min-width:0}
.ultra-image-load-addroot-path{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#c1c8d0;padding:.48em .2em}
.ultra-image-load-addroot-list{max-height:190px;overflow:auto;display:flex;flex-direction:column;gap:2px;background:#101214;border:1px solid #3a3f46;border-radius:5px;padding:.35em}
.ultra-image-load-browse-item{display:block!important;width:100%;text-align:left;background:transparent!important;border:1px solid transparent!important;padding:.42em .6em!important}
.ultra-image-load-browse-item:hover:not(:disabled){background:#2c3136!important}
.ultra-image-load-browse-status{color:#9aa2ab;padding:.5em .6em}
.ultra-image-load-addroot-footer{display:flex;align-items:center;gap:.5em;flex-wrap:wrap}
.ultra-image-load-addroot-label{flex:1;min-width:9em}
.ultra-image-load-toggle{display:flex}.ultra-image-load-toggle button{border-radius:0}.ultra-image-load-toggle button:first-child{border-radius:5px 0 0 5px}.ultra-image-load-toggle button:last-child{border-radius:0 5px 5px 0}.ultra-image-load-toggle .active{background:#385879;border-color:#7193b6}
.ultra-image-load-slider{display:flex;align-items:center;gap:.35em;color:#bcc3cc;white-space:nowrap}.ultra-image-load-slider input{width:7em;padding:0}
.ultra-image-load-content{flex:1;min-height:0;overflow:auto;padding:.75em}
.ultra-image-load-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--uil-thumb),1fr));gap:.7em;align-content:start}
.ultra-image-load-tile{display:block!important;width:100%;min-width:0;text-align:left;padding:.35em!important;background:transparent!important;border:1px solid transparent!important}
.ultra-image-load-tile.selected{background:#304d6e!important;border-color:#85add7!important}
.ultra-image-load-tile img{display:block;width:100%;height:calc(var(--uil-thumb) * .72);object-fit:contain;background:#17191c;border-radius:4px}
.ultra-image-load-name{display:block;margin-top:.35em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.88em}
.ultra-image-load-table{width:100%;border-collapse:collapse}.ultra-image-load-table th,.ultra-image-load-table td{text-align:left;padding:.55em;border-bottom:1px solid #454b54}.ultra-image-load-table th{color:#bac1ca;font-weight:400}.ultra-image-load-table tr{cursor:pointer}.ultra-image-load-table tr.selected{background:#304d6e}.ultra-image-load-list-preview{width:calc(var(--uil-thumb) * .3466667);height:calc(var(--uil-thumb) * .2533333);object-fit:contain;background:#17191c;border-radius:3px;display:block}
.ultra-image-load-original-menu{position:fixed;z-index:100002;display:flex;flex-direction:column;min-width:15em;padding:.3em;background:#24272b;color:#f1f3f5;border:1px solid #59616b;border-radius:6px;box-shadow:0 8px 24px rgba(0,0,0,.55);font-family:var(--uil-font-family,Arial,sans-serif);font-size:var(--uil-font-size,14px)}
.ultra-image-load-menu-target{max-width:min(28em,calc(100vw - 32px));padding:.5em .7em .6em;border-bottom:1px solid #454b54;margin-bottom:.25em}.ultra-image-load-menu-target-label{display:block;color:#9aa2ab;font-size:.82em;margin-bottom:.15em}.ultra-image-load-menu-target-name{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.ultra-image-load-original-menu[hidden]{display:none}.ultra-image-load-original-menu button{display:block;max-width:min(34em,calc(100vw - 32px));width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:left;border:0!important;background:transparent!important;color:inherit!important;border-radius:4px!important;padding:.55em .7em!important;font:inherit;cursor:pointer}.ultra-image-load-original-menu button:hover:not(:disabled){background:#385879!important}
.ultra-image-load-original-menu button:disabled{opacity:.55;cursor:default}.ultra-image-load-menu-separator{height:1px;background:#454b54;margin:.3em .15em}
.ultra-image-load-delete-confirm{position:fixed;inset:0;z-index:100003;display:flex;align-items:center;justify-content:center;padding:18px;background:rgba(0,0,0,.62)}.ultra-image-load-delete-confirm[hidden]{display:none}.ultra-image-load-delete-panel{width:min(520px,calc(100vw - 36px));max-height:calc(100vh - 36px);display:flex;flex-direction:column;gap:.75em;padding:1em;background:#24272b;border:1px solid #59616b;border-radius:8px;box-shadow:0 14px 44px rgba(0,0,0,.6)}.ultra-image-load-delete-panel strong{font-size:1.08em}.ultra-image-load-delete-panel button{font:inherit;color:#f1f3f5;background:#31353a;border:1px solid #4b525b;border-radius:5px;padding:.48em .75em;cursor:pointer}.ultra-image-load-delete-list{margin:0;max-height:240px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;padding:.7em;background:#17191c;border:1px solid #3a3f46;border-radius:5px;color:#d8dde3}.ultra-image-load-delete-warning{color:#ffca78}.ultra-image-load-delete-actions{display:flex;justify-content:flex-end;gap:.5em}.ultra-image-load-delete-action{background:#8b3030!important;border-color:#c45a5a!important}
.ultra-image-load-empty{text-align:center;color:#bac1ca;padding:3em 1em}.ultra-image-load-more{display:block;margin:1em auto 0!important;width:auto!important}
.ultra-image-load-foot{justify-content:space-between;border-top:1px solid #454b54}.ultra-image-load-candidate{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#c1c8d0}.ultra-image-load-actions{display:flex;gap:.5em}.ultra-image-load-actions button{width:auto}.ultra-image-load-confirm{background:#385879!important;border-color:#7193b6!important}
@media(max-width:640px){.ultra-image-load-backdrop{padding:8px}.ultra-image-load-dialog{min-width:0;width:calc(100vw - 16px)!important;height:calc(100vh - 16px)!important;max-width:none;max-height:none;resize:none}.ultra-image-load-slider{width:100%}.ultra-image-load-slider input{flex:1}}
`;
    document.head.appendChild(style);
}

// "ext:<root_id>:<rel/path>" identifies a file under one of the user's
// registered external folders (see image_load.py's _resolve_external_path).
// Distinguishing it here, once, keeps every other helper below (viewUrl,
// thumbUrl, folder grouping, filename display) working unmodified for both
// input-relative and external values.
function externalParts(value) {
    const raw = String(value || "");
    if (!raw.startsWith("ext:")) return null;
    const rest = raw.slice(4);
    const sep = rest.indexOf(":");
    if (sep < 0) return null;
    const rootId = rest.slice(0, sep);
    const relPath = rest.slice(sep + 1).replace(/\\/g, "/").trim();
    if (!rootId || !relPath) return null;
    const parts = relPath.split("/").filter(Boolean);
    const filename = parts.pop() || "";
    return { filename, subfolder: parts.join("/"), type: "external", rootId };
}

function annotatedParts(value) {
    const external = externalParts(value);
    if (external) return external;
    let path = String(value || "").replace(/\\/g, "/").trim();
    let type = "input";
    const annotated = path.match(/\s+\[(input|output|temp)\]\s*$/i);
    if (annotated) {
        type = annotated[1].toLowerCase();
        path = path.slice(0, annotated.index).trim();
    }
    const parts = path.split("/").filter(Boolean);
    const filename = parts.pop() || "";
    return { filename, subfolder: parts.join("/"), type };
}

function viewUrl(value, generation = previewGeneration, previewQuality = 75) {
    const item = annotatedParts(value);
    const query = new URLSearchParams({ filename: item.filename, subfolder: item.subfolder, type: item.type });
    if (previewQuality != null) query.set("preview", `webp;${previewQuality}`);
    query.set("rand", String(generation));
    const path = `/view?${query.toString()}`;
    return typeof api.apiURL === "function" ? api.apiURL(path) : path;
}

// Core's "/view" endpoint always decodes+re-encodes the ORIGINAL file, with no
// resize option — using it for every browser tile means dozens of full-res
// decodes on open. This hits the resized/cached thumbnail route added by
// image_load.py instead, which is both smaller to transfer and much cheaper
// for the server to produce a second time (disk-cached by file mtime).
function thumbUrl(value, maxDim = 320) {
    const item = annotatedParts(value);
    const query = new URLSearchParams({
        filename: item.filename,
        subfolder: item.subfolder,
        type: item.type,
        max: String(maxDim),
    });
    if (item.type === "external" && item.rootId) query.set("root", item.rootId);
    const path = `/ultra_tools/image_load/thumbnail?${query.toString()}`;
    return typeof api.apiURL === "function" ? api.apiURL(path) : path;
}

// Preview thumbnail for a file surfaced by /browse_dirs, before it's part
// of any registered folder — the "+ 폴더 추가" panel uses this so a folder's
// images are visible while still just navigating, not only after commiting.
function browseThumbUrl(absolutePath, maxDim = 160) {
    const query = new URLSearchParams({ type: "path", path: absolutePath, max: String(maxDim) });
    const path = `/ultra_tools/image_load/thumbnail?${query.toString()}`;
    return typeof api.apiURL === "function" ? api.apiURL(path) : path;
}

function originalUrl(value, download = false) {
    const item = annotatedParts(value);
    const query = new URLSearchParams({ filename: item.filename, subfolder: item.subfolder, type: item.type });
    if (item.type === "external" && item.rootId) query.set("root", item.rootId);
    if (download) query.set("download", "1");
    const path = `/ultra_tools/image_load/original?${query.toString()}`;
    return typeof api.apiURL === "function" ? api.apiURL(path) : path;
}

function browseOriginalUrl(absolutePath, download = false) {
    const query = new URLSearchParams({ type: "path", path: absolutePath });
    if (download) query.set("download", "1");
    const path = `/ultra_tools/image_load/original?${query.toString()}`;
    return typeof api.apiURL === "function" ? api.apiURL(path) : path;
}

function materializeComboValues(values, widget, node) {
    if (typeof values === "function") {
        try { return values(widget, node); } catch (_) { return []; }
    }
    return values;
}

function comboEntries(widget, node, override = undefined) {
    const values = materializeComboValues(override === undefined ? widget?.options?.values : override, widget, node);
    if (Array.isArray(values)) return normalizeComboValues(values).map((value) => ({ value, label: value }));
    if (values && typeof values === "object") {
        return Object.entries(values).map(([value, label]) => ({ value, label: String(label ?? value) }));
    }
    return [];
}

function comboEntryFolder(entry) {
    const labelFolder = annotatedParts(entry?.label).subfolder;
    return labelFolder || annotatedParts(entry?.value).subfolder;
}

function collectFolders(items) {
    const folders = new Set();
    for (const item of items) {
        const parts = String(item.folder || "").split("/").filter(Boolean);
        for (let index = 1; index <= parts.length; index += 1) {
            folders.add(parts.slice(0, index).join("/"));
        }
    }
    return [...folders].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
}

function normalizeComboValues(values) {
    if (!Array.isArray(values)) return [];
    const seen = new Set();
    return values.map((value) => String(value || "")).filter((value) => value && !seen.has(value) && seen.add(value));
}

async function refreshInputValues(imageWidget) {
    const response = await api.fetchApi(`/object_info/${encodeURIComponent(NODE_CLASS)}`);
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const payload = await response.json();
    const values = payload?.[NODE_CLASS]?.input?.required?.image?.[0];
    const normalized = normalizeComboValues(values);
    // Keep the node definition used for subsequently reconstructed nodes in
    // sync too. Core upload updates the current widget, but the definition
    // cached by the frontend can still contain the pre-upload filename list.
    const registeredValues = registeredNodeData?.input?.required?.image?.[0];
    if (Array.isArray(registeredValues)) registeredValues.splice(0, registeredValues.length, ...normalized);
    imageWidget.options ||= {};
    const existing = imageWidget.options.values;
    if (Array.isArray(existing) || existing == null) imageWidget.options.values = normalized;
    else if (existing && typeof existing === "object" && typeof existing !== "function") {
        for (const value of normalized) if (!(value in existing)) existing[value] = value;
    }
    previewGeneration += 1;
    return normalized;
}

function markNodeChanged(node) {
    node?.setDirtyCanvas?.(true, true);
    app?.graph?.setDirtyCanvas?.(true, true);
    app?.canvas?.setDirty?.(true, true);
}

// Node-body preview (the thumbnail LiteGraph/Vue Nodes draws under the
// node's widgets). Previously this loaded the ORIGINAL, full-resolution file
// a second time (no resize, no cache) — for a large source image that request
// alone could take long enough that it looked like "selecting does nothing".
// A resized preview from the same cached thumbnail route above shows up fast
// and is plenty for the node body's display size.
const NODE_PREVIEW_MAX_DIMENSION = 1024;

function refreshNodeImagePreview(node, value) {
    const image = new Image();
    image.onload = () => {
        // setSizeForImage() is deprecated (no effect) in current frontends;
        // the preview area sizes itself, so only a repaint is needed.
        markNodeChanged(node);
    };
    image.onerror = () => {
        if (node?.imgs?.[0] === image) node.imgs = undefined;
        markNodeChanged(node);
    };
    node.imgs = [image];
    node.imageIndex = null;
    node.previewMediaType = "image";
    image.src = thumbUrl(value, NODE_PREVIEW_MAX_DIMENSION);
}

function addComboValue(widget, value, label = value) {
    widget.options ||= {};
    const values = widget.options.values;
    if (Array.isArray(values)) {
        if (!values.includes(value)) values.push(value);
    } else if (values && typeof values === "object" && typeof values !== "function") {
        if (!(value in values)) values[value] = label;
    } else if (values == null) widget.options.values = [value];
}

async function applyImageValue(node, widget, value, label = value) {
    addComboValue(widget, value, label);
    const oldValue = widget.value;
    // Always go through the same beforeChange/value-set/incrementVersion/
    // afterChange sequence, even when re-selecting the file that's already
    // the widget's value. Vue Nodes' node body re-renders off graph version
    // changes, not off canvas dirty flags — skipping incrementVersion() (as
    // the old "value unchanged" shortcut did) meant the preview only ever
    // updated when the *combo value itself* changed, not on every confirmed
    // selection, so re-picking the same file silently did nothing visible.
    const graph = node?.graph || app?.graph;
    graph?.beforeChange?.(node);
    try {
        // Match ComfyUI Core's upload widget path. Calling a renderer-specific
        // setValue method is not reliable across legacy canvas and Vue nodes.
        widget.value = value;
        await widget.callback?.(value, app?.canvas, node);
        // Confirming the same filename is meaningful when a restored node is
        // carrying a stale "missing combo value" warning. Notify ComfyUI even
        // when the visible value itself did not change.
        node?.onWidgetChanged?.(widget.name, value, oldValue, widget);
        graph?.incrementVersion?.();
        refreshNodeImagePreview(node, value);
    } finally {
        graph?.afterChange?.(node);
    }
    markNodeChanged(node);
}

function reconcileRestoredImageValue(node) {
    const imageWidget = findImageWidget(node);
    const restoredValue = String(imageWidget?.value || "");
    if (!imageWidget || !restoredValue) return;
    const wasMissing = !comboEntries(imageWidget, node).some((entry) => entry.value === restoredValue);
    if (!wasMissing) return;

    refreshInputValues(imageWidget).then((values) => {
        // Ignore a late response if the user changed the node meanwhile. A
        // genuinely absent file must retain ComfyUI's red warning.
        if (findImageWidget(node) !== imageWidget || imageWidget.value !== restoredValue) return;
        if (!values.includes(restoredValue)) return;
        addComboValue(imageWidget, restoredValue);
        node?.onWidgetChanged?.(imageWidget.name, restoredValue, restoredValue, imageWidget);
        (node?.graph || app?.graph)?.incrementVersion?.();
        markNodeChanged(node);
    }).catch(() => {
        // Keep the original warning if the backend cannot confirm the file.
    });
}

function createEl(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text != null) el.textContent = text;
    return el;
}

function showMessage(message) {
    if (app?.ui?.dialog?.show) app.ui.dialog.show(message);
    else window.alert(message);
}

function prioritizeImageSuggestion() {
    const list = globalThis.LiteGraph?.slot_types_default_in?.IMAGE;
    if (!Array.isArray(list)) return;
    const originalLength = list.length;
    const existingIndex = list.indexOf(NODE_CLASS);
    if (existingIndex >= 0) list.splice(existingIndex, 1);
    list.unshift(NODE_CLASS);
    if (originalLength > 0 && list.length > originalLength) list.length = originalLength;
}

function extOf(name) {
    const idx = name.lastIndexOf(".");
    return idx > 0 ? name.slice(idx + 1).toLocaleLowerCase() : "";
}

function openBrowser(node, imageWidget) {
    ensureStyle();
    const prefs = loadPrefs();
    // Combo values for external-folder files are the plain "ext:<root_id>:
    // <rel/path>" identifier (see image_load.py — the combo itself has to
    // stay a flat array of raw values for ComfyUI's frontend to recognise
    // it as a dropdown at all). The friendly "RootLabel/rel/path" text
    // shown in this dialog is built here instead, from the separately
    // loaded roots list (loadRoots() below fills this map in and triggers
    // a rebuild once it resolves).
    let rootLabels = new Map();
    let lastRoots = []; // last-fetched roots, kept only to re-render chip text on a locale change
    const buildItems = (values) => comboEntries(imageWidget, node, values).map((entry) => {
        const parts = annotatedParts(entry.value);
        if (parts.type === "external") {
            const rootLabel = rootLabels.get(parts.rootId) || parts.rootId;
            const displayPath = parts.subfolder ? `${rootLabel}/${parts.subfolder}/${parts.filename}` : `${rootLabel}/${parts.filename}`;
            return {
                key: displayPath,
                name: parts.filename || entry.label,
                folder: parts.subfolder ? `${rootLabel}/${parts.subfolder}` : rootLabel,
                value: entry.value,
            };
        }
        // key keeps the full "subfolder/name.ext" value so search still
        // matches on folder name too; name is just the filename for a
        // cleaner tile/list label once subfolders are in the mix.
        return {
            key: entry.label,
            name: parts.filename || entry.label,
            folder: comboEntryFolder(entry),
            value: entry.value,
        };
    });
    let items = buildItems(undefined);
    // Populated from GET /ultra_tools/image_load/list (value -> {mtime, size}).
    // Only needed for the "date modified" sort; name/extension sort works
    // straight off `items` without waiting on this.
    let fileMeta = new Map();
    function sortItems() {
        const mult = prefs.sortDir === "desc" ? -1 : 1;
        items.sort((a, b) => {
            let cmp;
            if (prefs.sortField === "date") {
                const ma = fileMeta.get(a.value)?.mtime ?? 0;
                const mb = fileMeta.get(b.value)?.mtime ?? 0;
                cmp = ma - mb || a.name.localeCompare(b.name, undefined, { numeric: true });
            } else if (prefs.sortField === "ext") {
                cmp = extOf(a.name).localeCompare(extOf(b.name)) || a.name.localeCompare(b.name, undefined, { numeric: true });
            } else {
                cmp = a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" });
            }
            return cmp * mult;
        });
    }
    sortItems();
    async function loadFileMeta() {
        try {
            const response = await api.fetchApi("/ultra_tools/image_load/list");
            if (!response.ok) return;
            const payload = await response.json();
            if (!alive() || !Array.isArray(payload?.files)) return;
            fileMeta = new Map(payload.files.map((entry) => [entry.path, entry]));
            if (prefs.sortField === "date") {
                sortItems();
                render();
            }
        } catch (_) {
            // Older backend without this route, or a request race on close —
            // date sort just falls back to filename ordering (see sortItems).
        }
    }
    let selected = items.find((item) => item.value === imageWidget.value) || null;
    const selectedValues = new Set(selected ? [selected.value] : []);
    let selectionAnchor = selected?.value || null;
    let visibleLimit = 120;
    let searchDebounce = null;
    const session = { closed: false };
    const alive = () => !session.closed && backdrop.isConnected;
    let locale = currentLocale();
    let localeTimer = null;
    const dimensions = new Map();
    const dimensionRequests = new Set();
    // Current location inside the "+ 폴더 추가" folder browser panel.
    // "" means the top-level drive/root list (browseParent stays null there
    // — there's nowhere further "up" to go).
    let browsePath = "";
    let browseParent = null;
    // While true, render() shows browsingPreviewImages (the currently
    // browsed folder's own images) in the main content grid instead of the
    // normal library view — set whenever the "+ 폴더 추가" folder browser is
    // open, cleared the moment it closes or the folder is actually added.
    let browsingPreviewMode = false;
    let browsingPreviewImages = [];

    const backdrop = createEl("div", "ultra-image-load-backdrop");
    const dialog = createEl("section", "ultra-image-load-dialog");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.style.width = `${Math.min(prefs.width, window.innerWidth - 36)}px`;
    dialog.style.height = `${Math.min(prefs.height, window.innerHeight - 36)}px`;
    const widgetFont = String(app?.canvas?.inner_text_font || node?.innerFontStyle || "");
    const widgetFontParts = widgetFont.match(/(\d+(?:\.\d+)?)px\s+(.+)$/);
    if (widgetFontParts) {
        // inner_text_font is sized for cramped in-node canvas text, not for a
        // separate readable dialog — it's a fixed value (doesn't track graph
        // zoom), but nothing guarantees it's a comfortable UI text size. Clamp
        // it instead of dropping it entirely, so a user who's set a larger
        // ComfyUI text size still sees that reflected here, without the
        // dialog ever becoming uncomfortably small (or oversized).
        const clampedSize = Math.min(16, Math.max(13, Number(widgetFontParts[1]) || 14));
        dialog.style.setProperty("--uil-font-size", `${clampedSize}px`);
        dialog.style.setProperty("--uil-font-family", widgetFontParts[2]);
    }
    dialog.style.setProperty("--uil-thumb", `${prefs.thumb}px`);
    backdrop.appendChild(dialog);

    const head = createEl("div", "ultra-image-load-head");
    const titleWrap = createEl("div", "ultra-image-load-title-wrap");
    const title = createEl("strong", "", tr("title"));
    const titleCount = createEl("span", "ultra-image-load-title-count", "");
    titleWrap.append(title, titleCount);
    const closeButton = createEl("button", "ultra-image-load-close", "×");
    closeButton.type = "button";
    closeButton.setAttribute("aria-label", tr("close"));
    head.append(titleWrap, closeButton);
    updateTitleCount();

    const toolbar = createEl("div", "ultra-image-load-toolbar");
    const toggle = createEl("div", "ultra-image-load-toggle");
    const thumbsButton = createEl("button", "", tr("thumbnails"));
    const listButton = createEl("button", "", tr("list"));
    thumbsButton.type = listButton.type = "button";
    toggle.append(thumbsButton, listButton);
    const search = createEl("input", "ultra-image-load-search");
    search.type = "search";
    search.placeholder = tr("search");
    const folderSelect = createEl("select", "ultra-image-load-folder");
    folderSelect.setAttribute("aria-label", tr("inputAll"));
    const sortSelect = createEl("select", "ultra-image-load-sort");
    sortSelect.setAttribute("aria-label", tr("sortBy"));
    for (const field of SORT_FIELDS) sortSelect.add(new Option(tr(`sort${field[0].toUpperCase()}${field.slice(1)}`), field));
    sortSelect.value = prefs.sortField;
    const sortDirButton = createEl("button", "ultra-image-load-sort-dir", prefs.sortDir === "desc" ? "↓" : "↑");
    sortDirButton.type = "button";
    sortDirButton.setAttribute("aria-label", tr(prefs.sortDir === "desc" ? "sortDesc" : "sortAsc"));
    const refreshButton = createEl("button", "", tr("refresh"));
    refreshButton.type = "button";
    const thumbLabel = createEl("label", "ultra-image-load-slider");
    thumbLabel.append(document.createTextNode(`${tr("thumbSize")} `));
    const thumbRange = createEl("input");
    thumbRange.type = "range"; thumbRange.min = "90"; thumbRange.max = "260"; thumbRange.step = "10"; thumbRange.value = String(prefs.thumb);
    thumbLabel.appendChild(thumbRange);
    // Registered external (non-input) folders. Kept out of the main toolbar
    // entirely — just one small toggle button there — so the everyday
    // input-folder browsing UI stays as uncluttered as it was before this
    // feature existed. Management (the chip list + add-folder panel) lives
    // in its own row, collapsed until manageFoldersButton is clicked.
    const manageFoldersButton = createEl("button", "", tr("manageFolders"));
    manageFoldersButton.type = "button";
    toolbar.append(toggle, search, folderSelect, sortSelect, sortDirButton, refreshButton, thumbLabel, manageFoldersButton);

    const manageRow = createEl("div", "ultra-image-load-manage-row");
    manageRow.hidden = true;
    const foldersChips = createEl("div", "ultra-image-load-chips");
    const openAddRootButton = createEl("button", "", tr("addRoot"));
    openAddRootButton.type = "button";
    manageRow.append(foldersChips, openAddRootButton);

    // Everything below goes through /ultra_tools/image_load/roots and
    // /ultra_tools/image_load/browse_dirs via fetch, never a browser
    // file/folder picker and never a native window.prompt()/confirm()
    // popup — the whole flow stays inside this same styled dialog end to
    // end, just like picking an input image already does.
    //
    // Inline "add folder" browser, hidden until openAddRootButton is
    // clicked. It's a real folder browser: opens on the drive/root list and
    // lets the user click their way down (and back up) a directory tree,
    // purely through the browse_dirs route.
    const addRootRow = createEl("div", "ultra-image-load-addroot-row");
    addRootRow.hidden = true;
    const addRootNav = createEl("div", "ultra-image-load-addroot-nav");
    const browseUpButton = createEl("button", "", tr("browseUp"));
    browseUpButton.type = "button";
    const browsePathLabel = createEl("span", "ultra-image-load-addroot-path", tr("browseDrives"));
    addRootNav.append(browseUpButton, browsePathLabel);
    const browseListEl = createEl("div", "ultra-image-load-addroot-list");
    const addRootFooter = createEl("div", "ultra-image-load-addroot-footer");
    const addRootLabelInput = createEl("input", "ultra-image-load-addroot-label");
    addRootLabelInput.type = "text";
    addRootLabelInput.placeholder = tr("browseLabelPlaceholder");
    const addRootSelectButton = createEl("button", "ultra-image-load-confirm", tr("addRootSelect"));
    addRootSelectButton.type = "button";
    addRootSelectButton.disabled = true;
    const addRootCancelButton = createEl("button", "", tr("addRootCancel"));
    addRootCancelButton.type = "button";
    addRootFooter.append(addRootLabelInput, addRootSelectButton, addRootCancelButton);
    addRootRow.append(addRootNav, browseListEl, addRootFooter);
    manageRow.appendChild(addRootRow);


    const content = createEl("div", "ultra-image-load-content");
    const foot = createEl("div", "ultra-image-load-foot");
    const candidate = createEl("div", "ultra-image-load-candidate", "");
    const actions = createEl("div", "ultra-image-load-actions");
    const closeBrowserButton = createEl("button", "", tr("close"));
    const confirmButton = createEl("button", "ultra-image-load-confirm", tr("select"));
    closeBrowserButton.type = confirmButton.type = "button";
    // The node's currently-loaded image is already resolved into `selected`
    // at this point (see the top of openBrowser), and its tile renders
    // pre-highlighted — so start the button enabled to match, instead of
    // unconditionally disabling it and leaving it stuck until the user
    // clicks a tile that's already visually selected.
    confirmButton.disabled = !selected;
    actions.append(closeBrowserButton, confirmButton);
    foot.append(candidate, actions);
    dialog.append(head, toolbar, manageRow, content, foot);

    // A native image context menu would operate on the cached WEBP used by
    // the tile's <img>. Keep thumbnails lightweight and expose explicit
    // original-file actions which fetch the full source only when chosen.
    const originalMenu = createEl("div", "ultra-image-load-original-menu");
    originalMenu.hidden = true;
    originalMenu.setAttribute("role", "menu");
    originalMenu.style.setProperty("--uil-font-family", dialog.style.getPropertyValue("--uil-font-family") || "Arial,sans-serif");
    originalMenu.style.setProperty("--uil-font-size", dialog.style.getPropertyValue("--uil-font-size") || "14px");
    const originalMenuTargetBox = createEl("div", "ultra-image-load-menu-target");
    const originalMenuTargetLabel = createEl("span", "ultra-image-load-menu-target-label", tr("menuTarget"));
    const originalMenuTargetName = createEl("span", "ultra-image-load-menu-target-name", "");
    originalMenuTargetBox.append(originalMenuTargetLabel, originalMenuTargetName);
    const openOriginalButton = createEl("button", "", tr("openOriginal"));
    const saveOriginalButton = createEl("button", "", tr("saveOriginal"));
    const copyOriginalButton = createEl("button", "", tr("copyOriginal"));
    const originalMenuSeparator = createEl("div", "ultra-image-load-menu-separator");
    const deleteSelectedButton = createEl("button", "", tr("deleteSelected"));
    for (const button of [openOriginalButton, saveOriginalButton, copyOriginalButton, deleteSelectedButton]) {
        button.type = "button";
        button.setAttribute("role", "menuitem");
    }
    originalMenu.append(originalMenuTargetBox, openOriginalButton, saveOriginalButton, copyOriginalButton, originalMenuSeparator, deleteSelectedButton);
    backdrop.appendChild(originalMenu);
    let originalMenuTarget = null;
    let deleteConfirmOverlay = null;
    let cancelDeleteConfirmation = null;

    // rootMargin was 1600px, which on a tall/maximized dialog effectively
    // pre-loaded the *entire* grid the moment it opened — dozens of tile
    // requests fired at once regardless of scroll position. A smaller margin
    // still preloads a comfortable buffer just past the visible area while
    // letting the grid fill in progressively as the user scrolls.
    const imageObserver = typeof IntersectionObserver === "function" ? new IntersectionObserver((entries) => {
        for (const entry of entries) {
            if (!entry.isIntersecting) continue;
            imageObserver.unobserve(entry.target);
            startImageLoad(entry.target);
        }
    }, { root: content, rootMargin: "600px 0px" }) : null;

    function close() {
        if (session.closed) return;
        session.closed = true;
        cancelDeleteConfirmation?.();
        document.removeEventListener("keydown", onKeyDown, true);
        document.removeEventListener("pointerdown", onDocumentPointerDown, true);
        clearInterval(localeTimer);
        clearTimeout(searchDebounce);
        resizeObserver?.disconnect();
        imageObserver?.disconnect();
        backdrop.remove();
    }

    function hideOriginalMenu() {
        originalMenu.hidden = true;
        originalMenuTarget = null;
    }

    function confirmImageDeletion(targets) {
        return new Promise((resolve) => {
            const overlay = createEl("div", "ultra-image-load-delete-confirm");
            const panel = createEl("section", "ultra-image-load-delete-panel");
            const title = createEl("strong", "", tr("deleteTitle"));
            const message = createEl("div", "", trf("deleteMessage", { count: targets.length }));
            const names = createEl("pre", "ultra-image-load-delete-list", targets.map((item) => item.key).join("\n"));
            const currentIncluded = targets.some((item) => item.value === imageWidget.value);
            const warning = createEl("div", "ultra-image-load-delete-warning", currentIncluded ? tr("deleteCurrentWarning") : "");
            warning.hidden = !currentIncluded;
            const actionRow = createEl("div", "ultra-image-load-delete-actions");
            const cancelButton = createEl("button", "", tr("deleteCancel"));
            const deleteButton = createEl("button", "ultra-image-load-delete-action", tr("deleteConfirm"));
            cancelButton.type = deleteButton.type = "button";
            actionRow.append(cancelButton, deleteButton);
            panel.append(title, message, names, warning, actionRow);
            overlay.appendChild(panel);
            backdrop.appendChild(overlay);
            deleteConfirmOverlay = overlay;
            let settled = false;
            const finish = (answer) => {
                if (settled) return;
                settled = true;
                overlay.remove();
                deleteConfirmOverlay = null;
                cancelDeleteConfirmation = null;
                resolve(answer);
            };
            cancelDeleteConfirmation = () => finish(false);
            cancelButton.addEventListener("click", () => finish(false));
            deleteButton.addEventListener("click", () => finish(true));
            overlay.addEventListener("click", (event) => {
                if (event.target === overlay) event.stopPropagation();
            });
            cancelButton.focus();
        });
    }

    function onDocumentPointerDown(event) {
        if (!originalMenu.hidden && !originalMenu.contains(event.target)) hideOriginalMenu();
    }

    function showOriginalMenu(event, target, item = null) {
        event.preventDefault();
        event.stopPropagation();
        if (item) selectForContextMenu(item);
        originalMenuTarget = target;
        const targetName = target.displayName || target.filename || item?.name || "";
        originalMenuTargetLabel.textContent = tr("menuTarget");
        originalMenuTargetName.textContent = targetName;
        originalMenuTargetName.title = targetName;
        openOriginalButton.textContent = tr("openOriginal");
        saveOriginalButton.textContent = tr("saveOriginal");
        copyOriginalButton.textContent = tr("copyOriginal");
        const selectedCount = selectedValues.size;
        deleteSelectedButton.textContent = `${tr("deleteSelected")} (${selectedCount})`;
        deleteSelectedButton.disabled = !item || selectedCount === 0;
        originalMenuSeparator.hidden = deleteSelectedButton.disabled;
        originalMenu.hidden = false;
        const margin = 8;
        const width = originalMenu.offsetWidth;
        const height = originalMenu.offsetHeight;
        originalMenu.style.left = `${Math.max(margin, Math.min(event.clientX, window.innerWidth - width - margin))}px`;
        originalMenu.style.top = `${Math.max(margin, Math.min(event.clientY, window.innerHeight - height - margin))}px`;
    }

    function attachOriginalActions(image, target, item = null) {
        image.addEventListener("contextmenu", (event) => showOriginalMenu(event, target, item));
    }

    async function copyOriginalImage(target) {
        if (!navigator.clipboard?.write || typeof ClipboardItem !== "function") throw new Error("image clipboard unavailable");
        const response = await fetch(target.url);
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        const sourceBlob = await response.blob();
        let pngBlob = sourceBlob;
        if (sourceBlob.type !== "image/png") {
            const bitmap = await createImageBitmap(sourceBlob);
            try {
                const canvas = document.createElement("canvas");
                canvas.width = bitmap.width;
                canvas.height = bitmap.height;
                const context = canvas.getContext("2d");
                if (!context) throw new Error("canvas unavailable");
                context.drawImage(bitmap, 0, 0);
                pngBlob = await new Promise((resolve, reject) => {
                    canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("PNG conversion failed")), "image/png");
                });
            } finally {
                bitmap.close?.();
            }
        }
        await navigator.clipboard.write([new ClipboardItem({ "image/png": pngBlob })]);
    }

    openOriginalButton.addEventListener("click", () => {
        const target = originalMenuTarget;
        hideOriginalMenu();
        if (!target) return;
        const link = document.createElement("a");
        link.href = target.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        document.body.appendChild(link);
        link.click();
        link.remove();
    });
    saveOriginalButton.addEventListener("click", () => {
        const target = originalMenuTarget;
        hideOriginalMenu();
        if (!target) return;
        const link = document.createElement("a");
        link.href = target.downloadUrl;
        link.download = target.filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
    });
    copyOriginalButton.addEventListener("click", async () => {
        const target = originalMenuTarget;
        hideOriginalMenu();
        if (!target) return;
        try {
            await copyOriginalImage(target);
            showMessage(tr("copyOriginalDone"));
        } catch (error) {
            console.error("[Ultra Tools Image Load] original image copy failed", error);
            showMessage(tr("copyOriginalFailed"));
        }
    });
    deleteSelectedButton.addEventListener("click", async () => {
        const targets = items.filter((item) => selectedValues.has(item.value));
        hideOriginalMenu();
        if (!targets.length || !(await confirmImageDeletion(targets))) return;
        deleteSelectedButton.disabled = true;
        try {
            const requestedValues = targets.map((item) => item.value);
            const deleted = [];
            const failed = [];
            // Keep each server operation bounded while allowing a large
            // Shift-selected range to be deleted from one confirmation.
            for (let offset = 0; offset < requestedValues.length; offset += 500) {
                const batch = requestedValues.slice(offset, offset + 500);
                const response = await api.fetchApi("/ultra_tools/image_load/delete_images", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ images: batch }),
                });
                const payload = await response.json().catch(() => ({}));
                const batchDeleted = Array.isArray(payload?.deleted) ? payload.deleted : [];
                const batchFailed = Array.isArray(payload?.failed) ? payload.failed : [];
                deleted.push(...batchDeleted);
                failed.push(...batchFailed);
                if (!response.ok && !batchDeleted.length) {
                    const knownFailed = new Set(batchFailed.map((entry) => entry?.image));
                    for (const value of batch) {
                        if (!knownFailed.has(value)) failed.push({ image: value, reason: "request_failed" });
                    }
                    for (const value of requestedValues.slice(offset + batch.length)) {
                        failed.push({ image: value, reason: "not_attempted" });
                    }
                    break;
                }
            }
            if (!deleted.length && failed.length) throw new Error(`(${failed.length})`);

            const deletedSet = new Set(deleted);
            for (const value of deletedSet) selectedValues.delete(value);
            if (deletedSet.has(imageWidget.value)) {
                const oldValue = imageWidget.value;
                imageWidget.value = "";
                node.imgs = undefined;
                node.imageIndex = null;
                node?.onWidgetChanged?.(imageWidget.name, "", oldValue, imageWidget);
                (node?.graph || app?.graph)?.incrementVersion?.();
                markNodeChanged(node);
            }
            const values = await refreshInputValues(imageWidget);
            if (alive()) {
                setInputItems(values);
                loadFileMeta();
                if (failed.length) showMessage(`${tr("deletePartial")} (${failed.length})`);
            }
        } catch (error) {
            console.error("[Ultra Tools Image Load] image deletion failed", error);
            if (alive()) showMessage(`${tr("deleteFailed")} ${error?.message || error}`);
        }
    });

    function onKeyDown(event) {
        if (event.key === "Escape") {
            event.preventDefault();
            event.stopPropagation();
            if (deleteConfirmOverlay) {
                cancelDeleteConfirmation?.();
                return;
            }
            if (!originalMenu.hidden) {
                hideOriginalMenu();
                return;
            }
            if (!addRootRow.hidden) {
                addRootRow.hidden = true;
                browsingPreviewMode = false;
                setLibraryControlsEnabled(true);
                render();
                return;
            }
            if (!manageRow.hidden) {
                manageRow.hidden = true;
                return;
            }
            close();
        }
    }

    function storeDimensions(item, image, { fallback = false } = {}) {
        // A resized-thumbnail load only counts as a fallback size: never let
        // it clobber an accurate size requestDimensions() already recorded
        // from the source file's real dimensions.
        if (fallback && dimensions.has(item.value)) return;
        if (!image.naturalWidth || !image.naturalHeight) return;
        dimensions.set(item.value, { width: image.naturalWidth, height: image.naturalHeight });
        if (selected?.value === item.value) updateCandidate();
    }

    function startImageLoad(image) {
        if (image.dataset.loaded) return;
        image.dataset.loaded = "1";
        image.src = image.dataset.src;
    }

    const GRID_THUMB_MAX_DIMENSION = 480; // covers the thumbnail slider's 260px max at ~2x DPR

    function prepareItemImage(image, item) {
        // IntersectionObserver already controls request timing. Native lazy
        // loading here would defer the request a second time during fast scroll.
        image.loading = "eager";
        image.decoding = "async";
        image.dataset.src = thumbUrl(item.value, GRID_THUMB_MAX_DIMENSION);
        // The thumbnail is resized, so its own naturalWidth/Height aren't the
        // source file's real dimensions — storeDimensions() is only used here
        // as a cheap fallback for items requestDimensions() never got to.
        image.addEventListener("load", () => storeDimensions(item, image, { fallback: true }), { once: true });
        imageObserver ? imageObserver.observe(image) : startImageLoad(image);
    }

    // Reads the real source dimensions from the thumbnail route's response
    // headers (X-Ultra-Original-Width/Height) so the "Selected: name · W × H"
    // footer doesn't need a separate full-resolution download just to learn
    // the size — that used to be the same slow, uncached "/view" request the
    // grid itself was switched away from above.
    async function requestDimensions(item) {
        if (!item || dimensions.has(item.value) || dimensionRequests.has(item.value)) return;
        dimensionRequests.add(item.value);
        try {
            const response = await fetch(thumbUrl(item.value, 64));
            if (!response.ok) throw new Error(String(response.status));
            const width = Number(response.headers.get("X-Ultra-Original-Width"));
            const height = Number(response.headers.get("X-Ultra-Original-Height"));
            dimensionRequests.delete(item.value);
            if (width > 0 && height > 0) {
                dimensions.set(item.value, { width, height });
                if (selected?.value === item.value) updateCandidate();
                return;
            }
            throw new Error("missing dimension headers");
        } catch (_) {
            dimensionRequests.delete(item.value);
            // Older/mismatched backend without the header — fall back to a
            // full-resolution probe rather than showing no size at all.
            // Core's own "/view" only ever understands input/output/temp, so
            // an external item has no fallback to try — just report unknown.
            if (annotatedParts(item.value).type === "external") {
                dimensions.set(item.value, null);
                if (selected?.value === item.value) updateCandidate();
                return;
            }
            const probe = new Image();
            probe.decoding = "async";
            probe.onload = () => storeDimensions(item, probe);
            probe.onerror = () => {
                dimensions.set(item.value, null);
                if (selected?.value === item.value) updateCandidate();
            };
            probe.src = viewUrl(item.value);
        }
    }

    function updateCandidate() {
        if (!selected) {
            candidate.textContent = "";
            return;
        }
        if (selectedValues.size > 1) {
            candidate.textContent = trf("selectedMany", { count: selectedValues.size, name: selected.key });
            return;
        }
        const size = dimensions.get(selected.value);
        const detail = size
            ? `${size.width} × ${size.height}`
            : dimensions.has(selected.value) ? tr("sizeUnavailable") : tr("sizeChecking");
        candidate.textContent = `${tr("selected")}: ${selected.key} · ${detail}`;
    }

    // Total image count next to the dialog title — input + every registered
    // external folder combined, independent of the current search/folder
    // filter (that's what "모든 이미지" means here, not "currently visible").
    function updateTitleCount() {
        titleCount.textContent = items.length ? `(${items.length.toLocaleString()})` : "";
    }

    // Search/sort/folder-filter/view-toggle only mean anything against the
    // library (`items`) — while browsingPreviewMode has taken the content
    // grid over for a not-yet-registered folder, applying them would do
    // nothing visible and just look broken. Greying them out makes that
    // obvious instead of leaving them looking live.
    function setLibraryControlsEnabled(enabled) {
        search.disabled = !enabled;
        folderSelect.disabled = !enabled;
        sortSelect.disabled = !enabled;
        sortDirButton.disabled = !enabled;
        thumbsButton.disabled = !enabled;
        listButton.disabled = !enabled;
        refreshButton.disabled = !enabled;
    }

    // Populates the folder-management panel's chip list from
    // GET /ultra_tools/image_load/roots. A backend that predates this route
    // just leaves the panel empty — no error shown, since the main
    // input-folder browsing flow doesn't depend on it at all.
    function renderFolderChips(roots) {
        foldersChips.replaceChildren();
        if (!roots.length) {
            foldersChips.appendChild(createEl("span", "ultra-image-load-chips-empty", tr("noRegisteredFolders")));
            return;
        }
        for (const root of roots) {
            const chip = createEl("span", "ultra-image-load-chip");
            chip.append(document.createTextNode(root.label));
            const removeButton = createEl("button", "ultra-image-load-chip-remove", "×");
            removeButton.type = "button";
            removeButton.setAttribute("aria-label", `${tr("removeRoot")}: ${root.label}`);
            // Unregistering just forgets the folder reference — it never
            // touches the actual files on disk — so this removes
            // immediately rather than interrupting with a confirm() popup.
            removeButton.addEventListener("click", async () => {
                removeButton.disabled = true;
                try {
                    const response = await api.fetchApi(`/ultra_tools/image_load/roots?id=${encodeURIComponent(root.id)}`, { method: "DELETE" });
                    if (!response.ok) {
                        const payload = await response.json().catch(() => ({}));
                        throw new Error(payload?.error || `${response.status} ${response.statusText}`);
                    }
                    await reloadAfterRootsChange();
                } catch (error) {
                    console.error("[Ultra Tools Image Load] remove folder failed", error);
                    if (alive()) showMessage(`${tr("removeRootFailed")} ${error?.message || error}`);
                    if (alive()) removeButton.disabled = false;
                }
            });
            chip.appendChild(removeButton);
            foldersChips.appendChild(chip);
        }
    }

    async function loadRoots() {
        try {
            const response = await api.fetchApi("/ultra_tools/image_load/roots");
            if (!response.ok) return;
            const payload = await response.json();
            if (!alive() || !Array.isArray(payload?.roots)) return;
            renderFolderChips(payload.roots);
            lastRoots = payload.roots;
            rootLabels = new Map(payload.roots.map((root) => [root.id, root.label]));
            // Items already built (at open, or by a prior refresh) used
            // whatever rootLabels held at that moment — usually empty on
            // first open, since this fetch hasn't resolved yet. Rebuild now
            // that real folder names are known so external entries show
            // "RootLabel/..." instead of a bare root id.
            items = buildItems(imageWidget.options?.values);
            sortItems();
            selected = items.find((item) => item.value === imageWidget.value) || selected;
            updateTitleCount();
            rebuildFolderOptions();
            render();
            updateCandidate();
        } catch (_) {
            // Older backend without this route — management controls are
            // harmless no-ops; the input-folder browser still works fully,
            // just showing raw "ext:<root_id>:..." text for external files.
        }
    }

    async function reloadAfterRootsChange() {
        await loadRoots();
        const values = await refreshInputValues(imageWidget);
        if (alive()) setInputItems(values);
        loadFileMeta();
    }

    // Drives/root list (path === "") or one folder's immediate subfolders,
    // via GET /ultra_tools/image_load/browse_dirs — the whole "+ 폴더 추가"
    // panel is just this one call driving click-to-navigate, never a
    // browser file/folder picker. The folder's own images (payload.images)
    // aren't rendered here — they take over the main content grid instead,
    // exactly like the library view, via browsingPreviewMode (see render()).
    function renderBrowseList(entries) {
        browseListEl.replaceChildren();
        if (!entries.length) {
            browseListEl.appendChild(createEl("div", "ultra-image-load-browse-status", tr("browseEmpty")));
            return;
        }
        for (const entry of entries) {
            const item = createEl("button", "ultra-image-load-browse-item", `📁 ${entry.name}`);
            item.type = "button";
            item.addEventListener("click", () => loadBrowseDir(entry.path));
            browseListEl.appendChild(item);
        }
    }

    async function loadBrowseDir(path) {
        browseListEl.replaceChildren(createEl("div", "ultra-image-load-browse-status", tr("browseLoading")));
        browsingPreviewImages = [];
        if (alive()) render();
        addRootSelectButton.disabled = true;
        try {
            const response = await api.fetchApi(`/ultra_tools/image_load/browse_dirs?path=${encodeURIComponent(path)}`);
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload?.error || `${response.status} ${response.statusText}`);
            if (!alive()) return;
            browsePath = payload.path || "";
            browseParent = payload.parent ?? null;
            browsePathLabel.textContent = browsePath || tr("browseDrives");
            // Disabled only at the very top (the drive/root list itself —
            // browsePath === ""). At a drive's own root, browseParent is
            // null but browsePath is still set, so "up" stays enabled and
            // steps back out to the drive list (see the click handler).
            browseUpButton.disabled = !browsePath;
            addRootSelectButton.disabled = !browsePath;
            renderBrowseList(Array.isArray(payload.entries) ? payload.entries : []);
            browsingPreviewImages = Array.isArray(payload.images) ? payload.images : [];
            render();
        } catch (error) {
            console.error("[Ultra Tools Image Load] browse folder failed", error);
            if (alive()) browseListEl.replaceChildren(createEl("div", "ultra-image-load-browse-status", `${tr("browseFailed")} ${error?.message || error}`));
        }
    }

    // Swaps the main content grid over to a live preview of whatever
    // folder is currently open in the "+ 폴더 추가" panel — the same
    // thumbnails the person would see in the library view once this folder
    // is actually added, just not selectable/searchable/sortable yet since
    // it isn't a registered folder. Cleared back to the normal library view
    // the moment the panel closes or the folder is actually added.
    function renderBrowsingPreview() {
        imageObserver?.disconnect();
        content.replaceChildren();
        if (!browsingPreviewImages.length) {
            content.appendChild(createEl("div", "ultra-image-load-empty", browsePath ? tr("browseNoImages") : tr("browsePreviewHint")));
            return;
        }
        const grid = createEl("div", "ultra-image-load-grid");
        for (const image of browsingPreviewImages) {
            const tile = createEl("div", "ultra-image-load-tile");
            const img = createEl("img");
            img.alt = image.name;
            img.loading = "lazy";
            img.decoding = "async";
            img.src = browseThumbUrl(image.path, GRID_THUMB_MAX_DIMENSION);
            attachOriginalActions(img, {
                url: browseOriginalUrl(image.path),
                downloadUrl: browseOriginalUrl(image.path, true),
                filename: image.name,
                displayName: image.path || image.name,
            });
            const name = createEl("span", "ultra-image-load-name", image.name);
            tile.title = image.name;
            tile.append(img, name);
            grid.appendChild(tile);
        }
        content.appendChild(grid);
    }

    function rebuildFolderOptions() {
        const previous = folderSelect.value;
        const folders = collectFolders(items);
        folderSelect.setAttribute("aria-label", tr("inputAll"));
        folderSelect.replaceChildren(new Option(tr("inputAll"), ""));
        for (const folder of folders) folderSelect.add(new Option(folder, folder));
        folderSelect.value = folders.includes(previous) ? previous : "";
        folderSelect.hidden = folders.length === 0;
    }

    function updateLanguage() {
        locale = currentLocale();
        title.textContent = tr("title");
        updateTitleCount();
        closeButton.setAttribute("aria-label", tr("close"));
        thumbsButton.textContent = tr("thumbnails");
        listButton.textContent = tr("list");
        search.placeholder = tr("search");
        sortSelect.setAttribute("aria-label", tr("sortBy"));
        for (const option of sortSelect.options) {
            option.textContent = tr(`sort${option.value[0].toUpperCase()}${option.value.slice(1)}`);
        }
        sortDirButton.setAttribute("aria-label", tr(prefs.sortDir === "desc" ? "sortDesc" : "sortAsc"));
        refreshButton.textContent = tr("refresh");
        closeBrowserButton.textContent = tr("close");
        confirmButton.textContent = tr("select");
        thumbLabel.firstChild.textContent = `${tr("thumbSize")} `;
        manageFoldersButton.textContent = tr("manageFolders");
        renderFolderChips(lastRoots);
        openAddRootButton.textContent = tr("addRoot");
        openOriginalButton.textContent = tr("openOriginal");
        saveOriginalButton.textContent = tr("saveOriginal");
        copyOriginalButton.textContent = tr("copyOriginal");
        originalMenuTargetLabel.textContent = tr("menuTarget");
        deleteSelectedButton.textContent = `${tr("deleteSelected")} (${selectedValues.size})`;
        browseUpButton.textContent = tr("browseUp");
        if (!browsePath) browsePathLabel.textContent = tr("browseDrives");
        addRootLabelInput.placeholder = tr("browseLabelPlaceholder");
        addRootSelectButton.textContent = tr("addRootSelect");
        addRootCancelButton.textContent = tr("addRootCancel");
        rebuildFolderOptions();
        render();
        updateCandidate();
    }

    function filteredItems() {
        const query = search.value.trim().toLocaleLowerCase();
        const folder = folderSelect.value;
        return items.filter((item) => {
            const inFolder = !folder || item.folder === folder || item.folder.startsWith(`${folder}/`);
            return (!query || item.key.toLocaleLowerCase().includes(query)) && inFolder;
        });
    }

    function syncSelectionClasses() {
        content.querySelectorAll("[data-image-value]").forEach((element) => {
            element.classList.toggle("selected", selectedValues.has(element.dataset.imageValue));
        });
    }

    function choose(item, element, event = {}) {
        const additive = Boolean(event.ctrlKey || event.metaKey);
        const range = Boolean(event.shiftKey && selectionAnchor);
        let rangeApplied = false;
        if (range) {
            const visible = filteredItems();
            const anchorIndex = visible.findIndex((entry) => entry.value === selectionAnchor);
            const itemIndex = visible.findIndex((entry) => entry.value === item.value);
            if (anchorIndex >= 0 && itemIndex >= 0) {
                if (!additive) selectedValues.clear();
                const start = Math.min(anchorIndex, itemIndex);
                const end = Math.max(anchorIndex, itemIndex);
                for (const entry of visible.slice(start, end + 1)) selectedValues.add(entry.value);
                rangeApplied = true;
            }
        }
        if (!rangeApplied && additive) {
            if (selectedValues.has(item.value)) selectedValues.delete(item.value);
            else selectedValues.add(item.value);
            selectionAnchor = item.value;
        } else if (!rangeApplied) {
            selectedValues.clear();
            selectedValues.add(item.value);
            selectionAnchor = item.value;
        }
        selected = selectedValues.has(item.value)
            ? item
            : items.find((entry) => selectedValues.has(entry.value)) || null;
        syncSelectionClasses();
        updateCandidate();
        requestDimensions(selected);
        confirmButton.disabled = !selected;
    }

    function selectForContextMenu(item) {
        if (!selectedValues.has(item.value)) {
            selectedValues.clear();
            selectedValues.add(item.value);
            selectionAnchor = item.value;
        }
        selected = item;
        syncSelectionClasses();
        updateCandidate();
        requestDimensions(item);
        confirmButton.disabled = false;
    }

    function render() {
        if (browsingPreviewMode) {
            renderBrowsingPreview();
            return;
        }
        imageObserver?.disconnect();
        content.replaceChildren();
        thumbsButton.classList.toggle("active", prefs.view === "thumbs");
        listButton.classList.toggle("active", prefs.view === "list");
        const filtered = filteredItems();
        if (!filtered.length) {
            content.appendChild(createEl("div", "ultra-image-load-empty", tr("noImages")));
            return;
        }
        const shown = filtered.slice(0, visibleLimit);
        if (prefs.view === "thumbs") {
            const grid = createEl("div", "ultra-image-load-grid");
            for (const item of shown) {
                const tile = createEl("button", "ultra-image-load-tile");
                tile.type = "button";
                const image = createEl("img");
                image.alt = item.name;
                prepareItemImage(image, item);
                attachOriginalActions(image, {
                    url: originalUrl(item.value),
                    downloadUrl: originalUrl(item.value, true),
                    filename: item.name,
                    displayName: item.key,
                }, item);
                const name = createEl("span", "ultra-image-load-name", item.name);
                tile.title = item.key; // full "subfolder/name.ext" on hover
                tile.append(image, name);
                tile.dataset.imageValue = item.value;
                if (selectedValues.has(item.value)) tile.classList.add("selected");
                tile.addEventListener("click", (event) => choose(item, tile, event));
                tile.addEventListener("dblclick", () => chooseAndConfirm(item, tile));
                grid.appendChild(tile);
            }
            content.appendChild(grid);
        } else {
            const table = createEl("table", "ultra-image-load-table");
            const body = document.createElement("tbody");
            for (const item of shown) {
                const row = document.createElement("tr");
                const previewCell = document.createElement("td");
                const image = createEl("img", "ultra-image-load-list-preview");
                image.alt = "";
                prepareItemImage(image, item);
                attachOriginalActions(image, {
                    url: originalUrl(item.value),
                    downloadUrl: originalUrl(item.value, true),
                    filename: item.name,
                    displayName: item.key,
                }, item);
                previewCell.appendChild(image);
                const nameCell = createEl("td", "", item.name);
                nameCell.title = item.key; // full "subfolder/name.ext" on hover
                row.append(previewCell, nameCell);
                row.dataset.imageValue = item.value;
                if (selectedValues.has(item.value)) row.classList.add("selected");
                row.addEventListener("click", (event) => choose(item, row, event));
                row.addEventListener("dblclick", () => chooseAndConfirm(item, row));
                body.appendChild(row);
            }
            table.appendChild(body);
            content.appendChild(table);
        }
        if (filtered.length > visibleLimit) {
            const more = createEl("button", "ultra-image-load-more", `${tr("loadMore")} (${filtered.length - visibleLimit})`);
            more.type = "button";
            more.addEventListener("click", () => { visibleLimit += 120; render(); });
            content.appendChild(more);
        }
    }

    function setInputItems(values) {
        const previousActive = selected?.value;
        items = buildItems(values);
        sortItems();
        const available = new Set(items.map((item) => item.value));
        for (const value of [...selectedValues]) if (!available.has(value)) selectedValues.delete(value);
        selected = items.find((item) => item.value === previousActive && selectedValues.has(item.value))
            || items.find((item) => selectedValues.has(item.value))
            || null;
        if (!selected) {
            const current = items.find((item) => item.value === imageWidget.value) || null;
            if (current) {
                selectedValues.add(current.value);
                selected = current;
                selectionAnchor = current.value;
            }
        }
        updateTitleCount();
        // Same reasoning as the initial button state: if the refreshed list
        // still contains the node's current image, it's shown pre-selected,
        // so the button should already be usable rather than forced disabled.
        confirmButton.disabled = !selected;
        updateCandidate();
        requestDimensions(selected);
        visibleLimit = 120;
        refreshButton.disabled = false;
        rebuildFolderOptions();
        render();
    }

    closeButton.addEventListener("click", close);
    closeBrowserButton.addEventListener("click", close);
    backdrop.addEventListener("click", (event) => {
        if (event.target === backdrop) event.stopPropagation();
    });
    thumbsButton.addEventListener("click", () => { prefs.view = "thumbs"; savePrefs(prefs); render(); });
    listButton.addEventListener("click", () => { prefs.view = "list"; savePrefs(prefs); render(); });
    search.addEventListener("input", () => {
        // Debounced: typing "frog" fired render() 4 times back-to-back before
        // this — each rebuild tore down and recreated up to 120 tiles and
        // bounced the IntersectionObserver, re-issuing thumbnail requests for
        // whatever was visible each time. Waiting a beat for typing to pause
        // collapses that into a single rebuild.
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => { visibleLimit = 120; render(); }, 150);
    });
    folderSelect.addEventListener("change", () => { visibleLimit = 120; render(); });
    sortSelect.addEventListener("change", () => {
        prefs.sortField = sortSelect.value;
        savePrefs(prefs);
        sortItems();
        visibleLimit = 120;
        render();
    });
    sortDirButton.addEventListener("click", () => {
        prefs.sortDir = prefs.sortDir === "desc" ? "asc" : "desc";
        savePrefs(prefs);
        sortDirButton.textContent = prefs.sortDir === "desc" ? "↓" : "↑";
        sortDirButton.setAttribute("aria-label", tr(prefs.sortDir === "desc" ? "sortDesc" : "sortAsc"));
        sortItems();
        visibleLimit = 120;
        render();
    });
    thumbRange.addEventListener("input", () => {
        prefs.thumb = Number(thumbRange.value);
        dialog.style.setProperty("--uil-thumb", `${prefs.thumb}px`);
        savePrefs(prefs);
    });
    // manageFoldersButton just toggles the collapsed management panel —
    // most users who never add an external folder never see any of this.
    manageFoldersButton.addEventListener("click", () => {
        manageRow.hidden = !manageRow.hidden;
        if (!manageRow.hidden) {
            loadRoots();
        } else {
            addRootRow.hidden = true;
            if (browsingPreviewMode) {
                browsingPreviewMode = false;
                setLibraryControlsEnabled(true);
                render();
            }
        }
    });
    // "+ 폴더 추가" reveals the browser panel and opens it on the drive/root
    // list — no window.prompt(), no file/folder picker, just this dialog's
    // own styled panel driven entirely by /ultra_tools/image_load/browse_dirs.
    // The main content grid switches to previewing whatever folder is open
    // here (see loadBrowseDir/renderBrowsingPreview) until the panel closes
    // or the folder is actually added.
    openAddRootButton.addEventListener("click", () => {
        addRootRow.hidden = false;
        addRootLabelInput.value = "";
        browsingPreviewMode = true;
        setLibraryControlsEnabled(false);
        loadBrowseDir("");
    });
    addRootCancelButton.addEventListener("click", () => {
        addRootRow.hidden = true;
        browsingPreviewMode = false;
        setLibraryControlsEnabled(true);
        render();
    });
    // At a drive's root (browseParent is null but a folder IS open), "up"
    // steps back out to the drive/root list instead of going nowhere — so
    // repeatedly pressing it always eventually lands back on the initial
    // drive-selection screen.
    browseUpButton.addEventListener("click", () => {
        loadBrowseDir(browseParent != null ? browseParent : "");
    });
    async function submitAddRoot() {
        if (!browsePath) return; // still at the drive list — nothing concrete to add yet
        const label = addRootLabelInput.value.trim();
        addRootSelectButton.disabled = true;
        try {
            const response = await api.fetchApi("/ultra_tools/image_load/roots", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: browsePath, label }),
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload?.error || `${response.status} ${response.statusText}`);
            if (alive()) {
                addRootRow.hidden = true;
                browsingPreviewMode = false; // reloadAfterRootsChange()'s render() below will draw the combined library view
                setLibraryControlsEnabled(true);
            }
            await reloadAfterRootsChange();
        } catch (error) {
            console.error("[Ultra Tools Image Load] add folder failed", error);
            if (alive()) showMessage(`${tr("addRootFailed")} ${error?.message || error}`);
        } finally {
            if (alive()) addRootSelectButton.disabled = !browsePath;
        }
    }
    addRootSelectButton.addEventListener("click", submitAddRoot);
    // Enter in the display-name field submits the currently browsed folder,
    // same as clicking the button; Escape cancels the panel (handled by the
    // shared onKeyDown above) without closing the whole dialog.
    addRootLabelInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            submitAddRoot();
        }
    });
    refreshButton.addEventListener("click", async () => {
        refreshButton.disabled = true;
        loadFileMeta(); // independent of the combo-value refresh below; runs in parallel
        try {
            const values = await refreshInputValues(imageWidget);
            if (alive()) setInputItems(values);
        } catch (error) {
            console.error("[Ultra Tools Image Load] input refresh failed", error);
            if (alive()) showMessage(`${tr("refreshFailed")} ${error?.message || error}`);
        } finally {
            if (alive()) refreshButton.disabled = false;
        }
    });
    async function confirmSelection() {
        if (!selected) return;
        confirmButton.disabled = true;
        closeBrowserButton.disabled = true;
        closeButton.disabled = true;
        try {
            await applyImageValue(node, imageWidget, selected.value, selected.key);
            close();
        } catch (error) {
            if (alive()) {
                console.error("[Ultra Tools Image Load] selection failed", error);
                showMessage(`${tr("selectFailed")} ${error?.message || error}`);
                confirmButton.disabled = false;
                closeBrowserButton.disabled = false;
                closeButton.disabled = false;
            }
        }
    }

    // Single click: select + preview only (existing, safe default — lets you
    // check the filename/resolution in the footer before committing).
    // Double click: select AND apply immediately, like a typical OS file
    // dialog — a shortcut for when you already know it's the right file.
    function chooseAndConfirm(item, element) {
        choose(item, element);
        confirmSelection();
    }

    confirmButton.addEventListener("click", confirmSelection);

    let resizeTimer = null;
    const resizeObserver = typeof ResizeObserver === "function" ? new ResizeObserver(() => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            prefs.width = Math.round(dialog.getBoundingClientRect().width);
            prefs.height = Math.round(dialog.getBoundingClientRect().height);
            savePrefs(prefs);
        }, 120);
    }) : null;
    resizeObserver?.observe(dialog);
    document.addEventListener("keydown", onKeyDown, true);
    document.addEventListener("pointerdown", onDocumentPointerDown, true);
    content.addEventListener("scroll", hideOriginalMenu, { passive: true });
    document.body.appendChild(backdrop);
    rebuildFolderOptions();
    render();
    updateCandidate();
    requestDimensions(selected);
    loadFileMeta();
    loadRoots();
    // Always re-check the combo against the server on open, not just when
    // the refresh button is clicked — otherwise a folder registered in an
    // earlier dialog session (or from another tab) wouldn't show its images
    // until the user thought to press 새로고침 themselves.
    refreshInputValues(imageWidget)
        .then((values) => { if (alive()) setInputItems(values); })
        .catch(() => {});
    localeTimer = setInterval(() => {
        if (currentLocale() !== locale) updateLanguage();
    }, 1000);
    search.focus();
}

function findImageWidget(node) {
    return node?.widgets?.find((widget) => widget?.name === IMAGE_WIDGET) || null;
}

function isCoreUploadButton(widget) {
    if (!widget || widget[BUTTON_MARK]) return false;
    if (String(widget.type || "").toLowerCase() !== "button") return false;
    const name = String(widget.name || "").toLowerCase();
    return /upload|choose.*file|file.*choose|업로드|파일.*선택/.test(name);
}

function installBrowseButton(node) {
    const imageWidget = findImageWidget(node);
    if (!imageWidget) return;
    let browse = node.widgets?.find((widget) => widget?.[BUTTON_MARK]);
    if (!browse) {
        // No canvasOnly: since frontend 1.55 canvasOnly means "never show in
        // Nodes 2.0", which hid the thumbnail browser entirely there.
        browse = node.addWidget("button", "ultra_image_browser", "", () => openBrowser(node, imageWidget), { serialize: false });
        browse[BUTTON_MARK] = true;
        browse.serialize = false;
    }
    if (browse.options?.canvasOnly) {
        try { browse.options.canvasOnly = false; } catch (_) { /* older frontends */ }
    }
    browse.label = tr("browse");
    browse.callback = () => openBrowser(node, imageWidget);

    const upload = node.widgets?.find(isCoreUploadButton);
    const imageIndex = node.widgets?.indexOf(imageWidget) ?? -1;
    const browseIndex = node.widgets?.indexOf(browse) ?? -1;
    if (browseIndex >= 0) node.widgets.splice(browseIndex, 1);
    const uploadIndex = upload ? node.widgets.indexOf(upload) : -1;
    node.widgets.splice(uploadIndex >= 0 ? uploadIndex : Math.max(0, imageIndex + 1), 0, browse);
}

app.registerExtension({
    name: "Ultra.Tools.ImageLoadBrowser",
    setup() {
        prioritizeImageSuggestion();
    },
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== NODE_CLASS) return;
        registeredNodeData = nodeData;
        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        const originalOnConfigure = nodeType.prototype.onConfigure;
        const originalOnDrawForeground = nodeType.prototype.onDrawForeground;

        nodeType.prototype.onNodeCreated = function () {
            const result = originalOnNodeCreated?.apply(this, arguments);
            installBrowseButton(this);
            return result;
        };

        nodeType.prototype.onConfigure = function () {
            const result = originalOnConfigure?.apply(this, arguments);
            // onConfigure first restores widgets_values. Reconcile on the
            // next task so the graph and Vue widget bridge are fully attached.
            setTimeout(() => reconcileRestoredImageValue(this), 0);
            return result;
        };

        nodeType.prototype.onDrawForeground = function () {
            const result = originalOnDrawForeground?.apply(this, arguments);
            const browse = this.widgets?.find((widget) => widget?.[BUTTON_MARK]);
            const label = tr("browse");
            if (browse && browse.label !== label) browse.label = label;
            return result;
        };
    },
});
