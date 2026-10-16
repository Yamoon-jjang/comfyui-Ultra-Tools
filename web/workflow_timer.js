import { app } from "../../../scripts/app.js";

// Current frontends expose a DOM widget's element as widget.element;
// widget.inputEl is a deprecated alias (warns on access). Prefer element and
// fall back to inputEl only on older frontends that lack it.
function ultraWidgetEl(widget) {
  if (!widget) return undefined;
  return "element" in widget ? widget.element : widget.inputEl;
}


const MAX_HISTORY = 100;
const MAX_PROMPT_WORKFLOW_IDS = 200;
const MIN_WIDTH = 210;
const WATCHDOG_INTERVAL_MS = 1000;
const WATCHDOG_STALE_MS = 30000;
const LIVE_UPDATE_INTERVAL_MS = 100;

const WORKFLOW_ID_KEY = "ultra_workflow_timer_id";

// 저장 파일에 ID를 새로 쓰지 않고, 현재 로드된 루트 워크플로우 단위로 상태를 분리한다.
// 복제 저장된 workflow JSON에 같은 ultra_workflow_timer_id가 남아 있어도 상태를 공유하지 않도록 한다.
const workflowObjectIds = new WeakMap();
let workflowObjectIdSeq = 0;

// ComfyUI workflowManager가 숫자 id(예: 0)를 재사용하는 환경에서도
// 서로 다른 워크플로우 탭/객체가 같은 시간 기록을 공유하지 않도록 객체별 보조 ID를 둔다.
const workflowManagerObjectIds = new WeakMap();
let workflowManagerObjectIdSeq = 0;

// 저장 경로가 없는 워크플로우도 탭을 순환할 때 기존 시간 기록을 유지해야 한다.
// 이때 그래프 내용 fingerprint만 쓰면 같은 내용의 복제본까지 합쳐질 수 있으므로
// ComfyUI 런타임의 워크플로우 슬롯/루트 그래프/로드된 노드 객체 정체성을 보조 ID로 사용한다.
const workflowGraphObjectIds = new WeakMap();
let workflowGraphObjectIdSeq = 0;

// 일부 ComfyUI 빌드는 app.graph 객체 자체를 재사용하고 _nodes만 교체한다.
// 그런 환경에서도 드래그 로드/복제 직후 워크플로우가 서로 섞이지 않도록
// 루트 그래프 안의 실제 노드 객체 정체성으로 로드된 그래프 스냅샷 ID를 만든다.
const workflowNodeObjectIds = new WeakMap();
let workflowNodeObjectIdSeq = 0;

let lastLoadedWorkflowData = null;
let lastLoadedWorkflowId = null;

// 워크플로우별 상태 저장
const workflowStates = new Map();
const promptWorkflowIds = new Map();

let currentWorkflowId = null;
let runningWorkflowId = null;
let watchdogId = null;
let renderTimeout = null;
let liveTimerId = null;
let loadGraphSeq = 0;
let lastDroppedWorkflowSourceId = null;
let lastDroppedWorkflowSourceAt = 0;
let lastDroppedWorkflowSourceUseCount = 0;
const WORKFLOW_DROP_SOURCE_TTL_MS = 10000;
const WORKFLOW_DROP_SOURCE_MAX_USES = 3;
const MAX_WORKFLOW_STATE_BUCKETS = 300;

// 타이머 노드 캐시
let timerNodeCache = [];

function createState() {
    return {
        startTime: null,
        running: false,
        history: [],
        totalCount: 0,
        totalDuration: 0,
        lastActivityAt: 0,
        queueRemaining: null,
        lastExecutingNode: undefined,
        currentPromptId: null,
    };
}

function getHashWorkflowId() {
    const hash = globalThis.location?.hash;
    if (hash && hash.length > 1) return hash.slice(1);
    return null;
}

function normalizeWorkflowIdPart(value, options = {}) {
    const allowNumericOnly = options.allowNumericOnly === true;

    if (value === null || value === undefined) return null;
    if (typeof value !== "string" && typeof value !== "number") return null;

    const text = String(value).trim();
    if (!text) return null;

    // Some ComfyUI/workflowManager builds use small integer ids starting at 0.
    // Those ids can be reused across duplicated or newly opened workflows, so do not
    // use a bare numeric value as a cross-workflow identity unless the caller
    // explicitly asks for it.
    if (!allowNumericOnly && /^-?\d+$/.test(text)) return null;

    return text;
}

function getWorkflowManagerObjectId(workflowObject) {
    if (!workflowObject || typeof workflowObject !== "object") return null;

    if (!workflowManagerObjectIds.has(workflowObject)) {
        workflowManagerObjectIdSeq += 1;
        workflowManagerObjectIds.set(workflowObject, `ui-object:${workflowManagerObjectIdSeq}`);
    }

    return workflowManagerObjectIds.get(workflowObject);
}

function getWorkflowGraphObjectId(graphObject = null) {
    const graph = graphObject || app?.graph || null;
    if (!graph || typeof graph !== "object") return null;

    if (!workflowGraphObjectIds.has(graph)) {
        workflowGraphObjectIdSeq += 1;
        workflowGraphObjectIds.set(graph, `graph-object:${workflowGraphObjectIdSeq}`);
    }

    return workflowGraphObjectIds.get(graph);
}

function getWorkflowNodeObjectId(nodeObject) {
    if (!nodeObject || typeof nodeObject !== "object") return null;

    if (!workflowNodeObjectIds.has(nodeObject)) {
        workflowNodeObjectIdSeq += 1;
        workflowNodeObjectIds.set(nodeObject, `node-object:${workflowNodeObjectIdSeq}`);
    }

    return workflowNodeObjectIds.get(nodeObject);
}

function getGraphNodesForIdentity(graphObject = null) {
    const graph = graphObject || app?.graph || null;
    if (!graph || typeof graph !== "object") return [];

    if (Array.isArray(graph._nodes)) return graph._nodes;
    if (Array.isArray(graph.nodes)) return graph.nodes;
    return [];
}

function getWorkflowGraphSnapshotId(graphObject = null) {
    const graph = graphObject || app?.graph || null;
    if (!graph || typeof graph !== "object") return null;

    const graphId = getWorkflowGraphObjectId(graph);
    if (!graphId) return null;

    const nodes = getGraphNodesForIdentity(graph).filter((node) => node && typeof node === "object");
    if (!nodes.length) return graphId;

    const parts = nodes.slice(0, 256).map((node) => {
        const nodeId = normalizeWorkflowIdPart(node?.id, { allowNumericOnly: true }) || "?";
        const type = normalizeWorkflowIdPart(node?.type || node?.comfyClass || node?.constructor?.name) || "node";
        const objectId = getWorkflowNodeObjectId(node) || "node-object:?";
        return `${nodeId}:${type}:${objectId}`;
    });

    // Include the graph object id and node-object snapshot. If app.graph is reused
    // but its loaded nodes are replaced, this ID changes, preventing unrelated
    // drag-loaded or duplicated workflows from sharing timing data. If a workflow
    // tab keeps the same node objects, A -> B -> A preserves the previous bucket.
    return `graph-snapshot:${graphId}:${hashString(parts.join("|"))}`;
}

