import { app } from "../../scripts/app.js";


// NOTE: 위젯 라벨(필드 이름) 번역은 ComfyUI 코어의 공식 i18n 메커니즘
// (locales/ko/nodeDefs.json)이 전담한다. 이 표는 그와 별개로 두 가지 용도로 쓰인다:
// 1) 콤보 옵션 값 번역 — 코어가 라벨은 번역해주지만 콤보 옵션 값(예: "adult
//    woman")까지는 아직 번역해주지 않아(2026-07 기준 실사용 확인), 이 JS가
//    patchComboValueTranslation()을 통해 최소한으로 보완한다.
// 2) 레거시 데이터 마이그레이션 — 과거 이 JS가 위젯 값을 한글 문자열로 직접
//    저장하던 시절의 옛 워크플로우를 불러올 때, canonical(영문) 값으로 되돌리기
//    위한 역참조 테이블(REVERSE)과 "이 필드에 허용되는 canonical 값 목록"
//    (optionKeys)의 데이터 소스이기도 하다.
const KO_LABELS = {
  model_profile: {
    "Z-Image Natural": "Z-Image 자연어",
    "Krea2 Natural": "Krea2 자연어",
    "Qwen Natural": "Qwen 자연어",
    "Flux Natural": "Flux 자연어",
    "Anima Mixed": "Anima 태그+문장",
    "SDXL Tag": "SDXL 태그형",
    "ILXL / Illustrious Tag": "ILXL / Illustrious 태그형",
    "Pony Tag": "Pony 태그형",
    "SD 1.5 Tag": "SD 1.5 태그형",
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
    "Vintage Film Look": "색바랜 필름 사진",
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
    auto: "선택 안함",
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
    auto: "선택 안함",
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
    "lace slip": "레이스 슬립",
    "satin lingerie": "새틴 란제리",
    "sheer blouse": "시스루 블라우스",
    "transparent robe": "투명 로브",
    "high-slit dress": "하이슬릿 드레스",
    "backless dress": "백리스 드레스",
    "deep v dress": "딥 브이 드레스",
    "bodycon dress": "바디콘 드레스",
    "wet shirt": "젖은 셔츠",
    "silk pajamas": "실크 파자마",
    "oversized sweater": "오버사이즈 스웨터",
    "stockings and garter": "스타킹 + 가터",
    "strappy lingerie": "스트랩 란제리",
    "lace bralette set": "레이스 브라렛 세트",
    "satin corset set": "새틴 코르셋 세트",
    "see-through cover-up": "시스루 커버업",
    "black lace lingerie": "블랙 레이스 란제리",
    "white button shirt": "화이트 버튼 셔츠",
    "black bodysuit": "블랙 바디수트",
    "red evening dress": "레드 이브닝 드레스",
    "satin slip dress": "새틴 슬립 드레스",
    "swimsuit cover-up": "수영복 커버업",
    "robe and lingerie": "로브 + 란제리",
  },
  scene_framing: {
    auto: "선택 안함",
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
    "Append style after external prompt": "원본 뒤에 추가",
    "Prepend style before external prompt": "스타일 앞에 배치",
    "Output style only": "스타일만 출력",
  },
  prompt_source_mode: {
    "Auto": "자동 전환",
    "External Prompt Composer": "연결 후 스타일 적용",
    "Standalone Scene Builder": "단독으로 만들기",
    "Style Only": "스타일만 출력",
  },
  builder_detail_mode: {
    "simple": "기본 메뉴",
    "advanced": "상세 메뉴",
    "professional": "전체 메뉴",
  },
  subject_profile: {
    "auto": "선택 안함",
    "adult woman": "성인 여성 1명",
    "adult man": "성인 남성 1명",
    "adult couple": "성인 커플 2명",
    "two adult women": "성인 여성 2명",
    "two adult men": "성인 남성 2명",
    "small adult group": "소규모 성인 그룹",
    "background only": "배경만 만들기",
    "product / object": "제품 / 사물",
  },
  subject_age: {
    "auto": "선택 안함",
    "20s": "20대",
    "30s": "30대",
    "40s": "40대",
    "50s": "50대",
    "60s+": "60대 이상",
    // Hidden legacy value: accepted/displayed only when an old workflow saved
    // the previous broad adult age. It is not inserted into new combo choices.
    "adult": "성인(기존 범용)",
  },
  subject_appearance: {
    "auto": "선택 안함",
    "natural-looking": "자연스러운",
    "cute": "귀여운",
    "beautiful": "아름다운",
    "elegant": "우아한",
    "glamorous": "화려한",
    "ordinary-looking": "평범한",
    "simple-looking": "수수한",
    "less conventionally attractive": "덜 예쁜",
    "distinctive-looking": "개성적인",
  },
  subject_ethnicity: {
    "auto": "선택 안함",
    "Korean": "한국인",
    "East Asian": "동아시아",
    "Southeast Asian": "동남아시아",
    "South Asian": "남아시아",
    "Western": "서양인",
    "Black": "흑인",
    "Latino": "라틴계",
    "Middle Eastern": "중동계",
    "mixed-heritage": "혼혈",
  },
  subject_hair: {
    "auto": "선택 안함",
    "short hair": "짧은 머리",
    "long dark hair": "긴 검은 머리",
    "long hair": "긴 머리",
    "wavy hair": "웨이브 머리",
    "bob cut": "단발",
    "ponytail": "포니테일",
    "updo": "업스타일",
    "straight long hair": "긴 생머리",
    "shoulder-length hair": "어깨 길이 머리",
    "medium-length hair": "중간 길이 머리",
    "layered hair": "레이어드 헤어",
    "side-parted hair": "가르마 탄 머리",
    "bangs": "앞머리",
    "braided hair": "땋은 머리",
    "twin braids": "양갈래 땋은 머리",
    "messy bun": "내추럴 번",
    "half-up hairstyle": "반묶음",
    "short bob": "짧은 단발",
    "pixie cut": "픽시컷",
    "curly hair": "곱슬머리",
    "wet hair": "젖은 머리",
    "wind-swept hair": "바람에 날리는 머리",
    "tied-back hair": "묶은 머리",
  },
  subject_outfit: {
    "auto": "선택 안함",
    "casual jeans and t-shirt": "캐주얼 티셔츠와 청바지",
    "white blouse and dark skirt": "흰 블라우스와 어두운 스커트",
    "knit sweater and skirt": "니트 스웨터와 스커트",
    "summer dress": "여름 원피스",
    "elegant long dress": "우아한 롱드레스",
    "business suit": "비즈니스 수트",
    "office blouse and slacks": "오피스 블라우스와 슬랙스",
    "hoodie and jeans": "후디와 청바지",
    "denim jacket outfit": "데님 재킷 코디",
    "trench coat outfit": "트렌치코트 코디",
    "winter coat and scarf": "겨울 코트와 머플러",
    "sportswear": "스포츠웨어",
    "swimwear / beachwear": "수영복 / 비치웨어",
    "traditional hanbok": "전통 한복",
    "simple black dress": "심플 블랙 드레스",
    "blouse and jeans": "블라우스와 청바지",
    "cardigan and skirt": "카디건과 스커트",
    "oversized knit sweater": "오버핏 니트 스웨터",
    "blazer and jeans": "블레이저와 청바지",
    "leather jacket outfit": "가죽 재킷 코디",
    "long coat outfit": "롱코트 코디",
    "cropped jacket outfit": "크롭 재킷 코디",
    "pleated skirt outfit": "플리츠 스커트 코디",
    "denim shorts and blouse": "데님 쇼츠와 블라우스",
    "linen shirt and trousers": "린넨 셔츠와 팬츠",
    "floral dress": "플로럴 원피스",
    "satin blouse and skirt": "새틴 블라우스와 스커트",
    "evening gown": "이브닝 가운",
    "cocktail dress": "칵테일 드레스",
    "business casual outfit": "비즈니스 캐주얼",
    "streetwear outfit": "스트리트웨어",
    "casual athleisure": "캐주얼 애슬레저",
    "yoga outfit": "요가복",
    "raincoat outfit": "레인코트 코디",
    "apron dress": "앞치마 원피스",
    "modern hanbok": "모던 한복",
    "pajamas / loungewear": "파자마 / 라운지웨어",
  },
  subject_expression: {
    "auto": "선택 안함",
    "natural expression": "자연스러운 표정",
    "gentle smile": "부드러운 미소",
    "broad smile": "함박웃음",
    "bright happy smile": "밝게 웃는 얼굴",
    "laughing face": "웃음 터진 얼굴",
    "soft closed-mouth smile": "입을 다문 은은한 미소",
    "shy smile": "수줍은 미소",
    "playful wink": "장난스러운 윙크",
    "confident smile": "자신감 있는 미소",
    "serious expression": "진지한 표정",
    "dreamy expression": "몽환적인 표정",
    "thoughtful expression": "생각에 잠긴 표정",
    "melancholic expression": "쓸쓸한 표정",
    "sad expression": "슬픈 표정",
    "tearful eyes": "눈물이 맺힌 눈",
    "crying face": "우는 얼굴",
    "lonely expression": "외로운 표정",
    "worried expression": "걱정스러운 표정",
    "anxious expression": "불안한 표정",
    "surprised expression": "놀란 표정",
    "angry expression": "화난 표정",
    "annoyed expression": "짜증난 표정",
    "pouting face": "삐진 얼굴",
    "sulky expression": "토라진 표정",
    "coy expression": "새침한 표정",
    "sassy expression": "도도한 표정",
    "smug expression": "능청스러운 표정",
    "embarrassed blush": "부끄러운 홍조",
    "tired expression": "피곤한 표정",
    "calm blank expression": "담담한 무표정",
    "determined expression": "결심한 표정",
    "seductive expression": "도발적인 표정",
  },
  subject_pose: {
    "auto": "선택 안함",
    "standing": "서 있는",
    "sitting": "앉아 있는",
    "leaning": "기대어 있는",
    "walking": "걷는",
    "looking back": "뒤돌아보는",
    "reclining": "기대어 누운",
    "lying down": "누워 있는",
    "standing with arms crossed": "팔짱 끼고 서 있음",
    "standing with hands on hips": "허리에 손을 얹고 서 있음",
    "standing with one hand in pocket": "한 손을 주머니에 넣고 서 있음",
    "hand near face": "손을 얼굴 근처에 둔",
    "hand on cheek": "손을 볼에 댄",
    "sitting cross-legged": "양반다리로 앉음",
    "seated sideways": "옆으로 앉음",
    "crouching": "쪼그려 앉음",
    "kneeling": "무릎 꿇은",
    "running": "달리는",
    "dancing": "춤추는",
    "jumping lightly": "가볍게 점프",
    "stretching": "스트레칭",
    "reaching upward": "위로 손을 뻗음",
    "turning sideways": "몸을 옆으로 튼",
    "side profile pose": "측면 프로필 포즈",
  },
  subject_action: {
    "auto": "선택 안함",
    "standing still": "가만히 서 있는",
    "sitting at a table": "테이블에 앉음",
    "walking naturally": "자연스럽게 걷기",
    "looking out the window": "창밖을 보는",
    "looking at the camera": "카메라 응시",
    "reading a book": "책 읽는",
    "using a phone": "휴대폰 보는",
    "working on a laptop": "노트북 작업",
    "drinking from a cup": "음료 마시는",
    "holding a flower bouquet": "꽃다발을 든",
    "carrying a handbag": "핸드백을 든",
    "taking a selfie": "셀피 촬영",
    "listening to music": "음악 듣는",
    "looking in a mirror": "거울 보는",
    "resting on a bed": "침대에 누운",
    "standing in water": "물가에 서 있는",
    "waiting at a station": "역에서 기다림",
    "shopping on a street": "거리에서 쇼핑",
    "opening curtains": "커튼을 여는",
    "cooking in kitchen": "주방에서 요리",
    "writing in a notebook": "노트에 글쓰기",
    "sketching in a notebook": "노트에 스케치",
    "applying makeup": "메이크업하는",
    "brushing hair": "머리를 빗는",
    "watering plants": "식물에 물 주기",
    "arranging flowers": "꽃을 정리하는",
    "browsing bookshelves": "책장을 둘러보는",
    "browsing a shop display": "상점 진열대를 둘러보는",
    "taking a photo": "사진을 찍는",
    "holding an umbrella": "우산을 든",
    "carrying a suitcase": "여행가방을 든",
    "playing guitar": "기타 연주",
    "dancing": "춤추는",
    "jogging": "조깅",
    "riding a bicycle": "자전거 타기",
    "stretching on a mat": "매트 위 스트레칭",
    "fixing hair": "머리를 정돈하는",
    "adjusting glasses": "안경을 고쳐 쓰는",
    "tying shoelaces": "신발끈 묶기",
    "looking down thoughtfully": "생각하며 아래를 보는",
    "smiling at someone": "누군가에게 미소 짓는",
    "talking with another person": "다른 사람과 대화",
    "waiting under rain": "비 속에서 기다림",
    "sitting by the window": "창가에 앉아 있음",
  },
  location_type: {
    "auto": "선택 안함",
    "cozy living room": "아늑한 거실",
    "modern apartment": "모던 아파트",
    "bedroom": "침실",
    "bathroom": "욕실",
    "hotel room": "호텔방",
    "cafe": "카페",
    "restaurant": "레스토랑",
    "office": "오피스",
    "library": "도서관",
    "bookstore": "서점",
    "kitchen": "주방",
    "art gallery": "아트 갤러리",
    "bar / lounge": "바 / 라운지",
    "balcony": "발코니",
    "rooftop": "옥상",
    "city street": "도시 거리",
    "shopping street": "쇼핑 거리",
    "alley": "골목",
    "train station": "기차역",
    "subway platform": "지하철 플랫폼",
    "park": "공원",
    "garden": "정원",
    "forest": "숲",
    "beach": "해변",
    "poolside": "수영장",
    "studio backdrop": "스튜디오 배경",
    "private studio": "프라이빗 스튜디오",
    "hanok room": "한옥 실내",
    "traditional Korean courtyard": "한옥 마당",
    "greenhouse": "온실",
    "museum": "박물관",
    "theater stage": "극장 무대",
    "dressing room": "드레싱룸",
    "makeup room": "메이크업룸",
    "photo studio": "촬영 스튜디오",
    "hotel lobby": "호텔 로비",
    "corridor hallway": "복도",
    "elevator lobby": "엘리베이터 로비",
    "convenience store": "편의점",
    "supermarket": "슈퍼마켓",
    "bakery": "베이커리",
    "flower shop": "꽃집",
    "salon": "살롱",
    "gym": "헬스장",
    "yoga studio": "요가 스튜디오",
    "airport terminal": "공항 터미널",
    "riverside walkway": "강변 산책로",
    "bridge": "다리 위",
    "lake shore": "호숫가",
    "mountain trail": "산길",
    "campsite": "캠프장",
    "parking garage": "주차장",
    "night market": "야시장",
    "indoor pool": "실내 수영장",
    "laundromat": "셀프 빨래방",
  },
  location_detail: {
    "auto": "선택 안함",
    "minimal modern": "미니멀 / 모던",
    "luxury": "럭셔리",
    "vintage classic": "빈티지 클래식",
    "dark intimate": "어둡고 친밀한",
    "bright spacious": "밝고 넓은",
    "natural organic": "자연스러운",
    "cozy warm": "따뜻하고 아늑한",
    "cinematic": "시네마틱",
    "soft romantic": "부드러운 로맨틱",
    "moody low-key": "무디한 로우키",
    "rainy urban": "비 오는 도시감",
    "rustic worn": "낡고 러스틱한",
    "cluttered lived-in": "생활감 있는",
    "clean minimal": "깔끔한 미니멀",
    "premium hotel": "프리미엄 호텔감",
    "traditional Korean": "전통 한국적",
    "industrial": "인더스트리얼",
    "futuristic neon": "미래적 네온",
    "soft pastel": "소프트 파스텔",
    "high-contrast dramatic": "강한 대비의 드라마틱",
  },
  time_of_day: {
    "auto": "선택 안함",
    "dawn": "새벽",
    "morning": "아침",
    "daytime": "낮",
    "afternoon": "오후",
    "late afternoon": "늦은 오후",
    "evening": "저녁",
    "sunset": "석양",
    "night": "밤",
    "late night": "늦은 밤",
  },
  weather_light: {
    "auto": "선택 안함",
    "clear": "맑음",
    "cloudy": "흐림",
    "rainy": "비",
    "snowy": "눈",
    "foggy": "안개",
    "indoor lighting only": "실내 조명만",
    "soft indoor lighting": "부드러운 실내 조명",
    "golden hour sunlight": "골든아워 햇빛",
    "sunset backlight": "석양 역광",
    "moonlight": "달빛",
    "neon lights": "네온 조명",
    "window light": "창문빛",
    "strong sunlight": "강한 햇빛",
    "overcast soft light": "흐린 날 확산광",
    "backlit silhouette": "역광 실루엣",
    "low-key lighting": "로우키 조명",
    "rim light": "림라이트",
    "candlelight": "촛불",
    "fluorescent indoor light": "형광등 실내광",
    "streetlights": "가로등",
    "rainy neon reflections": "비 오는 네온 반사",
  },
  scene_props: {
    "auto": "선택 안함",
    "none": "없음",
    "plants": "식물",
    "book / magazine": "책 / 잡지",
    "cup / drink": "컵 / 음료",
    "smartphone": "스마트폰",
    "lamp": "조명",
    "mirror": "거울",
    "umbrella": "우산",
    "studio lighting": "스튜디오 조명",
    "luxury interior details": "럭셔리 인테리어",
    "cosmetic product": "화장품 제품",
    "laptop": "노트북",
    "flower bouquet": "꽃다발",
    "handbag": "핸드백",
    "shopping bag": "쇼핑백",
    "camera": "카메라",
    "suitcase": "여행가방",
    "headphones": "헤드폰",
    "tableware": "식기 / 테이블웨어",
    "window": "창문",
    "curtains": "커튼",
    "sofa": "소파",
    "chair": "의자",
    "desk": "책상",
    "bed": "침대",
    "bookshelf": "책장",
    "picture frames": "액자",
    "potted plants": "화분",
    "vase": "꽃병",
    "flowers": "꽃",
    "notebook and pen": "노트와 펜",
    "art supplies": "미술 도구",
    "makeup tools": "메이크업 도구",
    "perfume bottle": "향수병",
    "blanket / fabric": "담요 / 천",
    "pillows": "베개",
    "street signs": "거리 표지판",
    "neon signs": "네온 간판",
    "bench": "벤치",
    "bicycle": "자전거",
    "food / dessert": "음식 / 디저트",
    "display shelves": "진열대",
    "shopping cart": "쇼핑 카트",
    "luggage": "짐가방",
    "train doors": "전철 문",
    "guitar": "기타",
    "microphone": "마이크",
  },
  auto_extra_detail: {
    "auto": "보강 안함",
    "light auto fill": "안전 보강",
    "balanced auto fill": "균형 보강",
    "rich auto fill": "풍부한 배경 보강",
  },
  adult_menu_level: {
    "essential": "기본 메뉴",
    "professional": "모든 단독 메뉴",
  },
  adult_exposure_level: {
    "auto": "선택 안함",
    "clothed sensual": "옷을 입은 관능",
    "revealing outfit": "노출 있는 의상",
    "lingerie / underwear": "란제리 / 속옷",
    "swimwear": "수영복",
    "implied nude / covered": "암시적 누드 / 가림",
    "sheet-covered nude": "시트로 가린 누드",
    "nude": "누드",
    "topless": "상의 탈의",
    "wet look swimwear": "젖은 느낌 수영복",
    "bodycon fashion": "바디콘 패션",
  },
  adult_scene_privacy: {
    "auto": "선택 안함",
    "private indoor": "사적인 실내",
    "bedroom / hotel room": "침실 / 호텔방",
    "boudoir bedroom": "부두아르 침실",
    "luxury hotel suite": "럭셔리 호텔 스위트",
    "private lounge": "프라이빗 라운지",
    "studio": "스튜디오",
    "dressing room": "드레싱룸",
    "bathroom": "욕실",
    "spa / bath": "스파 / 목욕",
    "poolside / beach": "수영장 / 해변",
  },
  adult_scene_mood: {
    "auto": "선택 안함",
    "soft boudoir": "소프트 부두아르",
    "romantic warm intimacy": "따뜻한 로맨틱 친밀감",
    "fashion editorial sensual": "패션 화보식 관능",
    "luxury hotel evening": "럭셔리 호텔의 저녁",
    "private mirror moment": "사적인 거울 장면",
    "noir intimate": "누아르 친밀감",
    "spa calm": "스파처럼 차분한",
    "poolside glamour": "풀사이드 글래머",
    "beach sunset sensual": "해변 석양 관능",
    "studio glamour": "스튜디오 글래머",
    "cozy morning softness": "부드러운 아침 분위기",
    "after-bath softness": "목욕 후 부드러움",
    "midnight hotel intimacy": "한밤의 호텔 친밀감",
    "soft lingerie editorial": "소프트 란제리 화보",
    "warm sheet-covered mood": "따뜻한 시트 커버 분위기",
    "fine-art nude calm": "파인아트 누드 차분함",
    "private dressing-room mood": "사적인 드레싱룸 분위기",
    "mirror-lit sensuality": "거울빛 관능",
    "rainy-window intimacy": "비 오는 창가 친밀감",
    "candlelit romantic privacy": "촛불 로맨틱 프라이버시",
    "glossy fashion sensuality": "글로시 패션 관능",
    "quiet teasing mood": "조용히 장난스러운 분위기",
  },
  adult_pose_style: {
    "auto": "선택 안함",
    "relaxed sensual pose": "편안한 관능 포즈",
    "reclining sensual pose": "기대어 누운 관능 포즈",
    "seated sensual pose": "앉은 관능 포즈",
    "standing confident pose": "당당하게 서 있는 포즈",
    "looking over shoulder": "어깨 너머로 돌아봄",
    "intimate portrait pose": "친밀한 인물 포즈",
    "sitting on bed edge": "침대 가장자리에 앉음",
    "lying on side": "옆으로 누움",
    "wrapped in sheets": "시트에 감싸인 포즈",
    "standing by mirror": "거울 옆에 서 있음",
    "leaning against wall": "벽에 기대어 있음",
    "adjusting robe": "로브를 정돈함",
    "poolside lounging": "풀사이드에 기대어 쉼",
    "back turned silhouette": "뒤돌아선 실루엣",
    "seated on floor": "바닥에 앉은 포즈",
    "kneeling portrait pose": "무릎 꿇은 인물 포즈",
    "sitting by window": "창가에 앉은 포즈",
    "lying on stomach": "엎드린 포즈",
    "stretching on bed": "침대 위 스트레칭",
    "hands in hair": "머리에 손을 얹은",
    "covering with sheet": "시트로 가린",
    "holding robe closed": "로브를 여민",
    "side-profile silhouette": "측면 실루엣",
    "seated mirror pose": "거울 옆에 앉은 포즈",
    "one leg bent pose": "한쪽 다리를 굽힌 포즈",
    "soft arched pose": "부드러운 아치형 포즈",
    "hands near collarbone": "쇄골 근처에 손",
    "looking down softly": "부드럽게 아래를 봄",
    "turning away with glance": "돌아서며 시선만 돌림",
  },
  adult_lighting: {
    "auto": "선택 안함",
    "warm bedside light": "따뜻한 침대 조명",
    "low-key shadow": "로우키 그림자",
    "soft window backlight": "부드러운 창가 역광",
    "candlelit glow": "촛불 느낌",
    "studio rim light": "스튜디오 림라이트",
    "neon lounge light": "네온 라운지 조명",
    "steamy bathroom light": "김 서린 욕실 조명",
    "sunset backlight": "석양 역광",
    "warm window glow": "따뜻한 창문빛",
    "moonlit room": "달빛 방",
    "rainy window light": "비 오는 창문빛",
    "bathroom mirror light": "욕실 거울 조명",
    "soft vanity lights": "부드러운 화장대 조명",
    "hotel lamp glow": "호텔 램프 조명",
    "silhouette backlight": "실루엣 역광",
    "high-key studio glamour": "하이키 스튜디오 글래머",
    "softbox glow": "소프트박스 광",
    "colored gel rim light": "컬러 젤 림라이트",
  },
  adult_scene_props: {
    "auto": "선택 안함",
    "satin sheets": "새틴 시트",
    "sheer curtains": "시스루 커튼",
    "bedside lamp": "침대 옆 조명",
    "large mirror": "큰 거울",
    "velvet chair": "벨벳 의자",
    "silk fabric": "실크 천",
    "candles": "촛불",
    "bath steam": "욕실 수증기",
    "pool reflection": "수영장 반사광",
    "studio softbox": "스튜디오 소프트박스",
    "curtains and pillows": "커튼과 베개",
    "robe": "로브",
    "towel": "수건",
    "vanity table": "화장대",
    "makeup mirror": "메이크업 거울",
    "perfume bottle": "향수병",
    "glass shower": "유리 샤워부스",
    "bathtub edge": "욕조 가장자리",
    "lace curtains": "레이스 커튼",
    "soft rug": "부드러운 러그",
    "dressing screen": "드레싱 스크린",
    "window curtains": "창가 커튼",
    "silk pillow": "실크 베개",
    "jewelry tray": "주얼리 트레이",
    "floor cushion": "바닥 쿠션",
  },
  adult_body_focus: {
    "auto": "선택 안함",
    "face and expression": "얼굴과 표정",
    "upper body elegance": "상반신 우아함",
    "full body silhouette": "전신 실루엣",
    "legs-focused fashion framing": "다리 중심 패션 구도",
    "back and shoulder silhouette": "등과 어깨 실루엣",
    "hands and fabric detail": "손과 천 디테일",
    "non-graphic body line": "비노골적 바디 라인",
    "face with hands": "얼굴과 손",
    "neckline and shoulders": "목선과 어깨",
    "waist silhouette": "허리 실루엣",
    "fabric-covered form": "천으로 가린 형태",
    "profile body line": "측면 바디 라인",
    "hair and shoulder line": "머리와 어깨선",
    "mirror reflection focus": "거울 반사 강조",
  },
  adult_framing_bias: {
    "auto": "선택 안함",
    "portrait safe": "안전한 인물 구도",
    "close portrait": "가까운 인물",
    "upper body": "상반신",
    "waist-up": "허리 위",
    "full body": "전신",
    "tasteful silhouette": "품위 있는 실루엣",
    "editorial full body": "화보식 전신",
    "fabric detail close-up": "천 디테일 클로즈업",
    "body-focused non-graphic": "몸 중심 / 비노골적",
  },
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
  "prompt_source_mode",
  "builder_detail_mode",
  "external_prompt_mode",
  "subject_profile",
  "subject_age",
  "subject_appearance",
  "subject_ethnicity",
  "subject_hair",
  "subject_outfit",
  "subject_expression",
  "subject_pose",
  "subject_action",
  "location_type",
  "location_detail",
  "time_of_day",
  "weather_light",
  "scene_props",
  "auto_extra_detail",
  "adult_menu_level",
  "adult_exposure_level",
  "adult_scene_privacy",
  "adult_scene_mood",
  "adult_pose_style",
  "adult_lighting",
  "adult_scene_props",
  "adult_body_focus",
  "adult_framing_bias",
  "seed",
  "control_after_generate",
  "custom_text",
];

