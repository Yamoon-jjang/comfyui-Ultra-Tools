import { app } from "../../scripts/app.js";

// Current frontends expose a DOM widget's element as widget.element;
// widget.inputEl is a deprecated alias (warns on access). Prefer element and
// fall back to inputEl only on older frontends that lack it.
function ultraWidgetEl(widget) {
  if (!widget) return undefined;
  return "element" in widget ? widget.element : widget.inputEl;
}



const KO_LABELS = {
  model_profile: {
    "Z-Image Natural": "Z-Image 자연어",
    "Qwen Natural": "Qwen 자연어",
    "Flux Natural": "Flux 자연어",
    "Anima Mixed": "Anima 태그+문장",
    "SDXL Tag": "SDXL 태그형",
    "ILXL / Illustrious Tag": "ILXL / Illustrious 태그형",
    "Pony Tag": "Pony 태그형",
    "SD 1.5 Tag": "SD 1.5 태그형",
    "Universal Natural Language": "범용 자연어",
    "SDXL / Anima Natural": "SDXL / Anima 자연어",
    "Pony / Illustrious Tag": "Pony / Illustrious 태그형",
    "Anime Tag General": "애니메이션 범용 태그형",
    "Flux / Qwen Instruction": "Flux / Qwen 지시문형",
  },
  mood_family: {
    "Default / None": "기본",
    "🎲 Random All": "🎲 랜덤 전체",
    "🎲 Random Transformative Style": "🎲 랜덤 변환 스타일",
    "🎲 Random Traditional Media Style": "🎲 랜덤 전통 매체 화풍",
    "Erotic / Sensual": "관능적인 분위기",
    "Lyrical / Poetic": "서정적인 분위기",
    "Classical / Golden Age": "클래식 영화 분위기",
    "Noir / Neo-noir": "어두운 영화 분위기",
    "Dreamlike / Surreal": "몽환적인 분위기",
    "Gothic Romance": "고딕 로맨스 분위기",
    Melodrama: "감정적인 드라마 분위기",
    "Fashion Editorial": "고급 화보 분위기",
    "Arthouse Realism": "차분한 예술영화 분위기",
    "Pop Neon": "선명한 네온 분위기",
    "Baroque / Operatic": "화려하고 웅장한 분위기",
    "Minimalist Psychological": "절제된 심리극 분위기",
    "Dark Fantasy Romance": "어두운 판타지 로맨스",
    "Black & White Film": "흑백 영화 분위기",
    "Golden Hour Warmth": "따뜻한 노을빛 분위기",
    "Vintage / Retro": "빈티지 감성",
    "Cyberpunk / Sci-fi": "미래적인 네온 분위기",
    "Watercolor / Painterly": "수채화처럼 부드러운 분위기",
    "Bright / High-key": "밝고 깨끗한 분위기",
    "Cinematic Widescreen": "넓고 장대한 분위기",
    "Romantic / Soft Focus": "부드러운 로맨틱 분위기",
    "Horror / Unsettling": "불안하고 어두운 분위기",
  },
  style_dna: {
    "Auto by Mood": "분위기에 맞춰 자동",
    "Neutral / Minimal Carryover": "중립 / 거의 추가 안 함",
    "Neon Melancholy / Rain Glass": "빗속 네온 감성",
    "Classical Studio Glamour": "클래식 스튜디오 화보",
    "Noir Chiaroscuro": "어두운 영화 명암",
    "Symmetric Psychological Coldness": "차갑고 대칭적인 화면",
    "Swedish Face Silence": "고요한 클로즈업 초상",
    "Mediterranean Sunlight": "따뜻한 지중해 햇빛",
    "French Natural Light New Wave": "자연광 거리 영화 느낌",
    "Gothic Candle Velvet": "고딕 촛불과 벨벳",
    "Dream Pastel Diffusion": "몽환적인 파스텔 빛",
    "Fashion Editorial Studio Cinema": "스튜디오 화보 영화감",
    "High-key Clean Light": "밝고 깨끗한 조명",
    "Cinematic Widescreen Scope": "넓은 영화 화면",
    "Baroque Operatic Atmosphere": "화려하고 웅장한 무대감",
    "Dark Fantasy Shadow Mass": "어두운 판타지 그림자",
    "Black & White Classic": "클래식 흑백",
    "Golden Hour Glow": "따뜻한 노을빛",
    "Vintage Film Look": "빈티지 필름 느낌",
    "Cyberpunk Neon": "사이버펑크 네온",
    "Soft Romantic Glow": "부드러운 로맨틱 빛",
    "Watercolor / Painterly": "수채화 회화 느낌",
    "Charcoal Drawing": "목탄 드로잉",
    "Graphite Pencil Sketch": "연필 스케치",
    "Pen and Ink Sketch": "펜화 스케치",
    "Ink Wash / Sumi-e": "수묵화",
    "Colored Pencil Illustration": "색연필 일러스트",
    "Pastel Chalk Drawing": "파스텔 드로잉",
    "Gouache Storybook Illustration": "불투명 물감 동화풍",
    "Hand-Painted Storybook Animation": "손그림 동화 애니풍",
    "Volumetric Dust Light": "공기 중 먼지 빛",
    "Long Exposure Light Trails": "긴 노출 빛 궤적",
    "Oil Painting": "유화 느낌",
    "Miniature Diorama": "미니어처 디오라마",
    "Pixel Art": "픽셀 아트",
    "3D Collectible Figure": "3D 피규어 느낌",
    "Apocalyptic Wasteland": "폐허 세계 분위기",
    "Chibi Style": "치비 스타일",
    "Clean Cel Animation": "깔끔한 셀 애니풍",
  },
  lens_preset: {
    auto: "자동",
    "18mm ultra-wide dramatic": "18mm 초광각 / 공간 강조",
    "24mm wide cinematic": "24mm 넓은 영화 화면",
    "28mm documentary wide": "28mm 넓은 현장감",
    "35mm environmental": "35mm 배경이 보이는 인물",
    "40mm cinematic natural": "40mm 자연스러운 화면",
    "50mm intimate natural": "50mm 자연스러운 인물",
    "58mm vintage character": "58mm 빈티지 인물",
    "85mm portrait shallow DOF": "85mm 인물 / 배경 흐림",
    "100mm macro detail": "100mm 가까운 디테일",
    "135mm compressed portrait": "135mm 망원 인물",
    "long lens compression": "망원 압축감",
    "anamorphic widescreen": "와이드 영화 화면",
    "wide architectural": "넓은 건축 공간",
    "overhead top-down": "위에서 내려다봄",
    "low angle dramatic": "아래에서 올려다봄",
    "dutch angle tension": "기울어진 긴장감",
    "handheld documentary": "핸드헬드 현장감",
  },
  style_strength: {
    subtle: "원본 보존",
    balanced: "균형 적용",
    strong: "스타일 우선",
  },
  style_conflict_cleanup: {
    off: "끔",
    soft: "부드럽게 완화",
    strong: "강하게 완화",
  },
  adult_tone: {
    default: "기본",
    safe: "안전한 표현",
    suggestive: "살짝 암시적",
    sensual: "부드러운 관능",
    "bold sensual": "강한 관능",
    nsfw: "성인 NSFW",
    "explicit nsfw": "강한 성인 NSFW",
    "romantic non-explicit": "노골적이지 않은 로맨스",
  },
  adult_wardrobe: {
    auto: "자동 / 미지정",
    nude: "누드",
    topless: "상의 탈의",
    lingerie: "란제리",
    bikini: "비키니",
    "one-piece swimsuit": "원피스 수영복",
    "sheer nightgown": "시스루 나이트가운",
    "silk slip dress": "실크 슬립 드레스",
    corset: "코르셋",
    bodysuit: "바디수트",
    "latex outfit": "라텍스 의상",
    "leather outfit": "가죽 의상",
    "evening dress": "이브닝 드레스",
    "tailored suit": "테일러드 수트",
    bathrobe: "목욕 가운",
    "lace lingerie set": "레이스 란제리 세트",
    "sheer robe": "시스루 로브",
    "satin robe": "새틴 로브",
    "silk camisole": "실크 캐미솔",
    bralette: "브라렛",
    "lace bodysuit": "레이스 바디수트",
    "sheer bodysuit": "시스루 바디수트",
    "garter belt": "가터 벨트",
    "thigh-high stockings": "허벅지 스타킹",
    pantyhose: "팬티스타킹",
    "open shirt": "오픈 셔츠",
    "oversized shirt": "오버사이즈 셔츠",
    "mini dress": "미니 드레스",
    "off-shoulder dress": "오프숄더 드레스",
    "halter dress": "홀터넥 드레스",
    "fishnet outfit": "그물망 의상",
    "vinyl outfit": "글로시 비닐 의상",
    "mesh top": "메시 탑",
  },
  scene_framing: {
    auto: "자동 / 미지정",
    "headshot (face-focused)": "얼굴 중심",
    "close-up": "가까운 인물",
    "upper body": "상반신",
    "waist-up": "허리 위",
    "three-quarter body": "무릎 위 정도",
    "full body (head to toe)": "전신",
    "full shot (full body + extra space)": "전신 + 주변 여백",
    "wide shot": "넓은 배경 포함",
    "high-angle portrait": "위쪽 시점 인물",
    "overhead portrait": "위에서 내려다본 인물",
    "over-the-shoulder": "어깨 너머 시점",
    "profile portrait": "옆모습",
    "back view": "뒷모습",
    "environmental portrait": "배경이 보이는 인물",
    "seated full body": "앉은 전신",
  },
  external_prompt_mode: {
    "Append style after external prompt": "원본 뒤에 스타일 문구 추가",
    "Prepend style before external prompt": "스타일 문구를 앞에 먼저 배치",
    "Output style only": "스타일 문구만 출력",
  },
};


