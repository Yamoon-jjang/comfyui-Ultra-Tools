import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ultraFetchApi } from "./ultra_tools_security.js";

// Current frontends expose a DOM widget's element as widget.element;
// widget.inputEl is a deprecated alias (warns on access). Prefer element and
// fall back to inputEl only on older frontends that lack it.
function ultraWidgetEl(widget) {
  if (!widget) return undefined;
  return "element" in widget ? widget.element : widget.inputEl;
}


const DEFAULT_WILDCARDS_PATH = "F:\\models\\wildcards";
const ROOT_FOLDER_LABEL = "[Root]";
const LEGACY_ROOT_FOLDER_LABELS = new Set(["[최상위]"]);
const MAX_FOLDER_VALUE_LENGTH = 2048;
const CURRENT_SCHEMA_VERSION = 3;
const ACTIONABLE_ENTRY_TYPES = new Set(["folder", "parent", "file"]);

function showPopup(message, anchorX, anchorY, duration = 1200) {
    const existing = document.getElementById("wildcard-popup");
    if (existing) existing.remove();

    const popup = document.createElement("div");
    popup.id = "wildcard-popup";
    popup.textContent = message;
    popup.style.cssText = `
        position:fixed;
        background:#2a4a2a;
        color:#aaffaa;
        padding:6px 14px;
        border-radius:6px;
        font-size:12px;
        z-index:99999;
        pointer-events:none;
        box-shadow:0 2px 10px rgba(0,0,0,0.6);
        white-space:nowrap;
        max-width:calc(100vw - 12px);
        overflow:hidden;
        text-overflow:ellipsis;
        transition:opacity 0.3s;
        opacity:1;
    `;

    document.body.appendChild(popup);

    const pw = popup.offsetWidth;
    const ph = popup.offsetHeight;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    let left = anchorX - pw / 2;
    let top = anchorY - ph - 10;

    if (left < 6) left = 6;
    if (left + pw > vw - 6) left = vw - pw - 6;
    if (top < 6) top = anchorY + 16;
    if (top + ph > vh - 6) top = vh - ph - 6;

    popup.style.left = `${left}px`;
    popup.style.top = `${top}px`;

    setTimeout(() => {
        popup.style.opacity = "0";
        setTimeout(() => popup.remove(), 300);
    }, duration);
}

function setFileValue(fileWidget, textarea, value) {
    const text = String(value ?? "");
    fileWidget.value = text;
    textarea.value = text;
}

function isExplicitRootPath(value) {
    const v = String(value || "").trim();
    return !!v && (
        /^[A-Za-z]:[\\/]/.test(v) ||
        /^\\\\/.test(v) ||
        /^\//.test(v) ||
        /^~(?:[\\/]|$)/.test(v) ||
        /^%[^%]+%(?:[\\/]|$)/.test(v) ||
        /^\$[A-Za-z_][A-Za-z0-9_]*(?:[\\/]|$)/.test(v)
    );
}

function looksLikeLegacyFileList(value) {
    const v = String(value || "");
    if (!v) return false;
    return /[\r\n]/.test(v) || /^(?:__.+__|📁\s)/.test(v.trim());
}

function sanitizeStoredFolder(value) {
    const v = String(value || "").trim();
    if (!v || /[\r\n]/.test(v) || v.length > MAX_FOLDER_VALUE_LENGTH) return "";
    return LEGACY_ROOT_FOLDER_LABELS.has(v) ? ROOT_FOLDER_LABEL : v;
}

function isAbortError(error) {
    return error?.name === "AbortError";
}

