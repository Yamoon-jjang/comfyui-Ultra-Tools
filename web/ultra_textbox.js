import { app } from "../../scripts/app.js";

// Current frontends expose a DOM widget's element as widget.element;
// widget.inputEl is a deprecated alias (warns on access). Prefer element and
// fall back to inputEl only on older frontends that lack it.
function ultraWidgetEl(widget) {
  if (!widget) return undefined;
  return "element" in widget ? widget.element : widget.inputEl;
}


const MAX_TEXT_ENTRIES = 32;
const STATE_VERSION = 2;
const STATE_MARKER = "__ultra_textbox_multi__";
const MIN_ROW_HEIGHT = 96;
const MIN_NODE_WIDTH = 340;
const TEXTAREA_SIDE_INSET = 3;
// Header-only side padding (label / ⋀⋁ / × / Copy row). Kept separate from
// TEXTAREA_SIDE_INSET so widening the header gap never shrinks the textarea
// or thickens the node border — it only pulls the label and Copy button in
// from the node's edges a bit further.
const HEADER_SIDE_INSET = 6;
const ROW_HEADER_HEIGHT = 22;
// Keep Text 1's upper spacing as the visual reference. Tighten only the
// spacing below Text 1 and around later Text N headers by exactly 1px.
const ROW_INTER_GAP = 0;
const FIRST_ROW_PANEL_GAP = 1;
const FIRST_ROW_HEADER_TOP_PAD = 2;

const ULTRA_TEXTBOX_STYLE_ID = "ultra-textbox-placeholder-style";

// ON: every OUT socket shows the backend variable name ("Text N"), even for
// rows with a custom name. OFF: custom name if set, otherwise "OUT N" - see
// updateRowUi(). Stored on node.properties so LiteGraph serializes/restores
// it automatically with the rest of the node, no separate save/load code
// needed.
const VAR_NAME_DISPLAY_PROPERTY = "ultraVarNameDisplay";
const VAR_NAME_TITLE_TOGGLE_INSTALLED = new WeakSet();
const VAR_NAME_TITLE_CONTROL_WIDTH = 64;
const VAR_NAME_TITLE_CONTROL_HEIGHT = 18;
const VAR_NAME_TITLE_CONTROL_RIGHT_GAP = 18;

function isVarNameDisplayOn(node) {
    return !!node?.properties?.[VAR_NAME_DISPLAY_PROPERTY];
}

function setVarNameDisplay(node, on) {
    node.properties ||= {};
    node.properties[VAR_NAME_DISPLAY_PROPERTY] = !!on;
}

// Nodes 2.0 (Vue node renderer) never calls node.onDrawForeground and skips
// LiteGraph's node-level onMouseDown entirely, so the canvas-drawn title
// toggle below is invisible and unclickable there. In that mode the same
// switch is rendered as a small DOM button inside Text 1's row header
// instead. Classic canvas mode keeps the original title-bar control.
function isVueNodesMode() {
    return !!globalThis?.LiteGraph?.vueNodesMode;
}

function toggleVarNameDisplay(node) {
    setVarNameDisplay(node, !isVarNameDisplayOn(node));
    updateRowUi(node);
    persistState(node);
    node.setDirtyCanvas?.(true, true);
    node.graph?.setDirtyCanvas?.(true, true);
}

function syncVarNameDomToggles(node) {
    const rows = node?._ultraRows || [];
    const vue = isVueNodesMode();
    const on = isVarNameDisplayOn(node);
    rows.forEach((row, index) => {
        const button = row?.varToggle;
        if (!button) return;
        const show = vue && index === 0;
        const display = show ? "inline-flex" : "none";
        if (button.style.display !== display) button.style.display = display;
        if (!show) return;
        const text = on ? "변수명 ON" : "변수명 OFF";
        if (button.textContent !== text) button.textContent = text;
        button.style.borderColor = on ? "rgba(255,255,255,0.62)" : "rgba(255,255,255,0.34)";
        button.style.color = on ? "rgba(245,247,250,0.82)" : "rgba(215,218,224,0.50)";
    });
}