const WIDGET_NAMES_KO = {
  model_profile: "모델 형식",
  mood_family: "분위기",
  adult_tone: "성인 표현 톤",
  adult_wardrobe: "성인 의상",
  style_dna: "스타일 방향",
  style_strength: "스타일 반영 방식",
  style_conflict_cleanup: "스타일 방해 문구 정리",
  scene_framing: "구도 / 화면 범위",
  lens_preset: "카메라 / 렌즈 느낌",
  custom_text: "추가 문구",
  external_prompt_mode: "원본 프롬프트와 합치기",
  seed: "시드",
  control_after_generate: "시드 제어",
};


const WIDGET_NAMES_EN = {
  model_profile: "Model Format",
  mood_family: "Mood",
  adult_tone: "Adult Tone",
  adult_wardrobe: "Adult Wardrobe",
  style_dna: "Style Direction",
  style_strength: "Style Application Mode",
  style_conflict_cleanup: "Style Conflict Cleanup",
  scene_framing: "Framing / Coverage",
  lens_preset: "Camera / Lens Feel",
  custom_text: "Additional Text",
  external_prompt_mode: "Merge With Original Prompt",
  seed: "Seed",
  control_after_generate: "Seed Control",
};

const KO_INPUT_PORT_NAMES = {
  external_positive_in: "외부 Positive 프롬프트",
  external_negative_in: "외부 Negative 프롬프트",
};
const EN_INPUT_PORT_NAMES = {
  external_positive_in: "External Positive",
  external_negative_in: "External Negative",
};