app.registerExtension({
    name: "UltraWildcardBrowser.Extension",

    beforeRegisterNodeDef(nodeType, nodeData) {
        if (!["WildcardBrowser", "UltraWildcardBrowser"].includes(nodeData.name)) return;
        if (nodeType.prototype.__ultraWildcardBrowserPatched) return;
        nodeType.prototype.__ultraWildcardBrowserPatched = true;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalOnNodeCreated?.apply(this, arguments);
            const node = this;

            const pathWidget = node.widgets?.find(widget => widget.name === "wildcards_path");
            const folderWidget = node.widgets?.find(widget => widget.name === "folder");
            const fileWidget = node.widgets?.find(widget => widget.name === "file_list");

            if (!pathWidget || !folderWidget || !fileWidget) {
                console.error("[Wildcard] 필요한 위젯을 찾을 수 없습니다.", node.widgets);
                return result;
            }

            folderWidget.options = folderWidget.options || {};
            if (!Array.isArray(folderWidget.options.values)) folderWidget.options.values = [];

            const textarea = ultraWidgetEl(fileWidget);
            if (!textarea) {
                console.error("[Wildcard] textarea 요소를 찾을 수 없습니다.");
                return result;
            }

            textarea.readOnly = true;
            textarea.style.backgroundColor = "#1e1e1e";
            textarea.style.color = "#ccc";
            textarea.style.whiteSpace = "pre";
            textarea.style.overflowX = "auto";

            let disposed = false;
            let cachedLines = [];
            let cachedLineOffsets = [];
            let cachedEntries = [];
            let folderSeq = 0;
            let fileSeq = 0;
            let copySeq = 0;
            let folderController = null;
            let fileController = null;
            let copyFlashTimer = null;
            let pathRefreshTimer = null;
            let initialRefreshTimer = null;
            let cachedLineHeight = 16;
            let cachedPaddingTop = 0;
            let lastFolderWarning = "";

            const pathInput = ultraWidgetEl(pathWidget);

            // LiteGraph serializes widget.value directly. Keep the third widget slot for
            // backward compatibility, but replace the derived file list with an empty value
            // in the saved workflow so large folders do not bloat workflow JSON.
            const originalOnSerialize = node.onSerialize;
            node.onSerialize = function (serialized) {
                const serializeResult = originalOnSerialize?.apply(this, arguments);
                if (serialized && typeof serialized === "object") {
                    const fileWidgetIndex = this.widgets?.indexOf(fileWidget) ?? -1;
                    if (Array.isArray(serialized.widgets_values) && fileWidgetIndex >= 0) {
                        serialized.widgets_values[fileWidgetIndex] = "";
                    }
                    serialized.properties = serialized.properties || {};
                    serialized.properties.ultraWildcardBrowserSchema = CURRENT_SCHEMA_VERSION;
                }
                return serializeResult;
            };

            const applyLines = (lines, entries = []) => {
                cachedLines = lines;
                cachedEntries = entries;
                cachedLineOffsets = new Array(lines.length);
                let offset = 0;
                for (let index = 0; index < lines.length; index += 1) {
                    cachedLineOffsets[index] = offset;
                    offset += lines[index].length + 1;
                }
                setFileValue(fileWidget, textarea, lines.join("\n"));
            };

            const updateCache = (value, entries = []) => {
                applyLines(String(value || "").split("\n"), Array.isArray(entries) ? entries : []);
            };

            const setEntries = (entries, fallback = "No files or folders found") => {
                let normalized = Array.isArray(entries) ? entries.filter(Boolean) : [];
                if (!normalized.length) normalized = [{ type: "status", display: fallback }];
                applyLines(normalized.map(entry => String(entry.display || "")), normalized);
            };

            const getPathValue = () => String(pathWidget.value || "").trim();

            const invalidateRequests = ({ showLoading = false } = {}) => {
                folderSeq += 1;
                fileSeq += 1;
                copySeq += 1;
                folderController?.abort();
                fileController?.abort();
                folderController = null;
                fileController = null;
                if (showLoading) setEntries([{ type: "status", display: "Loading folders..." }]);
            };

            const migrateLegacyWidgetValues = (configuration = null) => {
                node.properties = node.properties || {};

                const savedValues = Array.isArray(configuration?.widgets_values)
                    ? configuration.widgets_values
                    : null;
                const savedSchema = Number(configuration?.properties?.ultraWildcardBrowserSchema);

                // Current schema values are authoritative. In particular, a relative root
                // and a folder whose name starts with "Loading" or "No files" are both
                // legitimate and must never be reinterpreted as a shifted old layout.
                if (configuration && Number.isFinite(savedSchema) && savedSchema >= 2) {
                    const normalizedFolder = sanitizeStoredFolder(folderWidget.value);
                    folderWidget.value = normalizedFolder || ROOT_FOLDER_LABEL;
                    node.properties.ultraWildcardBrowserSchema = CURRENT_SCHEMA_VERSION;
                    return false;
                }

                // onNodeCreated runs before a workflow configuration is applied. Do not use
                // heuristics against fresh/default widget values at that stage.
                if (!savedValues) {
                    node.properties.ultraWildcardBrowserSchema = CURRENT_SCHEMA_VERSION;
                    return false;
                }

                const definiteTwoWidgetLayout = savedValues.length === 2;
                const pathValue = String(savedValues[0] || "").trim();
                const shiftedListValue = String(savedValues[1] || "");
                const trailingValue = String(savedValues[2] || "");
                const conservativeThreeWidgetRecovery = (
                    savedValues.length >= 3 &&
                    !trailingValue.trim() &&
                    pathValue &&
                    !isExplicitRootPath(pathValue) &&
                    looksLikeLegacyFileList(shiftedListValue)
                );
                const confidentlyShifted = definiteTwoWidgetLayout || conservativeThreeWidgetRecovery;

                if (confidentlyShifted) {
                    pathWidget.value = DEFAULT_WILDCARDS_PATH;
                    folderWidget.value = sanitizeStoredFolder(pathValue) || ROOT_FOLDER_LABEL;
                    setFileValue(fileWidget, textarea, shiftedListValue);
                    updateCache(shiftedListValue);
                }

                node.properties.ultraWildcardBrowserSchema = CURRENT_SCHEMA_VERSION;
                return confidentlyShifted;
            };

            const scheduleFolderRefresh = (preserve = false) => {
                invalidateRequests({ showLoading: true });
                if (pathRefreshTimer) clearTimeout(pathRefreshTimer);
                pathRefreshTimer = setTimeout(() => {
                    pathRefreshTimer = null;
                    if (!disposed) node.updateFolders({ preserve });
                }, 180);
            };

            const originalPathCallback = pathWidget.callback;
            const onPathWidgetCallback = function (...args) {
                const callbackResult = originalPathCallback?.apply(this, args);
                pathWidget.value = args[0];
                scheduleFolderRefresh(false);
                return callbackResult;
            };
            pathWidget.callback = onPathWidgetCallback;

            const onPathInputCommit = () => scheduleFolderRefresh(false);
            pathInput?.addEventListener?.("change", onPathInputCommit);
            pathInput?.addEventListener?.("blur", onPathInputCommit);

            const originalFolderCallback = folderWidget.callback;
            const onFolderWidgetCallback = function (...args) {
                const callbackResult = originalFolderCallback?.apply(this, args);
                const value = sanitizeStoredFolder(args[0]);
                folderWidget.value = value || ROOT_FOLDER_LABEL;
                setEntries([{ type: "status", display: "Loading..." }]);
                node.updateFiles(folderWidget.value);
                return callbackResult;
            };
            folderWidget.callback = onFolderWidgetCallback;

            function entryAt(lineNum) {
                return cachedEntries[lineNum] || null;
            }

            function isValidWildcardLine(line) {
                return /^__.+__$/.test(String(line || "").trim());
            }

            function measureNormalLineHeight(computedStyle) {
                const probe = document.createElement("div");
                probe.textContent = "M";
                probe.style.position = "fixed";
                probe.style.left = "-10000px";
                probe.style.top = "0";
                probe.style.visibility = "hidden";
                probe.style.pointerEvents = "none";
                probe.style.whiteSpace = "pre";
                probe.style.padding = "0";
                probe.style.margin = "0";
                probe.style.border = "0";
                probe.style.fontFamily = computedStyle.fontFamily;
                probe.style.fontSize = computedStyle.fontSize;
                probe.style.fontStyle = computedStyle.fontStyle;
                probe.style.fontWeight = computedStyle.fontWeight;
                probe.style.fontStretch = computedStyle.fontStretch;
                probe.style.letterSpacing = computedStyle.letterSpacing;
                probe.style.lineHeight = computedStyle.lineHeight;
                document.body.appendChild(probe);

                const oneLine = probe.getBoundingClientRect().height;
                probe.textContent = "M\nM";
                const twoLines = probe.getBoundingClientRect().height;
                probe.remove();

                const measured = twoLines - oneLine;
                return Number.isFinite(measured) && measured > 0 ? measured : 0;
            }

            function updateTextareaMetrics() {
                if (disposed) return;
                const computedStyle = window.getComputedStyle(textarea);
                let lineHeight = Number.parseFloat(computedStyle.lineHeight);
                if (!Number.isFinite(lineHeight) || lineHeight <= 0) {
                    lineHeight = measureNormalLineHeight(computedStyle);
                }
                if (!Number.isFinite(lineHeight) || lineHeight <= 0) {
                    const fontSize = Number.parseFloat(computedStyle.fontSize);
                    lineHeight = Number.isFinite(fontSize) && fontSize > 0 ? fontSize : 16;
                }
                cachedLineHeight = lineHeight;
                cachedPaddingTop = Number.parseFloat(computedStyle.paddingTop) || 0;
            }

            function lineNumberFromPointer(event) {
                const contentY = Math.max(0, event.offsetY + textarea.scrollTop - cachedPaddingTop);
                return Math.floor(contentY / Math.max(cachedLineHeight, 1));
            }

            function lineNumberFromSelection(position = textarea.selectionStart) {
                if (!cachedLineOffsets.length) return -1;

                const numericPosition = Number(position);
                const clampedPosition = Math.max(
                    0,
                    Math.min(
                        Number.isFinite(numericPosition) ? numericPosition : 0,
                        textarea.value.length,
                    ),
                );

                let low = 0;
                let high = cachedLineOffsets.length - 1;
                let lineNum = 0;

                while (low <= high) {
                    const middle = (low + high) >> 1;
                    if (cachedLineOffsets[middle] <= clampedPosition) {
                        lineNum = middle;
                        low = middle + 1;
                    } else {
                        high = middle - 1;
                    }
                }

                return lineNum;
            }

            function lineNumberFromCaretPoint(event) {
                const caret = document.caretPositionFromPoint?.(event.clientX, event.clientY);
                if (caret?.offsetNode === textarea && Number.isFinite(caret.offset)) {
                    const caretRect = caret.getClientRect?.();
                    if (
                        !caretRect ||
                        (event.clientY >= caretRect.top - 1 && event.clientY <= caretRect.bottom + 1)
                    ) {
                        return lineNumberFromSelection(caret.offset);
                    }
                    return -1;
                }

                // Older browsers may not expose native textarea caret hit-testing.
                return lineNumberFromPointer(event);
            }

            updateTextareaMetrics();
            requestAnimationFrame(updateTextareaMetrics);
            textarea.addEventListener("mouseenter", updateTextareaMetrics);
            textarea.addEventListener("focus", updateTextareaMetrics);
            if (document.fonts?.ready) {
                document.fonts.ready.then(() => {
                    if (!disposed) updateTextareaMetrics();
                }).catch(() => {});
            }
            const onWindowResize = () => updateTextareaMetrics();
            window.addEventListener?.("resize", onWindowResize);

            const onTextareaMouseMove = event => {
                // Use the browser's native textarea caret hit-test so folder emoji rows,
                // font fallback, zoom, and theme metrics cannot accumulate vertical drift.
                const lineNum = lineNumberFromCaretPoint(event);
                const line = cachedLines[lineNum]?.trim();
                const entry = entryAt(lineNum);
                const actionable = entry
                    ? ACTIONABLE_ENTRY_TYPES.has(entry.type)
                    : isValidWildcardLine(line);
                const nextCursor = actionable ? "pointer" : "text";
                if (textarea.style.cursor !== nextCursor) textarea.style.cursor = nextCursor;
            };
            textarea.addEventListener("mousemove", onTextareaMouseMove);

            async function copyToClipboard(text) {
                try {
                    if (navigator.clipboard?.writeText) {
                        await navigator.clipboard.writeText(text);
                        return true;
                    }
                } catch (_error) {
                    // Fall through to the legacy browser copy path.
                }

                const temporary = document.createElement("textarea");
                temporary.value = text;
                temporary.setAttribute("readonly", "");
                temporary.style.position = "fixed";
                temporary.style.opacity = "0";
                document.body.appendChild(temporary);
                temporary.select();
                try {
                    return document.execCommand("copy");
                } catch (_error) {
                    return false;
                } finally {
                    temporary.remove();
                }
            }

            const onTextareaClick = event => {
                // Use the same native point hit-test as hover. selectionStart alone maps clicks
                // in the empty area below the list to the final line, which can copy the last
                // wildcard even though no row was clicked.
                const lineNum = lineNumberFromCaretPoint(event);
                if (lineNum < 0 || lineNum >= cachedLines.length) return;

                const line = cachedLines[lineNum]?.trim();
                const entry = entryAt(lineNum);

                if (entry?.type === "folder" || entry?.type === "parent") {
                    const targetFolder = sanitizeStoredFolder(entry.path);
                    if (!targetFolder) return;
                    folderWidget.value = targetFolder;
                    setEntries([{ type: "status", display: "Loading..." }]);
                    node.setDirtyCanvas(true, true);
                    node.updateFiles(targetFolder);
                    return;
                }

                if (entry && entry.type !== "file") return;
                if (!isValidWildcardLine(line)) return;

                const copyText = String(entry?.copy || line);
                const currentCopySeq = ++copySeq;
                const popupX = event.clientX;
                const popupY = event.clientY;

                const startPosition = cachedLineOffsets[lineNum] ?? 0;
                const endPosition = startPosition + cachedLines[lineNum].length;
                textarea.setSelectionRange(startPosition, endPosition);
                textarea.focus();

                copyToClipboard(copyText).then(copied => {
                    if (disposed || currentCopySeq !== copySeq) return;
                    if (!copied) {
                        showPopup("복사 실패: 브라우저 클립보드 권한을 확인하세요.", popupX, popupY, 1800);
                        return;
                    }

                    textarea.style.backgroundColor = "#2a4a2a";
                    if (copyFlashTimer) clearTimeout(copyFlashTimer);
                    copyFlashTimer = setTimeout(() => {
                        copyFlashTimer = null;
                        if (!disposed) textarea.style.backgroundColor = "#1e1e1e";
                    }, 800);
                    showPopup(`복사됨: ${copyText}`, popupX, popupY);
                });
            };
            textarea.addEventListener("click", onTextareaClick);

            node.updateFolders = async function ({ preserve = true } = {}) {
                if (disposed) return;

                folderController?.abort();
                fileController?.abort();
                fileController = null;
                folderController = new AbortController();

                const seq = ++folderSeq;
                fileSeq += 1;
                copySeq += 1;
                const requestPath = getPathValue();
                setEntries([{ type: "status", display: "Loading folders..." }]);

                try {
                    const response = await ultraFetchApi("/Ultra-wildcard_browser/folders", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ wildcards_path: requestPath }),
                        signal: folderController.signal,
                    });
                    const data = await response.json().catch(() => ({}));
                    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
                    if (disposed || seq !== folderSeq || requestPath !== getPathValue()) return;

                    if (data.path_defaulted && data.default_path) pathWidget.value = data.default_path;

                    const folders = Array.isArray(data.folders) && data.folders.length
                        ? data.folders.map(String)
                        : [ROOT_FOLDER_LABEL];
                    folderWidget.options = folderWidget.options || {};
                    folderWidget.options.values = folders;

                    const warning = String(data.warning || "").trim();
                    if (warning && warning !== lastFolderWarning) {
                        lastFolderWarning = warning;
                        console.warn(`[Wildcard] ${warning}`);
                        showPopup(`주의: ${warning}`, window.innerWidth / 2, 52, 3000);
                    } else if (!warning) {
                        lastFolderWarning = "";
                    }

                    const previousFolder = sanitizeStoredFolder(folderWidget.value);
                    const nextFolder = preserve && previousFolder ? previousFolder : folders[0];
                    folderWidget.value = nextFolder || ROOT_FOLDER_LABEL;
                    node.setDirtyCanvas(true, true);

                    if (data.ok === false) {
                        setEntries([{ type: "status", display: `Error: ${data.error || "폴더를 읽을 수 없습니다."}` }]);
                        return;
                    }

                    node.updateFiles(folderWidget.value);
                } catch (error) {
                    if (disposed || seq !== folderSeq || isAbortError(error)) return;
                    console.error("[Wildcard] Folder refresh error:", error);
                    setEntries([{ type: "status", display: `Error: ${error.message}` }]);
                    node.setDirtyCanvas(true, true);
                }
            };

            node.updateFiles = async function (selectedFolder = null) {
                if (disposed) return;

                fileController?.abort();
                fileController = new AbortController();

                const seq = ++fileSeq;
                copySeq += 1;
                const folder = sanitizeStoredFolder(
                    selectedFolder ?? folderWidget.value ?? folderWidget.options?.values?.[0]
                ) || ROOT_FOLDER_LABEL;
                const requestPath = getPathValue();

                setEntries([{ type: "status", display: "Loading..." }]);

                try {
                    const response = await ultraFetchApi("/Ultra-wildcard_browser/get_files", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ folder, wildcards_path: requestPath }),
                        signal: fileController.signal,
                    });
                    const data = await response.json().catch(() => ({}));
                    if (!response.ok || data.ok === false) {
                        throw new Error(data.error || `HTTP ${response.status}`);
                    }
                    if (disposed || seq !== fileSeq) return;
                    if (folderWidget.value !== folder || requestPath !== getPathValue()) return;

                    setEntries(data.entries);
                    node.setDirtyCanvas(true, true);
                } catch (error) {
                    if (disposed || seq !== fileSeq || isAbortError(error)) return;
                    console.error("[Wildcard] File refresh error:", error);
                    setEntries([{ type: "status", display: `Error: ${error.message}` }]);
                    node.setDirtyCanvas(true, true);
                }
            };

            const scheduleInitialRefresh = (delay = 100) => {
                if (initialRefreshTimer) clearTimeout(initialRefreshTimer);
                initialRefreshTimer = setTimeout(() => {
                    initialRefreshTimer = null;
                    if (!disposed) node.updateFolders({ preserve: true });
                }, delay);
            };

            node._wildcardMigrateLegacy = migrateLegacyWidgetValues;
            node._wildcardScheduleInitialRefresh = scheduleInitialRefresh;
            migrateLegacyWidgetValues();

            if (!sanitizeStoredFolder(folderWidget.value)) {
                folderWidget.value = folderWidget.options.values[0] || ROOT_FOLDER_LABEL;
            }
            scheduleInitialRefresh(120);

            const originalOnRemoved = node.onRemoved;
            node.onRemoved = function () {
                disposed = true;
                folderSeq += 1;
                fileSeq += 1;
                copySeq += 1;
                folderController?.abort();
                fileController?.abort();
                if (pathRefreshTimer) clearTimeout(pathRefreshTimer);
                if (initialRefreshTimer) clearTimeout(initialRefreshTimer);
                if (copyFlashTimer) clearTimeout(copyFlashTimer);
                window.removeEventListener?.("resize", onWindowResize);
                textarea.removeEventListener("mouseenter", updateTextareaMetrics);
                textarea.removeEventListener("focus", updateTextareaMetrics);
                textarea.removeEventListener("mousemove", onTextareaMouseMove);
                textarea.removeEventListener("click", onTextareaClick);
                pathInput?.removeEventListener?.("change", onPathInputCommit);
                pathInput?.removeEventListener?.("blur", onPathInputCommit);
                delete this._wildcardMigrateLegacy;
                delete this._wildcardScheduleInitialRefresh;
                return originalOnRemoved?.apply(this, arguments);
            };

            return result;
        };

        const originalOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = originalOnConfigure?.apply(this, arguments);
            this._wildcardMigrateLegacy?.(arguments[0]);
            this._wildcardScheduleInitialRefresh?.(30);
            return result;
        };
    },
});