function ensureUltraTextboxStyles() {
    if (document.getElementById(ULTRA_TEXTBOX_STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = ULTRA_TEXTBOX_STYLE_ID;
    style.textContent = `
        textarea.ultra-textbox-editor::placeholder {
            color: rgba(230, 230, 230, 0.38) !important;
            -webkit-text-fill-color: rgba(230, 230, 230, 0.38) !important;
            opacity: 1 !important;
        }
        textarea.ultra-textbox-editor:placeholder-shown {
            color: rgba(230, 230, 230, 0.38) !important;
            -webkit-text-fill-color: rgba(230, 230, 230, 0.38) !important;
        }
        textarea.ultra-textbox-editor:not(:placeholder-shown) {
            color: #e6e6e6 !important;
            -webkit-text-fill-color: #e6e6e6 !important;
        }
    `;
    document.head.appendChild(style);
}

function makeId() {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
    return `utb_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

function normalizeEntry(item) {
    if (item && typeof item === "object" && !Array.isArray(item)) {
        return {
            id: typeof item.id === "string" && item.id ? item.id : makeId(),
            text: item.text == null ? "" : String(item.text),
            label: typeof item.label === "string" ? item.label.trim() : "",
        };
    }
    return { id: makeId(), text: item == null ? "" : String(item), label: "" };
}

function parseState(raw) {
    const legacy = raw == null ? "" : String(raw);
    try {
        const parsed = JSON.parse(legacy);
        if (
            parsed &&
            typeof parsed === "object" &&
            !Array.isArray(parsed) &&
            parsed[STATE_MARKER] === STATE_VERSION &&
            Array.isArray(parsed.entries)
        ) {
            const entries = parsed.entries.slice(0, MAX_TEXT_ENTRIES).map(normalizeEntry);
            return entries.length ? entries : [normalizeEntry("")];
        }
    } catch {
        // Legacy Ultra Textbox value: plain text, not JSON.
    }
    return [normalizeEntry(legacy)];
}

function serializeState(entries) {
    return JSON.stringify({
        [STATE_MARKER]: STATE_VERSION,
        entries: entries.slice(0, MAX_TEXT_ENTRIES).map((entry) => ({
            id: entry.id,
            text: entry.text == null ? "" : String(entry.text),
            label: entry.label ? String(entry.label).trim() : "",
        })),
    });
}

function getStateWidget(node) {
    return node?._ultraStateWidget || node?.widgets?.find((w) => w?.name === "text");
}

// OUT N socket labels are drawn directly on the LiteGraph/Vue canvas, not via
// DOM/CSS, so a long custom label has no ellipsis and instead stretches or
// overlaps the node's slot layout. Cap the on-canvas text by *display width*
// rather than character count: Korean/CJK characters render roughly twice as
// wide as Latin/ASCII characters, so a character-count cap makes Korean
// labels look far shorter on-screen than English ones of the same length.
// Width budget matches the example "서울시 금호동 사칠 구 번지" (11 Hangul
// chars * 2 + 4 spaces * 1 = 26), so a Latin label gets roughly 26 characters
// while a Korean label gets roughly 13 before being cut off. The full name is
// still visible in the Text N row header above the textarea.
const OUTPUT_LABEL_MAX_WIDTH = 26;

function displayWidth(str) {
    let width = 0;
    for (const ch of str) {
        width += ch.codePointAt(0) > 0xff ? 2 : 1;
    }
    return width;
}

function truncateForSocket(text, maxWidth = OUTPUT_LABEL_MAX_WIDTH) {
    const value = String(text ?? "");
    if (displayWidth(value) <= maxWidth) return value;

    let width = 0;
    let result = "";
    for (const ch of value) {
        const chWidth = ch.codePointAt(0) > 0xff ? 2 : 1;
        if (width + chWidth > maxWidth - 1) break; // reserve 1 for the ellipsis
        result += ch;
        width += chWidth;
    }
    return `${result}…`;
}

function sourceNameForRow(index) {
    return index === 0 ? "source" : `source_${index + 1}`;
}

function isUltraSourceName(name) {
    if (name === "source") return true;
    const match = /^source_(\d+)$/.exec(name || "");
    if (!match) return false;
    const index = Number(match[1]);
    return Number.isInteger(index) && index >= 2 && index <= MAX_TEXT_ENTRIES;
}

function getSourceInputs(node) {
    return (node?.inputs || []).filter((input) => isUltraSourceName(input?.name));
}

function getSourceInput(node, rowIndex) {
    const wanted = sourceNameForRow(rowIndex);
    return node?.inputs?.find((input) => input?.name === wanted) || null;
}

function rememberNativeSourceShape(node) {
    if (Object.prototype.hasOwnProperty.call(node || {}, "_ultraNativeSourceShape")) return;
    const source = getSourceInputs(node)[0];
    if (source) node._ultraNativeSourceShape = source.shape;
}

function applyNativeSourceShape(node, input) {
    if (!input || !Object.prototype.hasOwnProperty.call(node || {}, "_ultraNativeSourceShape")) return;
    const shape = node._ultraNativeSourceShape;
    if (shape == null) delete input.shape;
    else input.shape = shape;
}

// ---------------------------------------------------------------------------
// Link access compatible with both frontend generations.
//
// Frontend 1.55+ keeps connectivity in a central link store: input.link /
// output.links are deprecated store-derived views (assigning to them either
// does nothing or *disconnects*), and the supported way to re-point an
// existing link is writing link.origin_slot / link.target_slot, which updates
// the store. Older frontends still keep the plain slot fields, so those are
// used only when the store API is not present.
// ---------------------------------------------------------------------------
function usesLinkStore(node) {
    return typeof node?.getInputLink === "function" && typeof node?.isInputConnected === "function";
}

function inputSlotLinkId(node, slot) {
    if (slot == null || slot < 0) return null;
    if (usesLinkStore(node)) {
        // A node that is not (yet) in a graph has no links; the store API
        // throws NullGraphError in that state (e.g. during onNodeCreated).
        if (!node.graph) return null;
        try {
            return node.getInputLink(slot)?.id ?? null;
        } catch (_) {
            return null;
        }
    }
    return node?.inputs?.[slot]?.link ?? null;
}

function graphLinkObjects(graph) {
    const links = graph?.links;
    if (!links) return [];
    if (typeof links.values === "function" && !Array.isArray(links)) return [...links.values()];
    return Object.values(links);
}

function outputSlotLinkIds(node, slot) {
    if (slot == null || slot < 0) return [];
    if (usesLinkStore(node)) {
        if (!node.graph) return [];
        return graphLinkObjects(node.graph)
            .filter((link) => link && link.origin_id === node.id && link.origin_slot === slot)
            .map((link) => link.id);
    }
    const links = node?.outputs?.[slot]?.links;
    return Array.isArray(links) ? links.slice() : [];
}

function isSourceConnected(node, rowIndex) {
    const input = getSourceInput(node, rowIndex);
    if (!input) return false;
    return inputSlotLinkId(node, node.inputs.indexOf(input)) != null;
}

function hideStateWidget(widget) {
    if (!widget || widget._ultraStateHidden) return;
    widget._ultraStateHidden = true;
    widget.serialize = true;
    widget.hidden = true;
    widget.computeSize = () => [0, 0];
    if (ultraWidgetEl(widget)) {
        ultraWidgetEl(widget).style.display = "none";
        ultraWidgetEl(widget).setAttribute("aria-hidden", "true");
        ultraWidgetEl(widget).tabIndex = -1;
    }
}


function isHiddenStateInput(input, stateWidget) {
    if (!input || !stateWidget) return false;
    if (isUltraSourceName(input.name)) return false;
    const widgetName = input.widget?.name ?? input._widget?.name;
    return widgetName === stateWidget.name || input._widget === stateWidget;
}

function removeHiddenStateInputSlot(node) {
    const stateWidget = getStateWidget(node);
    if (!stateWidget || !Array.isArray(node?.inputs)) return false;

    const stateIndex = node.inputs.findIndex((input) => isHiddenStateInput(input, stateWidget));
    if (stateIndex < 0) return false;

    const stateInput = node.inputs[stateIndex];
    const sourceInput = getSourceInput(node, 0);
    const stateLinkId = inputSlotLinkId(node, stateIndex);

    if (stateLinkId != null) {
        // Older/original workflows may have connected the multiline widget itself.
        // The multi node has a dedicated editable IN 1, so migrate that one legacy
        // link when IN 1 is free. This avoids silently losing an old connection.
        if (sourceInput && inputSlotLinkId(node, node.inputs.indexOf(sourceInput)) == null && node.graph) {
            const sourceIndex = node.inputs.indexOf(sourceInput);
            // Use the same lookup as relinkOutputsAfterSwap/relinkSourceInputsAfterSwap
            // below (graphLinkById handles both the plain-object and Map link stores
            // different ComfyUI frontend versions use). A bare `.get?.()` call here
            // previously returned undefined whenever the graph used the plain-object
            // form, which silently dropped this migration into the disconnect branch.
            const link = graphLinkById(node, stateLinkId);
            if (sourceIndex >= 0 && link) {
                if (usesLinkStore(node)) {
                    // Store-backed frontend: re-pointing the link moves it.
                    // (Assigning stateInput.link = null here would disconnect it.)
                    link.target_slot = sourceIndex;
                } else {
                    stateInput.link = null;
                    sourceInput.link = stateLinkId;
                    // removeInput() will shift this index automatically when the
                    // hidden state slot is located before IN 1.
                    link.target_slot = sourceIndex;
                }
            } else {
                node.disconnectInput?.(stateIndex, true);
            }
        } else if (node.graph) {
            // IN 1 already has a real connection: keep it authoritative and
            // discard the obsolete hidden-widget connection.
            node.disconnectInput?.(stateIndex, true);
        } else {
            // Configuration can briefly run before the graph owns the node.
            // Do not orphan a legacy link; retry after configuration instead.
            return false;
        }
    }

    const currentIndex = node.inputs.indexOf(stateInput);
    if (currentIndex >= 0) node.removeInput(currentIndex);
    hideStateWidget(stateWidget);
    return true;
}

function persistState(node) {
    const widget = getStateWidget(node);
    if (!widget || !Array.isArray(node._ultraEntries)) return;
    const value = serializeState(node._ultraEntries);
    if (widget.value !== value) widget.value = value;
    if (ultraWidgetEl(widget) && ultraWidgetEl(widget).value !== value) ultraWidgetEl(widget).value = value;
}

async function copyTextToClipboard(text) {
    const value = text == null ? "" : String(text);
    try {
        await navigator.clipboard.writeText(value);
        return true;
    } catch {
        let ta = null;
        try {
            ta = document.createElement("textarea");
            ta.value = value;
            ta.setAttribute("readonly", "");
            ta.style.position = "fixed";
            ta.style.opacity = "0";
            ta.style.pointerEvents = "none";
            document.body.appendChild(ta);
            ta.select();
            return !!document.execCommand("copy");
        } catch {
            return false;
        } finally {
            if (ta?.parentNode) ta.parentNode.removeChild(ta);
        }
    }
}

function styleButton(button, kind = "normal") {
    const compact = kind === "delete" || kind === "move";
    Object.assign(button.style, {
        // Keep the row controls visually lighter than the 22px header itself.
        // The header's align-items:center then gives them equal top/bottom air.
        height: compact ? "18px" : "22px",
        minWidth: kind === "delete" ? "24px" : kind === "move" ? "20px" : "46px",
        padding: compact ? "0 4px" : "0 9px",
        border: "1px solid rgba(255,255,255,0.16)",
        borderRadius: compact ? "4px" : "5px",
        background: kind === "delete" ? "rgba(135,45,45,0.42)" : "rgba(255,255,255,0.07)",
        color: "rgba(255,255,255,0.88)",
        fontSize: "11px",
        display: compact ? "inline-flex" : "inline-block",
        alignItems: compact ? "center" : "normal",
        justifyContent: compact ? "center" : "normal",
        lineHeight: compact ? "1" : "20px",
        textAlign: "center",
        cursor: "pointer",
        boxSizing: "border-box",
        flex: "0 0 auto",
        pointerEvents: "auto",
    });
    button.addEventListener("mouseenter", () => {
        if (button.disabled) return;
        button.style.background = kind === "delete" ? "rgba(165,55,55,0.62)" : "rgba(255,255,255,0.12)";
    });
    button.addEventListener("mouseleave", () => {
        if (button.disabled) return;
        button.style.background = kind === "delete" ? "rgba(135,45,45,0.42)" : "rgba(255,255,255,0.07)";
    });
}

// DOM-button counterpart of the compact row controls.
// Keep Copy the same outer height as ⋀ / ⋁ / ×; only the glyph baseline gets
// a tiny optical correction so the button itself never looks shorter.
function styleTitleControlButton(button, { minWidth = "0" } = {}) {
    Object.assign(button.style, {
        height: "18px",
        minWidth,
        // With border-box sizing this keeps the outer box at 18px while
        // nudging only the text very slightly upward inside the flex box.
        padding: "0 7px 1px",
        border: "1px solid rgba(255,255,255,0.62)",
        borderRadius: "4px",
        background: "transparent",
        color: "rgba(245,247,250,0.82)",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        fontSize: "10.5px",
        fontWeight: "400",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        lineHeight: "1",
        textAlign: "center",
        cursor: "pointer",
        boxSizing: "border-box",
        flex: "0 0 auto",
        pointerEvents: "auto",
        whiteSpace: "nowrap",
    });
}

function setMoveButtonDisabled(button, disabled) {
    if (!button) return;
    button.disabled = disabled;
    button.style.opacity = disabled ? "0.32" : "1";
    button.style.cursor = disabled ? "default" : "pointer";
    if (disabled) button.style.background = "rgba(255,255,255,0.07)";
}

function startLabelEdit(node, row, index) {
    if (row.labelInput) return;

    const input = document.createElement("input");
    input.type = "text";
    input.value = typeof row.entry?.label === "string" ? row.entry.label : "";
    input.placeholder = `Text ${index + 1}`;
    input.spellcheck = false;
    Object.assign(input.style, {
        flex: "1 1 auto",
        minWidth: "0",
        boxSizing: "border-box",
        background: "#111",
        color: "#fff",
        border: "1px solid rgba(255,255,255,0.35)",
        borderRadius: "4px",
        fontSize: "11px",
        fontWeight: "600",
        letterSpacing: "0.1px",
        padding: "0 5px",
        height: "18px",
        outline: "none",
        pointerEvents: "auto",
    });

    row.header.replaceChild(input, row.label);
    row.labelInput = input;
    input.focus();
    input.select();

    let settled = false;
    const finish = (commit) => {
        if (settled) return;
        settled = true;
        if (commit) {
            row.entry.label = input.value.trim();
            persistState(node);
        }
        if (input.parentNode) row.header.replaceChild(row.label, input);
        row.labelInput = null;
        updateRowUi(node);
        node.setDirtyCanvas(true, true);
    };

    input.addEventListener("blur", () => finish(true));
    input.addEventListener("keydown", (event) => {
        event.stopPropagation();
        if (event.key === "Enter") {
            event.preventDefault();
            finish(true);
        } else if (event.key === "Escape") {
            event.preventDefault();
            finish(false);
        }
    });
    input.addEventListener("pointerdown", (event) => event.stopPropagation());
    input.addEventListener("mousedown", (event) => event.stopPropagation());
}

function createRowElement(node, entry) {
    ensureUltraTextboxStyles();
    const root = document.createElement("div");
    Object.assign(root.style, {
        width: "100%",
        height: "100%",
        boxSizing: "border-box",
        display: "flex",
        padding: `0 0 ${ROW_INTER_GAP}px 0`,
        overflow: "visible",
        // The DOM widget is layered above LiteGraph's canvas. Everything except
        // the real textarea/buttons must let pointer events fall through so the
        // native socket hit boxes stay fully usable.
        pointerEvents: "none",
    });

    const panel = document.createElement("div");
    Object.assign(panel.style, {
        width: "100%",
        height: "100%",
        minWidth: "0",
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        gap: `${FIRST_ROW_PANEL_GAP}px`,
        padding: "0",
        // Do not place an opaque card behind the socket row. ComfyUI renders
        // sockets on the canvas below DOM widgets; an opaque wrapper can make a
        // perfectly valid native socket look clipped. Keep only the textarea's
        // own thin border/background below the header line.
        background: "transparent",
        border: "0",
        overflow: "visible",
        pointerEvents: "none",
    });

    const header = document.createElement("div");
    Object.assign(header.style, {
        height: `${ROW_HEADER_HEIGHT}px`,
        display: "flex",
        alignItems: "center",
        gap: "6px",
        flex: `0 0 ${ROW_HEADER_HEIGHT}px`,
        boxSizing: "border-box",
        // Native sockets live in ComfyUI's own compact slot rail above the DOM
        // rows, so the row header no longer needs artificial socket corridors.
        paddingLeft: `${HEADER_SIDE_INSET}px`,
        paddingRight: `${HEADER_SIDE_INSET}px`,
        userSelect: "none",
        pointerEvents: "none",
    });

    const label = document.createElement("div");
    Object.assign(label.style, {
        flex: "1 1 auto",
        minWidth: "0",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
        color: "rgba(255,255,255,0.82)",
        fontSize: "11px",
        fontWeight: "600",
        letterSpacing: "0.1px",
        pointerEvents: "auto",
        cursor: "text",
    });
    label.title = "클릭하여 이름 변경 (비우면 기본값으로 복원)";
    label.addEventListener("click", (event) => {
        event.stopPropagation();
        const index = node._ultraRows?.indexOf(row) ?? -1;
        if (index >= 0) startLabelEdit(node, row, index);
    });
    label.addEventListener("mousedown", (event) => event.stopPropagation());
    label.addEventListener("pointerdown", (event) => event.stopPropagation());

    const copy = document.createElement("button");
    copy.type = "button";
    copy.textContent = "Copy";
    copy.title = "이 텍스트만 복사";
    // Match the compact title-bar control used by Ultra MiniMax H3 Prompt.
    // A fixed minimum width keeps the button stable when it flips to "Copied".
    styleTitleControlButton(copy, { minWidth: "50px" });

    const moveUp = document.createElement("button");
    moveUp.type = "button";
    moveUp.textContent = "⋀";
    moveUp.title = "위 텍스트와 순서 교체";
    styleButton(moveUp, "move");

    const moveDown = document.createElement("button");
    moveDown.type = "button";
    moveDown.textContent = "⋁";
    moveDown.title = "아래 텍스트와 순서 교체";
    styleButton(moveDown, "move");

    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "×";
    remove.title = "이 텍스트와 대응 출력 삭제";
    styleButton(remove, "delete");

    // Nodes 2.0 fallback for the title-bar "변수명 ON/OFF" control. Hidden
    // unless this is the first row and the Vue node renderer is active; see
    // syncVarNameDomToggles().
    const varToggle = document.createElement("button");
    varToggle.type = "button";
    varToggle.textContent = "변수명 OFF";
    varToggle.title = "OUT 소켓 표시 전환 (ON: Text N / OFF: 지정한 이름 또는 OUT N)";
    styleTitleControlButton(varToggle, { minWidth: "64px" });
    varToggle.style.display = "none";
    varToggle.style.marginRight = "4px";

    // Keep Copy anchored at the far-right in both single- and multi-row states.
    // ⋀ ⋁ sit immediately to the left of the delete (×) button, and the delete
    // button sits immediately before Copy. Order left-to-right: label,
    // (Nodes 2.0 only: 변수명 toggle on Text 1), up, down, delete, copy.
    header.append(label, varToggle, moveUp, moveDown, remove, copy);

    const textarea = document.createElement("textarea");
    textarea.classList.add("ultra-textbox-editor");
    textarea.spellcheck = false;
    textarea.placeholder = "텍스트 입력";
    Object.assign(textarea.style, {
        width: `calc(100% - ${TEXTAREA_SIDE_INSET * 2}px)`,
        minWidth: "0",
        marginLeft: `${TEXTAREA_SIDE_INSET}px`,
        marginRight: `${TEXTAREA_SIDE_INSET}px`,
        flex: "1 1 auto",
        resize: "none",
        boxSizing: "border-box",
        border: "1px solid #4b4b4b",
        borderRadius: "5px",
        background: "#1f1f1f",
        color: "#e6e6e6",
        caretColor: "#ffffff",
        padding: "7px 8px",
        outline: "none",
        font: "12px/1.35 monospace",
        overflow: "auto",
        pointerEvents: "auto",
    });

    panel.append(header, textarea);
    root.append(panel);

    const row = { entry, root, panel, header, label, copy, moveUp, moveDown, remove, varToggle, textarea, widget: null };

    varToggle.addEventListener("click", (event) => {
        event.stopPropagation();
        toggleVarNameDisplay(node);
    });
    varToggle.addEventListener("pointerdown", (event) => event.stopPropagation());
    varToggle.addEventListener("mousedown", (event) => event.stopPropagation());

    // Switching between classic canvas and Nodes 2.0 re-mounts DOM widgets
    // into a different container without calling any node hook. The row's
    // size changes when that happens, so a ResizeObserver is a cheap, local
    // signal to re-evaluate whether the DOM toggle should be visible.
    if (typeof ResizeObserver === "function") {
        try {
            row.resizeObserver = new ResizeObserver(() => {
                try { syncVarNameDomToggles(node); } catch (_) {}
            });
            row.resizeObserver.observe(root);
        } catch (_) {}
    }

    textarea.addEventListener("input", () => {
        const index = node._ultraRows?.indexOf(row) ?? -1;
        if (index < 0 || !row.entry) return;
        row.entry.text = textarea.value ?? "";
        persistState(node);
        node.setDirtyCanvas(true, true);
    });

    copy.addEventListener("click", async (event) => {
        event.stopPropagation();
        const ok = await copyTextToClipboard(textarea.value ?? "");
        if (!ok) return;
        copy.textContent = "Copied";
        clearTimeout(row.copyTimer);
        row.copyTimer = setTimeout(() => {
            copy.textContent = "Copy";
            row.copyTimer = null;
        }, 1100);
    });

    remove.addEventListener("click", (event) => {
        event.stopPropagation();
        const index = node._ultraRows?.indexOf(row) ?? -1;
        if (index >= 0) removeEntry(node, index);
    });

    moveUp.addEventListener("click", (event) => {
        event.stopPropagation();
        if (moveUp.disabled) return;
        const index = node._ultraRows?.indexOf(row) ?? -1;
        if (index > 0) moveEntry(node, index, -1);
    });

    moveDown.addEventListener("click", (event) => {
        event.stopPropagation();
        if (moveDown.disabled) return;
        const index = node._ultraRows?.indexOf(row) ?? -1;
        if (index >= 0 && index < (node._ultraRows?.length ?? 0) - 1) moveEntry(node, index, 1);
    });

    return row;
}

function syncRowWidgetOrder(node) {
    const widgets = node.widgets || [];
    const activeWidgets = (node._ultraRows || []).map((row) => row?.widget).filter(Boolean);
    const pooledWidgets = (node._ultraRowPool || []).map((row) => row?.widget).filter(Boolean);
    const addButton = node._ultraAddWidget || null;
    const managedOrdered = [
        ...activeWidgets,
        ...pooledWidgets,
        ...(addButton ? [addButton] : []),
    ];
    const managed = new Set(managedOrdered);
    const firstManagedIndex = widgets.findIndex((widget) => managed.has(widget));
    const insertionIndex = firstManagedIndex < 0
        ? widgets.length
        : widgets.slice(0, firstManagedIndex).filter((widget) => !managed.has(widget)).length;
    const others = widgets.filter((widget) => !managed.has(widget));
    others.splice(insertionIndex, 0, ...managedOrdered);
    widgets.splice(0, widgets.length, ...others);
}

function removeRowWidget(node, row) {
    if (!row) return;
    if (row.copyTimer) {
        clearTimeout(row.copyTimer);
        row.copyTimer = null;
        row.copy.textContent = "Copy";
    }
    // If a label edit is open while the row is removed/rebuilt, blur follows the
    // documented cancel path and restores the non-editing label DOM before pooling.
    row.labelInput?.blur?.();
    row.widget.hidden = true;
    row.widget.computedHeight = 0;
    row.root.style.display = "none";
    row.entry = null;
    node._ultraRowPool ||= [];
    if (!node._ultraRowPool.includes(row)) node._ultraRowPool.push(row);
}

function activateRowWidget(node, row, entry) {
    row.entry = entry;
    row.widget.name = `ultra_text_${entry.id}`;
    row.widget.hidden = false;
    delete row.widget.computedHeight;
    row.root.style.display = "flex";
    row.textarea.value = entry.text == null ? "" : String(entry.text);
    const pool = node._ultraRowPool || [];
    const poolIndex = pool.indexOf(row);
    if (poolIndex >= 0) pool.splice(poolIndex, 1);
    return row;
}

function createRowWidget(node, entry) {
    const row = createRowElement(node, entry);
    const widget = node.addDOMWidget(`ultra_text_${entry.id}`, "ultra_text_row", row.root, {
        serialize: false,
        hideOnZoom: false,
        margin: 0,
        getMinHeight: () => MIN_ROW_HEIGHT,
        getValue: () => row.entry?.text ?? "",
        setValue: (value) => {
            if (!row.entry) return;
            row.entry.text = value == null ? "" : String(value);
            row.textarea.value = row.entry.text;
        },
    });
    widget.serialize = false;
    row.widget = widget;
    return row;
}

function acquireRowWidget(node, entry) {
    node._ultraRowPool ||= [];
    const row = node._ultraRowPool.pop() || createRowWidget(node, entry);
    return activateRowWidget(node, row, entry);
}

function ensureAddButton(node) {
    let button = node._ultraAddWidget;
    if (button && node.widgets?.includes(button)) return button;

    button = node.addWidget("button", "＋  텍스트 추가", null, () => {
        addEntry(node);
    });
    button.serialize = false;
    button.options ||= {};
    button.options.serialize = false;
    node._ultraAddWidget = button;
    return button;
}

function moveAddButtonToEnd(node) {
    ensureAddButton(node);
    syncRowWidgetOrder(node);
}

function setInputCount(node, count) {
    const target = Math.max(1, Math.min(MAX_TEXT_ENTRIES, count | 0));
    node.inputs ||= [];
    rememberNativeSourceShape(node);

    // Only manage the dedicated Ultra source inputs. This deliberately leaves
    // unrelated/legacy inputs alone if a future ComfyUI frontend adds any.
    let sources = getSourceInputs(node);
    while (sources.length > target) {
        const doomed = sources[sources.length - 1];
        const slot = node.inputs.indexOf(doomed);
        if (slot < 0) break;
        node.removeInput(slot);
        sources = getSourceInputs(node);
    }

    while (sources.length < target) {
        const rowIndex = sources.length;
        const added = node.addInput(sourceNameForRow(rowIndex), "STRING");
        applyNativeSourceShape(node, added);
        sources = getSourceInputs(node);
    }

    // Middle-row deletion shifts LiteGraph target_slot indices for later links.
    // Renaming the surviving source slots keeps backend keyword names aligned
    // with the newly compacted Text 1..N row order without reconnecting them.
    sources = getSourceInputs(node);
    for (let i = 0; i < sources.length; i++) {
        sources[i].name = sourceNameForRow(i);
        sources[i].label = `IN ${i + 1}`;
        applyNativeSourceShape(node, sources[i]);
        // Never hard-position native sockets. Current ComfyUI may use Vue DOM
        // slot layouts as the source of truth for rendering and hit testing.
        delete sources[i].pos;
    }
}

function setOutputCount(node, count) {
    const target = Math.max(1, Math.min(MAX_TEXT_ENTRIES, count | 0));
    node.outputs ||= [];

    while (node.outputs.length > target) {
        node.removeOutput(node.outputs.length - 1);
    }
    while (node.outputs.length < target) {
        node.addOutput(`Text ${node.outputs.length + 1}`, "STRING");
    }

    for (let i = 0; i < node.outputs.length; i++) {
        const output = node.outputs[i];
        output.name = `Text ${i + 1}`;
        output.label = `OUT ${i + 1}`;
        delete output.pos;
    }
}

function syncRowWidgetWidths(node) {
    // ComfyUI frontend revisions have repeatedly regressed DOM-widget width
    // bookkeeping: after node selection, side-panel changes, or resize, a DOM
    // widget can retain an older fixed `widget.width` even though the LiteGraph
    // node itself is wider. Our row root is already width:100%, so that stale
    // outer widget width is the only thing constraining the textarea/header.
    //
    // Keep this node-local and idempotent. Do not touch canvas scale, DOM
    // transforms, node size, widget y/height, or global ComfyUI behaviour.
    const nodeWidth = Number(node?.size?.[0]);
    if (!(nodeWidth > 0)) return;
    for (const row of node?._ultraRows || []) {
        if (!row?.widget || row.widget.hidden) continue;
        if (row.widget.width !== nodeWidth) row.widget.width = nodeWidth;
    }
}

function updateRowUi(node) {
    const rows = node._ultraRows || [];
    const sources = getSourceInputs(node);

    syncRowWidgetWidths(node);

    for (let i = 0; i < sources.length; i++) {
        const input = sources[i];
        input.label = `IN ${i + 1}`;
        applyNativeSourceShape(node, input);
        delete input.pos;
    }

    rows.forEach((row, index) => {
        const defaultName = `Text ${index + 1}`;
        const custom = typeof row.entry.label === "string" ? row.entry.label.trim() : "";
        // Keep the row's own number visible even after a custom name is set,
        // so users can still tell rows apart at a glance ("1 my label"
        // instead of losing the leading index once renamed).
        row.label.textContent = custom ? `${index + 1} ${custom}` : defaultName;
        // Match Text 1's upper divider to the same inset/colour as the textarea
        // borders that visually bound every later row. Use a 1px background rule
        // instead of borderTop so this changes no row height or socket geometry.
        row.header.style.borderTop = "0";
        row.header.style.backgroundImage = index === 0
            ? "linear-gradient(#555, #555)"
            : "none";
        row.header.style.backgroundRepeat = "no-repeat";
        row.header.style.backgroundPosition = "center top";
        row.header.style.backgroundSize = index === 0
            ? `calc(100% - ${TEXTAREA_SIDE_INSET * 2}px) 1px`
            : "auto";
        // Text 1's upper spacing is the fixed visual reference and must not move.
        // Its lower gap is tightened by 1px, while later rows use 0px auxiliary
        // inter-row/panel gaps so their upper/lower air is each reduced by 1px.
        row.header.style.paddingTop = index === 0 ? `${FIRST_ROW_HEADER_TOP_PAD}px` : "0px";
        row.panel.style.gap = index === 0 ? `${FIRST_ROW_PANEL_GAP}px` : `${ROW_INTER_GAP}px`;
        if (!row.labelInput) row.label.style.marginLeft = "0px";
        row.remove.style.visibility = rows.length > 1 ? "visible" : "hidden";
        row.remove.disabled = rows.length <= 1;

        setMoveButtonDisabled(row.moveUp, index === 0);
        setMoveButtonDisabled(row.moveDown, index === rows.length - 1);

        const connected = isSourceConnected(node, index);

        // Dedicated IN sockets intentionally behave like the original Ultra
        // Textbox source input: the received string is mirrored into the row,
        // but the textarea stays fully normal and editable. Do not use the
        // grey/read-only styling ComfyUI applies to converted multiline widgets.
        row.textarea.readOnly = false;
        row.textarea.disabled = false;
        row.textarea.placeholder = connected ? "IN 연결됨 · 실행값 표시/편집 가능" : "텍스트 입력";
        row.textarea.title = connected
            ? `${custom || defaultName} IN 연결됨 · 실행 시 입력값이 이 칸에 표시됩니다. 직접 편집도 가능합니다.`
            : "";
        row.textarea.style.opacity = "1";
        row.textarea.style.color = "#e6e6e6";
        row.textarea.style.webkitTextFillColor = "#e6e6e6";
        row.textarea.style.caretColor = "#ffffff";
        row.textarea.style.background = "#1f1f1f";
        row.textarea.style.borderColor = "#555";

        const wanted = row.entry.text == null ? "" : String(row.entry.text);
        if (row.textarea.value !== wanted) row.textarea.value = wanted;
    });

    if (node._ultraAddWidget) {
        const full = rows.length >= MAX_TEXT_ENTRIES;
        node._ultraAddWidget.name = full
            ? `최대 ${MAX_TEXT_ENTRIES}개`
            : `＋  텍스트 추가  (${rows.length}/${MAX_TEXT_ENTRIES})`;
        node._ultraAddWidget.disabled = full;
    }

    const outputs = node.outputs || [];
    for (let i = 0; i < outputs.length; i++) {
        const custom = typeof rows[i]?.entry.label === "string" ? rows[i].entry.label.trim() : "";
        outputs[i].name = `Text ${i + 1}`;
        // 변수명 ON always wins, including rows that have a custom name:
        // the socket then shows the backend variable name "Text N" for every
        // row. 변수명 OFF shows the custom name when set, otherwise "OUT N".
        // (Previously a custom name overrode the toggle, so once rows were
        // renamed the switch appeared to do nothing.)
        outputs[i].label = isVarNameDisplayOn(node)
            ? `Text ${i + 1}`
            : custom
                ? truncateForSocket(custom)
                : `OUT ${i + 1}`;
        delete outputs[i].pos;
    }

    syncVarNameDomToggles(node);
}

function captureStructureSize(node, { forcePreserveHeight = false } = {}) {
    const width = Number(node.size?.[0]) || 0;
    const height = Number(node.size?.[1]) || 0;
    const currentMinimum = node.computeSize?.() || [MIN_NODE_WIDTH, height];
    const minimumHeight = Number(currentMinimum[1]) || height;
    const rowCount = Math.max(1, node._ultraRows?.length || node._ultraEntries?.length || 1);

    return {
        width,
        height,
        minimumHeight,
        rowCount,
        preserveExactHeight: forcePreserveHeight,
    };
}

function fitAfterStructureChange(node, sizeBefore = null) {
    const currentHeight = Number(node.size?.[1]) || 0;
    const computed = node.computeSize?.() || [MIN_NODE_WIDTH, currentHeight];
    const minimumHeight = Number(computed[1]) || currentHeight;
    node._ultraAutoHeight = minimumHeight;

    const widthBefore = Number(sizeBefore?.width) || 0;
    const width = Math.max(
        MIN_NODE_WIDTH,
        widthBefore || Number(node.size?.[0]) || computed[0] || MIN_NODE_WIDTH,
    );

    const previousHeight = Number(sizeBefore?.height) || 0;
    const previousMinimumHeight = Number(sizeBefore?.minimumHeight) || 0;
    const previousRowCount = Math.max(1, Number(sizeBefore?.rowCount) || 1);
    const nextRowCount = Math.max(1, node._ultraRows?.length || node._ultraEntries?.length || 1);

    let height = minimumHeight;
    if (sizeBefore?.preserveExactHeight && previousHeight > 0) {
        // Workflow restore: keep the serialized node height exactly as saved.
        height = previousHeight;
    } else if (previousHeight > 0 && previousMinimumHeight > 0) {
        // Preserve the user's current *per-text-row* expansion relative to
        // ComfyUI's stable minimum layout.  Do not read computedHeight here:
        // computedHeight is a post-layout allocation and can contain fractional
        // redistribution/rounding from the previous frame. Reusing it after each
        // add/delete turns that tiny allocation difference into cumulative drift.
        //
        // With this invariant:
        //   nodeHeight = minimumHeight(rowCount) + perRowExtra * rowCount
        // add/delete are exact inverses. If every visible textarea is currently
        // 5-lines tall, a new row is born at that same height; deleting a row
        // leaves every survivor at that same height. A manual node resize simply
        // changes perRowExtra the next time the structure changes.
        const perRowExtra = Math.max(
            0,
            (previousHeight - previousMinimumHeight) / previousRowCount,
        );
        height = minimumHeight + perRowExtra * nextRowCount;
    }

    node.setSize([width, height]);
    node.setDirtyCanvas(true, true);
}

function rebuildRows(node, entries, { preserveHeight = false } = {}) {
    const sizeBefore = captureStructureSize(node, { forcePreserveHeight: preserveHeight });

    // The hidden serialized STRING widget has its own widget-backed input slot in
    // current ComfyUI. It is normally invisible, but becomes visible as a valid
    // target while dragging a STRING link and overlaps IN 1. Keep the widget for
    // state serialization, but remove only that obsolete connection slot.
    removeHiddenStateInputSlot(node);

    const previousRows = [...(node._ultraRows || [])];
    // Detach the active-row list before pooling. If a row happens to be in label
    // edit mode, its blur/cancel callback can safely refresh the node without
    // encountering an earlier pooled row whose entry has already been cleared.
    node._ultraRows = [];
    for (const row of previousRows) removeRowWidget(node, row);
    node._ultraEntries = entries.slice(0, MAX_TEXT_ENTRIES).map(normalizeEntry);
    if (!node._ultraEntries.length) node._ultraEntries.push(normalizeEntry(""));

    // Nodes 2.0 currently has a layout regression when a native LiteGraph
    // widget is created *after* a DOM widget. Text 1 used to be the only row
    // created before our native "+ text" button, while rows added later were
    // created after that button already existed. That made the first row prone
    // to keeping a stale/narrow DOM width after selection or resize. Register
    // the native button first, then create/acquire every DOM row. We still move
    // the button to the visual end below, so the user-facing order is unchanged.
    ensureAddButton(node);

    for (const entry of node._ultraEntries) {
        node._ultraRows.push(acquireRowWidget(node, entry));
    }

    moveAddButtonToEnd(node);
    setInputCount(node, node._ultraEntries.length);
    setOutputCount(node, node._ultraEntries.length);
    persistState(node);
    updateRowUi(node);
    fitAfterStructureChange(node, sizeBefore);
}

function addEntry(node) {
    if (!Array.isArray(node._ultraEntries)) return;
    if (node._ultraEntries.length >= MAX_TEXT_ENTRIES) return;

    const sizeBefore = captureStructureSize(node);
    const entry = normalizeEntry("");
    node._ultraEntries.push(entry);
    node._ultraRows.push(acquireRowWidget(node, entry));
    moveAddButtonToEnd(node);
    setInputCount(node, node._ultraEntries.length);
    setOutputCount(node, node._ultraEntries.length);
    persistState(node);
    updateRowUi(node);
    fitAfterStructureChange(node, sizeBefore);

    const row = node._ultraRows.at(-1);
    row?.textarea?.focus();
}

function removeEntry(node, index) {
    if (!Array.isArray(node._ultraEntries) || node._ultraEntries.length <= 1) return;
    if (index < 0 || index >= node._ultraEntries.length) return;

    const sizeBefore = captureStructureSize(node);
    const row = node._ultraRows[index];

    // Remove exactly this row's input and output. LiteGraph updates target_slot
    // / origin_slot indices of surviving later links, so Text 3's two links stay
    // attached to Text 3's row object when Text 2 is removed.
    const sourceInput = getSourceInput(node, index);
    if (sourceInput) {
        const inputSlot = node.inputs.indexOf(sourceInput);
        if (inputSlot >= 0) node.removeInput(inputSlot);
    }
    node.removeOutput(index);
    removeRowWidget(node, row);
    node._ultraRows.splice(index, 1);
    node._ultraEntries.splice(index, 1);

    setInputCount(node, node._ultraEntries.length);
    moveAddButtonToEnd(node);
    persistState(node);
    updateRowUi(node);
    fitAfterStructureChange(node, sizeBefore);
}

function graphLinkById(node, linkId) {
    if (linkId == null || linkId === -1) return null;
    const graph = node?.graph;
    // Current ComfyUI exposes graph.links as a Map (with a temporary indexed
    // compatibility Proxy). Prefer the supported Map API, then fall back to
    // older frontend shapes without changing the row-reorder semantics.
    return graph?.links?.get?.(linkId)
        ?? graph?._links?.get?.(linkId)
        ?? graph?.getLink?.(linkId)
        ?? graph?.links?.[linkId]
        ?? null;
}

function graphNodeList(node) {
    const graph = node?.graph;
    if (!graph) return [];
    return Array.isArray(graph._nodes) ? graph._nodes : Array.isArray(graph.nodes) ? graph.nodes : [];
}

// Fallback lookups used only when graphLinkById() cannot resolve the shared
// link object - i.e. this ComfyUI frontend's graph link-store shape doesn't
// match any of the forms graphLinkById knows how to read. Rather than guess
// at yet another internal shape, these scan node.inputs[*].link and
// node.outputs[*].links directly: data this file already treats as
// authoritative everywhere else (isSourceConnected, getSourceInput, etc.),
// so they stay correct regardless of how the graph itself indexes links.
function findDownstreamForOutputLink(node, linkId) {
    if (linkId == null) return null;
    for (const other of graphNodeList(node)) {
        const inputs = other?.inputs || [];
        for (let slot = 0; slot < inputs.length; slot++) {
            if (inputSlotLinkId(other, slot) === linkId) return { node: other, slot };
        }
    }
    return null;
}

function findUpstreamForInputLink(node, linkId) {
    if (linkId == null) return null;
    for (const other of graphNodeList(node)) {
        const outputs = other?.outputs || [];
        for (let slot = 0; slot < outputs.length; slot++) {
            if (outputSlotLinkIds(other, slot).includes(linkId)) {
                return { node: other, slot };
            }
        }
    }
    return null;
}

// Re-point the *existing* links so each one keeps following the text it was
// originally attached to, instead of staying pinned to a slot number.
// Fast path: deliberately does NOT call removeOutput/addOutput/removeInput/
// addInput/connect/disconnect - those fire onConnectionsChange and briefly
// put the graph in a "disconnected" state a downstream node could observe
// mid-move. Instead this mutates link.origin_slot / link.target_slot
// directly (a plain data write, not a graph topology change), so from the
// downstream node's perspective nothing ever "disconnects" - the line just
// now originates from / lands on a different already-connected slot.
//
// That fast path only works when graphLinkById() can actually find the
// shared link object to mutate. If it can't (see graphLinkById), silently
// swapping only the *.links/.link slot bookkeeping while leaving the link's
// real origin_slot/target_slot untouched would make the visible row order
// and the actual executed data disagree - the swap would look right on
// screen while the downstream node keeps receiving the pre-swap value. So
// when any involved link can't be resolved, every link in this swap is
// rebuilt through the official connect/disconnect API instead, which always
// resolves correctly regardless of the graph's internal link storage shape.
// This guarantees the data a downstream node receives always matches what's
// shown, at the cost of a brief reconnect flicker in that fallback case.
function relinkOutputsAfterSwap(node, i, j) {
    const outputs = node.outputs || [];
    const outA = outputs[i];
    const outB = outputs[j];
    if (!outA || !outB) return;

    const linksA = outputSlotLinkIds(node, i);
    const linksB = outputSlotLinkIds(node, j);
    const moves = [
        ...linksA.map((id) => ({ id, toSlot: j })),
        ...linksB.map((id) => ({ id, toSlot: i })),
    ];
    const resolved = moves.map((m) => ({ ...m, link: graphLinkById(node, m.id) }));

    if (resolved.every((m) => m.link)) {
        for (const m of resolved) m.link.origin_slot = m.toSlot;
        if (!usesLinkStore(node)) {
            // Older frontends keep these lists as plain data.
            outA.links = linksB;
            outB.links = linksA;
        }
        return;
    }

    for (const m of resolved) {
        const downstream = findDownstreamForOutputLink(node, m.id);
        if (!downstream) {
            console.warn(`[Ultra Tools Textbox] Could not relink output link ${m.id} during row reorder; leaving it as-is.`);
            continue;
        }
        downstream.node.disconnectInput?.(downstream.slot);
        node.connect?.(m.toSlot, downstream.node, downstream.slot);
    }
}

function relinkSourceInputsAfterSwap(node, rowIndexA, rowIndexB) {
    const inA = getSourceInput(node, rowIndexA);
    const inB = getSourceInput(node, rowIndexB);
    if (!inA || !inB) return;

    const slotA = node.inputs.indexOf(inA);
    const slotB = node.inputs.indexOf(inB);
    if (slotA < 0 || slotB < 0) return;

    const linkIdA = inputSlotLinkId(node, slotA);
    const linkIdB = inputSlotLinkId(node, slotB);

    const linkA = linkIdA != null ? graphLinkById(node, linkIdA) : null;
    const linkB = linkIdB != null ? graphLinkById(node, linkIdB) : null;
    const needsFallback = (linkIdA != null && !linkA) || (linkIdB != null && !linkB);

    if (!needsFallback) {
        if (linkA && linkB && usesLinkStore(node)) {
            // The link store rejects moving a link onto an input that is still
            // occupied ("occupied-target"), so swap through a temporary,
            // unused slot index. All three writes happen synchronously, so no
            // render or execution ever observes the intermediate state.
            const parkingSlot = 100000 + Math.max(slotA, slotB);
            linkA.target_slot = parkingSlot;
            linkB.target_slot = slotA;
            linkA.target_slot = slotB;
        } else {
            if (linkA) linkA.target_slot = slotB;
            if (linkB) linkB.target_slot = slotA;
        }
        if (!usesLinkStore(node)) {
            // Older frontends keep input.link as plain data. On store-backed
            // frontends the assignment is deprecated and assigning null would
            // disconnect the slot, so only the link endpoints are rewritten.
            inA.link = linkIdB;
            inB.link = linkIdA;
        }
        return;
    }

    const upstreamA = linkIdA != null ? findUpstreamForInputLink(node, linkIdA) : null;
    const upstreamB = linkIdB != null ? findUpstreamForInputLink(node, linkIdB) : null;
    if (linkIdA != null && !upstreamA) {
        console.warn(`[Ultra Tools Textbox] Could not relink input link ${linkIdA} during row reorder; leaving it as-is.`);
    }
    if (linkIdB != null && !upstreamB) {
        console.warn(`[Ultra Tools Textbox] Could not relink input link ${linkIdB} during row reorder; leaving it as-is.`);
    }

    // Disconnect both slots first so neither is briefly fed by the wrong
    // upstream link while the two connections are re-wired.
    node.disconnectInput?.(slotA);
    node.disconnectInput?.(slotB);
    if (upstreamB) upstreamB.node.connect?.(upstreamB.slot, node, slotA);
    if (upstreamA) upstreamA.node.connect?.(upstreamA.slot, node, slotB);
}

function moveEntry(node, index, direction) {
    const entries = node._ultraEntries;
    const rows = node._ultraRows;
    if (!Array.isArray(entries) || !Array.isArray(rows)) return;

    const targetIndex = index + direction;
    if (index < 0 || index >= entries.length) return;
    if (targetIndex < 0 || targetIndex >= entries.length) return;

    const entryA = entries[index];
    const entryB = entries[targetIndex];
    const rowA = rows[index];
    const rowB = rows[targetIndex];
    if (!entryA || !entryB || !rowA || !rowB) return;

    // Swap the complete logical entries while the two DOM row positions stay
    // fixed. The stable entry ID moves together with text/label, which is
    // important for mapping a slow queued execution back to the same data after
    // the user reorders rows before that execution finishes.
    entries[index] = entryB;
    entries[targetIndex] = entryA;
    rowA.entry = entryB;
    rowB.entry = entryA;

    rowA.textarea.value = entryB.text;
    rowB.textarea.value = entryA.text;
    if (rowA.widget) rowA.widget.name = `ultra_text_${entryB.id}`;
    if (rowB.widget) rowB.widget.name = `ultra_text_${entryA.id}`;

    // Carry each link along with the content it was originally attached to,
    // so a downstream connection keeps receiving the exact same text it
    // always received, no matter which slot number that text now lives in.
    relinkOutputsAfterSwap(node, index, targetIndex);
    relinkSourceInputsAfterSwap(node, index, targetIndex);

    persistState(node);
    updateRowUi(node);
    node.setDirtyCanvas(true, true);
    node.graph?.setDirtyCanvas?.(true, true);
}

function syncExecutedSourceValues(node, message) {
    const values = Array.isArray(message?.text)
        ? message.text
        : typeof message?.text === "string"
            ? [message.text]
            : [];
    const queuedEntryIds = Array.isArray(message?.entry_ids) ? message.entry_ids : null;

    // Mirror only connected source values into the logical row that belonged to
    // that queued execution. Current backends return the stable entry ID beside
    // each value, so a row moved while a slow queue item is running still receives
    // its own result. A row deleted after queueing is simply ignored. Legacy
    // results without IDs retain the historical index-based behavior.
    let changed = false;
    for (let queuedIndex = 0; queuedIndex < values.length; queuedIndex++) {
        const queuedId = typeof queuedEntryIds?.[queuedIndex] === "string"
            && queuedEntryIds[queuedIndex]
            ? queuedEntryIds[queuedIndex]
            : null;
        const currentIndex = queuedId
            ? (node._ultraEntries || []).findIndex((entry) => entry?.id === queuedId)
            : queuedIndex;
        if (currentIndex < 0 || currentIndex >= (node._ultraRows?.length || 0)) continue;
        if (!isSourceConnected(node, currentIndex)) continue;

        const value = values[queuedIndex] == null ? "" : String(values[queuedIndex]);
        const entry = node._ultraEntries?.[currentIndex];
        const row = node._ultraRows?.[currentIndex];
        if (entry && entry.text !== value) {
            entry.text = value;
            changed = true;
        }
        if (row?.textarea && row.textarea.value !== value) {
            row.textarea.value = value;
        }
    }
    if (changed) persistState(node);
    return changed;
}

function titleVarNameToggleBounds(node) {
    // The title control only exists where it is actually drawn. In Nodes 2.0
    // it is never drawn (DOM toggle is used instead), and when the draw pass
    // hid it for lack of title space it stores null - neither case may leave
    // an invisible click target in the title bar.
    if (isVueNodesMode()) return null;
    if (Object.prototype.hasOwnProperty.call(node || {}, "__ultraTextboxVarNameToggleBounds")
        && node.__ultraTextboxVarNameToggleBounds === null) return null;
    const cached = node?.__ultraTextboxVarNameToggleBounds;
    if (cached && Number.isFinite(cached.x) && Number.isFinite(cached.w)) return cached;
    const width = Number(node?.size?.[0]) || 0;
    if (!(width > 0)) return null;
    const titleHeight = Math.max(24, Number(globalThis?.LiteGraph?.NODE_TITLE_HEIGHT) || 30);
    const x = width - VAR_NAME_TITLE_CONTROL_RIGHT_GAP - VAR_NAME_TITLE_CONTROL_WIDTH;
    const y = -titleHeight + Math.max(3, (titleHeight - VAR_NAME_TITLE_CONTROL_HEIGHT) / 2);
    if (x < 8) return null;
    return { x, y, w: VAR_NAME_TITLE_CONTROL_WIDTH, h: VAR_NAME_TITLE_CONTROL_HEIGHT };
}

function titleVarNameToggleHit(node, pos) {
    if (!Array.isArray(pos) || !Number.isFinite(pos[0]) || !Number.isFinite(pos[1])) return false;
    const b = titleVarNameToggleBounds(node);
    if (!b) return false;
    return pos[0] >= b.x && pos[0] <= b.x + b.w && pos[1] >= b.y && pos[1] <= b.y + b.h;
}

function drawTitleVarNameToggle(node, ctx) {
    if (!ctx) return;
    const on = isVarNameDisplayOn(node);
    const label = on ? "변수명 ON" : "변수명 OFF";
    const width = Number(node?.size?.[0]) || 0;
    if (!(width > 0)) return;

    const titleHeight = Math.max(24, Number(globalThis?.LiteGraph?.NODE_TITLE_HEIGHT) || 30);
    const titleLeft = 32;
    const titleGap = 8;

    ctx.save();
    try {
        const titleTextSize = Math.max(12, Number(globalThis?.LiteGraph?.NODE_TEXT_SIZE) || 14);
        ctx.font = `bold ${titleTextSize}px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`;
        const titleWidth = Math.ceil(ctx.measureText(String(node?.title || "")).width);
        const x = width - VAR_NAME_TITLE_CONTROL_RIGHT_GAP - VAR_NAME_TITLE_CONTROL_WIDTH;
        const y = -titleHeight + Math.max(3, (titleHeight - VAR_NAME_TITLE_CONTROL_HEIGHT) / 2);
        if (x < 8 || x < titleLeft + titleWidth + titleGap) {
            node.__ultraTextboxVarNameToggleBounds = null;
            return;
        }

        const b = { x, y, w: VAR_NAME_TITLE_CONTROL_WIDTH, h: VAR_NAME_TITLE_CONTROL_HEIGHT };
        node.__ultraTextboxVarNameToggleBounds = b;

        // Same visual recipe as Ultra MiniMax H3 Prompt's title "툴팁 ON" control:
        // no filled background, only a thin rounded outline and restrained text.
        ctx.strokeStyle = on ? "rgba(255,255,255,0.62)" : "rgba(255,255,255,0.34)";
        ctx.lineWidth = 1;
        const r = 4;
        const w = b.w;
        const h = b.h;
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
        ctx.stroke();

        ctx.fillStyle = on ? "rgba(245,247,250,0.82)" : "rgba(215,218,224,0.50)";
        ctx.font = "10.5px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(label, x + w / 2, y + h / 2 + 0.25);
    } finally {
        ctx.restore();
    }
}

function installTitleVarNameToggle(node) {
    if (!node || VAR_NAME_TITLE_TOGGLE_INSTALLED.has(node)) return;
    VAR_NAME_TITLE_TOGGLE_INSTALLED.add(node);

    const previousDraw = node.onDrawForeground;
    node.onDrawForeground = function (...args) {
        const result = typeof previousDraw === "function" ? previousDraw.apply(this, args) : undefined;
        // Do this on every foreground draw because the frontend can overwrite a
        // DOM widget's cached width *after* a normal resize/configure callback.
        // DomWidgets then consumes widget.width on the same canvas frame.
        try { syncRowWidgetWidths(this); } catch (_) {}
        try { drawTitleVarNameToggle(this, args[0]); } catch (_) {}
        // Canvas mode is active whenever this runs: make sure a DOM fallback
        // toggle left over from Nodes 2.0 is hidden again.
        try { syncVarNameDomToggles(this); } catch (_) {}
        return result;
    };

    const previousMouseDown = node.onMouseDown;
    node.onMouseDown = function (event, pos, ...rest) {
        if (titleVarNameToggleHit(this, pos)) {
            toggleVarNameDisplay(this);
            return true;
        }
        return typeof previousMouseDown === "function"
            ? previousMouseDown.call(this, event, pos, ...rest)
            : undefined;
    };
}

function initializeNode(node) {
    const stateWidget = getStateWidget(node);
    if (!stateWidget) return;
    node._ultraStateWidget = stateWidget;
    hideStateWidget(stateWidget);
    rememberNativeSourceShape(node);
    removeHiddenStateInputSlot(node);

    // Keep the native ComfyUI slot rail and default widget layout. Do not set
    // deprecated `widgets_up`; current ComfyUI already places the widget area
    // below the native slot rail. Clearing widgets_start_y avoids stale custom
    // offsets from older revisions without changing the default layout policy.
    node.widgets_start_y = undefined;

    installTitleVarNameToggle(node);

    const entries = parseState(stateWidget.value ?? ultraWidgetEl(stateWidget)?.value ?? "");
    rebuildRows(node, entries, { preserveHeight: false });
}

app.registerExtension({
    name: "Ultra.Textbox.Multi",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "UltraTextbox") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);
            initializeNode(this);
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            onConfigure?.apply(this, arguments);

            // Configure restores the hidden serialized "text" widget first.
            // Rebuild dynamic DOM rows only after that restoration completes.
            queueMicrotask(() => {
                const stateWidget = getStateWidget(this);
                if (!stateWidget) return;
                this._ultraStateWidget = stateWidget;
                hideStateWidget(stateWidget);
                rememberNativeSourceShape(this);
                removeHiddenStateInputSlot(this);
                installTitleVarNameToggle(this);
                const entries = parseState(stateWidget.value ?? ultraWidgetEl(stateWidget)?.value ?? "");
                rebuildRows(this, entries, { preserveHeight: true });
            });
        };

        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            onExecuted?.apply(this, arguments);

            syncExecutedSourceValues(this, message);

            updateRowUi(this);
            this.setDirtyCanvas(true, true);
        };

        const onConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function () {
            onConnectionsChange?.apply(this, arguments);
            updateRowUi(this);
            this.setDirtyCanvas(true, true);
        };

        const onRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            for (const row of [...(this._ultraRows || []), ...(this._ultraRowPool || [])]) {
                if (row.copyTimer) clearTimeout(row.copyTimer);
                try { row.resizeObserver?.disconnect(); } catch (_) {}
            }
            onRemoved?.apply(this, arguments);
        };
    },
});