const KO_OUTPUT_PORT_NAMES = {
  positive_prompt: "Positive 프롬프트",
  negative_prompt: "Negative 프롬프트",
};

const WIDGET_ORDER = [
  "model_profile",
  "mood_family",
  "style_dna",
  "style_strength",
  "style_conflict_cleanup",
  "scene_framing",
  "lens_preset",
  "adult_tone",
  "adult_wardrobe",
  "external_prompt_mode",
  "seed",
  "control_after_generate",
  "custom_text",
];

const PREVIOUS_WIDGET_ORDER = [
  "model_profile",
  "mood_family",
  "adult_tone",
  "adult_wardrobe",
  "style_dna",
  "style_strength",
  "scene_framing",
  "lens_preset",
  "external_prompt_mode",
  "seed",
  "control_after_generate",
  "custom_text",
];

const PRE_CLEANUP_WIDGET_ORDER = [
  "model_profile",
  "mood_family",
  "style_dna",
  "style_strength",
  "scene_framing",
  "lens_preset",
  "adult_tone",
  "adult_wardrobe",
  "external_prompt_mode",
  "seed",
  "control_after_generate",
  "custom_text",
];


const STALE_WIDGETS = new Set([
  "generation_control",
  "subject",
  "wardrobe",
  "location",
]);


function buildReverse(labels) {
  const out = {};
  for (const [widgetName, mapping] of Object.entries(labels)) {
    out[widgetName] = {};
    for (const [en, ko] of Object.entries(mapping))
      out[widgetName][ko] = en;
  }
  return out;
}
const REVERSE = buildReverse(KO_LABELS);

