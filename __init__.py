# comfyui-Ultra-Tools
# Unified lightweight utility pack for ComfyUI.

import warnings

WEB_DIRECTORY = "./web"
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}


def _register(mapping, display_mapping):
    NODE_CLASS_MAPPINGS.update(mapping)
    NODE_DISPLAY_NAME_MAPPINGS.update(display_mapping)


# Ultra Tools Textbox
try:
    from .nodes import UltraTextbox
    _register({"UltraTextbox": UltraTextbox}, {"UltraTextbox": "Ultra Tools Textbox"})
except Exception as exc:
    warnings.warn(f"Ultra Tools Textbox could not be loaded: {exc}", RuntimeWarning, stacklevel=1)

# Ultra Tools Audio Fade
try:
    from .audio_fade import UltraAudioFade
    _register({"UltraAudioFade": UltraAudioFade}, {"UltraAudioFade": "Ultra Tools Audio Fade"})
except Exception as exc:
    warnings.warn(f"Ultra Tools Audio Fade could not be loaded: {exc}", RuntimeWarning, stacklevel=1)

# Ultra Tools Translator + optional Google API settings routes
register_translation_api_routes = None
try:
    from .ultra_translator_node import UltraTranslatorTextNode, register_translation_api_routes
    _register({"UltraTranslatorTextNode": UltraTranslatorTextNode}, {"UltraTranslatorTextNode": "Ultra Tools Translator"})
except Exception as exc:
    warnings.warn(f"Ultra Tools Translator could not be loaded: {exc}", RuntimeWarning, stacklevel=1)

try:
    if callable(register_translation_api_routes):
        register_translation_api_routes()
except Exception as exc:
    warnings.warn(f"Ultra Tools Translator settings routes could not be registered: {exc}", RuntimeWarning, stacklevel=1)

# Ultra Tools Model Viewer pair
try:
    from .model_viewer import ModelSizeViewerDetailed, ModelSizeViewerWorkflow
    _register(
        {
            "ModelSizeViewerDetailed": ModelSizeViewerDetailed,
            "ModelSizeViewerWorkflow": ModelSizeViewerWorkflow,
        },
        {
            "ModelSizeViewerDetailed": "Ultra Tools Model Viewer (All)",
            "ModelSizeViewerWorkflow": "Ultra Tools Model Viewer",
        },
    )
except Exception as exc:
    warnings.warn(f"Ultra Tools Model Viewer could not be loaded: {exc}", RuntimeWarning, stacklevel=1)

# Ultra Tools Wildcard Browser
try:
    from .wildcard_browser import UltraWildcardBrowser
    _register({"WildcardBrowser": UltraWildcardBrowser}, {"WildcardBrowser": "Ultra Tools Wildcard Browser"})
except Exception as exc:
    warnings.warn(f"Ultra Tools Wildcard Browser could not be loaded: {exc}", RuntimeWarning, stacklevel=1)

# Ultra Tools Workflow Timer
try:
    from .workflow_timer import UltraWorkflowTimer
    _register({"UltraWorkflowTimer": UltraWorkflowTimer}, {"UltraWorkflowTimer": "Ultra Tools Workflow Timer"})
except Exception as exc:
    warnings.warn(f"Ultra Tools Workflow Timer could not be loaded: {exc}", RuntimeWarning, stacklevel=1)

# Ultra Tools Text Watermark
try:
    from .text_watermark import UltraTextWatermark
    _register({"UltraTextWatermark": UltraTextWatermark}, {"UltraTextWatermark": "Ultra Tools Text Watermark"})
except Exception as exc:
    warnings.warn(f"Ultra Tools Text Watermark could not be loaded: {exc}", RuntimeWarning, stacklevel=1)

# Ultra Tools Image Watermark
try:
    from .image_watermark import UltraImageWatermark
    _register({"UltraImageWatermark": UltraImageWatermark}, {"UltraImageWatermark": "Ultra Tools Image Watermark"})
except Exception as exc:
    warnings.warn(f"Ultra Tools Image Watermark could not be loaded: {exc}", RuntimeWarning, stacklevel=1)

# Ultra Tools Prompt Styler
try:
    from .prompt_styler import UltraPromptStyler
    _register({"UltraPromptStyler": UltraPromptStyler}, {"UltraPromptStyler": "Ultra Tools Prompt Styler"})
except Exception as exc:
    warnings.warn(f"Ultra Tools Prompt Styler could not be loaded: {exc}", RuntimeWarning, stacklevel=1)

# Ultra Tools Prompt Composer
try:
    from .prompt_composer import UltraPromptComposer
    _register({"UltraPromptComposer": UltraPromptComposer}, {"UltraPromptComposer": "Ultra Tools Prompt Composer"})
except Exception as exc:
    warnings.warn(f"Ultra Tools Prompt Composer could not be loaded: {exc}", RuntimeWarning, stacklevel=1)

# Ultra Tools Image + PiD
try:
    from .ultra_image_pid import UltraImagePiD
    _register({"UltraImagePiD": UltraImagePiD}, {"UltraImagePiD": "Ultra Tools Image + PiD"})
except Exception as exc:
    warnings.warn(f"Ultra Tools Image + PiD could not be loaded: {exc}", RuntimeWarning, stacklevel=1)

# Ultra Tools Image Load
register_image_load_routes = None
try:
    from .image_load import UltraToolsImageLoad, register_image_load_routes
    _register({"UltraToolsImageLoad": UltraToolsImageLoad}, {"UltraToolsImageLoad": "Ultra Tools Image Load"})
except Exception as exc:
    warnings.warn(f"Ultra Tools Image Load could not be loaded: {exc}", RuntimeWarning, stacklevel=1)

try:
    if callable(register_image_load_routes):
        register_image_load_routes()
except Exception as exc:
    warnings.warn(f"Ultra Tools Image Load thumbnail routes could not be registered: {exc}", RuntimeWarning, stacklevel=1)

print(f"[comfyui-Ultra-Tools] Loaded {len(NODE_CLASS_MAPPINGS)}/13 nodes")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
