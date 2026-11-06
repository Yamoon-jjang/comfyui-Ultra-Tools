import { app } from "../../scripts/app.js";

// Saves this pack's Comfy Registry ID (cnr_id) in each node's properties, so a
// shared workflow names the right pack in the missing-nodes panel even when the
// Registry cannot look the pack up by node class name.
const CNR_ID = "comfyui-ultra-tools";
const KNOWN_NODES = new Set(["UltraTextbox", "UltraAudioFade", "UltraTranslatorTextNode", "ModelSizeViewerDetailed", "ModelSizeViewerWorkflow", "WildcardBrowser", "UltraWorkflowTimer", "UltraTextWatermark", "UltraImageWatermark", "UltraPromptStyler", "UltraPromptComposer", "UltraToolsImageLoad"]);
let packModule = null;

app.registerExtension({
  name: "comfyui-ultra-tools.cnrIdTag",
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (!packModule && KNOWN_NODES.has(nodeData?.name) && nodeData?.python_module) {
      packModule = nodeData.python_module;
    }
  },
  nodeCreated(node) {
    const module = node?.constructor?.nodeData?.python_module;
    const ours = KNOWN_NODES.has(node?.comfyClass) || (packModule !== null && module === packModule);
    if (!ours) return;
    if (!node.properties || typeof node.properties !== "object") node.properties = {};
    if (!node.properties.cnr_id) node.properties.cnr_id = CNR_ID;
  },
});