const LEGACY_VALUE_ALIASES = {
  external_prompt_mode: {
    "External prompt + style only": "Output style only",
    "외부 프롬프트 뒤에 스타일 추가": "Append style after external prompt",
    "외부 프롬프트 앞에 스타일 추가": "Prepend style before external prompt",
    "스타일만 출력": "Output style only",
  },
  mood_family: {
    "누아르 / 현대 누아르": "Noir / Neo-noir",
    "고전 영화 / 황금기": "Classical / Golden Age",
    "서정적 / 시적": "Lyrical / Poetic",
    "관능적 / 감각적": "Erotic / Sensual",
    "몽환적 / 초현실적": "Dreamlike / Surreal",
    "패션 화보풍": "Fashion Editorial",
    "예술영화 리얼리즘": "Arthouse Realism",
    "팝 네온 감성": "Pop Neon",
    "바로크풍 / 오페라적 웅장함": "Baroque / Operatic",
    "미니멀 심리극": "Minimalist Psychological",
    "따뜻한 노스탤지어": "Golden Hour Warmth",
    "사이버펑크 / SF 정서": "Cyberpunk / Sci-fi",
    "수채화 / 회화풍": "Watercolor / Painterly",
    "수채화적 서정감": "Watercolor / Painterly",
    "밝고 경쾌한 정서": "Bright / High-key",
    "장대한 서사감": "Cinematic Widescreen",
    "로맨틱한 친밀감": "Romantic / Soft Focus",
    "호러 / 불안한 분위기": "Horror / Unsettling",
    "🎲 Random Mood": "🎲 Random All",
    "🎲 랜덤 분위기": "🎲 Random All",
    "랜덤 분위기": "🎲 Random All",
    "🎲 랜덤 전체": "🎲 Random All",
    "랜덤 전체": "🎲 Random All",
    "🎲 랜덤 변환 스타일": "🎲 Random Transformative Style",
    "🎲 랜덤 전통 매체 화풍": "🎲 Random Traditional Media Style",
  },
  style_dna: {
    "정서에 맞춰 자동": "Auto by Mood",
    "중립 / 최소 개입": "Neutral / Minimal Carryover",
    "네온 멜랑콜리 / 빗물 유리": "Neon Melancholy / Rain Glass",
    "클래식 스튜디오 글래머": "Classical Studio Glamour",
    "누아르 키아로스쿠로": "Noir Chiaroscuro",
    "대칭적 심리적 냉기": "Symmetric Psychological Coldness",
    "스웨덴식 정적 초상": "Swedish Face Silence",
    "지중해 햇빛": "Mediterranean Sunlight",
    "프랑스 자연광 누벨바그": "French Natural Light New Wave",
    "고딕 촛불 벨벳": "Gothic Candle Velvet",
    "몽환 파스텔 확산광": "Dream Pastel Diffusion",
    "패션 에디토리얼 스튜디오 시네마": "Fashion Editorial Studio Cinema",
    "하이키 클린 라이트": "High-key Clean Light",
    "시네마틱 와이드스크린 스코프": "Cinematic Widescreen Scope",
    "바로크 오페라틱 분위기": "Baroque Operatic Atmosphere",
    "다크 판타지 그림자 덩어리": "Dark Fantasy Shadow Mass",
    "흑백 클래식": "Black & White Classic",
    "골든아워 빛감": "Golden Hour Glow",
    "빈티지 필름": "Vintage Film Look",
    "사이버펑크 네온": "Cyberpunk Neon",
    "부드러운 로맨틱 광채": "Soft Romantic Glow",
    "수채화 / 회화풍": "Watercolor / Painterly",
    "흑연 연필 스케치": "Graphite Pencil Sketch",
    "펜 앤 잉크 스케치": "Pen and Ink Sketch",
    "먹그림 / 수묵화": "Ink Wash / Sumi-e",
    "파스텔 초크 드로잉": "Pastel Chalk Drawing",
    "구아슈 동화책 일러스트": "Gouache Storybook Illustration",
    "손그림 동화풍": "Hand-Painted Storybook Animation",
    "손그림 동화풍 애니메이션": "Hand-Painted Storybook Animation",
    "먼지 / 빛 산란(볼류메트릭)": "Volumetric Dust Light",
    "먼지 / 볼류메트릭 빛 산란": "Volumetric Dust Light",
    "롱 익스포저 / 빛 궤적": "Long Exposure Light Trails",
    "아포칼립스": "Apocalyptic Wasteland",
    "아포칼립스 / 폐허 세계": "Apocalyptic Wasteland",
    "치비 스타일": "Chibi Style",
    "작고 귀여운 캐릭터풍": "Chibi Style",
    "클린 셀 애니메이션": "Clean Cel Animation",
  },
  lens_preset: {
    "18mm 초광각 드라마틱": "18mm ultra-wide dramatic",
    "24mm 와이드 시네마틱": "24mm wide cinematic",
    "28mm 다큐멘터리 와이드": "28mm documentary wide",
    "35mm 환경형": "35mm environmental",
    "40mm 시네마틱 자연형": "40mm cinematic natural",
    "50mm 자연스러운 친밀감": "50mm intimate natural",
    "58mm 빈티지 캐릭터": "58mm vintage character",
    "85mm 얕은 심도 인물형": "85mm portrait shallow DOF",
    "100mm 매크로 디테일": "100mm macro detail",
    "135mm 압축 인물형": "135mm compressed portrait",
    "아나모픽 와이드스크린": "anamorphic widescreen",
    "광각 건축적 구도": "wide architectural",
    "오버헤드 탑다운": "overhead top-down",
    "로우앵글 드라마틱": "low angle dramatic",
    "더치앵글 긴장감": "dutch angle tension",
    "핸드헬드 다큐멘터리": "handheld documentary",
  },
  style_strength: {
    "원본 보존": "subtle",
    "균형 적용": "balanced",
    "스타일 우선": "strong",
    "절제": "subtle",
    "균형": "balanced",
    "강함": "strong",
  },
  style_conflict_cleanup: {
    "끔": "off",
    "사용 안 함": "off",
    "부드럽게 완화": "soft",
    "약하게 완화": "soft",
    "강하게 완화": "strong",
    "강함": "strong",
  },
  adult_tone: {
    "세이프": "safe",
    "암시적": "suggestive",
    "센슈얼": "sensual",
    "대담한 센슈얼": "bold sensual",
    "강한 NSFW": "explicit nsfw",
    "로맨틱 비노골적": "romantic non-explicit",
  },
  scene_framing: {
    "헤드샷 (얼굴 중심)": "headshot (face-focused)",
    "클로즈업": "close-up",
    "3/4 바디": "three-quarter body",
    "전신 (머리~발끝)": "full body (head to toe)",
    "풀샷 (전신+여백)": "full shot (full body + extra space)",
    "와이드샷": "wide shot",
    "하이앵글 인물샷": "high-angle portrait",
    "오버헤드 인물샷": "overhead portrait",
    "오버더숄더": "over-the-shoulder",
    "프로필 인물샷": "profile portrait",
    "환경 인물샷": "environmental portrait",
  },
};

const CURRENT_WIDGET_DEFAULTS = {
  model_profile: "Z-Image Natural",
  mood_family: "Default / None",
  style_dna: "Auto by Mood",
  style_strength: "strong",
  style_conflict_cleanup: "off",
  scene_framing: "auto",
  lens_preset: "auto",
  adult_tone: "default",
  adult_wardrobe: "auto",
  external_prompt_mode: "Prepend style before external prompt",
  seed: 0,
  control_after_generate: "fixed",
  custom_text: "",
};

function applyLegacyAlias(widgetName, value) {
  const s = String(value ?? "");
  return LEGACY_VALUE_ALIASES[widgetName]?.[s] || s;
}

function optionKeys(widgetName) {
  return Object.keys(KO_LABELS[widgetName] || {});
}

