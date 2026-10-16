import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_NAME = "UltraTranslatorTextNode";
const STATUS_PATH = "/ultra_translator/translation_api";
const TEST_PATH = "/ultra_translator/translation_api/test";
const MARKER = Symbol.for("ultraTranslator.translationApiWidget");
const LIVE_WIDGETS = new Set();

const T = Object.freeze({
  buttonUnset: "Google 번역 API 설정",
  buttonReady: "Google 번역 API · 키 저장됨",
  tooltip:
    "공식 Google Cloud Translation Basic v2 API Key를 설정합니다. Ultra MiniMax H3 Prompt와 같은 Key를 공유하며, Key는 workflow에 저장되지 않습니다. Key가 없거나 공식 API가 실패하면 기존 무료 Google/MyMemory 경로를 계속 사용합니다.",
  title: "Google 번역 API 설정",
  intro:
    "공식 Google Cloud Translation Basic v2를 우선 사용합니다. 이 Key는 Ultra MiniMax H3 Prompt와 공유되므로 한쪽에서 저장한 Key를 다른 쪽에서도 사용할 수 있습니다. 공식 API가 실패하면 기존 무료 Google/MyMemory 번역 경로를 계속 시도합니다.",
  configured: "상태: API Key 저장됨 · H3 Prompt와 공유됨",
  notConfigured: "상태: API Key 미설정",
  keyLabel: "Google Cloud Translation API Key",
  keyPlaceholderSaved: "저장된 키가 있습니다 · 변경하려면 새 키 입력",
  keyPlaceholderEmpty: "API Key 입력",
  savedKeyPrivacyHint:
    "보안을 위해 이미 저장된 API Key는 다시 표시하지 않습니다. 이 입력란은 새 Key 입력 또는 기존 Key 교체용입니다.",
  sharedHint:
    "공유 안내: Ultra MiniMax H3 Prompt에서 이미 Key를 저장했다면 여기에서 다시 입력할 필요가 없습니다. 반대로 여기에서 저장한 Key도 H3 Prompt가 함께 사용합니다.",
  setupHint:
    "Google Cloud Console에서 Cloud Translation API를 활성화하고 Billing을 연결한 뒤 API Key를 발급하세요. Key 제한은 Cloud Translation API로 지정하는 것을 권장합니다.",
  fallbackHint:
    "429 안내: 무료·익명 번역 경로는 사용량이 많지 않아도 일시적으로 429 제한이 걸릴 수 있습니다. 공식 API Key를 사용하면 무료 웹 번역 경로보다 안정적이지만 Google Cloud 할당량 자체는 적용됩니다.",
  workflowHint:
    "보안: API Key는 ComfyUI 사용자 로컬 설정에만 저장되고 workflow, 노드 속성, prompt payload에는 포함되지 않습니다.",
  showKey: "입력 중인 키 표시",
  keyTestHint:
    "새 Key를 입력한 상태에서 ‘연결 테스트’를 누르면 저장 전에 그 Key를 시험합니다. 입력칸이 비어 있으면 현재 저장된 공유 Key를 시험합니다.",
  test: "연결 테스트",
  save: "키 저장",
  remove: "저장된 키 삭제",
  close: "닫기",
  testing: "공식 Google Cloud Translation 연결을 테스트하는 중...",
  saving: "API Key를 저장하는 중...",
  deleting: "저장된 API Key를 삭제하는 중...",
  testOk: (text) => `테스트 성공: ${text}`,
  saveOk: "API Key를 저장했습니다. Ultra MiniMax H3 Prompt와 공유됩니다.",
  deleteOk: "저장된 공유 API Key를 삭제했습니다. 번역은 기존 무료 경로를 사용합니다.",
  enterKey: "저장할 API Key를 입력하세요.",
  confirmDelete:
    "공유된 Google Translation API Key를 삭제할까요? Ultra MiniMax H3 Prompt에서도 이 Key를 더 이상 사용할 수 없게 됩니다.",
  errorRateLimited:
    "Google Cloud Translation 사용량/속도 제한에 걸렸습니다. Google Cloud 할당량을 확인하고 잠시 후 다시 시도하세요.",
  errorConfiguration:
    "API Key 또는 Google Cloud 프로젝트 설정을 확인하세요. Cloud Translation API 활성화, Billing 연결, API Key의 Cloud Translation API 제한을 확인하세요.",
  errorStorage:
    "API Key를 ComfyUI 사용자 폴더에 저장하거나 삭제하지 못했습니다. 폴더 쓰기 권한을 확인하세요.",
  errorMissingKey: "테스트할 API Key를 입력하거나 먼저 저장하세요.",
  errorProvider:
    "Google Cloud Translation 연결 테스트에 실패했습니다. 인터넷 연결과 Google Cloud 서비스 상태를 확인하세요.",
  requestFailed: "요청에 실패했습니다.",
});