function getWorkflowManagerRoots() {
    return [
        app?.workflowManager,
        app?.workflowManagerV2,
        app?.ui?.workflowManager,
        app?.ui,
    ].filter((item) => item && typeof item === "object");
}

function getActiveWorkflowObjectsFromRoot(root) {
    return [
        root?.activeWorkflow,
        root?.currentWorkflow,
        root?.workflow,
        root?.selectedWorkflow,
    ].filter((item) => item && typeof item === "object");
}

function getWorkflowSlotIdFromRoot(root) {
    if (!root || typeof root !== "object") return null;

    const rootId = getWorkflowManagerObjectId(root);
    if (!rootId) return null;

    const activeObjects = getActiveWorkflowObjectsFromRoot(root);
    const listKeys = [
        "workflows",
        "workflowList",
        "openedWorkflows",
        "openWorkflows",
        "workflowTabs",
        "tabs",
        "items",
    ];

    for (const listKey of listKeys) {
        const list = root?.[listKey];
        if (!Array.isArray(list)) continue;

        for (const activeObject of activeObjects) {
            const index = list.indexOf(activeObject);
            if (index >= 0) return `ui-slot:${rootId}:${listKey}:${index}`;
        }
    }

    const indexKeys = [
        "activeWorkflowIndex",
        "currentWorkflowIndex",
        "selectedWorkflowIndex",
        "workflowIndex",
        "activeIndex",
        "currentIndex",
        "selectedIndex",
        "activeTabIndex",
        "currentTabIndex",
        "selectedTabIndex",
        "tabIndex",
    ];

    for (const key of indexKeys) {
        const index = normalizeWorkflowIdPart(root?.[key], { allowNumericOnly: true });
        if (index !== null) return `ui-slot:${rootId}:${key}:${index}`;
    }

    for (const activeObject of activeObjects) {
        for (const key of indexKeys) {
            const index = normalizeWorkflowIdPart(activeObject?.[key], { allowNumericOnly: true });
            if (index !== null) return `ui-slot:${rootId}:active.${key}:${index}`;
        }
    }

    return null;
}

function getActiveWorkflowSlotId() {
    for (const root of getWorkflowManagerRoots()) {
        const slotId = getWorkflowSlotIdFromRoot(root);
        if (slotId) return slotId;
    }
    return null;
}

function getLoadedRuntimeWorkflowId() {
    // For pathless workflows, a visible workflow/tab slot is the best identity: it
    // separates duplicated workflows while preserving A -> B -> A switching.
    const slotId = getActiveWorkflowSlotId();
    if (slotId) return slotId;

    // JSON drag/drop often exposes the source filename only through the active
    // workflow manager entry rather than workflowData itself. Use only file-like
    // labels here, and only after slot identity so duplicated tabs stay separated.
    const fileSourceId = getActiveWorkflowFileSourceId();
    if (fileSourceId) return fileSourceId;

    // If the manager exposes no slot/source, use the loaded graph snapshot rather
    // than a reused workflowManager object. This covers common drag/drop and
    // duplicate cases where app.graph is reused but its node objects are replaced.
    const graphSnapshotId = getWorkflowGraphSnapshotId();
    if (graphSnapshotId) return graphSnapshotId;

    return null;
}

function getRuntimeWorkflowObjectId(options = {}) {
    // When a workflow has no saved path/filename, callers that run after
    // loadGraphData should prefer the loaded workflow slot/graph snapshot over
    // workflowManager object identity. Manager objects and numeric ids are reused
    // by some ComfyUI builds, while slot/snapshot identity better preserves the
    // user's required separation between original/duplicate workflows.
    if (options.preferGraph === true || options.preferLoaded === true) {
        const loadedId = getLoadedRuntimeWorkflowId();
        if (loadedId) return loadedId;
    }

    const slotId = getActiveWorkflowSlotId();
    if (slotId) return slotId;

    const managerId = getActiveWorkflowManagerId();
    if (managerId) return managerId;

    return getWorkflowGraphSnapshotId() || getWorkflowGraphObjectId();
}

function getWorkflowIdentityFromManagerObject(workflowObject) {
    if (!workflowObject || typeof workflowObject !== "object") return null;

    const stableFields = [
        "path",
        "filePath",
        "filepath",
        "filename",
        "fileName",
    ];

    for (const key of stableFields) {
        const normalized = normalizeWorkflowIdPart(workflowObject?.[key]);
        if (normalized) return `ui:${key}:${normalized}`;
    }

    // Accept non-numeric ids such as UUID-like strings, but avoid plain 0/1/2 ids.
    const id = normalizeWorkflowIdPart(workflowObject?.id);
    if (id) return `ui:id:${id}`;

    // Last resort for manager objects: object identity is safer than numeric id=0,
    // because duplicated workflows/tabs commonly have separate manager objects.
    return getWorkflowManagerObjectId(workflowObject);
}

function getActiveWorkflowManagerId() {
    const manager = app?.workflowManager || app?.workflowManagerV2 || null;
    const ui = app?.ui || null;

    const workflowObjects = [
        manager?.activeWorkflow,
        manager?.currentWorkflow,
        manager?.workflow,
        ui?.currentWorkflow,
    ].filter((item) => item && typeof item === "object");

    for (const workflowObject of workflowObjects) {
        const id = getWorkflowIdentityFromManagerObject(workflowObject);
        if (id) return id;
    }

    // Some older builds expose only a direct string field instead of a workflow object.
    // Keep those when they are descriptive strings, but still reject bare numbers.
    const directCandidates = [
        manager?.activeWorkflowId,
        manager?.currentWorkflowId,
        manager?.workflowId,
        ui?.currentWorkflowId,
    ];

    for (const candidate of directCandidates) {
        const normalized = normalizeWorkflowIdPart(candidate);
        if (normalized) return `ui:${normalized}`;
    }

    return null;
}

function stableStringify(value) {
    if (value === null || typeof value !== "object") {
        return JSON.stringify(value);
    }
    if (Array.isArray(value)) {
        return `[${value.map((item) => stableStringify(item)).join(",")}]`;
    }

    const keys = Object.keys(value).sort();
    const parts = [];
    for (const key of keys) {
        const item = value[key];
        if (item === undefined || typeof item === "function") continue;
        parts.push(`${JSON.stringify(key)}:${stableStringify(item)}`);
    }
    return `{${parts.join(",")}}`;
}