function normalizeSeedControlValue(value) {
  const raw = String(value ?? "").trim();
  const lower = raw.toLowerCase();
  const localized = {
    "고정": "fixed",
    "무작위": "randomize",
    "랜덤": "randomize",
    "임의": "randomize",
    "증가": "increment",
    "증분": "increment",
    "감소": "decrement",
    "감분": "decrement",
  };
  if (localized[raw]) return localized[raw];
  if (["fixed", "randomize", "increment", "decrement"].includes(lower)) {
    return lower;
  }
  return CURRENT_WIDGET_DEFAULTS.control_after_generate;
}

function normalizeWidgetValue(widgetName, value, options = {}) {
  if (widgetName === "seed") {
    if (value == null || value === "") return 0;
    if (typeof value === "number") return Number.isFinite(value) ? value : 0;
    if (typeof value === "bigint") return value.toString();
    if (typeof value === "string") {
      const raw = value.trim();
      if (/^\d+$/.test(raw)) {
        const n = Number(raw);
        return Number.isSafeInteger(n) ? n : raw;
      }
      const n = Number(raw);
      return Number.isFinite(n) ? n : 0;
    }
    return value;
  }
  if (widgetName === "control_after_generate") return normalizeSeedControlValue(value);
  if (widgetName === "custom_text") return String(value ?? "");

  const aliased = applyLegacyAlias(widgetName, value);
  const canonical = REVERSE[widgetName]?.[aliased] || aliased;
  const allowed = optionKeys(widgetName);
  if (!allowed.length || allowed.includes(canonical)) return canonical;


  if (options.preserveUnknownCanonical && typeof aliased === "string" && aliased.trim() && !REVERSE[widgetName]?.[aliased]) {
    return canonical;
  }
  return CURRENT_WIDGET_DEFAULTS[widgetName] ?? canonical;
}

function valueLooksValidFor(widgetName, value) {
  if (widgetName === "seed" || widgetName === "custom_text") return true;
  if (widgetName === "control_after_generate") {
    return ["fixed", "randomize", "increment", "decrement"].includes(normalizeSeedControlValue(value));
  }
  const aliased = applyLegacyAlias(widgetName, value);
  const canonical = REVERSE[widgetName]?.[aliased] || aliased;
  return optionKeys(widgetName).includes(canonical);
}

function getInputWidgetNames(data) {
  const names = new Set();
  for (const input of data?.inputs || []) {
    const raw = typeof input === "string" ? input : (input?.name || input?.widget?.name || input?.widget_name);
    const name = String(raw || "").trim();
    if (name && Object.prototype.hasOwnProperty.call(CURRENT_WIDGET_DEFAULTS, name)) names.add(name);
  }
  return names;
}

function readCurrentWidgetNamedValues(node) {
  const named = {};
  for (const widget of node?.widgets || []) {
    if (isConvertedWidget(widget)) continue;
    const name = widget?._ultraCanonicalName || widget?.name;
    if (!name || !Object.prototype.hasOwnProperty.call(CURRENT_WIDGET_DEFAULTS, name)) continue;
    if (widget.value !== undefined) {
      named[name] = widget.value;
    }
  }
  return named;
}

function dataLikelyHasSeedControl(data, inputNames = new Set()) {
  const vals = data?.widgets_values;
  if (!Array.isArray(vals) || inputNames.has("control_after_generate")) return false;
  const activeWithControl = WIDGET_ORDER.filter((name) => !inputNames.has(name));
  const controlIndex = activeWithControl.indexOf("control_after_generate");
  return (
    controlIndex >= 0 &&
    vals.length === activeWithControl.length &&
    valueLooksValidFor("control_after_generate", vals[controlIndex])
  );
}

function ensureSeedControlWidgetOrder(order, inputNames = new Set(), options = {}) {
  const preserveControl = options.preserveControl === true && !inputNames.has("control_after_generate");
  const out = [];
  const seen = new Set();
  for (const name of order || []) {
    if (!name || inputNames.has(name) || seen.has(name)) continue;
    if (!Object.prototype.hasOwnProperty.call(CURRENT_WIDGET_DEFAULTS, name)) continue;
    if (name === "control_after_generate" && !preserveControl) continue;
    seen.add(name);
    out.push(name);
  }

  if (preserveControl && !seen.has("control_after_generate")) {
    const seedIndex = out.indexOf("seed");
    if (seedIndex >= 0) {
      out.splice(seedIndex + 1, 0, "control_after_generate");
    } else {
      const customIndex = out.indexOf("custom_text");
      if (customIndex >= 0) out.splice(customIndex, 0, "control_after_generate");
      else out.push("control_after_generate");
    }
  }
  return out;
}

function isConvertedWidget(widget) {
  return widget?.type === "converted-widget" || widget?.convertedToInput === true || widget?.options?.convertedWidget === true;
}

function isLiveNode(node) {
  if (!node || !Array.isArray(node.widgets)) return false;
  const graph = app?.graph || node.graph;
  if (!graph) return false;
  if (typeof graph.getNodeById === "function" && node.id != null) return graph.getNodeById(node.id) === node;
  if (Array.isArray(graph._nodes)) return graph._nodes.includes(node);
  return node.graph === graph;
}

function scheduleLocalizeNode(node) {
  setTimeout(() => {
    if (!isLiveNode(node)) return;
    localizeNode(node);
  }, 0);
}

