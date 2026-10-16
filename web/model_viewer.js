import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Current frontends expose a DOM widget's element as widget.element;
// widget.inputEl is a deprecated alias (warns on access). Prefer element and
// fall back to inputEl only on older frontends that lack it.
function ultraWidgetEl(widget) {
  if (!widget) return undefined;
  return "element" in widget ? widget.element : widget.inputEl;
}


/**
 * Ultra Tools Model Viewer
 *
 * frontend 1.40+ 호환 수정:
 * - ComfyWidgets.STRING() 동적 호출 제거
 *   → Python INPUT_TYPES에 미리 선언된 위젯을 node.widgets.find()로 탐색
 * - inputEl ?? element 로 frontend 버전별 프로퍼티명 차이 대응
 * - async beforeRegisterNodeDef 에서 불필요한 async 제거
 */

// ----------------- helpers -----------------
const MODEL_EXTS = [".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".nunchaku", ".onnx", ".sft", ".pt2", ".engine"];
const MODEL_VALUE_KEYS = new Set([
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
]);
// Generic "name" is intentionally not a model key. Only exact typed model keys
// such as model_name, ckpt_name, lora_name, filename, and path may open
// model-value context.
const POSSIBLE_MODEL_KEYS = [...MODEL_VALUE_KEYS].sort();
const KEY_TAG_TYPES = new Map([
  ["lora", "lora"], ["lora_name", "lora"], ["lora_path", "lora"], ["lora_file", "lora"],
  ["embedding", "embedding"], ["embedding_name", "embedding"], ["ti", "embedding"], ["ti_name", "embedding"],
  ["hypernet", "hypernet"], ["hypernet_name", "hypernet"],
  ["hypernetwork", "hypernet"], ["hypernetwork_name", "hypernet"],
]);

function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const MODEL_EXT_PATTERN = MODEL_EXTS.map(escapeRegExp).join("|");
const MODEL_REF_RE = new RegExp(
  `(^|[^\\w.\\-])((?:[A-Za-z]:[\\\\/])?(?:[^\\s\"'<>\\[\\]{}|;,:]+[\\\\/])*[^\\s\"'<>\\[\\]{}|;,:]+(?:${MODEL_EXT_PATTERN}))(?=$|[\\s\"'<>\\[\\]{}|;,):])`,
  "gi"
);
const LORA_TAG_RE = new RegExp(
  `<\\s*(lora|lyco|locon|loha|hypernet|embedding|ti)\\s*:\\s*([^<>:\\n\\r]+?(?:${MODEL_EXT_PATTERN}))(?:\\s*[:>])`,
  "gi"
);

const LORA_TAG_ANY_RE = /<\s*(lora|lyco|locon|loha|hypernet|embedding|ti)\s*:\s*([^<>:\n\r]+?)(?:\s*[:>])/gi;
const JSON_KEY_VALUE_RE = new RegExp(
  `(^|[^A-Za-z0-9_])[\"']?(${POSSIBLE_MODEL_KEYS.map(escapeRegExp).join("|")})[\"']?\\s*:\\s*(\\"[^\\"<>\\n\\r]+\\"|'[^'<>\\n\\r]+'|[^,}\\]<>\\n\\r]+)`,
  "gi"
);
const EXTENSIONLESS_STOPWORDS = new Set([
  "default", "none", "null", "true", "false", "auto", "cpu", "cuda", "gpu",
  "fast", "slow", "normal", "high", "low", "best", "base", "main",
  "model", "checkpoint", "clip", "vae", "lora", "unet", "text", "encoder",
]);
const MAX_SCAN_TEXT = 4096;
const MAX_JSON_SCAN_TEXT = 65536;
const MAX_SCAN_DEPTH = 8;
const INPUT_DESCRIPTOR_META_KEYS = new Set([
  "name", "type", "link", "label", "localized_name", "slot_index", "index",
  "shape", "widget", "optional", "isoptional", "control_after_generate",
]);
const NON_LOOSE_PROPERTY_META_KEYS = new Set(["name", "label", "title"]);

function uniquePreserveOrder(values) {
  const seen = new Set();
  const out = [];
  for (const value of values) {
    const key = String(value).toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(value);
  }
  return out;
}

function isPositionInsideAnySpan(pos, spans) {
  return spans.some(([start, end]) => start <= pos && pos < end);
}

function stripRef(ref) {
  if (!ref || typeof ref !== "string") return null;
  let value = ref.trim().replace(/^[\"']+|[\"']+$/g, "");
  if (value.startsWith("<") && value.endsWith(">")) value = value.slice(1, -1).trim();
  return value || null;
}

function canonicalTagType(tag) {
  const lower = String(tag || "").trim().toLowerCase();
  if (["lora", "lyco", "locon", "loha"].includes(lower)) return "lora";
  if (["embedding", "ti"].includes(lower)) return "embedding";
  if (lower === "hypernet") return "hypernet";
  return lower || "";
}

function tagStateToken(ref, tag) {
  const cleaned = stripRef(ref);
  const kind = canonicalTagType(tag);
  return cleaned && kind ? `${kind}::${cleaned}` : cleaned;
}

function isExactModelKey(key) {
  return MODEL_VALUE_KEYS.has(String(key || "").toLowerCase());
}

function tagTypeForKey(key) {
  return KEY_TAG_TYPES.get(String(key || "").toLowerCase()) || "";
}

function applyKeyHint(refs, tagType = "") {
  if (!tagType) return refs || [];
  return (refs || []).map(ref => String(ref).includes("::") ? ref : tagStateToken(ref, tagType)).filter(Boolean);
}

function refsFromExactKeyValue(key, rawValue) {
  const keyLower = String(key || "").toLowerCase();
  if (!isExactModelKey(keyLower)) return [];
  const rawText = String(rawValue || "").trim();
  const quoteWrapped = rawText.length >= 2 && rawText[0] === rawText[rawText.length - 1] && (rawText[0] === "\"" || rawText[0] === "'");
  const cleaned = stripRef(rawText);
  if (!cleaned) return [];
  const tagType = tagTypeForKey(keyLower);
  const refs = [];
  if (looksLikeFullModelRef(cleaned)) refs.push(cleaned);
  else if (["lora", "embedding", "hypernet"].includes(tagType) && looksLikeExtensionlessLoraTagRef(cleaned)) {
    if (quoteWrapped || !/\s/.test(cleaned)) refs.push(cleaned);
  }
  return applyKeyHint(refs, tagType);
}

function isJsonLikeText(text) {
  if (typeof text !== "string") return false;
  const stripped = text.trim();
  return stripped.startsWith("{") || stripped.startsWith("[");
}

function looksLikeExtensionlessModelRef(v) {
  if (!v || typeof v !== "string") return false;
  const text = v.trim().replace(/^[\"']+|[\"']+$/g, "");
  if (!text) return false;
  const lower = text.toLowerCase();
  if (MODEL_EXTS.some(ext => lower.endsWith(ext))) return false;
  if (EXTENSIONLESS_STOPWORDS.has(lower)) return false;
  if (text.length < 3 || /^\d+$/.test(text)) return false;
  if (/[\s\"'<>\[\]{}|;,:]/.test(text)) return false;
  if (text.split(/[\\/]+/).some(part => !part || part === "." || part === "..")) return false;
  return /[A-Za-z_]/.test(text);
}

function looksLikeFullModelRef(v) {
  if (!v || typeof v !== "string") return false;
  const text = v.trim().replace(/^[\"']+|[\"']+$/g, "");
  if (!text) return false;
  const lower = text.toLowerCase();
  if (!MODEL_EXTS.some(ext => lower.endsWith(ext))) return false;
  if (/[<>\[\]{}|;,\n\r\t]/.test(text)) return false;
  if (text.split(/[\\/]+/).some(part => !part || part === "." || part === "..")) return false;
  return true;
}

function looksLikeExtensionlessLoraTagRef(v) {
  if (!v || typeof v !== "string") return false;
  const text = v.trim().replace(/^[\"']+|[\"']+$/g, "");
  if (!text) return false;
  const lower = text.toLowerCase();
  if (MODEL_EXTS.some(ext => lower.endsWith(ext))) return false;
  if (EXTENSIONLESS_STOPWORDS.has(lower)) return false;
  if (text.length > 180 || /^\d+$/.test(text)) return false;
  if (/[\"'<>{}\[\]|;,:\n\r\t]/.test(text)) return false;
  if (text.split(/[\\/]+/).some(part => !part || part === "." || part === "..")) return false;
  return /[A-Za-z_]/.test(text);
}

function splitLooseModelStack(text, { allowExtensionless = false, allowPlainExtensionless = false } = {}) {
  if (!text || typeof text !== "string") return [];
  if (!/[,\n\r]/.test(text)) return [];
  const refs = [];
  for (const part of text.split(/[,\n\r]+/)) {
    const item = part.trim().replace(/^[\"']+|[\"']+$/g, "");
    if (!item) continue;
    if (looksLikeFullModelRef(item)) refs.push(item);
    else if (allowExtensionless && allowPlainExtensionless && (looksLikeExtensionlessModelRef(item) || looksLikeExtensionlessLoraTagRef(item))) refs.push(item);
  }
  return uniquePreserveOrder(refs);
}

function extractModelRefsFromString(v, { loose = false, allowExtensionless = false, allowStandalone = true, allowPlainExtensionless = false } = {}) {
  const refs = [];
  if (!v || typeof v !== "string") return refs;
  const text = v.trim();
  if (!text) return refs;

  const jsonLikeText = text.startsWith("{") || text.startsWith("[");
  if (jsonLikeText) {
    if (text.length <= MAX_JSON_SCAN_TEXT) {
      try {
        return extractModelStringsFromValue(JSON.parse(text), [], { loose, allowExtensionless, allowStandalone, allowPlainExtensionless });
      } catch (_) {}
    } else {
      return refs;
    }
  }

  if (text.length > MAX_SCAN_TEXT) return refs;

  // A single key/value parser handles both extension-bearing and extensionless
  // exact-key values, avoiding duplicate processing of quoted filename values.
  let m;
  JSON_KEY_VALUE_RE.lastIndex = 0;
  while ((m = JSON_KEY_VALUE_RE.exec(text)) !== null) {
    refs.push(...refsFromExactKeyValue(m[2], m[3]));
  }

  // Pseudo JSON/dict text is structural metadata. After exact-key extraction,
  // do not run broad loose regex over unknown keys such as {name: "..."}.
  if (jsonLikeText) return uniquePreserveOrder(refs);

  const stripped = text.trim().replace(/^[\"']+|[\"']+$/g, "");
  const fullModelRef = looksLikeFullModelRef(stripped);
  const tagSpans = [];

  LORA_TAG_RE.lastIndex = 0;
  while ((m = LORA_TAG_RE.exec(text)) !== null) {
    const token = tagStateToken(m[2], m[1]);
    if (token) {
      refs.push(token);
      if (loose) tagSpans.push([m.index, LORA_TAG_RE.lastIndex]);
    }
  }

  if (allowExtensionless) {
    LORA_TAG_ANY_RE.lastIndex = 0;
    while ((m = LORA_TAG_ANY_RE.exec(text)) !== null) {
      const cleaned = stripRef(m[2]);
      if (cleaned && (looksLikeExtensionlessModelRef(cleaned) || looksLikeExtensionlessLoraTagRef(cleaned))) {
        refs.push(tagStateToken(cleaned, m[1]));
        if (loose) tagSpans.push([m.index, LORA_TAG_ANY_RE.lastIndex]);
      }
    }
  }

  if (!loose) {
    if (allowStandalone) {
      if (fullModelRef && !/\s/.test(stripped)) {
        refs.push(stripped);
        return uniquePreserveOrder(refs);
      }
      MODEL_REF_RE.lastIndex = 0;
      const match = MODEL_REF_RE.exec(stripped);
      if (match && match.index + match[1].length === 0 && match[2].length === stripped.length) {
        const cleaned = stripRef(match[2]);
        if (cleaned) refs.push(cleaned);
      }
    }
    return uniquePreserveOrder(refs);
  }

  const stackRefs = splitLooseModelStack(text, { allowExtensionless, allowPlainExtensionless });
  if (stackRefs.length) refs.push(...stackRefs);

  if (fullModelRef) refs.push(stripped);

  MODEL_REF_RE.lastIndex = 0;
  while ((m = MODEL_REF_RE.exec(text)) !== null) {
    const refStart = m.index + String(m[1] || "").length;
    if (isPositionInsideAnySpan(refStart, tagSpans)) continue;
    const cleaned = stripRef(m[2]);
    if (cleaned) refs.push(cleaned);
  }

  if (allowExtensionless && allowPlainExtensionless && (looksLikeExtensionlessModelRef(stripped) || looksLikeExtensionlessLoraTagRef(stripped))) refs.push(stripped);

  return uniquePreserveOrder(refs);
}


function cleanModelRef(v) {
  const refs = extractModelRefsFromString(v, { loose: true, allowExtensionless: true });
  return refs.length ? refs[0] : null;
}

function isModelPath(v) {
  return !!cleanModelRef(v);
}

function compactNodeType(nodeType) {
  return String(nodeType || "").toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function extractModelStringsFromValue(v, out = [], options = {}) {
  const loose = !!options.loose;
  const modelKeyContext = !!options.modelKeyContext;
  const allowExtensionless = !!options.allowExtensionless;
  const allowStandalone = options.allowStandalone !== false;
  const allowPlainExtensionless = !!options.allowPlainExtensionless;
  const depth = options.depth || 0;
  if (depth > MAX_SCAN_DEPTH) return uniquePreserveOrder(out);

  if (typeof v === "string") {
    out.push(...extractModelRefsFromString(v, {
      loose: loose || modelKeyContext,
      allowExtensionless,
      allowStandalone,
      allowPlainExtensionless: allowPlainExtensionless || (allowExtensionless && modelKeyContext),
    }));
  } else if (v && typeof v === "object") {
    const visited = options.visited || new WeakSet();
    if (visited.has(v)) return uniquePreserveOrder(out);
    visited.add(v);

    if (Array.isArray(v)) {
      for (const child of v) {
        extractModelStringsFromValue(child, out, { loose, modelKeyContext, allowExtensionless, allowStandalone, allowPlainExtensionless, visited, depth: depth + 1 });
      }
    } else {
      for (const [k, child] of Object.entries(v)) {
        const key = String(k).toLowerCase();
        const childIsModelKey = isExactModelKey(key);
        const keyTagType = childIsModelKey ? tagTypeForKey(key) : "";
        if (childIsModelKey) {
          const temp = [];
          extractModelStringsFromValue(child, temp, { loose, modelKeyContext: true, allowExtensionless, allowStandalone: true, allowPlainExtensionless: true, visited, depth: depth + 1 });
          out.push(...applyKeyHint(temp, keyTagType));
        } else if (typeof child === "string") {
          if (isJsonLikeText(child)) {
            extractModelStringsFromValue(child, out, { loose: false, modelKeyContext: false, allowExtensionless: false, allowStandalone: false, visited, depth: depth + 1 });
          }
        } else if (child && typeof child === "object") {
          extractModelStringsFromValue(child, out, { loose, modelKeyContext: false, allowExtensionless, allowStandalone: false, allowPlainExtensionless, visited, depth: depth + 1 });
        }
      }
    }
  }
  return uniquePreserveOrder(out);
}

function extractModelStringsFromInputs(v, out = [], options = {}) {
  const loose = !!options.loose;
  const modelKeyContext = !!options.modelKeyContext;
  const allowExtensionless = !!options.allowExtensionless;
  const allowStandalone = options.allowStandalone !== false;
  const allowPlainExtensionless = !!options.allowPlainExtensionless;
  const depth = options.depth || 0;
  if (depth > MAX_SCAN_DEPTH) return uniquePreserveOrder(out);

  if (typeof v === "string") {
    out.push(...extractModelRefsFromString(v, {
      loose: loose || modelKeyContext,
      allowExtensionless,
      allowStandalone,
      allowPlainExtensionless: allowPlainExtensionless || (allowExtensionless && modelKeyContext),
    }));
  } else if (v && typeof v === "object") {
    const visited = options.visited || new WeakSet();
    if (visited.has(v)) return uniquePreserveOrder(out);
    visited.add(v);

    if (Array.isArray(v)) {
      for (const child of v) {
        extractModelStringsFromInputs(child, out, { loose, modelKeyContext, allowExtensionless, allowStandalone, allowPlainExtensionless, visited, depth: depth + 1 });
      }
    } else {
      for (const [k, child] of Object.entries(v)) {
        const key = String(k).toLowerCase();
        if (INPUT_DESCRIPTOR_META_KEYS.has(key)) continue;
        const childIsModelKey = isExactModelKey(key);
        const keyTagType = childIsModelKey ? tagTypeForKey(key) : "";
        if (childIsModelKey) {
          const temp = [];
          extractModelStringsFromInputs(child, temp, { loose, modelKeyContext: true, allowExtensionless, allowStandalone: true, allowPlainExtensionless: true, visited, depth: depth + 1 });
          out.push(...applyKeyHint(temp, keyTagType));
        } else if (typeof child === "string") {
          if (isJsonLikeText(child)) {
            extractModelStringsFromInputs(child, out, { loose: false, modelKeyContext: false, allowExtensionless: false, allowStandalone: false, visited, depth: depth + 1 });
          }
        } else if (child && typeof child === "object") {
          extractModelStringsFromInputs(child, out, { loose, modelKeyContext: false, allowExtensionless, allowStandalone: false, allowPlainExtensionless, visited, depth: depth + 1 });
        }
      }
    }
  }
  return uniquePreserveOrder(out);
}

function extractModelStringsFromProperties(v, out = [], options = {}, state = {}) {
  const loose = !!options.loose;
  const modelKeyContext = !!options.modelKeyContext;
  const allowExtensionless = !!options.allowExtensionless;
  const allowStandalone = options.allowStandalone !== false;
  const allowPlainExtensionless = !!options.allowPlainExtensionless;
  const depth = state.depth || 0;
  const seen = state.seen || new WeakSet();
  if (depth > MAX_SCAN_DEPTH) return uniquePreserveOrder(out);
  if (typeof v === "string") {
    out.push(...extractModelRefsFromString(v, {
      loose: loose || modelKeyContext,
      allowExtensionless,
      allowStandalone,
      allowPlainExtensionless: allowPlainExtensionless || (allowExtensionless && modelKeyContext),
    }));
  } else if (Array.isArray(v)) {
    if (seen.has(v)) return uniquePreserveOrder(out);
    seen.add(v);
    for (const child of v) extractModelStringsFromProperties(child, out, { loose, modelKeyContext, allowExtensionless, allowStandalone, allowPlainExtensionless }, { seen, depth: depth + 1 });
  } else if (v && typeof v === "object") {
    if (seen.has(v)) return uniquePreserveOrder(out);
    seen.add(v);
    for (const [k, child] of Object.entries(v)) {
      const key = String(k).toLowerCase();
      if (!loose && !modelKeyContext && NON_LOOSE_PROPERTY_META_KEYS.has(key)) continue;
      const childIsModelKey = isExactModelKey(key);
      const keyTagType = childIsModelKey ? tagTypeForKey(key) : "";
      if (childIsModelKey) {
        const temp = [];
        extractModelStringsFromProperties(child, temp, { loose, modelKeyContext: true, allowExtensionless, allowStandalone: true, allowPlainExtensionless: true }, { seen, depth: depth + 1 });
        out.push(...applyKeyHint(temp, keyTagType));
      } else if (typeof child === "string") {
        if (isJsonLikeText(child)) {
          extractModelStringsFromProperties(child, out, { loose: false, modelKeyContext: false, allowExtensionless: false, allowStandalone: false, allowPlainExtensionless: false }, { seen, depth: depth + 1 });
        }
      } else if (child && typeof child === "object") {
        extractModelStringsFromProperties(child, out, { loose, modelKeyContext: false, allowExtensionless, allowStandalone: false, allowPlainExtensionless }, { seen, depth: depth + 1 });
      }
    }
  }
  return uniquePreserveOrder(out);
}

function getModelViewerNodeSubgraph(candidateNode) {
  if (!candidateNode || typeof candidateNode !== "object") return null;
  const candidates = [
    candidateNode.subgraph,
    candidateNode.subGraph,
    candidateNode.properties?.subgraph,
    candidateNode.properties?.subGraph,
    candidateNode.graph?.subgraph,
    candidateNode.graph?.subGraph,
  ];
  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== "object") continue;
    if (Array.isArray(candidate._nodes)) return candidate;
    if (candidate.graph && Array.isArray(candidate.graph._nodes)) return candidate.graph;
  }
  return null;
}

function collectModelViewerGraphsRecursive(graph, out = [], visited = new Set()) {
  if (!graph || typeof graph !== "object" || visited.has(graph)) return out;
  visited.add(graph);
  out.push(graph);

  const nodes = Array.isArray(graph._nodes) ? graph._nodes : [];
  for (const node of nodes) {
    const subgraph = getModelViewerNodeSubgraph(node);
    if (subgraph) collectModelViewerGraphsRecursive(subgraph, out, visited);
  }
  return out;
}

function getAllModelViewerGraphs() {
  if (!app.graph) return [];
  return collectModelViewerGraphsRecursive(app.graph, [], new Set());
}

function notifyWorkflowNodes() {
  for (const graph of getAllModelViewerGraphs()) {
    const nodes = Array.isArray(graph?._nodes) ? graph._nodes : [];
    for (const node of nodes) {
      if (node && node.type === "ModelSizeViewerWorkflow" && typeof node.scheduleUpdate === "function") {
        node.scheduleUpdate();
      }
    }
  }
}

// ----------------- global hook (widget callbacks) -----------------
let widgetHookInstalled = false;
const _wrappedCallbacks = new WeakMap();

function wrapWidgetCallback(widget) {
  if (!widget || typeof widget !== "object") return;
  if (_wrappedCallbacks.has(widget)) return;

  const originalCallback = widget.callback;
  widget.callback = function(...args) {
    let result;
    try {
      if (originalCallback) result = originalCallback.apply(this, args);
    } finally {
      notifyWorkflowNodes();
    }
    return result;
  };

  _wrappedCallbacks.set(widget, true);
}

function hookAllExistingNodesWidgets() {
  for (const graph of getAllModelViewerGraphs()) {
    const nodes = Array.isArray(graph?._nodes) ? graph._nodes : [];
    for (const node of nodes) {
      if (!node || !node.widgets) continue;
      for (const w of node.widgets) wrapWidgetCallback(w);
    }
  }
}

function installWidgetHook() {
  hookAllExistingNodesWidgets();

  const LGraphNode = window.LGraphNode;
  if (!LGraphNode) return;
  if (widgetHookInstalled) return;
  widgetHookInstalled = true;

  if (!LGraphNode.prototype._modelViewerPatchedOnPropertyChanged) {
    const originalOnPropertyChanged = LGraphNode.prototype.onPropertyChanged;
    LGraphNode.prototype.onPropertyChanged = function(...args) {
      const result = originalOnPropertyChanged ? originalOnPropertyChanged.apply(this, args) : undefined;
      const value = args[1];
      if (isModelPath(value)) {
        notifyWorkflowNodes();
      } else if (this && this.widgets && this.widgets.some(w => w && isExactModelKey(w.name))) {
        notifyWorkflowNodes();
      }
      return result;
    };
    LGraphNode.prototype._modelViewerPatchedOnPropertyChanged = true;
  }

  if (!LGraphNode.prototype._modelViewerPatchedAddWidget) {
    const originalAddWidget = LGraphNode.prototype.addWidget;
    LGraphNode.prototype.addWidget = function() {
      const widget = originalAddWidget ? originalAddWidget.apply(this, arguments) : null;
      if (widget) wrapWidgetCallback(widget);
      if (this && this.widgets) {
        const lastWidget = this.widgets[this.widgets.length - 1];
        if (lastWidget) wrapWidgetCallback(lastWidget);
      }
      notifyWorkflowNodes();
      return widget;
    };
    LGraphNode.prototype._modelViewerPatchedAddWidget = true;
  }
}

// ----------------- graph hook -----------------
const graphChangeHookedGraphs = new WeakSet();

function hookSingleGraphChange(graph) {
  if (!graph || typeof graph !== "object" || graphChangeHookedGraphs.has(graph)) return;
  graphChangeHookedGraphs.add(graph);

  const originalOnNodeAdded   = graph.onNodeAdded;
  const originalOnNodeRemoved = graph.onNodeRemoved;

  graph.onNodeAdded = function(node) {
    const result = originalOnNodeAdded ? originalOnNodeAdded.call(this, node) : undefined;
    if (node && node.widgets) {
      for (const w of node.widgets) wrapWidgetCallback(w);
    }
    const subgraph = getModelViewerNodeSubgraph(node);
    if (subgraph) hookSingleGraphChange(subgraph);
    hookAllExistingNodesWidgets();
    notifyWorkflowNodes();
    return result;
  };

  graph.onNodeRemoved = function(node) {
    const result = originalOnNodeRemoved ? originalOnNodeRemoved.call(this, node) : undefined;
    hookGraphChange();
    notifyWorkflowNodes();
    return result;
  };
}

function hookGraphChange() {
  for (const graph of getAllModelViewerGraphs()) {
    hookSingleGraphChange(graph);
  }
}

// ----------------- extension -----------------
app.registerExtension({
  name: "ModelViewer.Extension",

  // async 불필요 - 함수 내부에 await 없음
  beforeRegisterNodeDef(nodeType, nodeData, app) {

    // ── ModelSizeViewerDetailed ──────────────────────────────────────
    if (nodeData.name === "ModelSizeViewerDetailed") {
      const onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function() {
        const result = onNodeCreated?.apply(this, arguments);
        const node = this;

        // Python INPUT_TYPES에서 ComfyUI가 미리 생성한 위젯 탐색
        const categoryWidget = node.widgets?.find(w => w.name === "category");
        const showTopWidget  = node.widgets?.find(w => w.name === "show_top");
        const infoWidget     = node.widgets?.find(w => w.name === "info");

        if (!categoryWidget || !showTopWidget || !infoWidget) {
          console.error("[ModelViewer] Detailed 위젯을 찾을 수 없습니다.", node.widgets);
          return result;
        }

        // frontend 버전별 textarea 프로퍼티명 대응
        const infoTextarea = ultraWidgetEl(infoWidget);
        if (infoTextarea) {
          infoTextarea.readOnly = true;
          infoTextarea.style.opacity = 0.85;
        }
        infoWidget.value = "Loading...";

        node.infoWidget      = infoWidget;
        node.isUpdating      = false;
        node.totalModelCount = 0;
        node._modelViewerRemoved = false;
        node._modelViewerPendingUpdate = false;

        // 폴더 변경 콜백
        const origCategoryCallback = categoryWidget.callback;
        categoryWidget.callback = function(...args) {
          const cbResult = origCategoryCallback ? origCategoryCallback.apply(this, args) : undefined;
          if (node._modelViewerRemoved) return cbResult;
          node.updateModels();
          return cbResult;
        };

        // show_top 변경 콜백
        const origShowTopCallback = showTopWidget.callback;
        showTopWidget.callback = function(...args) {
          const cbResult = origShowTopCallback ? origShowTopCallback.apply(this, args) : undefined;
          if (node._modelViewerRemoved) return cbResult;
          node.updateModels();
          return cbResult;
        };

        // Refresh 버튼을 별도 추가 (INPUT_TYPES에 없는 버튼 위젯은 동적 추가 허용)
        node.addWidget("button", "refresh", "🔄 Refresh", () => {
          if (node._modelViewerRemoved) return;
          node.updateShowTopOptions();
          node.updateModels();
        });

        node.updateShowTopOptions = function() {
          if (this.totalModelCount <= 0) {
            showTopWidget.options.values = ["0"];
            showTopWidget.value = "0";
            this.setDirtyCanvas(true, true);
            return;
          }

          const options = [];
          const maxOption = Math.min(this.totalModelCount, 200);
          for (let i = 5; i <= maxOption; i += 5) options.push(String(i));
          if (this.totalModelCount % 5 !== 0 || this.totalModelCount > 200) options.push(String(this.totalModelCount));

          const currentValue = String(showTopWidget.value || "20");
          const preferredValue = options.includes(currentValue) ? currentValue : (options.includes("20") ? "20" : options[options.length - 1]);
          showTopWidget.options.values = options;
          showTopWidget.value = preferredValue;

          this.setDirtyCanvas(true, true);
        };

        node.formatSize = function(bytes) {
          if (bytes === 0) return "0 B";
          const units = ["B","KB","MB","GB","TB"];
          let size = bytes, i = 0;
          while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
          return `${size.toFixed(2)} ${units[i]}`;
        };

        node.updateModels = async function() {
          if (this._modelViewerRemoved) return;
          if (this.isUpdating) {
            this._modelViewerPendingUpdate = true;
            return;
          }
          this.isUpdating = true;

          const category = categoryWidget.value;
          infoWidget.value = "Loading...";
          if (infoTextarea) infoTextarea.value = "Loading...";

          try {
            const url = `/Ultra-model-viewer/scan/${encodeURIComponent(category)}`;
            const response = await api.fetchApi(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            if (data.error) {
              const msg = `Error: ${data.error}`;
              infoWidget.value = msg;
              if (infoTextarea) infoTextarea.value = msg;
              this.totalModelCount = 0;
              this.updateShowTopOptions();
              return;
            }
            if (!data.files || data.files.length === 0) {
              const emptyMessage = data.message || "No models found";
              infoWidget.value = emptyMessage;
              if (infoTextarea) infoTextarea.value = emptyMessage;
              this.totalModelCount = 0;
              this.updateShowTopOptions();
              return;
            }

            this.totalModelCount = data.count;
            this.updateShowTopOptions();

            const topN = parseInt(showTopWidget.value);
            let text = `━━━ ${data.count} models (${this.formatSize(data.total_size)}) ━━━\n\n`;
            const displayCount = Math.min(topN, data.files.length);

            for (let i = 0; i < displayCount; i++) {
              const file = data.files[i];
              const percentage = data.total_size > 0 ? ((file.size / data.total_size) * 100).toFixed(1) : "0.0";
              const folderPrefix = file.folder_prefix ? `[${file.folder_prefix}] ` : "";
              text += `${String(i+1).padStart(2)}. ${percentage.padStart(5)}% │ ${file.size_formatted.padStart(10)} │ ${folderPrefix}${file.display_name}\n`;
            }

            infoWidget.value = text;
            if (infoTextarea) infoTextarea.value = text;
          } catch (error) {
            infoWidget.value = `Error: ${error.message}`;
            if (infoTextarea) infoTextarea.value = `Error: ${error.message}`;
          } finally {
            this.isUpdating = false;
            if (this._modelViewerPendingUpdate && !this._modelViewerRemoved) {
              this._modelViewerPendingUpdate = false;
              this.updateModels();
            }
          }
        };

        node._modelViewerInitialUpdateTimer = setTimeout(() => {
          if (!node._modelViewerRemoved) node.updateModels();
        }, 300);
        return result;
      };

      const onRemoved = nodeType.prototype.onRemoved;
      nodeType.prototype.onRemoved = function() {
        this._modelViewerRemoved = true;
        if (this._modelViewerInitialUpdateTimer) {
          clearTimeout(this._modelViewerInitialUpdateTimer);
          this._modelViewerInitialUpdateTimer = null;
        }
        return onRemoved?.apply(this, arguments);
      };
    }

    // ── ModelSizeViewerWorkflow ──────────────────────────────────────
    if (nodeData.name === "ModelSizeViewerWorkflow") {
      const onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function() {
        const result = onNodeCreated?.apply(this, arguments);
        const node = this;
        node._modelViewerRemoved = false;

        // Python INPUT_TYPES에서 ComfyUI가 미리 생성한 위젯 탐색
        const modelsWidget = node.widgets?.find(w => w.name === "models");

        if (!modelsWidget) {
          console.error("[ModelViewer] Workflow 위젯을 찾을 수 없습니다.", node.widgets);
          return result;
        }

        // frontend 버전별 textarea 프로퍼티명 대응
        const modelsTextarea = ultraWidgetEl(modelsWidget);
        if (modelsTextarea) {
          modelsTextarea.readOnly = true;
          modelsTextarea.style.opacity = 0.85;
        }
        modelsWidget.value = "Loading...";

        node.modelsWidget       = modelsWidget;
        node.isUpdating         = false;
        node.lastWorkflowState  = null;
        node.updateScheduled    = false;

        node._stateTokenToCandidate = function(token, nodeType = "", key = "") {
          if (!token) return null;
          const text = String(token);
          const sep = text.indexOf("::");
          if (sep > 0) {
            return {
              ref: text.slice(sep + 2),
              tag_type: text.slice(0, sep),
              node_type: nodeType || "",
              key: key || "",
              source: "frontend_widget"
            };
          }
          return { ref: text, node_type: nodeType || "", key: key || "", source: "frontend_widget" };
        };

        node._getNodeSubgraphForModelViewer = function(candidateNode) {
          if (!candidateNode || typeof candidateNode !== "object") return null;
          const candidates = [
            candidateNode.subgraph,
            candidateNode.subGraph,
            candidateNode.properties?.subgraph,
            candidateNode.properties?.subGraph,
            candidateNode.graph?.subgraph,
            candidateNode.graph?.subGraph,
          ];
          for (const candidate of candidates) {
            if (!candidate || typeof candidate !== "object") continue;
            if (Array.isArray(candidate._nodes)) return candidate;
            if (candidate.graph && Array.isArray(candidate.graph._nodes)) return candidate.graph;
          }
          return null;
        };

        node._collectGraphsForModelViewer = function(graph, out = [], visited = new Set()) {
          if (!graph || typeof graph !== "object" || visited.has(graph)) return out;
          visited.add(graph);
          out.push(graph);

          const nodes = Array.isArray(graph._nodes) ? graph._nodes : [];
          for (const graphNode of nodes) {
            const subgraph = this._getNodeSubgraphForModelViewer(graphNode);
            if (subgraph) this._collectGraphsForModelViewer(subgraph, out, visited);
          }
          return out;
        };

        node.collectFrontendModelCandidates = function() {
          const candidates = [];
          const seen = new Set();
          const addCandidate = (token, nodeType = "", key = "") => {
            const item = this._stateTokenToCandidate(token, nodeType, key);
            if (!item || !item.ref) return;
            const dedupeKey = `${item.node_type}|${item.key}|${item.tag_type || ""}|${item.ref}`.toLowerCase();
            if (seen.has(dedupeKey)) return;
            seen.add(dedupeKey);
            candidates.push(item);
          };

          const graphs = this._collectGraphsForModelViewer ? this._collectGraphsForModelViewer(app.graph) : [];
          for (const graph of graphs) {
            const nodes = Array.isArray(graph?._nodes) ? graph._nodes : [];
            for (const n of nodes) {
              if (!n) continue;
              const nodeMode = n.mode ?? 0;
              if (nodeMode === 2 || nodeMode === 4) continue;
              const nodeType = n.type || n.class_type || "";
              for (const w of (n.widgets || [])) {
                if (!w || !isExactModelKey(w.name)) continue;
                const key = w.name || "";
                const val = (w.value !== undefined) ? w.value : w;
                let hits = [];
                if (typeof val === "string") {
                  hits = refsFromExactKeyValue(key, val);
                }
                if (!hits.length || typeof val !== "string" || /[,\n\r<>{}\[\]]/.test(val)) {
                  const keyTag = tagTypeForKey(key);
                  const extracted = extractModelStringsFromValue(val, [], {
                    loose: false,
                    modelKeyContext: true,
                    allowExtensionless: true,
                    allowStandalone: true,
                    allowPlainExtensionless: true
                  });
                  for (const hit of extracted) {
                    hits.push(keyTag && !String(hit).includes("::") ? tagStateToken(hit, keyTag) : hit);
                  }
                }
                hits = uniquePreserveOrder(hits);
                for (const hit of hits) addCandidate(hit, nodeType, key);
              }
            }
          }
          return candidates;
        };

        node._compactWorkflowStateForFingerprint = function(workflow) {
          const compactValue = (value, depth = 0) => {
            if (depth > 5) return "[max-depth]";
            if (value === null || value === undefined) return value;
            const valueType = typeof value;
            if (valueType === "string" || valueType === "number" || valueType === "boolean") return value;
            if (Array.isArray(value)) return value.map(v => compactValue(v, depth + 1));
            if (valueType === "object") {
              const out = {};
              for (const key of Object.keys(value).sort()) {
                if (key === "pos" || key === "size" || key === "flags" || key === "color" || key === "bgcolor") continue;
                out[key] = compactValue(value[key], depth + 1);
              }
              return out;
            }
            return String(value);
          };

          const modelTokensFrom = (value, mode = "value") => {
            const options = {
              loose: true,
              modelKeyContext: false,
              allowExtensionless: true,
              allowStandalone: true,
              allowPlainExtensionless: false,
            };
            const hits = mode === "inputs"
              ? extractModelStringsFromInputs(value, [], options)
              : mode === "properties"
                ? extractModelStringsFromProperties(value, [], options)
                : extractModelStringsFromValue(value, [], options);
            return uniquePreserveOrder(hits).sort();
          };

          const collectSubgraphRefs = (value, out = [], depth = 0) => {
            if (depth > 4 || value === null || value === undefined) return out;
            if (typeof value === "string" || typeof value === "number") {
              const text = String(value);
              if (text) out.push(text);
              return out;
            }
            if (Array.isArray(value)) {
              for (const child of value) collectSubgraphRefs(child, out, depth + 1);
              return out;
            }
            if (typeof value === "object") {
              for (const key of ["id", "name", "title", "subgraph_id", "subgraphId", "subgraph", "subgraph_name", "subgraphName", "definition_id", "definitionId", "graph_id", "graphId"]) {
                if (Object.prototype.hasOwnProperty.call(value, key)) collectSubgraphRefs(value[key], out, depth + 1);
              }
            }
            return out;
          };

          const summarizeNode = (n) => {
            if (!n) return null;
            const nodeType = n.type || n.class_type || "";
            const isViewerNode = nodeType === "ModelSizeViewerWorkflow";
            return compactValue({
              id: n.id,
              type: nodeType,
              class_type: n.class_type,
              mode: n.mode ?? 0,
              widget_model_refs: isViewerNode ? [] : modelTokensFrom(n.widgets_values),
              property_model_refs: modelTokensFrom(n.properties, "properties"),
              input_model_refs: modelTokensFrom(n.inputs, "inputs"),
              subgraph_refs: uniquePreserveOrder([
                ...collectSubgraphRefs(n),
                ...collectSubgraphRefs(n?.properties),
              ]).sort(),
            });
          };

          const state = { nodes: [] };
          const nodes = Array.isArray(workflow?.nodes) ? workflow.nodes : [];
          state.nodes = nodes.map(summarizeNode);

          const subgraphs = workflow?.definitions?.subgraphs;
          if (Array.isArray(subgraphs)) {
            state.definitions = {
              subgraphs: subgraphs.map((sg, index) => compactValue({
                id: sg?.id ?? index,
                name: sg?.name,
                title: sg?.title,
                nodes: Array.isArray(sg?.nodes) ? sg.nodes.map(summarizeNode) : [],
              }))
            };
          }
          return state;
        };

        node.getWorkflowState = function(frontendCandidates = null, workflowOverride = null) {
          try {
            const workflow = workflowOverride || app.graph?.serialize?.() || {};
            const candidatesForState = Array.isArray(frontendCandidates)
              ? frontendCandidates
              : (this.collectFrontendModelCandidates ? this.collectFrontendModelCandidates() : []);
            return JSON.stringify({
              workflow_state: this._compactWorkflowStateForFingerprint(workflow),
              frontend_candidates: candidatesForState
            });
          } catch (e) {
            console.error("[ModelViewer] getWorkflowState error:", e);
            return JSON.stringify({ workflow_state_error: true, frontend_candidates: [] });
          }
        };

        node.updateModels = async function(options = {}) {
          if (this._modelViewerRemoved) return;
          if (this.isUpdating) {
            this.updateScheduled = false;
            this._modelViewerPendingUpdate = true;
            return;
          }
          this.isUpdating = true;
          this.updateScheduled = false;

          let nextWorkflowState = null;
          try {
            const workflow = app.graph.serialize();
            const frontendCandidates = this.collectFrontendModelCandidates ? this.collectFrontendModelCandidates() : [];
            nextWorkflowState = this.getWorkflowState(frontendCandidates, workflow);
            const forceUpdate = !!(options && options.force);
            if (!forceUpdate && nextWorkflowState === this.lastWorkflowState) {
              return;
            }

            const response = await api.fetchApi("/Ultra-model-viewer/workflow-models", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ workflow, frontend_candidates: frontendCandidates })
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            this.lastWorkflowState = nextWorkflowState;

            if (data.error) {
              const msg = `Error: ${data.error}`;
              modelsWidget.value = msg;
              if (modelsTextarea) modelsTextarea.value = msg;
              return;
            }

            if (!data.models || data.total_count === 0) {
              modelsWidget.value = "No models in workflow";
              if (modelsTextarea) modelsTextarea.value = "No models in workflow";
              return;
            }

            const icons = {
              "UNET":"🧠","Checkpoints":"🎨","Text_Encoders":"📚","CLIP":"📝","CLIP_Vision":"👁️","VAE":"🔧","LORA":"✨",
              "Upscale":"🔍","ControlNet":"🎮",
              "UNET_GGUF":"⚙️","CLIP_GGUF":"📑","VAE_GGUF":"🔩",
              "UNET_Nunchaku":"🥋","VAE_Nunchaku":"🥊",
              "SEEDVR2":"🎬","Animatediff":"🎞️","Motion_Module":"🌊",
              "CogVideo":"📹","Photomaker":"📸","Insightface":"👤","Facerestore":"✨","Facedetection":"👁️",
              "ONNX":"⚡","Diffusers":"🌐","SAMS":"✂️","GroundingDINO":"🎯","BBOX":"📦","Segm":"🗺️",
              "Audio_Encoders":"🎵","Style_Models":"🎨","Hypernetworks":"🕸️","Embeddings":"💎",
              "GLigen":"🖼️","Ipadapter":"🔌","LLM":"🤖","Prompt_Expander":"💬","Blip":"👀",
              "Model_Patches":"🩹","VAE_Approx":"🧪","Background_Removal":"🧼","Frame_Interpolation":"🎯",
              "Geometry_Estimation":"📐","Optical_Flow":"🌪️","Detection":"🚨","Custom":"🔧"
            };

            const order = [
              "UNET","UNET_GGUF","UNET_Nunchaku",
              "Checkpoints",
              "Text_Encoders","CLIP","CLIP_GGUF","CLIP_Vision",
              "VAE","VAE_GGUF","VAE_Nunchaku",
              "LORA","LLM",
              "Upscale","ControlNet",
              "Animatediff","Motion_Module","SEEDVR2","CogVideo",
              "Ipadapter",
              "Embeddings","Hypernetworks","Style_Models",
              "ONNX","Diffusers","SAMS","GroundingDINO","BBOX","Segm",
              "Audio_Encoders","Blip","Photomaker","Insightface","Facerestore","Facedetection",
              "Prompt_Expander","Model_Patches","VAE_Approx","Background_Removal","Frame_Interpolation",
              "Geometry_Estimation","Optical_Flow","Detection",
              "Custom",
            ];

            let text = `━━━ ${data.total_count} models ━━━\n\n`;
            const seenCats = new Set();
            const orderedCats = [];
            for (const cat of order) {
              if (data.models[cat]) {
                orderedCats.push(cat);
                seenCats.add(cat);
              }
            }
            for (const cat of Object.keys(data.models).sort()) {
              if (!seenCats.has(cat)) orderedCats.push(cat);
            }
            for (const cat of orderedCats) {
              if (!data.models[cat]) continue;
              for (const f of data.models[cat].files) {
                text += `${icons[cat] || "📦"} ${f.size_formatted.padStart(10)} │ ${f.display_name} (${cat})\n`;
              }
            }
            modelsWidget.value = text;
            if (modelsTextarea) modelsTextarea.value = text;
          } catch (error) {
            if (nextWorkflowState !== null) this.lastWorkflowState = nextWorkflowState;
            modelsWidget.value = `Error: ${error.message}`;
            if (modelsTextarea) modelsTextarea.value = `Error: ${error.message}`;
          } finally {
            this.isUpdating = false;
            if (this._modelViewerPendingUpdate && !this._modelViewerRemoved) {
              this._modelViewerPendingUpdate = false;
              this.scheduleUpdate();
            }
          }
        };

        node.scheduleUpdate = function() {
          if (this._modelViewerRemoved) return;
          if (this.updateScheduled) return;
          this.updateScheduled = true;

          setTimeout(() => {
            if (this._modelViewerRemoved) {
              this.updateScheduled = false;
              return;
            }
            this.updateModels();
          }, 50);
        };

        const originalOnDblClick = node.onDblClick;
        node.onDblClick = function(...args) {
          const dblResult = originalOnDblClick ? originalOnDblClick.apply(this, args) : undefined;
          if (!node._modelViewerRemoved) node.updateModels({ force: true });
          return dblResult;
        };

        const originalGetExtraMenuOptions = node.getExtraMenuOptions;
        node.getExtraMenuOptions = function(canvas, options = []) {
          const menuResult = originalGetExtraMenuOptions ? originalGetExtraMenuOptions.apply(this, arguments) : undefined;
          const targetOptions = Array.isArray(menuResult) ? menuResult : options;
          if (Array.isArray(targetOptions)) {
            targetOptions.push({ content: "🔄 Refresh Models", callback: () => node.updateModels({ force: true }) });
          }
          return Array.isArray(menuResult) ? targetOptions : menuResult;
        };

        node._modelViewerHookTimer = setTimeout(() => {
          if (node._modelViewerRemoved) return;
          if (app.graph && Array.isArray(app.graph._nodes) && !app.graph._nodes.includes(node)) return;

          hookGraphChange();
          installWidgetHook();

          node._modelViewerOnExecuting = () => setTimeout(() => {
            if (!node._modelViewerRemoved) node.scheduleUpdate();
          }, 100);
          node._modelViewerOnExecuted = () => setTimeout(() => {
            if (!node._modelViewerRemoved) node.scheduleUpdate();
          }, 200);
          api.addEventListener("executing", node._modelViewerOnExecuting);
          api.addEventListener("executed", node._modelViewerOnExecuted);
        }, 100);

        node._modelViewerInitialUpdateTimer = setTimeout(() => {
          if (!node._modelViewerRemoved) node.updateModels();
        }, 500);
        return result;
      };

      const onRemoved = nodeType.prototype.onRemoved;
      nodeType.prototype.onRemoved = function() {
        this._modelViewerRemoved = true;
        if (this._modelViewerHookTimer) {
          clearTimeout(this._modelViewerHookTimer);
          this._modelViewerHookTimer = null;
        }
        if (this._modelViewerInitialUpdateTimer) {
          clearTimeout(this._modelViewerInitialUpdateTimer);
          this._modelViewerInitialUpdateTimer = null;
        }
        if (this._modelViewerOnExecuting && typeof api.removeEventListener === "function") {
          api.removeEventListener("executing", this._modelViewerOnExecuting);
          this._modelViewerOnExecuting = null;
        }
        if (this._modelViewerOnExecuted && typeof api.removeEventListener === "function") {
          api.removeEventListener("executed", this._modelViewerOnExecuted);
          this._modelViewerOnExecuted = null;
        }
        return onRemoved?.apply(this, arguments);
      };
    }
  },

  setup() {  // async 불필요
    const waitForGraph = setInterval(() => {
      if (app.graph) {
        clearInterval(waitForGraph);
        hookGraphChange();
        installWidgetHook();
        hookAllExistingNodesWidgets();
      }
    }, 100);

    setTimeout(() => clearInterval(waitForGraph), 10000);
  }
});