const PRE_APPEARANCE_WIDGET_ORDER = [
  "model_profile",
  "mood_family",
  "style_dna",
  "style_strength",
  "style_conflict_cleanup",
  "scene_framing",
  "lens_preset",
  "adult_tone",
  "adult_wardrobe",
  "prompt_source_mode",
  "builder_detail_mode",
  "external_prompt_mode",
  "subject_profile",
  "subject_age",
  "subject_ethnicity",
  "subject_hair",
  "subject_outfit",
  "subject_expression",
  "subject_pose",
  "subject_action",
  "location_type",
  "location_detail",
  "time_of_day",
  "weather_light",
  "scene_props",
  "auto_extra_detail",
  "adult_menu_level",
  "adult_exposure_level",
  "adult_scene_privacy",
  "adult_scene_mood",
  "adult_pose_style",
  "adult_lighting",
  "adult_scene_props",
  "adult_body_focus",
  "adult_framing_bias",
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

// Full schema saved by earlier JS builds that placed the three prompt-source
// controls immediately after model_profile.  Keep this as a legacy candidate
// only; WIDGET_ORDER above must mirror the Python INPUT_TYPES order.
const LEGACY_PROMPT_CONTROLS_EARLY_WIDGET_ORDER = [
  "model_profile",
  "prompt_source_mode",
  "builder_detail_mode",
  "external_prompt_mode",
  "mood_family",
  "style_dna",
  "style_strength",
  "style_conflict_cleanup",
  "scene_framing",
  "lens_preset",
  "adult_tone",
  "adult_wardrobe",
  "subject_profile",
  "subject_age",
  "subject_ethnicity",
  "subject_hair",
  "subject_outfit",
  "subject_expression",
  "subject_pose",
  "subject_action",
  "location_type",
  "location_detail",
  "time_of_day",
  "weather_light",
  "scene_props",
  "auto_extra_detail",
  "adult_menu_level",
  "adult_exposure_level",
  "adult_scene_privacy",
  "adult_scene_mood",
  "adult_pose_style",
  "adult_lighting",
  "adult_scene_props",
  "adult_body_focus",
  "adult_framing_bias",
  "seed",
  "control_after_generate",
  "custom_text",
];

// Full-schema legacy order with prompt-source controls near the front and
// external_prompt_mode before builder_detail_mode.  Used only after positional
// value validation, never as the current schema.
const PRE_REORDER_WIDGET_ORDER = [
  "model_profile",
  "prompt_source_mode",
  "external_prompt_mode",
  "builder_detail_mode",
  "mood_family",
  "style_dna",
  "style_strength",
  "style_conflict_cleanup",
  "scene_framing",
  "lens_preset",
  "adult_tone",
  "adult_wardrobe",
  "subject_profile",
  "subject_age",
  "subject_ethnicity",
  "subject_hair",
  "subject_outfit",
  "subject_expression",
  "subject_pose",
  "subject_action",
  "location_type",
  "location_detail",
  "time_of_day",
  "weather_light",
  "scene_props",
  "auto_extra_detail",
  "adult_menu_level",
  "adult_exposure_level",
  "adult_scene_privacy",
  "adult_scene_mood",
  "adult_pose_style",
  "adult_lighting",
  "adult_scene_props",
  "adult_body_focus",
  "adult_framing_bias",
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

const BASIC_STANDALONE_WIDGETS = new Set([
  "builder_detail_mode",
  "subject_profile",
  "subject_pose",
  "subject_action",
  "location_type",
  "auto_extra_detail",
]);

const ADVANCED_STANDALONE_WIDGETS = new Set([
  "subject_age",
  "subject_appearance",
  "subject_ethnicity",
  "subject_hair",
  "subject_outfit",
  "subject_expression",
  "location_detail",
  "time_of_day",
  "weather_light",
  "scene_props",
]);

const STANDALONE_WIDGETS = new Set([
  ...BASIC_STANDALONE_WIDGETS,
  ...ADVANCED_STANDALONE_WIDGETS,
]);

const ADULT_MENU_WIDGETS = new Set([
  "adult_menu_level",
]);

const ADULT_ESSENTIAL_WIDGETS = new Set([
  "adult_exposure_level",
  "adult_scene_privacy",
  "adult_scene_mood",
]);

const ADULT_PRO_WIDGETS = new Set([
  "adult_pose_style",
  "adult_lighting",
  "adult_scene_props",
  "adult_body_focus",
  "adult_framing_bias",
]);

const ADULT_STANDALONE_WIDGETS = new Set([
  ...ADULT_MENU_WIDGETS,
  ...ADULT_ESSENTIAL_WIDGETS,
  ...ADULT_PRO_WIDGETS,
]);

function findWidgetByCanonical(node, name) {
  return (node?.widgets || []).find((w) => (w?._ultraCanonicalName || w?.name) === name);
}

function widgetCanonicalValue(node, name) {
  const w = findWidgetByCanonical(node, name);
  if (!w) return CURRENT_WIDGET_DEFAULTS[name];
  return toCanonical(name, w.value, { preserveUnknownCanonical: true });
}

const EXTERNAL_POSITIVE_INPUT_INDEX = 0;

function inputOriginalName(input) {
  return String(input?.name || "").trim();
}

function isExternalPositiveInput(node, input, slotIndex = null) {
  if (!input) return false;
  if (inputOriginalName(input) === "external_positive_in") return true;
  if (Number.isInteger(slotIndex)) return slotIndex === EXTERNAL_POSITIVE_INPUT_INDEX;
  return Array.isArray(node?.inputs) && node.inputs[EXTERNAL_POSITIVE_INPUT_INDEX] === input;
}

function findExternalPositiveInput(node) {
  if (!Array.isArray(node?.inputs)) return null;
  return node.inputs.find((input, index) => isExternalPositiveInput(node, input, index)) || null;
}

function externalPositiveLinked(node) {
  const input = findExternalPositiveInput(node);
  if (input == null) return false;
  // Store-backed frontends (1.55+): input.link is a deprecated view.
  if (typeof node?.isInputConnected === "function") {
    if (!node.graph) return false;
    const slot = node.inputs.indexOf(input);
    try { return slot >= 0 && node.isInputConnected(slot); } catch (_) { return false; }
  }
  if (input.link == null) return false;

  const rawLink = input.link;
  const linkId = (typeof rawLink === "object" && rawLink !== null)
    ? (rawLink.id ?? rawLink.link_id ?? rawLink.linkId)
    : rawLink;
  const graph = node?.graph || globalThis?.app?.graph;

  if (graph?.links != null && (typeof linkId === "number" || typeof linkId === "string")) {
    const links = graph.links;
    if (Array.isArray(links)) {
      return links.some((link) => link && String(link.id ?? link.link_id ?? link.linkId) === String(linkId));
    }
    return links[linkId] != null || links[String(linkId)] != null;
  }

  return true;
}

function connectionEventLooksLikeExternalPositive(node, argsLike) {
  const args = Array.from(argsLike || []);
  const typeArg = args[0];
  const connectedArg = args[2];
  const lgInput = globalThis?.LiteGraph?.INPUT;
  const lgOutput = globalThis?.LiteGraph?.OUTPUT;
  const typeLooksInput = (
    typeArg === "input" || typeArg === "INPUT" ||
    (lgInput != null && typeArg === lgInput) ||
    (lgInput == null && (typeArg === 1 || typeArg === "1"))
  );
  const typeLooksOutput = (
    typeArg === "output" || typeArg === "OUTPUT" ||
    (lgOutput != null && typeArg === lgOutput) ||
    (lgInput == null && (typeArg === 2 || typeArg === "2"))
  );
  if (typeLooksOutput) return false;
  if ((typeLooksInput || args.length >= 3) && connectedArg === false) return false;

  const slotCandidates = [];
  for (const arg of args) {
    if (Number.isInteger(arg)) slotCandidates.push(arg);
    if (arg && typeof arg === "object") {
      if (Number.isInteger(arg.slot)) slotCandidates.push(arg.slot);
      if (Number.isInteger(arg.target_slot)) slotCandidates.push(arg.target_slot);
      if (Number.isInteger(arg.input_slot)) slotCandidates.push(arg.input_slot);
      if (isExternalPositiveInput(node, arg)) return true;
      if (arg.input && isExternalPositiveInput(node, arg.input)) return true;
      if (arg.target && isExternalPositiveInput(node, arg.target)) return true;
    }
  }
  if ((typeLooksInput || args.length < 3) && slotCandidates.includes(EXTERNAL_POSITIVE_INPUT_INDEX)) return true;
  return externalPositiveLinked(node);
}

function standaloneUiActive(node) {
  const mode = widgetCanonicalValue(node, "prompt_source_mode");
  if (mode === "Standalone Scene Builder") return true;
  if (mode === "External Prompt Composer" || mode === "Style Only") return false;
  return !externalPositiveLinked(node);
}

function adultStandaloneUiActive(node) {
  if (!standaloneUiActive(node)) return false;
  const tone = widgetCanonicalValue(node, "adult_tone");
  const wardrobe = widgetCanonicalValue(node, "adult_wardrobe");
  const exposure = widgetCanonicalValue(node, "adult_exposure_level");
  const privacy = widgetCanonicalValue(node, "adult_scene_privacy");
  const mood = widgetCanonicalValue(node, "adult_scene_mood");
  const pose = widgetCanonicalValue(node, "adult_pose_style");
  const lighting = widgetCanonicalValue(node, "adult_lighting");
  const props = widgetCanonicalValue(node, "adult_scene_props");
  const focus = widgetCanonicalValue(node, "adult_body_focus");
  const framing = widgetCanonicalValue(node, "adult_framing_bias");
  return ["romantic non-explicit", "suggestive", "sensual", "bold sensual", "nsfw", "explicit nsfw"].includes(tone)
    || wardrobe !== "auto"
    || exposure !== "auto"
    || privacy !== "auto"
    || mood !== "auto"
    || pose !== "auto"
    || lighting !== "auto"
    || props !== "auto"
    || focus !== "auto"
    || framing !== "auto";
}

function setWidgetVisible(widget, visible) {
  if (!widget || isConvertedWidget(widget)) return;

  if (!widget._ultraVisibilitySaved) {
    widget._ultraOriginalComputeSize = widget.computeSize;
    widget._ultraOriginalDraw = widget.draw;
    widget._ultraOriginalDisabled = widget.disabled;
    widget._ultraVisibilitySaved = true;
  }

  if (visible) {
    widget.visible = true;
    widget.hidden = false;
    widget.disabled = widget._ultraOriginalDisabled ?? false;
    widget.computeSize = widget._ultraOriginalComputeSize;
    if (widget._ultraOriginalDraw) widget.draw = widget._ultraOriginalDraw;
    else {
      try { delete widget.draw; } catch (_) { widget.draw = undefined; }
    }
  } else {
    widget.visible = false;
    widget.hidden = true;
    widget.disabled = true;
    widget.computeSize = () => [0, 0];
    widget.draw = () => {};
  }
}

const ALWAYS_VISIBLE_INPUT_SLOTS = new Set([
  "external_positive_in",
  "external_negative_in",
  "positive_prompt",
  "negative_prompt",
]);

function canonicalInputSlotName(input) {
  const raw = input?.widget?.name
    ?? input?.widget_name
    ?? input?.widgetName
    ?? input?.widget?.options?.name
    ?? input?.name
    ?? input?.label
    ?? "";
  return String(raw || "").trim();
}

const MANAGED_WIDGET_INPUT_SLOTS = new Set([
  ...WIDGET_ORDER,
  ...ALWAYS_VISIBLE_INPUT_SLOTS,
]);

function inputLinkId(input) {
  // Store-backed frontends (1.55+): ask the owning node instead of reading the
  // deprecated input.link view.
  const owner = input?._node;
  if (owner && typeof owner.getInputLink === "function" && Array.isArray(owner.inputs)) {
    if (!owner.graph) return null;
    const slot = owner.inputs.indexOf(input);
    if (slot >= 0) {
      try { return owner.getInputLink(slot)?.id ?? null; } catch (_) { return null; }
    }
  }
  const raw = input?.link;
  if (raw == null) return null;
  if (typeof raw === "object") return raw.id ?? raw.link_id ?? raw.linkId ?? null;
  return raw;
}

function findGraphLinkById(graph, linkId) {
  if (linkId == null || !graph?.links) return null;
  if (typeof graph.getLink === "function") {
    const found = graph.getLink(linkId) ?? graph.getLink(Number(linkId));
    if (found) return found;
  }
  const links = graph.links;
  if (Array.isArray(links)) {
    return links.find((link) => link && String(link.id ?? link[0] ?? link.link_id ?? link.linkId) === String(linkId)) || null;
  }
  if (typeof links.get === "function") return links.get(linkId) || links.get(Number(linkId)) || null;
  return links[linkId] || links[String(linkId)] || null;
}

function graphLinkTargetsNode(link, node) {
  if (!link || node?.id == null) return true;
  if (Array.isArray(link)) return String(link[3]) === String(node.id);
  const rawTarget = link.target_id ?? link.targetId ?? link.target_node_id ?? link.target;
  const targetId = (rawTarget && typeof rawTarget === "object") ? rawTarget.id : rawTarget;
  return targetId == null || String(targetId) === String(node.id);
}

function inputHasLiveOrSerializedLink(node, input) {
  const linkId = inputLinkId(input);
  if (linkId == null) return false;
  const graph = node?.graph || globalThis?.app?.graph;
  const link = findGraphLinkById(graph, linkId);
  if (link) return graphLinkTargetsNode(link, node);
  // During onConfigure the graph link table may not be available yet.  In that
  // early phase a non-null input.link must be treated as meaningful so a saved
  // connection is not discarded before LiteGraph finishes configuring links.
  return !graph?.links;
}

function managedInputSlotName(input) {
  const name = canonicalInputSlotName(input);
  return MANAGED_WIDGET_INPUT_SLOTS.has(name) ? name : "";
}

function shouldPreferManagedInput(node, previous, candidate) {
  if (!previous) return true;
  if (!candidate) return false;
  const prevLinked = inputHasLiveOrSerializedLink(node, previous);
  const candLinked = inputHasLiveOrSerializedLink(node, candidate);
  if (candLinked && !prevLinked) return true;
  if (prevLinked && !candLinked) return false;
  return false;
}

function compactManagedInputArray(node, inputs) {
  if (!Array.isArray(inputs) || !inputs.length) return [];
  const out = [];
  const seenObjects = new Set();
  const managedByName = new Map();

  for (const input of inputs) {
    if (!input || seenObjects.has(input)) continue;
    const name = managedInputSlotName(input);
    if (!name) {
      seenObjects.add(input);
      out.push(input);
      continue;
    }

    const existing = managedByName.get(name);
    if (!existing) {
      managedByName.set(name, { input, index: out.length });
      input._ultraDuplicateManagedInput = false;
      seenObjects.add(input);
      out.push(input);
      continue;
    }

    if (shouldPreferManagedInput(node, existing.input, input)) {
      existing.input._ultraDuplicateManagedInput = true;
      seenObjects.delete(existing.input);
      out[existing.index] = input;
      managedByName.set(name, { input, index: existing.index });
      input._ultraDuplicateManagedInput = false;
      seenObjects.add(input);
    } else {
      input._ultraDuplicateManagedInput = true;
    }
  }

  return out;
}

function updateGraphTargetSlotsForVisibleInputs(node) {
  if (!node || !Array.isArray(node.inputs)) return;
  const graph = node.graph || globalThis?.app?.graph;
  if (!graph?.links) return;

  for (let slot = 0; slot < node.inputs.length; slot++) {
    const input = node.inputs[slot];
    const linkId = inputLinkId(input);
    if (linkId == null) continue;
    const link = findGraphLinkById(graph, linkId);
    if (!link || !graphLinkTargetsNode(link, node)) continue;
    if (Array.isArray(link)) link[4] = slot;
    else {
      link.target_slot = slot;
      if (Object.prototype.hasOwnProperty.call(link, "targetSlot")) link.targetSlot = slot;
    }
  }
}

function dedupeManagedInputSlots(node) {
  if (!node || !Array.isArray(node.inputs)) return false;
  const current = node.inputs;
  const compact = compactManagedInputArray(node, current);
  let changed = compact.length !== current.length;
  if (!changed) {
    for (let i = 0; i < compact.length; i++) {
      if (compact[i] !== current[i]) { changed = true; break; }
    }
  }
  if (changed) {
    node.inputs = compact;
    updateGraphTargetSlotsForVisibleInputs(node);
  }
  return changed;
}

function collectHiddenStandaloneWidgetNames(node) {
  const hidden = new Set();
  for (const widget of node?.widgets || []) {
    if (!widget || isConvertedWidget(widget)) continue;
    const canonical = widget?._ultraCanonicalName || widget?.name;
    if (!canonical) continue;
    if (widget.visible === false || widget.hidden === true || widget.disabled === true) {
      hidden.add(canonical);
    }
  }
  return hidden;
}

function captureWidgetInputRegistry(node) {
  if (!node || !Array.isArray(node.inputs)) return [];
  const existing = Array.isArray(node._ultraWidgetInputRegistry) ? node._ultraWidgetInputRegistry : [];
  // Merge the old registry and current runtime inputs, but keep only one slot
  // object per managed input name.  This prevents the registry itself from
  // becoming a hidden duplicate factory after repeated configure/refresh cycles.
  const registry = compactManagedInputArray(node, [...existing, ...node.inputs]);
  node._ultraWidgetInputRegistry = registry;
  return registry;
}

function syncHiddenWidgetInputSlots(node) {
  if (!node || !Array.isArray(node.inputs)) return;
  dedupeManagedInputSlots(node);
  const registry = captureWidgetInputRegistry(node);
  if (!registry.length) return;

  const hiddenNames = collectHiddenStandaloneWidgetNames(node);
  const visibleInputs = [];
  const currentInputs = Array.isArray(node.inputs) ? node.inputs : [];
  const pushedInputs = new Set();
  const keptManagedByName = new Map();

  function managedInputMustRemainVisible(input) {
    const name = canonicalInputSlotName(input);
    if (!managedInputSlotName(input)) return true;
    if (ALWAYS_VISIBLE_INPUT_SLOTS.has(name)) return true;
    if (inputHasLiveOrSerializedLink(node, input)) return true;
    return !hiddenNames.has(name);
  }

  function pushVisibleInput(input) {
    if (!input || pushedInputs.has(input)) return;
    const name = managedInputSlotName(input);
    if (name) {
      const previous = keptManagedByName.get(name);
      if (previous) {
        // Keep exactly one visible input per managed widget/input name.  The
        // preferred object is the one with a live/saved link; otherwise the
        // earliest object is retained to preserve native LiteGraph slot order.
        if (shouldPreferManagedInput(node, previous, input)) {
          const idx = visibleInputs.indexOf(previous);
          if (idx >= 0) visibleInputs[idx] = input;
          pushedInputs.delete(previous);
          previous._ultraDuplicateManagedInput = true;
          keptManagedByName.set(name, input);
          pushedInputs.add(input);
          input._ultraDuplicateManagedInput = false;
        } else {
          input._ultraDuplicateManagedInput = true;
        }
        return;
      }
      keptManagedByName.set(name, input);
      input._ultraDuplicateManagedInput = false;
    }
    pushedInputs.add(input);
    visibleInputs.push(input);
  }

  for (const input of registry) {
    if (!input) continue;
    if (managedInputMustRemainVisible(input)) {
      input._ultraHiddenByWidgetVisibility = false;
      pushVisibleInput(input);
    } else {
      // Remove only the unlinked widget-input slot from node.inputs so LiteGraph
      // cannot draw it as a connection candidate during wire dragging.  The slot
      // object is kept in a name-deduped runtime registry and restored only when
      // the corresponding widget becomes visible again.  We intentionally do
      // not force geometry, install resize/draw hooks, or edit input coords.
      input._ultraHiddenByWidgetVisibility = true;
    }
  }

  // Some ComfyUI builds create widget-input slots after our registry pass.
  // Apply both visibility and name de-duplication to those late objects instead
  // of letting them survive as one-frame or saved ghost inputs.
  for (const input of currentInputs) {
    if (input && !registry.includes(input)) {
      if (managedInputMustRemainVisible(input)) {
        input._ultraHiddenByWidgetVisibility = false;
        pushVisibleInput(input);
      } else {
        input._ultraHiddenByWidgetVisibility = true;
      }
    }
  }

  let changed = visibleInputs.length !== currentInputs.length;
  if (!changed) {
    for (let i = 0; i < visibleInputs.length; i++) {
      if (visibleInputs[i] !== currentInputs[i]) { changed = true; break; }
    }
  }
  if (changed) {
    node.inputs = visibleInputs;
    updateGraphTargetSlotsForVisibleInputs(node);
  }
}
function refreshStandaloneVisibility(node) {
  if (!node || !Array.isArray(node.widgets)) return;
  const showStandalone = standaloneUiActive(node);
  const adultTriggered = adultStandaloneUiActive(node);
  const detailMode = widgetCanonicalValue(node, "builder_detail_mode");
  const adultMenuLevel = widgetCanonicalValue(node, "adult_menu_level") || "essential";
  const showAllStandalone = showStandalone && detailMode === "professional";
  const showGeneralAdvanced = showStandalone && (detailMode === "advanced" || showAllStandalone);
  const showAdultMenu = showStandalone && (adultTriggered || showAllStandalone);
  const showAdultEssential = showAdultMenu && (adultMenuLevel === "essential" || adultMenuLevel === "professional");
  const showAdultProfessional = showAdultMenu && adultMenuLevel === "professional";

  for (const widget of node.widgets) {
    const canonical = widget?._ultraCanonicalName || widget?.name;
    if (BASIC_STANDALONE_WIDGETS.has(canonical)) setWidgetVisible(widget, showStandalone);
    if (ADVANCED_STANDALONE_WIDGETS.has(canonical)) setWidgetVisible(widget, showGeneralAdvanced);
    if (ADULT_MENU_WIDGETS.has(canonical)) setWidgetVisible(widget, showAdultMenu);
    if (ADULT_ESSENTIAL_WIDGETS.has(canonical)) setWidgetVisible(widget, showAdultEssential);
    if (ADULT_PRO_WIDGETS.has(canonical)) setWidgetVisible(widget, showAdultProfessional);
    if (canonical === "external_prompt_mode") setWidgetVisible(widget, !showStandalone);
  }
  syncHiddenWidgetInputSlots(node);

  // Visibility changes are expressed through each widget's own visible/hidden
  // state and computeSize.  Let ComfyUI perform its normal node layout and
  // preserve any manual node size chosen by the user.
  node.setDirtyCanvas?.(true, true);
}

// Identical to refreshStandaloneVisibility but intentionally omits setDirtyCanvas.
// Used during the first-insertion height fix in onAdded, where calling
// setDirtyCanvas before LiteGraph has cached input-slot positions causes the
// external-positive input circle to render twice on the first connection attempt.
function refreshStandaloneVisibilityNoCanvas(node) {
  if (!node || !Array.isArray(node.widgets)) return;
  const showStandalone = standaloneUiActive(node);
  const adultTriggered = adultStandaloneUiActive(node);
  const detailMode = widgetCanonicalValue(node, "builder_detail_mode");
  const adultMenuLevel = widgetCanonicalValue(node, "adult_menu_level") || "essential";
  const showAllStandalone = showStandalone && detailMode === "professional";
  const showGeneralAdvanced = showStandalone && (detailMode === "advanced" || showAllStandalone);
  const showAdultMenu = showStandalone && (adultTriggered || showAllStandalone);
  const showAdultEssential = showAdultMenu && (adultMenuLevel === "essential" || adultMenuLevel === "professional");
  const showAdultProfessional = showAdultMenu && adultMenuLevel === "professional";

  for (const widget of node.widgets) {
    const canonical = widget?._ultraCanonicalName || widget?.name;
    if (BASIC_STANDALONE_WIDGETS.has(canonical)) setWidgetVisible(widget, showStandalone);
    if (ADVANCED_STANDALONE_WIDGETS.has(canonical)) setWidgetVisible(widget, showGeneralAdvanced);
    if (ADULT_MENU_WIDGETS.has(canonical)) setWidgetVisible(widget, showAdultMenu);
    if (ADULT_ESSENTIAL_WIDGETS.has(canonical)) setWidgetVisible(widget, showAdultEssential);
    if (ADULT_PRO_WIDGETS.has(canonical)) setWidgetVisible(widget, showAdultProfessional);
    if (canonical === "external_prompt_mode") setWidgetVisible(widget, !showStandalone);
  }
  syncHiddenWidgetInputSlots(node);
  // NOTE: setDirtyCanvas intentionally omitted — see caller comment.
}

function scheduleStandaloneVisibility(node) {
  setTimeout(() => refreshStandaloneVisibility(node), 0);
}

function scheduleConnectionVisibilityRefresh(node) {
  // ComfyUI/LiteGraph can update input.link and graph.links at slightly
  // different moments during connect/disconnect.  Refresh a few times without
  // touching node size so the UI follows the real connection state while
  // preserving native manual resize behavior.
  scheduleStandaloneVisibility(node);
  setTimeout(() => refreshStandaloneVisibility(node), 60);
  setTimeout(() => refreshStandaloneVisibility(node), 180);
}

function attachStandaloneVisibilityCallbacks(node) {
  const watched = new Set([
    "prompt_source_mode",
    "builder_detail_mode",
    "adult_tone",
    "adult_wardrobe",
    "adult_menu_level",
    "adult_exposure_level",
    "adult_scene_privacy",
    "adult_scene_mood",
    "adult_pose_style",
    "adult_lighting",
    "adult_scene_props",
    "adult_body_focus",
    "adult_framing_bias",
    "subject_profile",
  ]);
  for (const widget of node?.widgets || []) {
    const canonical = widget?._ultraCanonicalName || widget?.name;
    if (!watched.has(canonical) || widget._ultraStandaloneCallbackWrapped) continue;
    const orig = widget.callback;
    widget.callback = function () {
      const r = orig?.apply(this, arguments);
      scheduleStandaloneVisibility(node);
      return r;
    };
    widget._ultraStandaloneCallbackWrapped = true;
  }
}


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
  model_profile: {
    "Universal Natural Language": "Krea2 Natural",
    "범용 자연어": "Krea2 Natural",
  },
  prompt_source_mode: {
    // old verbose Korean labels
    "외부 프롬프트 스타일 꾸미기": "External Prompt Composer",
    "외부 연결 프롬프트 스타일 꾸미기": "External Prompt Composer",
    "연결 후 스타일 적용": "External Prompt Composer",
    "연결 없이 단독 프롬프트 만들기": "Standalone Scene Builder",
    "단독으로 만들기": "Standalone Scene Builder",
    "자동 전환": "Auto",
    "스타일만 출력": "Style Only",
  },
  builder_detail_mode: {
    // old labels
    "기본 메뉴만": "simple",
    "자세한 메뉴": "advanced",
    "모든 단독 메뉴": "professional",
    // new labels (canonical passthrough – safe to keep)
    "기본": "simple",
    "상세": "advanced",
    "전체": "professional",
    "기본 메뉴": "simple",
    "상세 메뉴": "advanced",
    "전체 메뉴": "professional",
  },
  subject_age: {
    "젊은 성인": "20s",
    "성인": "adult",
    "중년 성인": "50s",
    "노년 성인": "60s+",
    "young adult": "20s",
    "adult": "adult",
    "mature adult": "50s",
    "elderly adult": "60s+",
    "20대": "20s",
    "30대": "30s",
    "40대": "40s",
    "50대": "50s",
    "60대 이상": "60s+",
    "성인(기존 범용)": "adult",
  },
  subject_appearance: {
    "선택 안함": "auto",
    "자연스러운": "natural-looking",
    "귀여운": "cute",
    "아름다운": "beautiful",
    "우아한": "elegant",
    "화려한": "glamorous",
    "평범한": "ordinary-looking",
    "수수한": "simple-looking",
    "덜 예쁜": "less conventionally attractive",
    "개성적인": "distinctive-looking",
  },
  external_prompt_mode: {
    "External prompt + style only": "Output style only",
    "외부 프롬프트 뒤에 스타일 추가": "Append style after external prompt",
    "원본 뒤에 스타일 추가": "Append style after external prompt",
    "원본 뒤에 추가": "Append style after external prompt",
    "외부 프롬프트 앞에 스타일 추가": "Prepend style before external prompt",
    "스타일을 먼저, 원본은 뒤에": "Prepend style before external prompt",
    "스타일 앞에 배치": "Prepend style before external prompt",
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
  prompt_source_mode: "Auto",
  builder_detail_mode: "simple",
  subject_profile: "auto",
  subject_age: "auto",
  subject_appearance: "auto",
  subject_ethnicity: "auto",
  subject_hair: "auto",
  subject_outfit: "auto",
  subject_expression: "auto",
  subject_pose: "auto",
  subject_action: "auto",
  location_type: "auto",
  location_detail: "auto",
  time_of_day: "auto",
  weather_light: "auto",
  scene_props: "auto",
  auto_extra_detail: "auto",
  adult_menu_level: "essential",
  adult_exposure_level: "auto",
  adult_scene_privacy: "auto",
  adult_scene_mood: "auto",
  adult_pose_style: "auto",
  adult_lighting: "auto",
  adult_scene_props: "auto",
  adult_body_focus: "auto",
  adult_framing_bias: "auto",
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

function rawLooksLikeSeedControlValue(value) {
  const raw = String(value ?? "").trim();
  const lower = raw.toLowerCase();
  return [
    "fixed", "randomize", "increment", "decrement",
    "고정", "무작위", "랜덤", "임의", "증가", "증분", "감소", "감분",
  ].includes(raw) || ["fixed", "randomize", "increment", "decrement"].includes(lower);
}

function valueLooksValidFor(widgetName, value) {
  if (widgetName === "seed" || widgetName === "custom_text") return true;
  if (widgetName === "control_after_generate") {
    return rawLooksLikeSeedControlValue(value);
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
  // node.graph(노드 본인이 실제로 속한 그래프)를 app.graph(현재 화면에 표시 중인
  // 그래프)보다 우선한다. 서브그래프 안으로 들어가면 app.graph는 서브그래프를
  // 가리키게 되는데, 이때 부모 그래프에 있는 노드를 app.graph 기준으로 검색하면
  // 찾지 못해 "삭제됨"으로 오판하게 된다.
  const graph = node.graph || app?.graph;
  if (!graph) return false;
  if (typeof graph.getNodeById === "function" && node.id != null) return graph.getNodeById(node.id) === node;
  if (Array.isArray(graph._nodes)) return graph._nodes.includes(node);
  return true;
}

function scheduleNodeUiRefresh(node) {
  // 라벨/콤보 값 번역은 이제 코어(locales/ko/nodeDefs.json)가 전담하므로, 이
  // JS는 더 이상 "언어 설정이 준비됐는지" 추측하거나 재시도할 필요가 없다.
  // 위젯 표시/숨김 같은 비-로케일 상태만 다음 매크로태스크에서 한 번 정리한다.
  setTimeout(() => {
    if (!isLiveNode(node)) return;
    refreshNodeUiState(node);
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


// ── 콤보 값 실시간 번역 (라벨은 nodeDefs.json이 처리하지만, 콤보 옵션 값
// 번역은 코어가 아직 지원하지 않아 여기서 최소한으로 보완한다) ──────────

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

// NOTE: 이 함수는 일부러 결과를 캐시하지 않는다. options.values/value의 getter가
// "읽는 바로 그 순간 항상 재계산"한다는 전제로 설계됐는데, 여기서 결과를 캐시해
// 버리면 사용자가 새로고침 없이 ComfyUI 언어 설정을 바꿨을 때 한쪽 방향으로만
// (특히 이미 한글로 캐시된 뒤 영어로 바꾸는 경우) 반영이 안 되는 문제가 생긴다.
// 매번 재계산하는 비용은 문자열 비교 몇 번 수준이라 무시할 만하다.
function isKoreanLocale() {
  const settingPaths = ["Comfy.Locale", "ComfyUI.Locale", "Comfy.Language"];
  for (const path of settingPaths) {
    const v = readSettingValue(path);
    if (!hasLocaleValue(v)) continue;
    // 공식 ComfyUI 설정값을 찾았으면 그 값이 한글이든 아니든 최종 답이다.
    // 여기서 더 약한 신호(localStorage/document.lang/navigator.language)로
    // 넘어가면, 브라우저/OS 언어가 한국어인 사용자가 ComfyUI를 영어로
    // 명시적으로 설정해도 그 설정이 무시되고 한글에 고착되는 문제가 생긴다.
    return localeLooksKorean(v);
  }

  // 공식 설정값 자체를 아직 못 찾았을 때만(설정 API가 아직 준비 전 등) 보조
  // 신호를 참고한다.
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i) || "";
      if (/locale|language/i.test(key)) {
        const val = localStorage.getItem(key);
        if (hasLocaleValue(val) && localeLooksKorean(val)) return true;
      }
    }
  } catch (_) {}

  try {
    const docLang = document.documentElement?.lang || "";
    if (hasLocaleValue(docLang) && localeLooksKorean(docLang)) return true;
  } catch (_) {}
  try {
    const navLang = navigator.language || "";
    if (hasLocaleValue(navLang) && localeLooksKorean(navLang)) return true;
  } catch (_) {}

  return false;
}

// 옛 워크플로우에 저장된 값(레거시 별칭, 과거 한글 표시 문자열 등)을 현재
// canonical(영문) 값으로 정규화한다. 화면 표시와는 무관하며 데이터 정합성을
// 위한 함수다.
function toCanonical(widgetName, value, options = {}) {
  return normalizeWidgetValue(widgetName, value, options);
}

// 콤보 옵션 값 번역: 저장/실행값(widget.value, options.values)은 항상 canonical
// 영문으로 유지하고, 화면 표시만 ComfyUI 공식 표시 훅(options.getOptionLabel)으로
// 번역한다. 이 훅은 레거시 캔버스 콤보와 Nodes 2.0(Vue) 콤보가 모두 지원한다.
// 예전에는 widget.value / options.values 자체를 getter로 재정의했는데, 새
// 프런트엔드는 위젯 값을 별도 저장소(widgetValueStore)에서 읽기 때문에 Nodes 2.0
// 화면에서 영문 값 + 빨간 테두리(목록에 없는 값)로 표시되는 문제가 있었다.
function patchComboValueTranslation(widget, canonicalName) {
  if (widget._ultraComboTranslationPatched) return;
  const map = KO_LABELS[canonicalName];
  if (!map) return;

  const rawValues = Array.isArray(widget.options.values) ? widget.options.values.slice() : Object.keys(map);
  const canonicals = [];
  const seen = new Set();
  for (const v of rawValues) {
    const c = toCanonical(canonicalName, v, { preserveUnknownCanonical: true });
    if (!seen.has(c)) {
      seen.add(c);
      canonicals.push(c);
    }
  }

  widget.options.values = canonicals;
  const canonicalValue = toCanonical(canonicalName, widget.value, { preserveUnknownCanonical: true });
  if (widget.value !== canonicalValue) widget.value = canonicalValue;

  // 읽는 순간의 로케일로 번역하므로 새로고침 없이 언어를 바꿔도 반영된다.
  widget.options.getOptionLabel = (value) => {
    const text = value == null ? "" : String(value);
    const canonical = toCanonical(canonicalName, text, { preserveUnknownCanonical: true });
    return isKoreanLocale() ? (map[canonical] || canonical) : canonical;
  };

  // 옛 워크플로우에 남은 한글/레거시 값이 실행값으로 나가지 않도록 정규화한다.
  widget.serializeValue = function () {
    return toCanonical(canonicalName, this.value, { preserveUnknownCanonical: true });
  };

  widget._ultraComboTranslationPatched = true;
}

function cleanupStaleWidgets(node) {
  // Hide legacy widget names that no longer exist in the current schema so they
  // do not take up space if an old workflow is loaded.  Visibility for all
  // current (non-stale) widgets is managed exclusively by refreshStandaloneVisibility.
  for (const w of node?.widgets || []) {
    if (isConvertedWidget(w)) continue;
    const canonical = w._ultraCanonicalName || w.name;
    if (!STALE_WIDGETS.has(canonical)) continue;
    w._ultraCanonicalName = canonical;
    w.visible = false;
    w.hidden = true;
    w.computeSize = () => [0, 0];
  }
}


function refreshNodeUiState(node) {
  if (!isLiveNode(node)) return;

  cleanupStaleWidgets(node);
  dedupeManagedInputSlots(node);

  // 라벨은 코어(locales/ko/nodeDefs.json)가 전담하지만, 콤보 옵션 값 번역은
  // 코어가 아직 지원하지 않아 여기서 최소한으로 보완한다. canonical 이름
  // 부여도 여기서 함께 처리한다 — 가시성 로직(standaloneUiActive 등)이
  // 이 이름으로 위젯을 찾아 canonical 값을 읽는다.
  for (const widget of node.widgets || []) {
    if (isConvertedWidget(widget)) continue;
    if (!widget._ultraCanonicalName) widget._ultraCanonicalName = widget.name;
    patchComboValueTranslation(widget, widget._ultraCanonicalName);
  }

  attachStandaloneVisibilityCallbacks(node);
  refreshStandaloneVisibility(node);

  node.setDirtyCanvas?.(true, true);
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
    vals.length >= LEGACY_PROMPT_CONTROLS_EARLY_WIDGET_ORDER.length &&
    valuesMatchOrder(vals, [
      ["model_profile", 0], ["prompt_source_mode", 1],
      ["builder_detail_mode", 2], ["external_prompt_mode", 3],
      ["mood_family", 4],
    ])
  ) {
    return namedValuesFromOrder(vals.slice(0, LEGACY_PROMPT_CONTROLS_EARLY_WIDGET_ORDER.length), LEGACY_PROMPT_CONTROLS_EARLY_WIDGET_ORDER);
  }

  // Workflows saved with the pre-reorder full schema (external_prompt_mode at index 2,
  // builder_detail_mode at index 3).  Detect by positional value checks and remap.
  if (
    vals.length >= PRE_REORDER_WIDGET_ORDER.length &&
    valuesMatchOrder(vals, [
      ["model_profile", 0], ["prompt_source_mode", 1],
      ["external_prompt_mode", 2], ["builder_detail_mode", 3],
      ["mood_family", 4],
    ])
  ) {
    return namedValuesFromOrder(vals.slice(0, PRE_REORDER_WIDGET_ORDER.length), PRE_REORDER_WIDGET_ORDER);
  }

  if (
    vals.length >= PRE_APPEARANCE_WIDGET_ORDER.length &&
    valuesMatchOrder(vals, PRE_APPEARANCE_WIDGET_ORDER.map((name, index) => [name, index]))
  ) {
    return namedValuesFromOrder(vals.slice(0, PRE_APPEARANCE_WIDGET_ORDER.length), PRE_APPEARANCE_WIDGET_ORDER);
  }

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
    const preAppearanceActiveOrder = PRE_APPEARANCE_WIDGET_ORDER.filter((name) => !inputNames.has(name));
    const preAppearanceWithoutSeedControl = preAppearanceActiveOrder.filter((name) => name !== "control_after_generate");
    const preAppearanceSourceOrder = (
      preAppearanceActiveOrder.includes("control_after_generate") &&
      vals.length === preAppearanceWithoutSeedControl.length
    ) ? preAppearanceWithoutSeedControl : preAppearanceActiveOrder;
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
    const legacyEarlyActiveOrder = LEGACY_PROMPT_CONTROLS_EARLY_WIDGET_ORDER.filter((name) => !inputNames.has(name));
    const legacyEarlyWithoutSeedControl = legacyEarlyActiveOrder.filter((name) => name !== "control_after_generate");
    const legacyEarlySourceOrder = (
      legacyEarlyActiveOrder.includes("control_after_generate") &&
      vals.length === legacyEarlyWithoutSeedControl.length
    ) ? legacyEarlyWithoutSeedControl : legacyEarlyActiveOrder;
    const preReorderActiveOrder = PRE_REORDER_WIDGET_ORDER.filter((name) => !inputNames.has(name));
    const preReorderWithoutSeedControl = preReorderActiveOrder.filter((name) => name !== "control_after_generate");
    const preReorderSourceOrder = (
      preReorderActiveOrder.includes("control_after_generate") &&
      vals.length === preReorderWithoutSeedControl.length
    ) ? preReorderWithoutSeedControl : preReorderActiveOrder;
    const candidates = [preAppearanceSourceOrder, previousSourceOrder, preCleanupSourceOrder, legacyEarlySourceOrder, preReorderSourceOrder, currentSourceOrder];
    const sourceOrder = candidates.find((order) => valuesMatchOrder(vals, order.map((name, index) => [name, index])));
    if (!sourceOrder) return;
    saveValues(namedValuesFromOrder(vals, sourceOrder), { preserveUnknownCanonical: true });
    return;
  }

  // A pre-subject_appearance workflow saved with ComfyUI's seed control has the
  // same widget_values length as a current workflow saved without seed control.
  // Disambiguate by checking the old seed-control slot before the generic
  // current-without-control path; otherwise default-heavy old workflows can be
  // shifted by one widget from subject_ethnicity onward.
  const preAppearanceControlIndex = PRE_APPEARANCE_WIDGET_ORDER.indexOf("control_after_generate");
  if (
    vals.length === PRE_APPEARANCE_WIDGET_ORDER.length &&
    vals.length === activeWithoutSeedControl.length &&
    preAppearanceControlIndex >= 0 &&
    valueLooksValidFor("control_after_generate", vals[preAppearanceControlIndex]) &&
    valuesMatchOrder(vals, PRE_APPEARANCE_WIDGET_ORDER.map((name, index) => [name, index]))
  ) {
    saveValues(namedValuesFromOrder(vals, PRE_APPEARANCE_WIDGET_ORDER), { preserveUnknownCanonical: true });
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

  if (
    vals.length >= expectedLength &&
    valuesMatchOrder(vals, WIDGET_ORDER.map((name, index) => [name, index]))
  ) {
    saveValues(namedValuesFromOrder(vals.slice(0, expectedLength), WIDGET_ORDER), { preserveUnknownCanonical: true });
    return;
  }

  if (
    vals.length === activeCurrentOrder.length &&
    valuesMatchOrder(vals, activeCurrentOrder.map((name, index) => [name, index]))
  ) {
    saveValues(namedValuesFromOrder(vals, activeCurrentOrder));
  }
}


app.registerExtension({
  name: "Ultra.PromptComposer.UiState",
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "UltraPromptComposer") return;

    const origCreated = nodeType.prototype.onNodeCreated;
    const origConfigure = nodeType.prototype.onConfigure;
    const origAdded = nodeType.prototype.onAdded;
    const origConnectionsChange = nodeType.prototype.onConnectionsChange;

    nodeType.prototype.onNodeCreated = function () {
      const r = origCreated?.apply(this, arguments);
      scheduleNodeUiRefresh(this);
      return r;
    };

    nodeType.prototype.onConfigure = function (data) {
      migrateWidgetValuesForCurrentSchema(data, this);

      // Mark that this node was restored from a saved workflow.
      // onAdded (called after onConfigure) uses this flag to skip the
      // first-insertion height correction so the user's saved size is preserved.
      this._ultraWasConfigured = true;

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
      // Do not alter restored inputs synchronously while LiteGraph is still
      // configuring saved graph links. scheduleNodeUiRefresh runs after the
      // graph restore pass and then removes duplicate runtime slots safely.
      scheduleNodeUiRefresh(this);
      return r;
    };

    nodeType.prototype.onAdded = function () {
      const r = origAdded?.apply(this, arguments);

      // ── First-insertion height fix ────────────────────────────────────────
      // When a node is dragged onto the canvas for the first time ComfyUI
      // calculates node.size based on all required widgets before our JS has
      // a chance to hide the ones that belong to inactive modes. We need
      // widget.computeSize = () => [0,0] on inactive widgets so that
      // node.computeSize() returns the correct collapsed height, so we run a
      // pure visibility pass (no setDirtyCanvas) and read computeSize from
      // that tidy state before the full refresh (scheduled below) runs.
      if (!this._ultraWasConfigured && isLiveNode(this)) {
        for (const w of this.widgets || []) {
          if (!w._ultraCanonicalName) w._ultraCanonicalName = w.name;
        }
        cleanupStaleWidgets(this);
        refreshStandaloneVisibilityNoCanvas(this);   // visibility only, no setDirtyCanvas
        const h = this.computeSize()[1];
        if (h > 0 && h < this.size[1]) {
          this.size[1] = h;                          // height-only correction, width untouched
        }
      }

      scheduleNodeUiRefresh(this);
      return r;
    };

    nodeType.prototype.onConnectionsChange = function () {
      const r = origConnectionsChange?.apply(this, arguments);
      const eventArgs = arguments;
      // Some ComfyUI builds update node.inputs after this callback, while other
      // builds pass the slot information only through the event arguments.
      // When the event touches external_positive_in, refresh visibility
      // immediately, then let the normal delayed refreshes reconcile the
      // final link state.
      if (connectionEventLooksLikeExternalPositive(this, eventArgs)) {
        refreshStandaloneVisibility(this);
      }
      scheduleConnectionVisibilityRefresh(this);
      return r;
    };
  },
});