function getRuntimeWidgetOrder(node, data = null) {
  const inputNames = getInputWidgetNames(data);
  const out = [];
  const seen = new Set();
  let hasRuntimeSeedControl = false;
  for (const widget of node?.widgets || []) {
    if (isConvertedWidget(widget)) continue;
    const name = widget?._ultraCanonicalName || widget?.name;
    if (name === "control_after_generate") hasRuntimeSeedControl = true;
    if (!name || inputNames.has(name) || seen.has(name)) continue;
    if (!Object.prototype.hasOwnProperty.call(CURRENT_WIDGET_DEFAULTS, name)) continue;
    seen.add(name);
    out.push(name);
  }

  const preserveControl = hasRuntimeSeedControl || dataLikelyHasSeedControl(data, inputNames) || !inputNames.has("seed");
  return ensureSeedControlWidgetOrder(out.length ? out : WIDGET_ORDER, inputNames, { preserveControl });
}

function makeWidgetValuesForOrder(namedValues = {}, widgetOrder = WIDGET_ORDER, options = {}) {
  return widgetOrder.map((name) =>
    normalizeWidgetValue(name, namedValues[name] ?? CURRENT_WIDGET_DEFAULTS[name], options)
  );
}


function readSettingValue(path) {
  try {
    const s = app?.extensionManager?.setting;
    if (!s) return undefined;
    if (typeof s.get === "function") return s.get(path);
    if (typeof s.getSettingValue === "function") return s.getSettingValue(path);
  } catch (_) {}
  return undefined;
}


function hasLocaleValue(value) {
  if (value == null) return false;
  if (typeof value === "string") return value.trim().length >= 2;
  return true;
}


function localeLooksKorean(value) {
  if (value == null) return false;
  const candidates = [];
  const pushCandidate = (v) => {
    if (v == null) return;
    if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") {
      candidates.push(String(v));
    } else {
      try { candidates.push(JSON.stringify(v)); } catch (_) {}
    }
  };
  pushCandidate(value);
  if (typeof value === "string") {
    const trimmed = value.trim();
    if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
      try { pushCandidate(JSON.parse(trimmed)); } catch (_) {}
    }
  }
  return candidates.some((item) => {
    const raw = String(item || "").toLowerCase().trim();
    return /(^|[^a-z0-9])ko(?:[-_][a-z0-9]+)?($|[^a-z0-9])/.test(raw);
  });
}


function isKoreanLocale() {

  const settingPaths = ["Comfy.Locale", "ComfyUI.Locale", "Comfy.Language"];
  for (const path of settingPaths) {
    const v = readSettingValue(path);
    if (hasLocaleValue(v)) {
      return localeLooksKorean(v);
    }
  }


  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i) || "";
      if (/locale|language/i.test(key)) {
        const val = localStorage.getItem(key);
        if (hasLocaleValue(val) && localeLooksKorean(val)) {
          return true;
        }
      }
    }
  } catch (_) {}


  try {
    const docLang = document.documentElement?.lang || "";
    if (hasLocaleValue(docLang)) return localeLooksKorean(docLang);
  } catch (_) {}
  try {
    const navLang = navigator.language || "";
    return hasLocaleValue(navLang) ? localeLooksKorean(navLang) : false;
  } catch (_) {}

  return false;
}


function toCanonical(widgetName, value, options = {}) {
  return normalizeWidgetValue(widgetName, value, options);
}


function toDisplay(widgetName, value, korean) {
  if (!korean) return value;
  return KO_LABELS[widgetName]?.[value] || value;
}


function patchComboWidget(widget, korean) {
  const canonicalName = widget._ultraCanonicalName || widget.name;
  const map = KO_LABELS[canonicalName];
  if (!map) return;
  widget._ultraCanonicalName = canonicalName;


  const rawValues = Array.isArray(widget.options?.values)
    ? widget.options.values
    : [];
  const canonicals = [];
  const seen = new Set();
  for (const v of rawValues) {
    const c = toCanonical(canonicalName, v, { preserveUnknownCanonical: true });
    if (!seen.has(c)) {
      seen.add(c);
      canonicals.push(c);
    }
  }


  widget.options.values = canonicals.map((c) =>
    toDisplay(canonicalName, c, korean)
  );
  widget.value = toDisplay(
    canonicalName,
    toCanonical(canonicalName, widget.value, { preserveUnknownCanonical: true }),
    korean
  );
  widget.serializeValue = function () {
    return toCanonical(canonicalName, this.value, { preserveUnknownCanonical: true });
  };
}


function patchWidgetLabel(widget, korean) {
  const canonical = widget._ultraCanonicalName || widget.name;
  widget._ultraCanonicalName = canonical;

  if (korean) {
    widget.label = WIDGET_NAMES_KO[canonical] || canonical;
  } else {
    widget.label = WIDGET_NAMES_EN[canonical] || canonical;
  }
}

function patchTextWidgetExtras(widget, korean) {
  const canonical = widget._ultraCanonicalName || widget.name;
  if (canonical !== "custom_text") return;

  const placeholder = korean
    ? "예) modern city skyline, luxury living room, black dress, night street"
    : "Ex) modern city skyline, luxury living room, black dress, night street";

  try {
    if (ultraWidgetEl(widget)) {
      ultraWidgetEl(widget).placeholder = placeholder;
      ultraWidgetEl(widget).title = placeholder;
    }
  } catch (_) {}

  try {
    widget.options = widget.options || {};
    widget.options.placeholder = placeholder;
  } catch (_) {}
}