function widgetsOf(node) {
  return Array.isArray(node?.widgets) ? node.widgets : [];
}

function apiWidget(node) {
  return widgetsOf(node).find((w) => Boolean(w?.[MARKER])) || null;
}

async function requestJson(path, options = {}) {
  const response = await api.fetchApi(path, options);
  let payload = null;
  try {
    payload = await response.json();
  } catch (_) {}
  if (!response.ok || !payload?.ok) {
    const error = new Error(String(payload?.error || response.statusText || "Request failed."));
    error.type = payload?.type || "request_error";
    throw error;
  }
  return payload;
}

function localizedError(error) {
  const type = String(error?.type || "");
  if (type === "rate_limited") return T.errorRateLimited;
  if (type === "configuration_error") return T.errorConfiguration;
  if (type === "storage_error") return T.errorStorage;
  if (type === "missing_key") return T.errorMissingKey;
  if (type === "provider_error") return T.errorProvider;
  return error?.message || T.requestFailed;
}

function applyButtonText(node, widget) {
  if (!widget) return;
  const text = widget.__ultraTranslatorApiConfigured ? T.buttonReady : T.buttonUnset;
  widget.name = text;
  widget.label = text;
  widget.tooltip = T.tooltip;
  widget.options = { ...(widget.options || {}), serialize: false, tooltip: T.tooltip };
  node?.setDirtyCanvas?.(true, true);
}

function track(node, widget) {
  if (!widget) return;
  widget.__ultraTranslatorApiNode = node;
  LIVE_WIDGETS.add(widget);
}

function setConfigured(node, widget, configured) {
  const value = Boolean(configured);
  track(node, widget);
  for (const candidate of Array.from(LIVE_WIDGETS)) {
    const owner = candidate?.__ultraTranslatorApiNode;
    if (!owner || !widgetsOf(owner).includes(candidate)) {
      LIVE_WIDGETS.delete(candidate);
      continue;
    }
    candidate.__ultraTranslatorApiConfigured = value;
    candidate.__ultraTranslatorApiStatusKnown = true;
    applyButtonText(owner, candidate);
  }
}

async function refreshStatus(node, widget) {
  if (!widget || widget.__ultraTranslatorApiStatusPending) return;
  widget.__ultraTranslatorApiStatusPending = true;
  try {
    const payload = await requestJson(STATUS_PATH);
    setConfigured(node, widget, Boolean(payload.configured));
  } catch (_) {
    applyButtonText(node, widget);
  } finally {
    widget.__ultraTranslatorApiStatusPending = false;
  }
}

function styledButton(text) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = text;
  Object.assign(button.style, {
    minHeight: "32px",
    padding: "6px 11px",
    borderRadius: "7px",
    border: "1px solid rgba(255,255,255,0.18)",
    background: "rgba(255,255,255,0.08)",
    color: "inherit",
    cursor: "pointer",
  });
  return button;
}

function addHint(panel, text, { strong = false } = {}) {
  const hint = document.createElement("div");
  hint.textContent = text;
  Object.assign(hint.style, {
    marginTop: "8px",
    padding: "8px 10px",
    borderRadius: "7px",
    background: strong ? "rgba(80,150,255,0.10)" : "rgba(255,255,255,0.045)",
    border: strong ? "1px solid rgba(100,170,255,0.22)" : "1px solid rgba(255,255,255,0.07)",
    lineHeight: "1.5",
    opacity: strong ? "0.95" : "0.78",
    fontSize: "12px",
  });
  panel.appendChild(hint);
  return hint;
}