function hashString(text) {
    let hash = 2166136261;
    for (let i = 0; i < text.length; i++) {
        hash ^= text.charCodeAt(i);
        hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(36);
}

function cleanTimerProperties(properties) {
    if (!properties || typeof properties !== "object") return properties;
    const out = {};
    for (const [key, value] of Object.entries(properties)) {
        if (key === WORKFLOW_ID_KEY) continue;
        out[key] = value;
    }
    return out;
}

function buildWorkflowFingerprintSource(workflowData) {
    if (!workflowData || typeof workflowData !== "object") return null;

    const nodes = Array.isArray(workflowData.nodes)
        ? workflowData.nodes.map((node) => ({
            id: node?.id,
            type: node?.type,
            title: node?.title,
            mode: node?.mode,
            flags: node?.flags,
            pos: node?.pos,
            size: node?.size,
            inputs: node?.inputs,
            outputs: node?.outputs,
            properties: cleanTimerProperties(node?.properties),
            // 타이머 표시용 위젯 값은 워크플로우 정체성에서 제외한다.
            widgets_values: node?.type === "UltraWorkflowTimer" ? [] : node?.widgets_values,
        }))
        : [];

    const extra = workflowData.extra && typeof workflowData.extra === "object"
        ? Object.fromEntries(
            Object.entries(workflowData.extra).filter(([key]) => key !== WORKFLOW_ID_KEY)
        )
        : workflowData.extra;

    return {
        version: workflowData.version,
        nodes,
        links: workflowData.links,
        groups: workflowData.groups,
        config: workflowData.config,
        extra,
    };
}

function getWorkflowFingerprint(workflowData) {
    const source = buildWorkflowFingerprintSource(workflowData);
    if (!source) return null;

    try {
        return hashString(stableStringify(source));
    } catch (e) {
        console.warn("[Ultra Workflow Timer] workflow fingerprint failed:", e);
        return null;
    }
}

function getObjectWorkflowId(workflowData) {
    if (!workflowData || typeof workflowData !== "object") return null;
    if (!workflowObjectIds.has(workflowData)) {
        workflowObjectIdSeq += 1;
        workflowObjectIds.set(workflowData, `object:${workflowObjectIdSeq}`);
    }
    return workflowObjectIds.get(workflowData);
}

function getNestedWorkflowValue(source, path) {
    let current = source;
    for (const key of path) {
        if (!current || typeof current !== "object") return null;
        current = current[key];
    }
    return normalizeWorkflowIdPart(current);
}

function getWorkflowDataSourceId(workflowData) {
    if (!workflowData || typeof workflowData !== "object") return null;

    // Use only file/path-like data as a stable workflowData source id. Generic
    // fields such as name/title/id/uuid/key can be copied into a saved-as duplicate,
    // so object identity is safer than those for preventing cross-workflow sharing.
    const paths = [
        ["path"],
        ["filePath"],
        ["filepath"],
        ["filename"],
        ["fileName"],
        ["extra", "path"],
        ["extra", "filePath"],
        ["extra", "filepath"],
        ["extra", "filename"],
        ["extra", "fileName"],
        ["extra", "ds", "filename"],
        ["extra", "ds", "path"],
        ["extra", "metadata", "filename"],
        ["extra", "metadata", "path"],
    ];

    for (const path of paths) {
        const value = getNestedWorkflowValue(workflowData, path);
        if (value && value !== WORKFLOW_ID_KEY) return `data:${value}`;
    }

    return null;
}

function normalizeWorkflowFileLabel(value) {
    const text = normalizeWorkflowIdPart(value);
    if (!text) return null;

    // Labels are only trusted when they look like an actual workflow file/source,
    // not a generic copied graph title. This helps JSON drag/drop workflows whose
    // filename is exposed as a UI/File label, while avoiding broad name/title reuse.
    if (/\.json(?:[?#].*)?$/i.test(text)) return text;
    return null;
}

function getNowMs() {
    return typeof performance !== "undefined" && typeof performance.now === "function"
        ? performance.now()
        : Date.now();
}

function rememberDroppedWorkflowSourceId(sourceId) {
    if (!sourceId) return;
    lastDroppedWorkflowSourceId = sourceId;
    lastDroppedWorkflowSourceAt = getNowMs();
    lastDroppedWorkflowSourceUseCount = 0;
}

function clearRecentDroppedWorkflowSourceId() {
    lastDroppedWorkflowSourceId = null;
    lastDroppedWorkflowSourceAt = 0;
    lastDroppedWorkflowSourceUseCount = 0;
}

function getRecentDroppedWorkflowSourceId() {
    if (!lastDroppedWorkflowSourceId) return null;

    const age = getNowMs() - lastDroppedWorkflowSourceAt;
    if (age < 0 || age > WORKFLOW_DROP_SOURCE_TTL_MS) {
        clearRecentDroppedWorkflowSourceId();
        return null;
    }

    lastDroppedWorkflowSourceUseCount += 1;
    const sourceId = lastDroppedWorkflowSourceId;

    // Some ComfyUI builds call loadGraphData more than once for one drop
    // (for example clear pass, then real data pass). Keep the drop source for
    // that short burst, but cap reuse so a stale drop cannot contaminate later
    // unrelated source-less loads. No polling/idle timer is used.
    if (lastDroppedWorkflowSourceUseCount >= WORKFLOW_DROP_SOURCE_MAX_USES) {
        clearRecentDroppedWorkflowSourceId();
    }

    return sourceId;
}

function getDataTransferWorkflowSourceId(dataTransfer) {
    if (!dataTransfer) return null;

    const files = dataTransfer.files ? Array.from(dataTransfer.files) : [];
    for (const file of files) {
        const sourceId = getObjectFileSourceId(file, "drop", { allowFileLabels: true });
        if (sourceId) return sourceId;
    }

    const items = dataTransfer.items ? Array.from(dataTransfer.items) : [];
    for (const item of items) {
        if (!item || item.kind !== "file" || typeof item.getAsFile !== "function") continue;
        const file = item.getAsFile();
        const sourceId = getObjectFileSourceId(file, "drop", { allowFileLabels: true });
        if (sourceId) return sourceId;
    }

    return null;
}

function captureWorkflowDropSource(evt) {
    const sourceId = getDataTransferWorkflowSourceId(evt?.dataTransfer);
    if (sourceId) rememberDroppedWorkflowSourceId(sourceId);
}

function installWorkflowDropSourceCapture() {
    if (app.__ultraWorkflowTimerDropSourcePatched) return;
    app.__ultraWorkflowTimerDropSourcePatched = true;

    const target =
        (globalThis?.window && typeof globalThis.window.addEventListener === "function" && globalThis.window) ||
        (globalThis?.document && typeof globalThis.document.addEventListener === "function" && globalThis.document) ||
        (globalThis && typeof globalThis.addEventListener === "function" && globalThis) ||
        null;

    if (target) {
        target.addEventListener("drop", captureWorkflowDropSource, true);
    }
}

function getObjectFileSourceId(source, prefix = "source", options = {}) {
    if (!source || typeof source !== "object") return null;

    const pathLikePaths = [
        ["path"],
        ["filePath"],
        ["filepath"],
        ["filename"],
        ["fileName"],
        ["webkitRelativePath"],
        ["metadata", "path"],
        ["metadata", "filename"],
        ["extra", "path"],
        ["extra", "filePath"],
        ["extra", "filepath"],
        ["extra", "filename"],
        ["extra", "fileName"],
        ["extra", "metadata", "path"],
        ["extra", "metadata", "filename"],
    ];

    for (const path of pathLikePaths) {
        const value = getNestedWorkflowValue(source, path);
        const normalized = normalizeWorkflowIdPart(value);
        if (normalized && normalized !== WORKFLOW_ID_KEY) return `${prefix}:${normalized}`;
    }

    const isBrowserFile =
        (typeof File !== "undefined" && source instanceof File) ||
        source?.constructor?.name === "File" ||
        (typeof source?.name === "string" && (typeof source?.lastModified === "number" || typeof source?.size === "number"));

    if (isBrowserFile) {
        const fileName = normalizeWorkflowFileLabel(source?.webkitRelativePath || source?.name);
        if (fileName) return `${prefix}:${fileName}`;
    }

    if (options.allowFileLabels === true) {
        const labelPaths = [
            ["name"],
            ["title"],
            ["label"],
            ["displayName"],
            ["workflowName"],
            ["workflowTitle"],
        ];

        for (const path of labelPaths) {
            const value = getNestedWorkflowValue(source, path);
            const fileLabel = normalizeWorkflowFileLabel(value);
            if (fileLabel) return `${prefix}:${fileLabel}`;
        }
    }

    return null;
}

function getLoadGraphSourceId(args = []) {
    if (!Array.isArray(args)) return null;

    // The first argument is usually workflowData, so keep its strict path-only rule.
    const workflowData = args?.[0];
    const dataSourceId = getWorkflowDataSourceId(workflowData);
    if (dataSourceId) {
        clearRecentDroppedWorkflowSourceId();
        return dataSourceId;
    }

    for (let i = 1; i < args.length; i++) {
        const sourceId = getObjectFileSourceId(args[i], "load", { allowFileLabels: true });
        if (sourceId) {
            clearRecentDroppedWorkflowSourceId();
            return sourceId;
        }
    }

    // Some ComfyUI builds call loadGraphData(parsedJSON) without passing the
    // browser File object. Capture-phase drop tracking preserves A.json -> B.json
    // -> A.json timing data without falling back to content fingerprint sharing.
    const droppedSourceId = getRecentDroppedWorkflowSourceId();
    if (droppedSourceId) return droppedSourceId;

    return null;
}

function getActiveWorkflowFileSourceId() {
    for (const root of getWorkflowManagerRoots()) {
        for (const activeObject of getActiveWorkflowObjectsFromRoot(root)) {
            const sourceId = getObjectFileSourceId(activeObject, "ui-file", { allowFileLabels: true });
            if (sourceId) return sourceId;
        }

    }

    return null;
}

function resolveWorkflowDataId(workflowData = null, options = {}) {
    if (!workflowData || typeof workflowData !== "object") return null;

    const dataSourceId = getWorkflowDataSourceId(workflowData);
    if (dataSourceId) return dataSourceId;

    // Object identity intentionally comes before fingerprint. A duplicated workflow
    // saved under a new name can have the same graph content as the original; using
    // fingerprint first would make the duplicate share timing data with the original.
    if (options.allowObjectFallback) {
        const objectId = getObjectWorkflowId(workflowData);
        if (objectId) return objectId;
    }

    const fingerprint = getWorkflowFingerprint(workflowData);
    if (fingerprint) return `fingerprint:${fingerprint}`;

    return null;
}

function resolveWorkflowId(workflowData = null, options = {}) {
    if (options.preferWorkflowData) {
        const workflowDataId = resolveWorkflowDataId(workflowData, options);
        if (workflowDataId) return workflowDataId;
    }

    const runtimeId = getRuntimeWorkflowObjectId();
    if (runtimeId) return runtimeId;

    if (!options.preferWorkflowData) {
        const workflowDataId = resolveWorkflowDataId(workflowData, options);
        if (workflowDataId) return workflowDataId;
    }

    const hashId = getHashWorkflowId();
    if (hashId) return `hash:${hashId}`;

    return "__default_workflow__";
}

function ensureWorkflowIdOnData(workflowData, options = {}) {
    // Never write an ID into workflow JSON. A saved-as duplicate can carry copied
    // metadata, so identity must be derived from the currently loaded workflow/tab.
    if (workflowData && typeof workflowData === "object") {
        const dataSourceId = getWorkflowDataSourceId(workflowData);
        if (dataSourceId) return dataSourceId;

        // For JSON drag/drop, ComfyUI may keep the filename outside workflowData.
        // Use that source while loadGraphData is still in-flight; after load, a
        // real slot/graph snapshot can still supersede it.
        if (options.sourceId) return options.sourceId;

        return resolveWorkflowId(workflowData, {
            allowObjectFallback: true,
            preferWorkflowData: true,
        });
    }

    return options.sourceId || resolveWorkflowId(null);
}

function ensureWorkflowIdAfterLoad(workflowData, options = {}) {
    if (workflowData && typeof workflowData === "object") {
        const dataSourceId = getWorkflowDataSourceId(workflowData);
        if (dataSourceId) return dataSourceId;

        // After ComfyUI has actually loaded the graph, a visible workflow/tab slot
        // is the safest pathless identity because it separates duplicated tabs and
        // preserves A -> B -> A switching.
        const slotId = getActiveWorkflowSlotId();
        if (slotId) return slotId;

        // JSON drag/drop may expose the source filename only through a File/load
        // argument or active workflow label. Prefer that before graph snapshots so
        // dragging A.json -> B.json -> A.json does not reset A merely because node
        // objects were recreated. Labels are accepted only when they look file-like.
        const activeFileSourceId = getActiveWorkflowFileSourceId();
        if (activeFileSourceId) return activeFileSourceId;
        if (options.sourceId) return options.sourceId;

        // If no slot/source is visible, use the loaded graph snapshot before the
        // transient workflowData object. Identical duplicated workflows remain
        // separated when they occupy different loaded node-object snapshots.
        const runtimeId = getRuntimeWorkflowObjectId({ preferLoaded: true });
        if (runtimeId) return runtimeId;

        return resolveWorkflowDataId(workflowData, { allowObjectFallback: true });
    }

    return getRuntimeWorkflowObjectId() || options.sourceId || resolveWorkflowId(null);
}

function isStateEmpty(state) {
    return !state || (
        !state.running &&
        state.totalCount === 0 &&
        state.totalDuration === 0 &&
        (!Array.isArray(state.history) || state.history.length === 0)
    );
}

function pruneEmptyWorkflowStates() {
    if (workflowStates.size <= MAX_WORKFLOW_STATE_BUCKETS) return;

    const protectedIds = new Set([
        currentWorkflowId,
        lastLoadedWorkflowId,
        runningWorkflowId,
    ].filter(Boolean));

    for (const workflowId of promptWorkflowIds.values()) {
        if (workflowId) protectedIds.add(workflowId);
    }

    for (const [workflowId, state] of workflowStates.entries()) {
        if (workflowStates.size <= MAX_WORKFLOW_STATE_BUCKETS) break;
        if (protectedIds.has(workflowId)) continue;
        if (!isStateEmpty(state)) continue;
        workflowStates.delete(workflowId);
    }
}

function migrateWorkflowState(fromId, toId) {
    if (!fromId || !toId || fromId === toId) return;
    if (!workflowStates.has(fromId)) return;

    const fromState = workflowStates.get(fromId);
    const toState = workflowStates.get(toId);

    if (isStateEmpty(toState)) {
        workflowStates.set(toId, fromState);
    }

    for (const [promptId, workflowId] of promptWorkflowIds.entries()) {
        if (workflowId === fromId) {
            promptWorkflowIds.set(promptId, toId);
        }
    }

    if (runningWorkflowId === fromId) {
        runningWorkflowId = toId;
    }

    pruneEmptyWorkflowStates();
}

function rememberLoadedWorkflow(workflowData, workflowId) {
    lastLoadedWorkflowData = workflowData && typeof workflowData === "object" ? workflowData : null;
    lastLoadedWorkflowId = workflowId || null;
}

function getEffectiveCurrentWorkflowId() {
    if (currentWorkflowId && currentWorkflowId !== "__default_workflow__") {
        return currentWorkflowId;
    }

    if (lastLoadedWorkflowId) {
        currentWorkflowId = lastLoadedWorkflowId;
        ensureCurrentWorkflowId();
        return currentWorkflowId;
    }

    const resolved = resolveWorkflowId(lastLoadedWorkflowData, {
        allowObjectFallback: true,
        preferWorkflowData: true,
    });

    if (resolved && resolved !== "__default_workflow__") {
        currentWorkflowId = resolved;
    }

    return ensureCurrentWorkflowId();
}

function ensureCurrentWorkflowId() {
    if (!currentWorkflowId) {
        currentWorkflowId = resolveWorkflowId(lastLoadedWorkflowData, {
            allowObjectFallback: true,
            preferWorkflowData: true,
        });
    }
    if (!workflowStates.has(currentWorkflowId)) {
        workflowStates.set(currentWorkflowId, createState());
        pruneEmptyWorkflowStates();
    }
    return currentWorkflowId;
}

function getStateForWorkflow(workflowId) {
    const id = workflowId || "__default_workflow__";
    if (!workflowStates.has(id)) {
        workflowStates.set(id, createState());
        pruneEmptyWorkflowStates();
    }
    return workflowStates.get(id);
}

function getCurrentState() {
    return getStateForWorkflow(getEffectiveCurrentWorkflowId());
}

function getWorkflowIdForNode(node) {
    return node?.__ultraWorkflowTimerWorkflowId || getEffectiveCurrentWorkflowId();
}

function getRenderStateForNode(node) {
    return getStateForWorkflow(getWorkflowIdForNode(node));
}

function assignWorkflowIdToTimerNodes(workflowId = null) {
    const id = workflowId || getEffectiveCurrentWorkflowId();
    for (const node of timerNodeCache) {
        if (node?.type === "UltraWorkflowTimer") {
            node.__ultraWorkflowTimerWorkflowId = id;
        }
    }
}

function extractPromptId(detail = {}) {
    if (!detail || typeof detail !== "object") return null;

    const promptId =
        detail.prompt_id ??
        detail.promptId ??
        detail?.data?.prompt_id ??
        detail?.data?.promptId ??
        detail?.status?.prompt_id ??
        detail?.status?.promptId ??
        null;

    if (promptId === null || promptId === undefined || promptId === "") return null;
    return String(promptId);
}

function rememberPromptWorkflow(promptId, workflowId) {
    if (!promptId || !workflowId) return;

    if (promptWorkflowIds.has(promptId)) {
        promptWorkflowIds.delete(promptId);
    }
    promptWorkflowIds.set(promptId, workflowId);

    while (promptWorkflowIds.size > MAX_PROMPT_WORKFLOW_IDS) {
        const oldestKey = promptWorkflowIds.keys().next().value;
        if (oldestKey === undefined) break;
        promptWorkflowIds.delete(oldestKey);
    }
}

function forgetPromptWorkflow(promptId) {
    if (!promptId) return;
    promptWorkflowIds.delete(promptId);
}

function getWorkflowIdForPrompt(promptId) {
    if (!promptId) return null;
    return promptWorkflowIds.get(promptId) || null;
}


function getRunningState() {
    if (!runningWorkflowId) return null;
    return getStateForWorkflow(runningWorkflowId);
}

function getRootGraph() {
    return app.graph || null;
}

function getNodeSubgraph(node) {
    return (
        node?.subgraph ||
        node?.subGraph ||
        node?.properties?.subgraph ||
        node?.graph?.subgraph ||
        null
    );
}

function collectGraphsRecursive(graph, out, visited) {
    if (!graph || visited.has(graph)) return;
    visited.add(graph);
    out.push(graph);

    const nodes = graph._nodes || [];
    for (const node of nodes) {
        const subgraph = getNodeSubgraph(node);
        if (subgraph) {
            collectGraphsRecursive(subgraph, out, visited);
        }
    }
}

function getAllGraphs() {
    const root = getRootGraph();
    if (!root) return [];

    const out = [];
    const visited = new Set();
    collectGraphsRecursive(root, out, visited);
    return out;
}

function rebuildTimerNodeCache() {
    const result = [];

    for (const graph of getAllGraphs()) {
        const nodes = graph._nodes || [];
        for (const node of nodes) {
            if (node.type === "UltraWorkflowTimer") {
                node.__ultraWorkflowTimerWorkflowId = getEffectiveCurrentWorkflowId();
                result.push(node);
            }
        }
    }

    timerNodeCache = result;
}

function getTimerNodes() {
    return timerNodeCache;
}

function getWidgetByName(node, name) {
    return node.widgets?.find((w) => w.name === name);
}

let measureCanvas = null;
let measureCtx = null;

function getMeasureContext() {
    if (!measureCanvas) {
        measureCanvas = document.createElement("canvas");
        measureCtx = measureCanvas.getContext("2d");
    }
    return measureCtx;
}

function getWidgetInputElement(widget) {
    return ultraWidgetEl(widget) || null;
}

function getHistoryElement(node) {
    return getWidgetInputElement(getWidgetByName(node, "History"));
}

function getHistoryFont(node) {
    const el = getHistoryElement(node);

    if (el && globalThis.getComputedStyle) {
        const cs = getComputedStyle(el);
        const fontStyle = cs.fontStyle || "normal";
        const fontVariant = cs.fontVariant || "normal";
        const fontWeight = cs.fontWeight || "400";
        const fontSize = cs.fontSize || "13px";
        const lineHeight = cs.lineHeight || "normal";
        const fontFamily = cs.fontFamily || "Consolas, 'Courier New', monospace";

        return `${fontStyle} ${fontVariant} ${fontWeight} ${fontSize}/${lineHeight} ${fontFamily}`;
    }

    return "normal normal 400 13px/normal Consolas, 'Courier New', monospace";
}

function measureTextWidth(text, font) {
    const ctx = getMeasureContext();
    if (!ctx) return text.length * 8;
    ctx.font = font;
    return ctx.measureText(text).width;
}

function getHistoryUsableWidth(node, fallbackNodeWidth) {
    const el = getHistoryElement(node);

    if (!el || !globalThis.getComputedStyle) {
        return Math.max(80, fallbackNodeWidth - 20);
    }

    const cs = getComputedStyle(el);
    const paddingLeft = parseFloat(cs.paddingLeft || "0") || 0;
    const paddingRight = parseFloat(cs.paddingRight || "0") || 0;
    const clientWidth = el.clientWidth || 0;

    if (clientWidth === 0) {
        return Math.max(80, fallbackNodeWidth - paddingLeft - paddingRight - 20);
    }

    const innerWidth = Math.max(
        80,
        clientWidth - paddingLeft - paddingRight
    );

    return Math.max(80, innerWidth);
}

function buildHistoryLine(left, right, font, usableWidth) {
    const minGap = "  ";
    const minGapWidth = measureTextWidth(minGap, font);
    const spaceWidth = Math.max(1, measureTextWidth(" ", font));

    const leftWidth = measureTextWidth(left, font);
    const rightWidth = measureTextWidth(right, font);
    const availableGapWidth = Math.max(minGapWidth, usableWidth - leftWidth - rightWidth);
    const spacesNeeded = Math.max(2, Math.floor(availableGapWidth / spaceWidth));

    return left + " ".repeat(spacesNeeded) + right;
}

function formatHistory(history, nodeWidth, node, totalCount = history.length) {
    if (!history.length) return " ";

    const font = getHistoryFont(node);
    const usableWidth = getHistoryUsableWidth(node, nodeWidth);

    return history
        .map((item, i) => {
            const left = `Run ${Math.max(1, totalCount - i)}`;
            const right = item;
            return buildHistoryLine(left, right, font, usableWidth);
        })
        .join("\n");
}

function fitNode(node) {
    try {
        const currentWidth = node.size?.[0] || 0;
        const currentHeight = node.size?.[1] || 0;
        const width = Math.max(MIN_WIDTH, currentWidth || MIN_WIDTH);

        let height = currentHeight;
        if (!height || height < 40) {
            const computed = typeof node.computeSize === "function" ? node.computeSize() : null;
            height = Math.max(120, computed?.[1] || 160);
        }

        if (currentWidth !== width || currentHeight !== height) {
            node.size = [width, height];
            if (typeof node.setSize === "function") {
                node.setSize(node.size);
            }
        }
    } catch (e) {
        console.warn("[Ultra Workflow Timer] fitNode failed:", e);
    }
}

function makeRuntimeOnlyWidget(widget) {
    if (!widget) return;

    // Stats는 Python INPUT_TYPES에 없는 프론트 전용 위젯이다.
    // 이것이 workflow JSON에 저장되면 Time/History 위젯 순서가 밀려 노드 외형이 변할 수 있다.
    widget.serialize = false;
    widget.options = widget.options || {};
    widget.options.serialize = false;
}

function applyBaseReadOnly(widget) {
    if (!widget) return;

    const el = ultraWidgetEl(widget);
    if (!el) return;

    if (el.__ultraWorkflowTimerBaseReadOnlyApplied) return;
    el.__ultraWorkflowTimerBaseReadOnlyApplied = true;

    el.readOnly = true;
    el.style.cursor = "default";
}

function applyHistoryStyle(widget) {
    if (!widget) return;

    const el = ultraWidgetEl(widget);
    if (!el || el.__ultraWorkflowTimerHistoryStyleApplied) return;

    el.__ultraWorkflowTimerHistoryStyleApplied = true;
    el.style.setProperty("font-family", "Consolas, 'Courier New', monospace", "important");
    el.style.setProperty("font-size", "13px", "important");
    el.style.setProperty("font-weight", "400", "important");
    el.style.whiteSpace = "pre";
    el.style.overflowX = "hidden";
    el.style.overflowY = "auto";

}

function applyStatsStyle(widget) {
    if (!widget) return;

    const el = ultraWidgetEl(widget);
    if (!el || el.__ultraWorkflowTimerStatsStyleApplied) return;

    el.__ultraWorkflowTimerStatsStyleApplied = true;
    el.style.setProperty("font-family", "Consolas, monospace", "important");
    el.style.setProperty("font-size", "12px", "important");
    el.style.setProperty("color", "#aaaaaa", "important");
    el.style.setProperty("margin-top", "-4px", "important");
}

function applyTimeBaseStyle(widget) {
    if (!widget) return;

    const el = ultraWidgetEl(widget);
    if (!el) return;

    el.style.setProperty("font-family", "Consolas, monospace", "important");
}

function getElapsedSeconds(state) {
    if (!state?.running || state.startTime == null) return 0;
    return (performance.now() - state.startTime) / 1000;
}

function getTimeDisplayText(state) {
    if (!state?.running || state.startTime == null) return "Idle";
    return `🔥 ${getElapsedSeconds(state).toFixed(1)} sec`;
}

function cancelRender() {
    if (renderTimeout !== null) {
        try {
            cancelAnimationFrame(renderTimeout);
        } catch (e) {
            // 일부 테스트/구버전 환경에서는 cancelAnimationFrame이 없을 수 있다.
        }
        renderTimeout = null;
    }
}

function render(options = {}) {
    const { timeOnly = false } = options;

    if (renderTimeout) return;

    renderTimeout = requestAnimationFrame(() => {
        try {
            const nodes = getTimerNodes();

            for (const node of nodes) {
                const state = getRenderStateForNode(node);
                const timeWidget = getWidgetByName(node, "Time");
                const statsWidget = getWidgetByName(node, "Stats");
                const historyWidget = getWidgetByName(node, "History");

                if (timeWidget) {
                    applyBaseReadOnly(timeWidget);
                    applyTimeBaseStyle(timeWidget);

                    const newValue = getTimeDisplayText(state);
                    if (timeWidget.value !== newValue) {
                        timeWidget.value = newValue;
                        node.setDirtyCanvas?.(true, false);
                    }
                }

                if (timeOnly) continue;

                if (statsWidget) {
                    applyBaseReadOnly(statsWidget);
                    applyStatsStyle(statsWidget);

                    const avg = state.totalCount > 0
                        ? (state.totalDuration / state.totalCount).toFixed(2)
                        : "0.00";
                    const newValue = `Total: ${state.totalCount} runs  |  Avg: ${avg}s`;

                    if (statsWidget.value !== newValue) {
                        statsWidget.value = newValue;
                        node.setDirtyCanvas?.(true, false);
                    }
                }

                if (historyWidget) {
                    if (!historyWidget._ultraWorkflowTimerOwnerNode) {
                        historyWidget._ultraWorkflowTimerOwnerNode = node;
                    }

                    applyBaseReadOnly(historyWidget);
                    applyHistoryStyle(historyWidget);

                    const nodeWidth = node.size?.[0] || MIN_WIDTH;
                    const formatted = formatHistory(state.history, nodeWidth, node, state.totalCount);

                    if (historyWidget.value !== formatted) {
                        historyWidget.value = formatted;
                        node.setDirtyCanvas?.(true, false);
                    }
                }
            }
        } finally {
            renderTimeout = null;
        }
    });
}

function renderLiveTimeOnly() {
    const nodes = getTimerNodes();

    for (const node of nodes) {
        const state = getRenderStateForNode(node);
        const newValue = getTimeDisplayText(state);
        const timeWidget = getWidgetByName(node, "Time");
        if (!timeWidget) continue;

        applyBaseReadOnly(timeWidget);
        applyTimeBaseStyle(timeWidget);

        if (timeWidget.value !== newValue) {
            timeWidget.value = newValue;
            node.setDirtyCanvas?.(true, false);
        }
    }
}

function markActivity(detail = {}) {
    const promptId = extractPromptId(detail);
    const workflowId = getWorkflowIdForPrompt(promptId) || runningWorkflowId;
    const state = workflowId ? getStateForWorkflow(workflowId) : getRunningState();
    if (!state || !state.running) return;

    state.lastActivityAt = performance.now();

    const isObjectDetail = detail && typeof detail === "object";

    const qr = isObjectDetail
        ? (
            detail?.status?.exec_info?.queue_remaining ??
            detail?.exec_info?.queue_remaining ??
            detail?.queue_remaining
        )
        : undefined;

    if (typeof qr === "number") state.queueRemaining = qr;

    if (isObjectDetail && "node" in detail) {
        state.lastExecutingNode = detail.node;
    }
}

function stopLiveTimer() {
    if (liveTimerId) {
        clearInterval(liveTimerId);
        liveTimerId = null;
    }
}

function startLiveTimer() {
    stopLiveTimer();

    liveTimerId = setInterval(() => {
        const state = getRunningState();
        if (!state || !state.running) {
            stopLiveTimer();
            return;
        }
        renderLiveTimeOnly();
    }, LIVE_UPDATE_INTERVAL_MS);
}

function stopWatchdog() {
    if (watchdogId) {
        clearInterval(watchdogId);
        watchdogId = null;
    }
}

function startWatchdog() {
    stopWatchdog();

    watchdogId = setInterval(() => {
        const state = getRunningState();

        if (!state || !state.running) {
            stopWatchdog();
            return;
        }

        const now = performance.now();
        const staleFor = now - state.lastActivityAt;

        const looksFinished =
            staleFor >= WATCHDOG_STALE_MS &&
            state.queueRemaining === 0 &&
            (state.lastExecutingNode === null || state.lastExecutingNode === undefined);

        if (looksFinished) {
            finishExecution(false, "Recovered");
        }
    }, WATCHDOG_INTERVAL_MS);
}

function startExecution(detail = {}) {
    const promptId = extractPromptId(detail);
    const workflowId = getWorkflowIdForPrompt(promptId) || getEffectiveCurrentWorkflowId();
    const state = getStateForWorkflow(workflowId);

    runningWorkflowId = workflowId;

    state.startTime = performance.now();
    state.running = true;
    state.lastActivityAt = performance.now();
    state.queueRemaining = null;
    state.lastExecutingNode = undefined;
    state.currentPromptId = promptId;

    render();
    startLiveTimer();
    startWatchdog();
}

function finishExecution(isError = false, label = null, detail = {}) {
    const promptId = extractPromptId(detail);
    const workflowId = getWorkflowIdForPrompt(promptId) || runningWorkflowId || getEffectiveCurrentWorkflowId();
    const state = getStateForWorkflow(workflowId);

    if (!state.running || state.startTime == null) {
        stopLiveTimer();
        stopWatchdog();
        state.running = false;
        state.currentPromptId = null;
        if (!promptId || runningWorkflowId === workflowId) {
            runningWorkflowId = null;
        }
        forgetPromptWorkflow(promptId);
        render();
        return;
    }

    stopLiveTimer();
    stopWatchdog();

    const elapsed = getElapsedSeconds(state);

    state.totalCount += 1;
    state.totalDuration += elapsed;

    const text = label
        ? `${label}  ${elapsed.toFixed(2)} sec`
        : isError
            ? `Error  ${elapsed.toFixed(2)} sec`
            : `${elapsed.toFixed(2)} sec`;

    state.history.unshift(text);
    state.history = state.history.slice(0, MAX_HISTORY);

    state.startTime = null;
    state.running = false;
    state.lastActivityAt = 0;
    state.queueRemaining = null;
    state.lastExecutingNode = undefined;
    state.currentPromptId = null;

    if (!promptId || runningWorkflowId === workflowId) {
        runningWorkflowId = null;
    }
    forgetPromptWorkflow(promptId);

    render();
}

function resetIfNoNodes() {
    if (getTimerNodes().length === 0) {
        const workflowId = getEffectiveCurrentWorkflowId();

        stopLiveTimer();
        stopWatchdog();
        workflowStates.set(workflowId, createState());
        if (runningWorkflowId === workflowId) {
            runningWorkflowId = null;
        }
    }
}

function patchGraphRemove(graph) {
    if (!graph || graph.__ultraWorkflowTimerRemovePatched) return;

    const originalRemove = graph.remove.bind(graph);
    graph.__ultraWorkflowTimerRemovePatched = true;

    graph.remove = function (node) {
        const result = originalRemove(node);
        queueMicrotask(() => {
            patchAllGraphRemoves();
            rebuildTimerNodeCache();
            resetIfNoNodes();
            render();
        });
        return result;
    };
}

function patchAllGraphRemoves() {
    for (const graph of getAllGraphs()) {
        patchGraphRemove(graph);
    }
}

function patchLoadGraphData() {
    if (!app.loadGraphData || app.__ultraWorkflowTimerLoadPatched) return;

    const original = app.loadGraphData.bind(app);
    app.__ultraWorkflowTimerLoadPatched = true;

    app.loadGraphData = async function (...args) {
        const loadSeq = ++loadGraphSeq;

        stopLiveTimer();
        stopWatchdog();
        cancelRender();
        timerNodeCache = [];

        const workflowData = args?.[0] ?? null;
        const loadSourceId = getLoadGraphSourceId(args);
        // loadGraphData 진입 시점에는 ComfyUI의 active workflow/tab 정보가 아직 이전 값일 수 있다.
        // 따라서 현재 로드 대상 workflowData/source를 stale manager/hash보다 우선한다.
        currentWorkflowId = ensureWorkflowIdOnData(workflowData, { sourceId: loadSourceId });
        rememberLoadedWorkflow(workflowData, currentWorkflowId);
        ensureCurrentWorkflowId();

        const result = await original(...args);

        setTimeout(() => {
            if (loadSeq !== loadGraphSeq) return;

            // loadGraphData 이후에는 실제 로드된 런타임 그래프/워크플로우 객체까지
            // 반영해 path 없는 워크플로우의 A->B->A 순환 기록도 보존한다.
            const previousWorkflowId = currentWorkflowId;
            currentWorkflowId = ensureWorkflowIdAfterLoad(workflowData, { sourceId: loadSourceId });
            migrateWorkflowState(previousWorkflowId, currentWorkflowId);
            rememberLoadedWorkflow(workflowData, currentWorkflowId);
            ensureCurrentWorkflowId();

            patchQueuePrompt();
            patchAllGraphRemoves();
            rebuildTimerNodeCache();
            assignWorkflowIdToTimerNodes(currentWorkflowId);
            render();

            const currentState = getCurrentState();
            const isViewingRunningWorkflow =
                !!runningWorkflowId &&
                currentWorkflowId === runningWorkflowId &&
                currentState?.running === true;

            if (isViewingRunningWorkflow) {
                startLiveTimer();
                startWatchdog();
                renderLiveTimeOnly();
            }
        }, 100);

        return result;
    };
}

function patchQueuePrompt() {
    const primaryApi = app?.api || null;
    const targets = [primaryApi, app].filter(Boolean);

    for (const target of targets) {
        if (!target.queuePrompt || target.__ultraWorkflowTimerQueuePromptPatched) continue;
        if (target.queuePrompt.__ultraWorkflowTimerQueuePromptPatched) {
            target.__ultraWorkflowTimerQueuePromptPatched = true;
            continue;
        }

        const original = target.queuePrompt.bind(target);
        const wrappedQueuePrompt = function (...args) {
            // Use the loaded workflow identity, not a stale/default fallback. This keeps
            // saved-as duplicates independent while all timer nodes in the same root
            // workflow, including subgraphs, share one timing state.
            const workflowId = getEffectiveCurrentWorkflowId();
            const result = original(...args);

            const rememberFromResult = (value) => {
                const promptId = extractPromptId(value);
                rememberPromptWorkflow(promptId, workflowId);
                return value;
            };

            if (result && typeof result.then === "function") {
                return result.then(rememberFromResult);
            }

            return rememberFromResult(result);
        };

        wrappedQueuePrompt.__ultraWorkflowTimerQueuePromptPatched = true;
        target.queuePrompt = wrappedQueuePrompt;
        target.__ultraWorkflowTimerQueuePromptPatched = true;
    }
}

function setupNode(node) {
    node.__ultraWorkflowTimerWorkflowId = getEffectiveCurrentWorkflowId();

    if (node.__ultraWorkflowTimerSetupDone) return;
    node.__ultraWorkflowTimerSetupDone = true;

    for (const widget of node.widgets || []) {
        if (widget?.name === "Stats") {
            makeRuntimeOnlyWidget(widget);
        }
    }

    if (!getWidgetByName(node, "Stats")) {
        const timeIdx = node.widgets?.findIndex((w) => w.name === "Time") ?? -1;
        node.addWidget("text", "Stats", "Total: 0 runs | Avg: 0.00s", () => {});
        makeRuntimeOnlyWidget(getWidgetByName(node, "Stats"));

        if (timeIdx !== -1) {
            const statsWidget = node.widgets.pop();
            node.widgets.splice(timeIdx + 1, 0, statsWidget);
        }
    }

    const originalOnResize = node.onResize;
    node.onResize = function () {
        if (originalOnResize) {
            originalOnResize.apply(this, arguments);
        }
        render();
    };

    queueMicrotask(() => {
        fitNode(node);
        patchAllGraphRemoves();
        rebuildTimerNodeCache();
        assignWorkflowIdToTimerNodes(ensureCurrentWorkflowId());
        render();
    });
}

function eventDetail(evt) {
    return evt?.detail ?? evt ?? {};
}

app.registerExtension({
    name: "Ultra.WorkflowTimer",

    setup() {
        if (app.__ultraWorkflowTimerSetupDone) return;
        app.__ultraWorkflowTimerSetupDone = true;

        currentWorkflowId = resolveWorkflowId(lastLoadedWorkflowData, {
            allowObjectFallback: true,
            preferWorkflowData: true,
        });
        ensureCurrentWorkflowId();
        installWorkflowDropSourceCapture();
        patchLoadGraphData();
        patchQueuePrompt();
        patchAllGraphRemoves();
        rebuildTimerNodeCache();
        assignWorkflowIdToTimerNodes(currentWorkflowId);

        window.addEventListener("hashchange", () => {
            const nextId = resolveWorkflowId(null);
            if (nextId && nextId !== currentWorkflowId) {
                cancelRender();
                currentWorkflowId = nextId;
                ensureCurrentWorkflowId();
                rebuildTimerNodeCache();
                assignWorkflowIdToTimerNodes(currentWorkflowId);
                render();
            }
        });

        app.api.addEventListener("execution_start", (evt) => {
            const detail = eventDetail(evt);
            startExecution(detail);
            markActivity(detail);
        });

        app.api.addEventListener("execution_success", (evt) => {
            finishExecution(false, null, eventDetail(evt));
        });

        app.api.addEventListener("execution_error", (evt) => {
            finishExecution(true, null, eventDetail(evt));
        });

        app.api.addEventListener("execution_interrupted", (evt) => {
            finishExecution(false, "Interrupted", eventDetail(evt));
        });

        app.api.addEventListener("executing", (evt) => {
            markActivity(eventDetail(evt));
        });

        app.api.addEventListener("executed", (evt) => {
            markActivity(eventDetail(evt));
        });

        app.api.addEventListener("status", (evt) => {
            markActivity(eventDetail(evt));
        });
    },

    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "UltraWorkflowTimer") return;

        const original = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            original?.apply(this, arguments);
            setupNode(this);
        };
    },

    nodeCreated(node) {
        if (node.type !== "UltraWorkflowTimer") return;
        setupNode(node);
    },
});