function patchPorts(node, korean) {
  for (const input of node.inputs || []) {
    const canonical = input._ultraCanonicalName || input.name;
    input._ultraCanonicalName = canonical;
    input.label = korean
      ? KO_INPUT_PORT_NAMES[canonical] || WIDGET_NAMES_KO[canonical] || canonical
      : EN_INPUT_PORT_NAMES[canonical] || WIDGET_NAMES_EN[canonical] || canonical;
  }
  for (const output of node.outputs || []) {
    const canonical = output._ultraCanonicalName || output.name;
    output._ultraCanonicalName = canonical;
    output.label = korean
      ? KO_OUTPUT_PORT_NAMES[canonical] || canonical
      : canonical;
  }
}

function cleanupAndReorderWidgets(node) {
  const widgets = Array.isArray(node.widgets) ? node.widgets : [];


  for (const w of widgets) {
    if (isConvertedWidget(w)) continue;
    const canonical = w._ultraCanonicalName || w.name;
    if (STALE_WIDGETS.has(canonical)) {
      w._ultraCanonicalName = canonical;
      w.visible = false;
      w.hidden = true;
      w.computeSize = () => [0, 0];
      continue;
    }
    if (!STALE_WIDGETS.has(canonical)) {
      if (w.visible === false) w.visible = true;
      if (w.hidden === true) w.hidden = false;
    }
  }

  node.widgets = widgets;
}


function localizeNode(node) {
  if (!isLiveNode(node)) return;

  const korean = isKoreanLocale();

  cleanupAndReorderWidgets(node);

  for (const widget of node.widgets || []) {
    if (isConvertedWidget(widget)) continue;
    const canonical = widget._ultraCanonicalName || widget.name;
    widget._ultraCanonicalName = canonical;
    patchComboWidget(widget, korean);
    patchWidgetLabel(widget, korean);
    patchTextWidgetExtras(widget, korean);
  }

  patchPorts(node, korean);


  node.title = korean
    ? "Ultra Tools Prompt Styler"
    : "Ultra Tools Prompt Styler";

  node.setDirtyCanvas?.(true, true);
  node.computeSize?.();
}


function valuesMatchOrder(vals, checks) {
  return checks.every(([name, index]) => valueLooksValidFor(name, vals[index]));
}

function namedValuesFromOrder(vals, sourceOrder) {
  const named = {};
  for (let i = 0; i < vals.length && i < sourceOrder.length; i++) named[sourceOrder[i]] = vals[i];
  return named;
}

function legacySchemaMigration(vals, expectedLength) {
  if (
    vals.length >= PREVIOUS_WIDGET_ORDER.length &&
    valuesMatchOrder(vals, [
      ["model_profile", 0], ["mood_family", 1], ["adult_tone", 2],
      ["adult_wardrobe", 3], ["style_dna", 4], ["style_strength", 5],
      ["scene_framing", 6], ["lens_preset", 7], ["external_prompt_mode", 8],
      ["seed", 9], ["control_after_generate", 10],
    ])
  ) {
    return namedValuesFromOrder(vals.slice(0, PREVIOUS_WIDGET_ORDER.length), PREVIOUS_WIDGET_ORDER);
  }

  if (
    vals.length >= PRE_CLEANUP_WIDGET_ORDER.length &&
    valuesMatchOrder(vals, PRE_CLEANUP_WIDGET_ORDER.map((name, index) => [name, index]))
  ) {
    return namedValuesFromOrder(vals.slice(0, PRE_CLEANUP_WIDGET_ORDER.length), PRE_CLEANUP_WIDGET_ORDER);
  }

  if (
    vals.length >= 8 &&
    valuesMatchOrder(vals, [
      ["model_profile", 0], ["mood_family", 1], ["adult_tone", 2],
      ["style_dna", 3], ["style_strength", 4], ["lens_preset", 5],
      ["external_prompt_mode", 6],
    ])
  ) {
    return {
      model_profile: vals[0],
      mood_family: vals[1],
      adult_tone: vals[2],
      style_dna: vals[3],
      style_strength: vals[4],
      lens_preset: vals[5],
      external_prompt_mode: vals[6],
      seed: vals[7],
    };
  }

  if (
    vals.length >= 9 &&
    valuesMatchOrder(vals, [
      ["model_profile", 0], ["mood_family", 1], ["adult_tone", 2],
      ["style_dna", 3], ["style_strength", 4], ["lens_preset", 5],
      ["external_prompt_mode", 7],
    ])
  ) {
    return {
      model_profile: vals[0],
      mood_family: vals[1],
      adult_tone: vals[2],
      style_dna: vals[3],
      style_strength: vals[4],
      lens_preset: vals[5],
      custom_text: vals[6],
      external_prompt_mode: vals[7],
      seed: vals[8],
    };
  }

  if (
    vals.length === PREVIOUS_WIDGET_ORDER.length - 1 &&
    valuesMatchOrder(vals, [
      ["model_profile", 0], ["mood_family", 1], ["adult_tone", 2],
      ["adult_wardrobe", 3], ["style_dna", 4], ["style_strength", 5],
      ["scene_framing", 6], ["lens_preset", 7], ["external_prompt_mode", 8],
      ["seed", 9],
    ]) &&
    (typeof vals[10] === "string" || vals[10] == null)
  ) {
    return {
      model_profile: vals[0],
      mood_family: vals[1],
      adult_tone: vals[2],
      adult_wardrobe: vals[3],
      style_dna: vals[4],
      style_strength: vals[5],
      scene_framing: vals[6],
      lens_preset: vals[7],
      external_prompt_mode: vals[8],
      seed: vals[9],
      control_after_generate: CURRENT_WIDGET_DEFAULTS.control_after_generate,
      custom_text: vals[10],
    };
  }

  return null;
}

