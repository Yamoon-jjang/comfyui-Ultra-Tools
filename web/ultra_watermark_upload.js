import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_NAME = "UltraImageWatermark";
const WIDGET_NAME = "watermark";

const LEGACY_UPLOAD_BUTTON_NAMES = new Set([
    "워터마크 파일 업로드/선택",
    "Upload Watermark File",
    "Upload / Select Watermark File",
]);

const UI_TEXT = {
    en: {
        uploadButton: "Upload / Select Watermark File",
        missingWidget: "Ultra Image Watermark: Could not find the watermark widget.",
        uploadFailedPrefix: "Ultra Image Watermark upload failed",
        emptyFilename: "Upload succeeded, but the returned filename was empty.",
    },
    ko: {
        uploadButton: "워터마크 파일 업로드/선택",
        missingWidget: "Ultra Image Watermark: watermark 위젯을 찾을 수 없습니다.",
        uploadFailedPrefix: "Ultra Image Watermark 업로드 실패",
        emptyFilename: "업로드는 성공했지만 반환된 파일명이 비어 있습니다.",
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

function readComfySetting(key) {
    try {
        const settings = app?.ui?.settings;
        if (settings && typeof settings.getSettingValue === "function") {
            const value = settings.getSettingValue(key);
            if (value != null && value !== "") return value;
        }
    } catch (_) {
        // Ignore unknown frontend setting APIs and use the next candidate.
    }
    return null;
}

function readLocalStorage(key) {
    try {
        if (typeof window === "undefined") return null;
        return window.localStorage?.getItem?.(key) ?? null;
    } catch (_) {
        return null;
    }
}

function getComfyLocale() {
    // Prefer ComfyUI's own language/locale settings. Do not fall back to the
    // browser language because many users run English ComfyUI in a Korean OS/browser.
    const settingKeys = [
        "Comfy.Locale",
        "Comfy.Language",
        "ComfyUI.Locale",
        "ComfyUI.Language",
        "locale",
        "language",
    ];

    for (const key of settingKeys) {
        const locale = classifyLocale(readComfySetting(key));
        if (locale) return locale;
    }

    const storageKeys = [
        "Comfy.Locale",
        "Comfy.Language",
        "ComfyUI.Locale",
        "ComfyUI.Language",
        "comfy.locale",
        "comfy.language",
        "locale",
        "language",
    ];

    for (const key of storageKeys) {
        const locale = classifyLocale(readLocalStorage(key));
        if (locale) return locale;
    }

    const htmlLocale = typeof document !== "undefined" ? classifyLocale(document.documentElement?.lang) : null;
    if (htmlLocale) return htmlLocale;

    return "en";
}

function t(key) {
    const locale = getComfyLocale();
    return UI_TEXT[locale]?.[key] || UI_TEXT.en[key] || key;
}

function isUploadButton(widget) {
    return Boolean(widget?.__ultraWatermarkUploadButton || LEGACY_UPLOAD_BUTTON_NAMES.has(widget?.name));
}

function findWidget(node, name) {
    return node?.widgets?.find((widget) => widget?.name === name) || null;
}

function toComfyInputName(uploadResult, fallbackName) {
    const name = uploadResult?.name || fallbackName || "";
    const subfolder = uploadResult?.subfolder || "";
    if (!subfolder) return name;
    return `${subfolder}/${name}`;
}

function addComboValue(widget, value) {
    if (!widget || !value) return;
    if (!widget.options) widget.options = {};
    if (!Array.isArray(widget.options.values)) widget.options.values = [];
    if (!widget.options.values.includes(value)) widget.options.values.push(value);
}

function showMessage(message) {
    if (app.ui?.dialog?.show) {
        app.ui.dialog.show(message);
    } else {
        window.alert(message);
    }
}

async function pickAndUploadWatermark(node) {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/png,image/jpeg,image/webp,image/gif,image/bmp";
    input.style.display = "none";

    input.addEventListener("change", async () => {
        const file = input.files?.[0];
        input.remove();
        if (!file) return;

        const widget = findWidget(node, WIDGET_NAME);
        if (!widget) {
            showMessage(t("missingWidget"));
            return;
        }

        const formData = new FormData();
        formData.append("image", file);
        formData.append("type", "input");
        formData.append("subfolder", "");
        formData.append("overwrite", "false");

        try {
            const response = await api.fetchApi("/upload/image", {
                method: "POST",
                body: formData,
            });
            if (!response.ok) {
                throw new Error(`upload failed: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();
            const comfyName = toComfyInputName(result, file.name);
            if (!comfyName) throw new Error(t("emptyFilename"));

            addComboValue(widget, comfyName);
            widget.value = comfyName;
            if (typeof widget.callback === "function") widget.callback(comfyName);
            node.setDirtyCanvas?.(true, true);
            app.graph?.setDirtyCanvas?.(true, true);
        } catch (error) {
            console.error("[Ultra Image Watermark] watermark upload failed", error);
            showMessage(`${t("uploadFailedPrefix")}: ${error?.message || error}`);
        }
    });

    document.body.appendChild(input);
    input.click();
}

app.registerExtension({
    name: "Ultra.Watermark.UploadButton",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== NODE_NAME) return;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalOnNodeCreated?.apply(this, arguments);

            const desiredLabel = t("uploadButton");
            let uploadWidget = this.widgets?.find(isUploadButton) || null;

            if (!uploadWidget) {
                uploadWidget = this.addWidget(
                    "button",
                    desiredLabel,
                    "",
                    () => pickAndUploadWatermark(this),
                    { serialize: false }
                );
            } else {
                uploadWidget.name = desiredLabel;
                uploadWidget.callback = () => pickAndUploadWatermark(this);
                uploadWidget.serialize = false;
            }
            uploadWidget.__ultraWatermarkUploadButton = true;

            const watermarkIndex = this.widgets?.findIndex((widget) => widget?.name === WIDGET_NAME) ?? -1;
            const uploadIndex = this.widgets?.indexOf(uploadWidget) ?? -1;
            if (watermarkIndex >= 0 && uploadIndex > watermarkIndex + 1) {
                this.widgets.splice(uploadIndex, 1);
                this.widgets.splice(watermarkIndex + 1, 0, uploadWidget);
            }

            return result;
        };
    },
});