function openSettingsDialog(node, widget) {
  if (typeof document === "undefined" || !document.body) return;
  if (widget.__ultraTranslatorApiDialog?.isConnected) return;

  const overlay = document.createElement("div");
  widget.__ultraTranslatorApiDialog = overlay;
  Object.assign(overlay.style, {
    position: "fixed",
    inset: "0",
    zIndex: "100000",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "24px",
    background: "rgba(0,0,0,0.58)",
    boxSizing: "border-box",
  });

  const panel = document.createElement("div");
  Object.assign(panel.style, {
    width: "min(650px, calc(100vw - 32px))",
    maxHeight: "calc(100vh - 48px)",
    overflow: "auto",
    boxSizing: "border-box",
    borderRadius: "12px",
    border: "1px solid rgba(255,255,255,0.16)",
    background: "var(--comfy-menu-bg, #252525)",
    color: "var(--input-text, #e8e8e8)",
    boxShadow: "0 18px 48px rgba(0,0,0,0.45)",
    padding: "18px",
    fontFamily: "Arial, sans-serif",
  });
  overlay.appendChild(panel);

  const titleRow = document.createElement("div");
  Object.assign(titleRow.style, { display: "flex", alignItems: "center", gap: "12px" });
  const title = document.createElement("div");
  title.textContent = T.title;
  Object.assign(title.style, { fontSize: "17px", fontWeight: "700", flex: "1" });
  const x = styledButton("×");
  Object.assign(x.style, { minWidth: "34px", padding: "2px 8px", fontSize: "20px" });
  titleRow.append(title, x);
  panel.appendChild(titleRow);

  const intro = document.createElement("div");
  intro.textContent = T.intro;
  Object.assign(intro.style, { marginTop: "10px", lineHeight: "1.5", opacity: "0.88", fontSize: "13px" });
  panel.appendChild(intro);

  addHint(panel, T.sharedHint, { strong: true });
  addHint(panel, T.setupHint);
  addHint(panel, T.fallbackHint);
  addHint(panel, T.workflowHint);

  const status = document.createElement("div");
  status.textContent = widget.__ultraTranslatorApiConfigured ? T.configured : T.notConfigured;
  Object.assign(status.style, { marginTop: "14px", fontWeight: "600", fontSize: "13px" });
  panel.appendChild(status);

  const keyLabel = document.createElement("label");
  keyLabel.textContent = T.keyLabel;
  keyLabel.title = T.tooltip;
  Object.assign(keyLabel.style, { display: "block", marginTop: "14px", marginBottom: "6px", fontSize: "13px" });
  panel.appendChild(keyLabel);

  const input = document.createElement("input");
  const canCssMaskKey = "webkitTextSecurity" in input.style;
  input.type = canCssMaskKey ? "text" : "password";
  input.autocomplete = "off";
  input.name = "ultra_translator_google_cloud_api_key_input";
  input.spellcheck = false;
  input.title = T.tooltip;
  input.setAttribute("autocapitalize", "none");
  input.setAttribute("autocorrect", "off");
  input.setAttribute("aria-autocomplete", "none");
  input.setAttribute("data-form-type", "other");
  input.setAttribute("data-1p-ignore", "true");
  input.setAttribute("data-lpignore", "true");
  input.setAttribute("data-bwignore", "true");
  input.placeholder = widget.__ultraTranslatorApiConfigured ? T.keyPlaceholderSaved : T.keyPlaceholderEmpty;
  Object.assign(input.style, {
    width: "100%",
    boxSizing: "border-box",
    minHeight: "36px",
    padding: "7px 9px",
    borderRadius: "7px",
    border: "1px solid rgba(255,255,255,0.18)",
    background: "var(--comfy-input-bg, #171717)",
    color: "inherit",
    fontFamily: "monospace",
  });
  if (canCssMaskKey) input.style.webkitTextSecurity = "disc";
  panel.appendChild(input);

  const privacy = document.createElement("div");
  privacy.textContent = T.savedKeyPrivacyHint;
  Object.assign(privacy.style, { marginTop: "7px", lineHeight: "1.45", opacity: "0.72", fontSize: "12px" });
  panel.appendChild(privacy);

  const showRow = document.createElement("label");
  Object.assign(showRow.style, { display: "inline-flex", alignItems: "center", gap: "7px", marginTop: "8px", fontSize: "12px", cursor: "pointer" });
  const show = document.createElement("input");
  show.type = "checkbox";
  show.addEventListener("change", () => {
    if (canCssMaskKey) input.style.webkitTextSecurity = show.checked ? "none" : "disc";
    else input.type = show.checked ? "text" : "password";
  });
  const showText = document.createElement("span");
  showText.textContent = T.showKey;
  showRow.append(show, showText);
  panel.appendChild(showRow);

  const keyTestHint = document.createElement("div");
  keyTestHint.textContent = T.keyTestHint;
  Object.assign(keyTestHint.style, { marginTop: "7px", lineHeight: "1.45", opacity: "0.72", fontSize: "12px" });
  panel.appendChild(keyTestHint);

  const message = document.createElement("div");
  Object.assign(message.style, { minHeight: "20px", marginTop: "12px", fontSize: "12px", lineHeight: "1.45", overflowWrap: "anywhere" });
  panel.appendChild(message);

  const actions = document.createElement("div");
  Object.assign(actions.style, { display: "flex", flexWrap: "wrap", gap: "8px", justifyContent: "flex-end", marginTop: "10px" });
  const test = styledButton(T.test);
  const save = styledButton(T.save);
  const remove = styledButton(T.remove);
  const close = styledButton(T.close);
  actions.append(test, save, remove, close);
  panel.appendChild(actions);

  const closeDialog = () => {
    try {
      overlay.remove();
    } catch (_) {}
    widget.__ultraTranslatorApiDialog = null;
  };
  x.addEventListener("click", closeDialog);
  close.addEventListener("click", closeDialog);

  function setBusy(busy) {
    for (const button of [test, save, remove, close, x]) button.disabled = Boolean(busy);
  }
  function setMessage(text, isError = false) {
    message.textContent = text || "";
    message.style.color = isError ? "#ff9b9b" : "inherit";
  }

  test.addEventListener("click", async () => {
    setBusy(true);
    setMessage(T.testing);
    try {
      const apiKey = input.value.trim();
      const payload = await requestJson(TEST_PATH, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(apiKey ? { api_key: apiKey } : {}),
      });
      setMessage(T.testOk(payload.translatedText || "OK"));
      if (payload.configured) setConfigured(node, widget, true);
    } catch (error) {
      setMessage(localizedError(error), true);
    } finally {
      setBusy(false);
    }
  });

  save.addEventListener("click", async () => {
    const apiKey = input.value.trim();
    if (!apiKey) {
      setMessage(T.enterKey, true);
      return;
    }
    setBusy(true);
    setMessage(T.saving);
    try {
      const payload = await requestJson(STATUS_PATH, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey }),
      });
      setConfigured(node, widget, Boolean(payload.configured));
      input.value = "";
      input.placeholder = T.keyPlaceholderSaved;
      status.textContent = T.configured;
      setMessage(T.saveOk);
    } catch (error) {
      setMessage(localizedError(error), true);
    } finally {
      setBusy(false);
    }
  });

  remove.addEventListener("click", async () => {
    if (!window.confirm(T.confirmDelete)) return;
    setBusy(true);
    setMessage(T.deleting);
    try {
      const payload = await requestJson(STATUS_PATH, { method: "DELETE" });
      setConfigured(node, widget, Boolean(payload.configured));
      input.value = "";
      input.placeholder = T.keyPlaceholderEmpty;
      status.textContent = T.notConfigured;
      setMessage(T.deleteOk);
    } catch (error) {
      setMessage(localizedError(error), true);
    } finally {
      setBusy(false);
    }
  });

  document.body.appendChild(overlay);
}

function install(node) {
  if (!node || typeof node.addWidget !== "function") return;
  let widget = apiWidget(node);
  if (!widget) {
    widget = node.addWidget("button", T.buttonUnset, null, () => openSettingsDialog(node, widget), {
      serialize: false,
      tooltip: T.tooltip,
    });
    if (!widget) return;
    widget[MARKER] = true;
    widget.serialize = false;
    widget.serializeValue = () => undefined;
    widget.options = { ...(widget.options || {}), serialize: false, tooltip: T.tooltip };
  }
  track(node, widget);
  widget.callback = () => openSettingsDialog(node, widget);
  applyButtonText(node, widget);
  if (!widget.__ultraTranslatorApiStatusKnown) void refreshStatus(node, widget);
}

app.registerExtension({
  name: "UltraTranslator.GoogleTranslationApiSettings",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE_NAME) return;
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function (...args) {
      const result = onNodeCreated?.apply(this, args);
      try {
        install(this);
      } catch (error) {
        console.warn("[Ultra Tools Translator] Google API settings UI failed:", error);
      }
      return result;
    };
  },
});