function migrateWidgetValuesForCurrentSchema(data, node) {
  if (!data?.widgets_values || !Array.isArray(data.widgets_values)) return;
  const vals = data.widgets_values;
  const expectedLength = WIDGET_ORDER.length;
  const inputNames = getInputWidgetNames(data);
  const activeCurrentOrder = WIDGET_ORDER.filter((name) => !inputNames.has(name));
  const activeWithoutSeedControl = activeCurrentOrder.filter((name) => name !== "control_after_generate");
  const targetOrder = getRuntimeWidgetOrder(node, data);
  const runtimeNamedValues = readCurrentWidgetNamedValues(node);
  const saveValues = (namedValues = {}, options = {}) => {
    data.widgets_values = makeWidgetValuesForOrder({ ...runtimeNamedValues, ...namedValues }, targetOrder, options);
  };

  if (inputNames.size) {
    const previousActiveOrder = PREVIOUS_WIDGET_ORDER.filter((name) => !inputNames.has(name));
    const previousWithoutSeedControl = previousActiveOrder.filter((name) => name !== "control_after_generate");
    const previousSourceOrder = (
      previousActiveOrder.includes("control_after_generate") &&
      vals.length === previousWithoutSeedControl.length
    ) ? previousWithoutSeedControl : previousActiveOrder;
    const preCleanupActiveOrder = PRE_CLEANUP_WIDGET_ORDER.filter((name) => !inputNames.has(name));
    const preCleanupWithoutSeedControl = preCleanupActiveOrder.filter((name) => name !== "control_after_generate");
    const preCleanupSourceOrder = (
      preCleanupActiveOrder.includes("control_after_generate") &&
      vals.length === preCleanupWithoutSeedControl.length
    ) ? preCleanupWithoutSeedControl : preCleanupActiveOrder;
    const currentSourceOrder = (
      activeCurrentOrder.includes("control_after_generate") &&
      vals.length === activeWithoutSeedControl.length
    ) ? activeWithoutSeedControl : activeCurrentOrder;
    const candidates = [previousSourceOrder, preCleanupSourceOrder, currentSourceOrder];
    const sourceOrder = candidates.find((order) => valuesMatchOrder(vals, order.map((name, index) => [name, index]))) || currentSourceOrder;
    saveValues(namedValuesFromOrder(vals, sourceOrder), { preserveUnknownCanonical: true });
    return;
  }

  if (
    vals.length === activeWithoutSeedControl.length &&
    activeCurrentOrder.includes("control_after_generate") &&
    valuesMatchOrder(vals, activeWithoutSeedControl.map((name, index) => [name, index]))
  ) {
    saveValues(namedValuesFromOrder(vals, activeWithoutSeedControl), { preserveUnknownCanonical: true });
    return;
  }

  const legacyNamedValues = legacySchemaMigration(vals, expectedLength);
  if (legacyNamedValues) {
    saveValues(legacyNamedValues);
    return;
  }

  if (vals.length >= expectedLength) {
    saveValues(namedValuesFromOrder(vals.slice(0, expectedLength), WIDGET_ORDER), { preserveUnknownCanonical: true });
    return;
  }

  saveValues(namedValuesFromOrder(vals, activeCurrentOrder));
}


app.registerExtension({
  name: "Ultra.PromptStyler.Locale",
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "UltraPromptStyler") return;

    const origCreated = nodeType.prototype.onNodeCreated;
    const origConfigure = nodeType.prototype.onConfigure;
    const origAdded = nodeType.prototype.onAdded;

    nodeType.prototype.onNodeCreated = function () {
      const r = origCreated?.apply(this, arguments);
      localizeNode(this);
      scheduleLocalizeNode(this);
      return r;
    };

    nodeType.prototype.onConfigure = function (data) {
      migrateWidgetValuesForCurrentSchema(data, this);


      if (data?.widgets_values && Array.isArray(data.widgets_values)) {
        const names = getRuntimeWidgetOrder(this, data);
        for (let i = 0; i < data.widgets_values.length && i < names.length; i++) {
          const name = names[i];
          if (REVERSE[name] || name === "control_after_generate") {
            data.widgets_values[i] = toCanonical(name, data.widgets_values[i], { preserveUnknownCanonical: true });
          }
        }
      }
      const r = origConfigure?.apply(this, arguments);
      localizeNode(this);
      scheduleLocalizeNode(this);
      return r;
    };

    nodeType.prototype.onAdded = function () {
      const r = origAdded?.apply(this, arguments);
      localizeNode(this);
      scheduleLocalizeNode(this);
      return r;
    };
  },
});
