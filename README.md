# 🧰 comfyui-Ultra-Tools

<a id="korean"></a>

**🇰🇷 한국어 | [🇺🇸 English](#english)**

[![Version](https://img.shields.io/badge/version-2.0.9-blue)](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases/tag/v2.0.9)
[![Comfy Registry](https://img.shields.io/badge/Comfy%20Registry-Ultra%20Tools-6f42c1)](https://registry.comfy.org/publishers/yamoon-jjang/nodes/comfyui-ultra-tools)
[![License: GPL v3](https://img.shields.io/badge/license-GPL--3.0-green)](LICENSE)
![UI](https://img.shields.io/badge/UI-%ED%95%9C%EA%B5%AD%EC%96%B4%20%2F%20English-orange)

**ComfyUI 작업에서 매번 반복되는 일들을 덜어 주는 12개 실용 노드 모음입니다.**

프롬프트를 고르고·꾸미고·번역하는 일, 이미지를 찾아 불러오는 일, 결과물에 워터마크를 넣는 일, 모델 용량과 실행 시간을 확인하는 일, 생성 오디오의 잡음을 다듬는 일까지 — 노드 하나하나를 실제 작업에서 불편했던 점을 직접 고쳐 가며 다듬었습니다. 모든 노드는 서로 독립적이라 필요한 것만 골라 워크플로우에 넣으면 됩니다.

## ✨ 특징

| | |
|---|---|
| 📦 **설치가 간단** | 추가 pip 패키지가 전혀 없습니다. ComfyUI 기본 라이브러리만 사용합니다. |
| 🌐 **한국어 / 영어 UI** | ComfyUI 언어 설정에 따라 노드 이름·메뉴·안내가 자동으로 바뀝니다. |
| 🖥️ **두 캔버스 모두 지원** | 새 **Nodes 2.0(Vue)** 화면과 기존 LiteGraph 캔버스에서 모두 동작하도록 맞췄습니다. |
| 🔒 **안전한 기본값** | 파일 탐색은 ComfyUI가 관리하는 폴더 안으로 제한되고, API 키는 워크플로우에 저장되지 않습니다. |
| 📖 **노드별 메뉴얼** | `메뉴얼` 폴더에 노드마다 자세한 한국어 설명서가 들어 있습니다. |
| 🔁 **워크플로우 호환** | 노드 ID와 입·출력을 함부로 바꾸지 않아, 업데이트해도 기존 워크플로우가 그대로 열립니다. |

---

## 🗂️ 노드 한눈에 보기

| 분류 | 노드 | 무엇을 해 주나요? |
|---|---|---|
| ✍️ 프롬프트 | [Prompt Composer](#prompt-composer) | 메뉴만 골라 **장면 프롬프트를 처음부터 조립** (모델 9종 문법 대응) |
| ✍️ 프롬프트 | [Prompt Styler](#prompt-styler) | 내 프롬프트는 그대로 두고 **분위기·화풍만 모델 문법에 맞게 입힘** |
| ✍️ 프롬프트 | [Textbox](#textbox) | 노드 하나에 텍스트 칸 **최대 32개**, 칸마다 독립 입·출력 |
| ✍️ 프롬프트 | [Translator](#translator) | 워크플로우 안에서 바로 **번역** (API 키 없이도 동작, 20개 언어) |
| ✍️ 프롬프트 | [Wildcard Browser](#wildcard-browser) | 와일드카드 폴더를 탐색하고 **`__폴더/파일__` 호출문을 클릭 한 번에 복사** |
| 📁 이미지 | [Image Load](#image-load) | 기본 Load Image에 **썸네일 브라우저 + output 폴더 직접 불러오기** 추가 |
| 🏷️ 마무리 | [Text Watermark](#text-watermark) | 두 블록 문단형 **글자 워터마크** (외곽선·글로우·회전, 글꼴 15종 동봉) |
| 🏷️ 마무리 | [Image Watermark](#image-watermark) | 로고·서명 **이미지 워터마크** (타일 반복·블렌드·그림자·MASK 출력) |
| 🔊 오디오 | [Audio Fade](#audio-fade) | 생성 오디오 **시작 부분의 팝·찌직음 제거**, 싱크는 그대로 |
| 📊 관리 | [Model Viewer](#model-viewer) | 지금 워크플로우가 **실제로 쓰는 모델과 용량** 확인 |
| 📊 관리 | [Model Viewer (All)](#model-viewer) | 모델 폴더 전체를 **종류별로 스캔**해 큰 파일 찾기 |
| ⏱️ 관리 | [Workflow Timer](#workflow-timer) | 실행 시간 **실시간 표시 + 최근 100회 기록 + 평균** |

모든 노드는 노드 검색에서 **`Ultra Tools`** 로 찾을 수 있고, 카테고리도 `Ultra Tools`에 모여 있습니다.

---

## 📦 설치

### ① ComfyUI Manager (가장 쉬운 방법)

ComfyUI Manager → **Custom Nodes Manager**에서 **`Ultra Tools`** 를 검색해 설치합니다. ([Comfy Registry 페이지](https://registry.comfy.org/publishers/yamoon-jjang/nodes/comfyui-ultra-tools))

### ② Git

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git
```

업데이트는 `comfyui-Ultra-Tools` 폴더에서 `git pull` 하면 됩니다.

### ③ 릴리스 ZIP 수동 설치

[**v2.0.9 설치용 ZIP**](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases/download/v2.0.9/comfyui-Ultra-Tools-v2.0.9.zip)을 받아 압축을 풀면 `comfyui-Ultra-Tools` 폴더가 나옵니다. 이 폴더를 `ComfyUI/custom_nodes/` 안에 넣으세요. 한글 파일명이 깨지지 않도록 포장되어 있습니다.

> ⚠️ 예전 ZIP 버전에서 업데이트할 때는 기존 폴더를 **백업한 뒤 삭제하고** 새 폴더를 넣으세요. 덮어쓰기만 하면 이전 버전에서 지워진 파일이 남을 수 있습니다.

설치·업데이트 후에는 **ComfyUI를 완전히 재시작**하고 브라우저를 **새로고침(Ctrl+F5)** 하세요.

---

## 🚀 빠르게 써 보기

- **예제 워크플로우**: `이미지 워크플로우/Ultra_Tools_Image_Load_Preview.json` 을 ComfyUI 화면에 끌어다 놓고, Image Load에서 이미지를 하나 고른 뒤 실행해 보세요.
- **자주 쓰는 조합**

| 하고 싶은 일 | 연결 예 |
|---|---|
| 한국어로 쓴 프롬프트를 영어 모델에 쓰기 | Textbox → **Translator**(english) → **Prompt Styler** → CLIP Text Encode |
| 메뉴만 골라 프롬프트 만들기 | **Prompt Composer** (positive / negative) → CLIP Text Encode 2개 |
| 결과물에 로고 + 제작자 표기 | 생성 이미지 → **Image Watermark** → **Text Watermark** → Save Image |
| MiniMax H3 영상의 오디오 잡음 정리 | H3 AUDIO → **Audio Fade** → Create Video |
| 설정별 생성 속도 비교 | 캔버스 아무 곳에 **Workflow Timer** 하나 올려 두기 (연결 불필요) |
| 워크플로우 공유 전 모델 목록 확인 | **Model Viewer** 하나 올려 두기 |

---

<a id="prompt-composer"></a>

## 🎨 Ultra Tools Prompt Composer

외부 입력 없이 **메뉴를 골라 장면 프롬프트를 처음부터 만드는** 프롬프트 조립기입니다. 이미 만든 프롬프트에 스타일을 덧입히는 용도로도 씁니다.

**이런 분께 좋습니다**
- 프롬프트를 직접 쓰기보다 "누가, 어디서, 어떤 구도로, 어떤 화풍으로"를 골라서 만들고 싶은 분
- 같은 장면을 자연어 모델용과 태그 모델용으로 각각 뽑아야 하는 분
- 랜덤 스타일로 여러 화풍을 빠르게 시험해 보고 싶은 분

**주요 기능**
- **모델 형식 9종**: Z-Image / Krea2 / Qwen / Flux 같은 자연어 모델, SDXL / Illustrious / Pony / SD 1.5 같은 태그 모델, Anima 혼합형. 같은 선택이라도 모델이 잘 알아듣는 문법으로 바꿔서 출력합니다.
- **분위기 22종(+랜덤 3종) × 스타일 34종**: 누아르, 고딕 로맨스, 사이버펑크, 골든아워, 빈티지 필름 같은 분위기와 수채화, 유화, 목탄, 연필, 수묵, 픽셀아트, 미니어처 디오라마, 3D 피규어, 치비 같은 화풍이 있습니다. `분위기에 맞춰 자동`을 고르면 분위기에 어울리는 화풍을 노드가 골라 줍니다.
- **구도 15종 · 렌즈 느낌 17종**으로 화면 범위와 카메라 느낌을 지정합니다.
- **단독 장면 만들기**: 주요 대상(인물·커플·그룹·배경만·제품/사물), 장소, 시간, 날씨, 소품, 조명을 조합합니다. `장면 디테일 보강`을 켜면 장면을 더 풍부하게 채워 줍니다.
- 메뉴 표시 범위(기본 / 상세 / 전체)를 고를 수 있어, 처음엔 기본 메뉴만, 익숙해지면 전체 메뉴를 쓰면 됩니다.
- **충돌 정리**: 수채화를 골랐는데 원문에 "photorealistic, DSLR" 같은 말이 있으면 스타일이 약해집니다. 이런 충돌 표현을 완화해 줍니다.
- 사용자가 직접 쓴 `custom_text`는 **절대 다른 뜻으로 바꾸지 않습니다.**
- Positive와 함께 모델에 맞는 **Negative 프롬프트도 같이 출력**합니다.

**사용 팁**
- 기존 프롬프트에 스타일만 붙일 때는 `external_positive_in`에 연결하고 `균형 적용`으로 시작하세요. 스타일이 약하면 `스타일 우선`으로 올리면 됩니다.
- 랜덤 분위기(`🎲 랜덤 전체`, `🎲 랜덤 전통 매체 화풍` 등)와 seed를 함께 쓰면 마음에 든 조합을 다시 재현할 수 있습니다.

---

<a id="prompt-styler"></a>

## 🖌️ Ultra Tools Prompt Styler

**내가 쓴 프롬프트는 최대한 그대로 두고**, 분위기·스타일·구도·렌즈 느낌만 모델 문법에 맞게 얹어 주는 스타일러입니다. Composer보다 메뉴가 간단해서, 이미 쓰고 있는 프롬프트 흐름에 바로 끼워 넣기 좋습니다.

**이런 분께 좋습니다**
- 텍스트 노드나 다른 프롬프트 생성기에서 나온 프롬프트에 화풍만 바꿔 입히고 싶은 분
- Pony / Illustrious / Anima의 rating·source 태그가 서로 충돌해 결과가 이상해진 경험이 있는 분

**주요 기능**
- Composer와 같은 모델 형식, 분위기, 스타일, 구도, 렌즈 체계를 씁니다.
- **스타일 반영 방식 3단계**(원본 보존 / 균형 적용 / 스타일 우선)로 원본을 얼마나 지킬지 정합니다.
- **합치는 위치 선택**: 원문 뒤에 붙이기(권장), 앞에 붙이기, 스타일 문구만 출력하기. 스타일 문구만 뽑아 다른 프롬프트 빌더와 섞어 쓸 수도 있습니다.
- `(watercolor wash:1.3)` 같은 **가중치 문법과 괄호를 최대한 보존**하고, 깨진 괄호나 쉼표도 안전하게 처리합니다.
- 수채화·연필·수묵 같은 **사진이 아닌 화풍에는 "카메라·렌즈·실사" 문구가 섞이지 않게** 막아 줍니다.
- Pony / ILXL / Anima의 **rating·source 태그 충돌을 자동 정리**합니다. 예: `rating_safe`와 `rating_explicit`이 함께 들어가는 일을 막습니다.
- 외부 Negative와 모델 기본 Negative를 **중복 없이 합칩니다.** 프롬프트에 램프·촛불·네온사인 같은 광원이 있으면, 그 광원을 지우는 Negative와 충돌하지 않게 조정합니다.

**사용 팁**
- Anima 계열에서 스타일이 잘 안 먹으면 품질·속도·화풍 LoRA를 먼저 꺼 보세요. LoRA가 화풍을 강하게 고정하는 경우가 많습니다. 메뉴얼에 확인 순서가 정리되어 있습니다.

---

<a id="textbox"></a>

## 📝 Ultra Tools Textbox

노드 하나에서 **여러 개의 텍스트를 독립적으로 관리**하는 텍스트 노드입니다.

**이런 분께 좋습니다**
- Positive, Negative, 파일명 접두어, 메모를 텍스트 노드 여러 개로 흩어 놓고 쓰던 분
- 다른 노드에서 넘어온 문자열을 눈으로 확인하고 고치고 싶은 분

**주요 기능**
- **＋ 텍스트 추가**로 칸을 최대 **32개**까지 늘립니다. `Text N`은 항상 `IN N → OUT N`으로 짝지어지고 서로 섞이지 않습니다.
- **입력을 연결해도 칸이 회색 읽기 전용으로 바뀌지 않습니다.** 실행 후 실제로 받은 문자열이 칸에 표시되니, 바로 확인·복사·수정할 수 있습니다.
- 중간 칸만 골라 **× 삭제**할 수 있고, 뒤쪽 칸의 연결은 그대로 유지됩니다.
- **⋀ ⋁ 버튼으로 순서를 바꾸면** 내용, 이름, 연결선이 함께 따라 움직입니다.
- 이름을 클릭해 **직접 이름 붙이기**("행동", "배경" 등)를 하면 출력 단자 이름도 같이 바뀝니다.
- 칸마다 **Copy 버튼**이 있습니다.
- 칸 개수와 내용은 워크플로우에 저장되어 그대로 복원됩니다. JSON처럼 생긴 문자열도 그냥 텍스트로 안전하게 취급합니다.

---

<a id="translator"></a>

## 🌐 Ultra Tools Translator

워크플로우 안에서 텍스트를 바로 번역하는 가벼운 번역 노드입니다. 기본 설정은 **한국어로 번역**, 원문 언어는 **자동 감지**입니다. 출력은 `STRING`이라 어떤 텍스트·프롬프트 노드에도 연결할 수 있습니다.

**주요 기능**
- **API 키 없이도** MyMemory 공개 번역 API로 바로 쓸 수 있습니다.
- 무료 번역은 요청이 많으면 `HTTP 429`(요청 과다) 제한이 걸릴 수 있습니다. 이때 노드의 **`Google 번역 API 설정`** 버튼에서 공식 **Google Cloud Translation API Key**를 저장하면 공식 API를 먼저 쓰고, 실패하면 MyMemory로 자동 전환합니다.
- API Key는 워크플로우 파일이 아니라 **이 PC의 ComfyUI 설정에만 저장**됩니다. 워크플로우를 공유해도 키가 따라가지 않고, 저장된 키는 화면에 다시 표시되지 않습니다.
- **Ultra MiniMax H3 Prompt** 노드와 같은 API Key를 공유하므로, 한쪽에서 저장하면 다른 쪽에 다시 입력할 필요가 없습니다.
- **줄바꿈 유지** 옵션으로 줄 단위로 관리하는 프롬프트도 구조가 깨지지 않습니다.
- **번역 실패 시 원문 그대로 출력** 옵션을 켜면 번역이 실패해도 워크플로우가 멈추지 않습니다.
- **지원 언어 20개**: 영어, 한국어, 일본어, 중국어(간체·번체), 스페인어, 프랑스어, 독일어, 이탈리아어, 포르투갈어, 러시아어, 우크라이나어, 베트남어, 태국어, 인도네시아어, 힌디어, 아랍어, 튀르키예어, 네덜란드어, 폴란드어.

---

<a id="wildcard-browser"></a>

## 🃏 Ultra Tools Wildcard Browser

와일드카드 폴더를 **한 단계씩 탐색**하다가 파일을 클릭하면, 그 파일의 호출문(예: `__01_Natural/K-Pop/female_singer__`)이 **바로 클립보드에 복사**됩니다.

**이런 분께 좋습니다**
- Impact Pack의 `와일드카드 처리기`에서 **"추가할 와일드카드" 목록이 안 나오거나, 클릭해도 삽입되지 않는** 분. 이 노드로 복사해 붙여넣으면 해결됩니다.
- 와일드카드 파일이 수천 개라 정확한 경로를 찾기 어려운 분

**주요 기능**
- 폴더를 클릭해 들어가고 `📁 ..`으로 나오는 **단계별 탐색**입니다. 하위 파일을 한꺼번에 쏟아내지 않아 큰 폴더도 깔끔하게 볼 수 있습니다.
- `.txt` `.yaml` `.yml` `.json`만 표시합니다. 이름이 같고 확장자만 다른 파일은 하나로 묶습니다.
- 심볼릭 링크와 Windows 정션을 지원하고, **순환 링크는 자동으로 차단**합니다.
- 워크플로우를 다시 열면 마지막으로 보던 하위 폴더 위치를 기억합니다.
- 보안을 위해 **ComfyUI 모델 폴더(`extra_model_paths.yaml` 포함)와 ComfyUI 안의 `wildcards` / `custom_wildcards` 폴더(Impact Pack 등)** 안에서만 탐색합니다. 기본 경로는 `models/wildcards`입니다.
- 생성 과정에는 참여하지 않는 노드라서, 와일드카드 드라이브가 빠져 있어도 **이미지 생성은 실패하지 않습니다.**

---

<a id="image-load"></a>

## 📁 Ultra Tools Image Load

ComfyUI 기본 **Load Image를 그대로 기반으로** 하고, 이미지를 고르는 화면을 크게 개선한 노드입니다. 출력(IMAGE / MASK)과 업로드 버튼이 기본 노드와 같아서 **기존 Load Image 자리에 그대로 바꿔 끼우면** 됩니다.

**이런 분께 좋습니다**
- input 폴더에 이미지가 수백 장이라 파일명 목록만으로는 원하는 이미지를 찾기 어려운 분
- 방금 생성한 결과물(output)을 다시 입력으로 쓰려고 매번 input 폴더로 복사하던 분

**주요 기능**
- **썸네일 브라우저** (`input 썸네일 보기` 버튼)
  - 썸네일 보기 / 목록 보기 전환, 파일명 검색, 폴더 필터, 썸네일 크기 슬라이더
  - 창 크기와 보기 설정은 다음에 열 때도 그대로 유지됩니다.
  - 해상도가 함께 표시되고, 비율이 다른 이미지도 잘리지 않고 전체가 보입니다.
  - 화면에 보이는 곳 위주로 먼저 불러와서, 이미지가 많아도 빠르게 넘겨 볼 수 있습니다.
- **output 폴더 직접 불러오기**: ComfyUI output 안의 폴더를 등록하면 input으로 **복사하지 않고** 원래 위치에서 바로 불러옵니다. 폴더는 여러 개 등록할 수 있고 하위 폴더도 함께 보입니다. 폴더를 탐색하는 동안 그 폴더의 이미지가 바로 미리 보입니다.
- 클릭으로 후보 선택 → `선택` 버튼으로 적용, 또는 **더블클릭으로 즉시 적용**합니다. `Esc`나 닫기로 나가면 노드의 기존 이미지는 바뀌지 않습니다.
- Ctrl/Shift 클릭으로 여러 장을 골라 **한꺼번에 삭제**할 수 있습니다.
- 우클릭 메뉴의 새 탭에서 열기, 다른 이름으로 저장, 이미지 복사는 썸네일이 아니라 **원본 해상도**로 동작합니다.

> ⚠️ 삭제 기능은 실제 원본 파일을 영구 삭제합니다. 삭제 전에 표시되는 파일 목록을 꼭 확인하세요.
>
> ℹ️ v2.0.2부터 Comfy Registry 보안 정책에 따라 ComfyUI **밖의** 드라이브·폴더는 등록할 수 없습니다. 그런 이미지는 `choose file to upload`로 올리거나 output 폴더 안으로 옮겨서 쓰세요.

---

<a id="text-watermark"></a>

## ✒️ Ultra Tools Text Watermark

이미지에 **두 블록 구성의 문단형 텍스트 워터마크**를 넣습니다. 예를 들어 위에는 제작자명, 아래에는 사이트 주소를 넣는 식입니다.

**주요 기능**
- Text 1과 Text 2는 서로 **다른 글꼴, 크기, 색, 정렬, 스타일**을 쓸 수 있고, 각각 여러 줄도 됩니다.
- 텍스트마다 **외곽선**을 따로 지정하고, **글로우**도 텍스트별로 켤 수 있습니다.
- 위아래 / 좌우 배치, 블록 간격, 전체 불투명도, 9방향 위치, X/Y 미세 조정, **회전**을 지원합니다.
- 한글 손글씨체와 영문 필기체를 포함한 **글꼴 15종이 동봉**되어 있습니다(행복고흥, 나눔손글씨, 빙그레 싸만코, Pretendard, Great Vibes 등).
- 원하는 글꼴(`.ttf` `.otf` `.ttc` `.otc`)을 `fonts` 폴더에 넣으면 목록에 추가됩니다. 보안을 위해 시스템 글꼴 폴더는 읽지 않습니다.

---

<a id="image-watermark"></a>

## 🖼️ Ultra Tools Image Watermark

로고, 서명, 아이콘 이미지를 워터마크로 합성합니다.

**주요 기능**
- 노드의 **업로드/선택 버튼**으로 워터마크 파일을 바로 고릅니다. 기존처럼 Load Image를 연결해도 됩니다. 투명 PNG / WebP의 투명도는 자동으로 적용됩니다.
- **투명 여백을 뺀 실제 로고 크기 기준**으로 크기를 맞춥니다(비율 / 픽셀 모드). 큰 투명 캔버스에 작은 로고가 있어도 로고가 지나치게 작아지지 않습니다.
- 색상 반전, 단색 틴트, 외곽선, 그림자, 경계 부드럽게 처리를 지원합니다.
- 블렌드 모드 5종(normal / multiply / screen / overlay / soft light).
- **타일 반복**: 격자로 채우는 full과 엇갈리게 채우는 diagonal을 고르고, 간격·회전을 조절해 저작권 보호용 패턴을 만들 수 있습니다.
- 워터마크가 들어간 영역을 **MASK로도 출력**합니다.
- 메모리가 폭증할 만한 극단적인 조합은 결과를 몰래 줄이지 않고, **실행 전에 명확히 알려 줍니다.**

> 💡 추천 순서: 원본 → **Image Watermark**(반복 로고) → **Text Watermark**(제작자 문구) → Save Image

---

<a id="audio-fade"></a>

## 🔊 Ultra Tools Audio Fade

생성된 오디오의 시작과 끝에 **페이드 인 / 아웃**을 적용합니다. MiniMax H3처럼 오디오 시작 순간에 **팝·찌직 소리**가 들어가는 경우를 위해 만들었습니다.

- AUDIO 선 중간에 끼워 넣기만 하면 됩니다. 기본값은 페이드 인 0.15초입니다. 잡음이 남으면 0.18~0.20초로 조금씩 올려 보세요.
- 곡선 4종(smooth / linear / equal_power / exponential).
- **길이, 샘플레이트, 영상과의 싱크는 절대 바꾸지 않습니다.** 원본 데이터도 덮어쓰지 않습니다.
- 아주 짧은 클립에서 인·아웃 시간의 합이 클립보다 길면, 두 페이드가 겹치지 않도록 비율을 유지한 채 자동으로 줄입니다.

---

<a id="model-viewer"></a>

## 📊 Ultra Tools Model Viewer / Model Viewer (All)

모델 파일을 확인하는 **정보 표시용 노드 2종**입니다. 파일을 옮기거나 지우는 기능이 없어서 안심하고 쓸 수 있습니다.

- **Model Viewer**: 지금 열려 있는 워크플로우가 **실제로 쓰고 있는 모델**을 찾아, 종류별로 파일명과 크기를 보여 줍니다. 그래프가 바뀌면 자동으로 갱신됩니다. 워크플로우를 다른 사람에게 줄 때 필요한 모델 목록을 확인하기 좋습니다.
- **Model Viewer (All)**: 모델 폴더 전체를 Checkpoint, UNET, LoRA, VAE, Text Encoder, CLIP, ControlNet, Upscale 같은 **종류별로 스캔**해 개수·총 용량·큰 파일 순위(5~100위)를 보여 줍니다. 디스크 정리에 유용합니다.
- safetensors, ckpt, pt, gguf, onnx, nunchaku 등 다양한 모델 형식을 인식합니다.

---

<a id="workflow-timer"></a>

## ⏱️ Ultra Tools Workflow Timer

캔버스에 올려 두기만 하면 되는 **실행 시간 측정기**입니다. 연결선이 필요 없습니다.

- 실행 중에는 경과 시간을 **실시간으로** 보여 줍니다.
- 끝나면 **기록(최근 100회)** 과 **총 횟수·평균 시간**이 쌓입니다.
- 워크플로우 탭마다 기록이 따로 관리됩니다.
- 모델, 샘플러, 해상도, 최적화 설정을 바꿨을 때 **전후 속도를 비교**하기 좋습니다.

---

## ❓ 자주 묻는 질문 / 문제 해결

**설치했는데 노드가 안 보여요.**
ComfyUI를 완전히 껐다 켜고 브라우저를 Ctrl+F5로 새로고침하세요. ZIP으로 설치했다면 폴더 구조가 `custom_nodes/comfyui-Ultra-Tools/__init__.py` 형태인지(폴더가 한 겹 더 들어가 있지 않은지) 확인하세요.

**번역이 갑자기 안 돼요 (HTTP 429).**
무료 번역 API의 요청 횟수 제한입니다. 잠시 뒤 다시 시도하거나, `Google 번역 API 설정`에서 공식 API Key를 등록하세요. `번역 실패 시 원문 출력`을 켜 두면 워크플로우는 멈추지 않습니다.

**Image Load에서 다른 드라이브 폴더를 등록할 수 없어요.**
Comfy Registry 보안 정책 때문에 v2.0.2부터 ComfyUI input / output 안으로 제한했습니다. 이미지를 output 폴더 안으로 옮기거나 업로드해서 쓰세요.

**Wildcard Browser에 내 와일드카드 폴더가 안 보여요.**
`ComfyUI/models/wildcards`, 또는 ComfyUI 안의 `wildcards` / `custom_wildcards` 폴더(Impact Pack 등)에 두세요. `extra_model_paths.yaml`에 등록한 모델 경로 안도 탐색할 수 있습니다.

**Text Watermark에 내 글꼴을 쓰고 싶어요.**
글꼴 파일을 `comfyui-Ultra-Tools/fonts/` 폴더에 넣고 ComfyUI를 재시작하세요.

**자세한 사용법은요?**
`메뉴얼` 폴더에 노드별 설명서가 있습니다. 버그나 제안은 [Issues](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/issues)에 남겨 주세요.

---

## 🧩 Ultra Image + PiD는 어디로 갔나요?

v2.0.0부터 이미지 생성·PiD(PixelDiT) 업스케일 노드는 Ultra Tools에서 분리되어 **독립 노드 팩 [Ultra Image + PiD](https://github.com/Yamoon-jjang/comfyui-Ultra-Image-PiD)** 로 제공됩니다(기능 폐지 아님). 모델별 의존성과 업데이트 주기가 다른 유틸리티 노드와 달라서, 나머지 Ultra Tools를 가볍고 안정적으로 유지하기 위해 나눴습니다.

- Ultra Tools에서는 이 노드 하나만 빠졌고, 나머지 12종의 노드 ID와 동작은 그대로입니다.
- 예전 `UltraImagePiD`가 들어 있던 워크플로우는 새 `UltraStandaloneImagePiD`로 자동 변환되지 않습니다. 독립 팩을 설치한 뒤 노드를 교체하고 연결을 다시 확인하세요.

---

## 🔗 함께 쓰면 좋은 노드

- [**Ultra Image + PiD**](https://github.com/Yamoon-jjang/comfyui-Ultra-Image-PiD) — 여러 이미지 모델 계열을 노드 하나로 생성하고, 모델별 설정을 기억하며, PiD 업스케일까지 처리
- [**Ultra Qwen Image Editor**](https://github.com/Yamoon-jjang/comfyui-Ultra-Qwen-Image-Editor) — Qwen Image Edit 계열 이미지 편집용 올인원 노드
- [**Ultra MiniMax H3 Prompt**](https://github.com/Yamoon-jjang/comfyui-Ultra-MiniMax-H3-Prompt) — MiniMax H3 영상(T2V / I2V / R2V) 프롬프트 생성 노드. Translator와 API Key를 공유합니다.

---

## 📝 최근 변경 사항

| 버전 | 내용 |
|---|---|
| **2.0.9** | 로컬 경로 정보 보호 — Wildcard Browser·Image Load가 실제 디스크 경로 대신 ComfyUI 기준 경로만 표시, Text Watermark는 동봉 글꼴만 사용. 입·출력과 워크플로우 호환성은 그대로. ([릴리스 노트](RELEASE_NOTES_v2.0.9.md)) |
| 2.0.2 | Image Load 외부 폴더를 ComfyUI input / output 안으로 제한 (Registry 보안 정책) |
| 2.0.0 | Image + PiD를 독립 노드 팩으로 분리 (13종 → 12종) |

전체 기록은 [Releases](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases)에서 볼 수 있습니다.

---

## 🔞 성인용 옵션 안내

Prompt Composer와 Prompt Styler에는 성인(18+) 대상의 선택형 프롬프트 옵션이 있습니다. **기본값은 꺼져 있고**, 사용자가 직접 선택했을 때만 적용됩니다. 성인 인물만을 대상으로 하며 미성년자 묘사에는 사용할 수 없습니다. 생성물에 대한 책임은 사용자에게 있습니다.

---

## 📄 라이선스

- 코드, 메뉴얼, 예제 워크플로우, 데이터 파일: **GNU GPL v3.0** (`LICENSE`)
- `fonts` 폴더의 글꼴: GPL 적용 대상이 아니며, 각 글꼴의 원래 라이선스를 따릅니다. → [`fonts/FONTS_LICENSE.md`](fonts/FONTS_LICENSE.md)

Copyright (C) 2026 Yamoon-jjang

---

<a id="english"></a>

## 🇺🇸 English

**[🇰🇷 한국어](#korean) | 🇺🇸 English**

**Twelve practical ComfyUI nodes that take the busywork out of everyday generation.**

Picking, styling and translating prompts; finding and loading images; stamping a watermark on the result; checking model sizes and run times; cleaning up pops in generated audio — each node grew out of a real annoyance in day-to-day ComfyUI work and was refined until it stopped being one. Every node is independent, so you can drop in only the ones you need.

### ✨ Highlights

| | |
|---|---|
| 📦 **Zero extra dependencies** | No pip packages to install. Only libraries that already ship with ComfyUI are used. |
| 🌐 **English / Korean UI** | Node names, menus and help text follow your ComfyUI language setting automatically. |
| 🖥️ **Both canvases** | Built and tested for the new **Nodes 2.0 (Vue)** frontend and the classic LiteGraph canvas. |
| 🔒 **Safe by default** | File browsing stays inside folders ComfyUI manages, and API keys are never written into workflows. |
| 📖 **Per-node manuals** | Detailed manuals for every node are included in the `메뉴얼` (Manuals) folder (Korean). |
| 🔁 **Workflow-stable** | Node IDs and inputs/outputs are kept stable, so your saved workflows keep opening after updates. |

---

### 🗂️ Node Overview

| Group | Node | What it does for you |
|---|---|---|
| ✍️ Prompt | [Prompt Composer](#en-prompt-composer) | Build a **complete scene prompt from menus** — output tuned for 9 model families |
| ✍️ Prompt | [Prompt Styler](#en-prompt-styler) | **Keep your prompt as written** and add mood/style in each model's syntax |
| ✍️ Prompt | [Textbox](#en-textbox) | Up to **32 text slots** in one node, each with its own input and output |
| ✍️ Prompt | [Translator](#en-translator) | **Translate inside the workflow** — works without an API key, 20 languages |
| ✍️ Prompt | [Wildcard Browser](#en-wildcard-browser) | Browse wildcard folders and **copy `__folder/file__` with one click** |
| 📁 Image | [Image Load](#en-image-load) | Core Load Image plus a **thumbnail browser and in-place loading from output folders** |
| 🏷️ Finishing | [Text Watermark](#en-text-watermark) | Two-block **text watermark** with outline, glow and rotation — 15 fonts bundled |
| 🏷️ Finishing | [Image Watermark](#en-image-watermark) | **Logo/signature watermark** with tiling, blend modes, shadow and a MASK output |
| 🔊 Audio | [Audio Fade](#en-audio-fade) | **Removes start-of-clip pops** from generated audio without touching sync |
| 📊 Utility | [Model Viewer](#en-model-viewer) | Lists the **models the current workflow actually uses**, with file sizes |
| 📊 Utility | [Model Viewer (All)](#en-model-viewer) | **Scans all model folders by type** to find what's eating your disk |
| ⏱️ Utility | [Workflow Timer](#en-workflow-timer) | **Live run timer** plus a 100-run history and average |

Search for **`Ultra Tools`** in the node search; all nodes are grouped under the `Ultra Tools` category.

---

### 📦 Installation

#### ① ComfyUI Manager (easiest)

Open ComfyUI Manager → **Custom Nodes Manager**, search for **`Ultra Tools`** and install. ([Comfy Registry page](https://registry.comfy.org/publishers/yamoon-jjang/nodes/comfyui-ultra-tools))

#### ② Git

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git
```

To update, run `git pull` inside the `comfyui-Ultra-Tools` folder.

#### ③ Release ZIP

Download the [**v2.0.9 install ZIP**](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases/download/v2.0.9/comfyui-Ultra-Tools-v2.0.9.zip). It contains a single `comfyui-Ultra-Tools` folder — place that folder inside `ComfyUI/custom_nodes/`. The archive is packed so Korean file names extract correctly.

> ⚠️ When upgrading from an older ZIP, **back up and delete the old folder first**, then add the new one. Extracting on top of an old copy can leave behind files that were removed in newer versions.

After installing or updating, **fully restart ComfyUI** and **hard-refresh the browser (Ctrl+F5)**.

---

### 🚀 Quick Start

- **Example workflow:** drag `이미지 워크플로우/Ultra_Tools_Image_Load_Preview.json` onto the ComfyUI canvas, pick an image in Image Load, and queue it.
- **Handy combinations**

| You want to… | Wire it like this |
|---|---|
| Write prompts in your own language for an English-trained model | Textbox → **Translator** (english) → **Prompt Styler** → CLIP Text Encode |
| Build a prompt just by choosing from menus | **Prompt Composer** (positive / negative) → two CLIP Text Encode nodes |
| Brand your images with a logo and a credit line | Generated image → **Image Watermark** → **Text Watermark** → Save Image |
| Clean the audio pop on MiniMax H3 videos | H3 AUDIO → **Audio Fade** → Create Video |
| Compare generation speed across settings | Drop a **Workflow Timer** anywhere on the canvas (no wires needed) |
| Check which models a workflow needs before sharing it | Drop a **Model Viewer** on the canvas |

---

<a id="en-prompt-composer"></a>

### 🎨 Ultra Tools Prompt Composer

A prompt builder that **assembles a full scene prompt from menus**, with no external input required. It can also restyle a prompt you already have.

**Great if you…**
- would rather choose *who, where, how it's framed and in what art style* than type a prompt from scratch;
- need the same scene for both natural-language models and tag-based models;
- want to try many art styles quickly with random picks.

**Features**
- **9 model formats**: natural-language models (Z-Image, Krea2, Qwen, Flux), tag-based models (SDXL, Illustrious, Pony, SD 1.5) and the hybrid Anima format. The same choices are rewritten in the syntax each model understands best.
- **22 moods (+3 random modes) × 34 styles**: moods such as noir, gothic romance, cyberpunk, golden hour and vintage film; styles such as watercolor, oil painting, charcoal, pencil, ink wash, pixel art, miniature diorama, 3D figure and chibi. Choose `Auto by Mood` and the node picks a style that suits the mood.
- **15 framings · 17 lens looks** to control shot size and camera feel.
- **Scene builder**: combine subject (person, couple, group, scenery only, product/object), location, time of day, weather, props and lighting. Turn on scene detail enrichment for a fuller scene.
- Menu depth (basic / detailed / full) lets beginners start simple and power users see everything.
- **Conflict cleanup**: words like "photorealistic, DSLR" weaken a watercolor style — the node softens such conflicting terms for you.
- Your own `custom_text` is **never reworded into a different meaning**.
- Outputs a model-appropriate **negative prompt** alongside the positive.

**Tips**
- To style an existing prompt, connect it to `external_positive_in` and start with `balanced`. If the style is too weak, step up to `strong`.
- Random moods (e.g. `🎲 Random All`, `🎲 Random Traditional Media Style`) are seed-driven, so a combination you like can be reproduced.

---

<a id="en-prompt-styler"></a>

### 🖌️ Ultra Tools Prompt Styler

A styler that **keeps your prompt as intact as possible** and layers mood, style, framing and lens feel on top in the right syntax for each model. Its menus are simpler than Composer's, so it slots straight into an existing prompt pipeline.

**Great if you…**
- want to restyle prompts coming from a text node or another prompt generator;
- have seen odd results from clashing Pony / Illustrious / Anima rating and source tags.

**Features**
- Uses the same model formats, moods, styles, framings and lens looks as Composer.
- **Three style strengths** (`subtle` / `balanced` / `strong`) decide how much of your original wording to protect.
- **Merge position**: append after your prompt (recommended), prepend, or output the style phrase only — handy for mixing with other prompt builders.
- **Preserves weighted syntax** such as `(watercolor wash:1.3)` and repairs broken brackets and stray commas safely.
- Keeps **camera, lens and photorealism terms out of non-photographic styles** like watercolor, pencil and ink wash.
- **Resolves Pony / ILXL / Anima rating and source tag conflicts** automatically — e.g. `rating_safe` and `rating_explicit` never end up together.
- Merges your external negative with the model's default negative **without duplicates**, and avoids negatives that would erase light sources (lamps, candles, neon signs) present in your prompt.

**Tips**
- If a style doesn't take on Anima-family models, try disabling quality, speed or style LoRAs first — they often lock the art style. The manual walks through the checks in order.

---

<a id="en-textbox"></a>

### 📝 Ultra Tools Textbox

A text node that **manages many independent texts in a single node**.

**Great if you…**
- keep positive prompt, negative prompt, filename prefix and notes in a pile of separate text nodes;
- want to see — and edit — the string another node sends in.

**Features**
- **＋ Add text** grows the node up to **32 slots**. `Text N` is always paired as `IN N → OUT N`; slots never mix.
- **Connecting an input does not grey the slot out.** After a run the slot shows the string it actually received, so you can inspect, copy and edit it.
- **× Delete** any slot in the middle; connections on later slots stay intact.
- **Reorder with ⋀ ⋁** — content, name and wires all move together.
- **Rename** a slot ("action", "background", …) and the output socket is renamed too.
- A **Copy button** on every slot.
- Slot count and contents are saved in the workflow and restored exactly. JSON-looking strings are safely treated as plain text.

---

<a id="en-translator"></a>

### 🌐 Ultra Tools Translator

A lightweight node that translates text right inside your workflow. Defaults: **translate to Korean**, **auto-detect source language** — just change `target_language` to `english` (or any of the 20 languages). The output is a `STRING`, so it connects to any text or prompt node.

**Features**
- **Works without an API key** using the public MyMemory translation API.
- Free translation can hit `HTTP 429` (too many requests) under heavy use. Save an official **Google Cloud Translation API key** via the node's **Google Translate API settings** button (labelled `Google 번역 API 설정`): the official API is then tried first, with automatic fallback to MyMemory.
- The key is stored **only in this PC's ComfyUI user settings — never in the workflow file**. Sharing a workflow never shares your key, and a saved key is never shown again in the browser.
- **Shares the same key with Ultra MiniMax H3 Prompt** — save it in one node and the other uses it too.
- **Preserve line breaks** keeps line-based prompts structured.
- **Return original text on failure** keeps the workflow running even if translation fails.
- **20 languages**: English, Korean, Japanese, Chinese (Simplified / Traditional), Spanish, French, German, Italian, Portuguese, Russian, Ukrainian, Vietnamese, Thai, Indonesian, Hindi, Arabic, Turkish, Dutch, Polish.

---

<a id="en-wildcard-browser"></a>

### 🃏 Ultra Tools Wildcard Browser

Walk through your wildcard folders **one level at a time**; click a file and its wildcard call (e.g. `__01_Natural/K-Pop/female_singer__`) is **copied to the clipboard instantly**.

**Great if you…**
- use Impact Pack's wildcard processor and its **"add wildcard" list is empty or clicking does nothing** — copy here and paste there instead;
- have thousands of wildcard files and can never remember the exact path.

**Features**
- **Step-by-step navigation**: click into folders, `📁 ..` to go back. Large folders stay tidy because sub-files aren't dumped all at once.
- Shows only `.txt` `.yaml` `.yml` `.json`; files with the same name and different extensions are grouped.
- Supports symlinks and Windows junctions, and **blocks circular links** automatically.
- Remembers the last sub-folder you were viewing when the workflow is reopened.
- For safety, browsing is limited to **ComfyUI model folders (including `extra_model_paths.yaml`) and `wildcards` / `custom_wildcards` folders inside ComfyUI** (e.g. Impact Pack). The default path is `models/wildcards`.
- It takes no part in generation, so **a missing wildcard drive never breaks image generation**.

---

<a id="en-image-load"></a>

### 📁 Ultra Tools Image Load

Built **directly on ComfyUI's core Load Image**, with a far better way to pick images. Outputs (IMAGE / MASK) and the upload button match the core node, so it's a **drop-in replacement** for any existing Load Image.

**Great if you…**
- have hundreds of images in `input` and can't find anything from a file-name list;
- keep copying fresh results from `output` into `input` just to reuse them.

**Features**
- **Thumbnail browser** (the *View Input Thumbnails* button)
  - Switch between thumbnail and list views; file-name search; folder filter; thumbnail size slider.
  - Window size and view settings are remembered for next time.
  - Shows each image's resolution, and images with any aspect ratio are shown whole, never cropped.
  - Loads what's on screen first, so even large libraries scroll quickly.
- **Load from output folders in place**: register folders inside ComfyUI `output` and images load from where they are — **no copying into `input`**. Register as many as you like; sub-folders are included, and you see a live preview of a folder's images while browsing for it.
- Click to choose a candidate and press **Select**, or **double-click to apply instantly**. Closing with `Esc` leaves the node's current image unchanged.
- Ctrl/Shift-click to select several images and **delete them in one go**.
- Right-click *Open in new tab*, *Save as* and *Copy image* work on the **original full-resolution file**, not the thumbnail.

> ⚠️ Delete permanently removes the original files. Always check the file list shown before confirming.
>
> ℹ️ Since v2.0.2, to comply with Comfy Registry security policy, folders **outside** ComfyUI can no longer be registered. Upload such images with *choose file to upload*, or move them into the `output` folder.

---

<a id="en-text-watermark"></a>

### ✒️ Ultra Tools Text Watermark

Adds a **two-block, paragraph-style text watermark** — for example your name on top and your site address below.

**Features**
- Text 1 and Text 2 each get their own **font, size, color, alignment and style**, and both can span multiple lines.
- Per-text **outline**, and **glow** that can be switched on per text.
- Vertical or horizontal layout, block spacing, overall opacity, 9 anchor positions, fine X/Y offsets and **rotation**.
- **15 fonts bundled**, including Korean handwriting fonts and English script fonts (Happy Goheung, Nanum Pen/Brush Script, Binggrae Samanco, Pretendard, Great Vibes and more).
- Drop your own fonts (`.ttf` `.otf` `.ttc` `.otc`) into the `fonts` folder to add them to the list. For safety, system font folders are not read.

---

<a id="en-image-watermark"></a>

### 🖼️ Ultra Tools Image Watermark

Composites a logo, signature or icon image as a watermark.

**Features**
- Pick the watermark file with the node's **upload/select button**, or connect a Load Image as before. Transparency in PNG / WebP files is applied automatically.
- **Sizes by the visible logo, ignoring transparent padding** (percentage or pixel mode), so a small logo on a large transparent canvas doesn't end up tiny.
- Color invert, solid tint, outline, drop shadow and edge softening.
- 5 blend modes: normal / multiply / screen / overlay / soft light.
- **Tiling**: *full* grid or staggered *diagonal*, with adjustable spacing and rotation — ideal for copy-protection patterns.
- Also **outputs a MASK** of the watermarked area.
- Extreme settings that would blow up memory are **reported clearly before running**, never silently scaled down.

> 💡 Recommended order: original → **Image Watermark** (repeating logo) → **Text Watermark** (credit line) → Save Image

---

<a id="en-audio-fade"></a>

### 🔊 Ultra Tools Audio Fade

Applies **fade-in / fade-out** to generated audio. Made for models such as MiniMax H3 that can produce a **pop or crackle at the very start** of the audio.

- Just insert it in the AUDIO line. The default is a 0.15 s fade-in; if a pop remains, nudge it up to 0.18–0.20 s.
- 4 curves: smooth / linear / equal_power / exponential.
- **Never changes length, sample rate or audio/video sync**, and never overwrites the source data.
- On very short clips where fade-in + fade-out exceed the clip length, both fades are scaled down proportionally so they don't overlap.

---

<a id="en-model-viewer"></a>

### 📊 Ultra Tools Model Viewer / Model Viewer (All)

Two **read-only information nodes** for your model files. They never move or delete anything.

- **Model Viewer**: finds the models **the open workflow actually uses** and lists file names and sizes by type. It refreshes automatically when the graph changes — perfect for checking what someone needs before you share a workflow.
- **Model Viewer (All)**: **scans every model folder by type** — Checkpoint, UNET, LoRA, VAE, Text Encoder, CLIP, ControlNet, Upscale and more — showing counts, total size and a ranking of the largest files (top 5–100). Great for disk cleanup.
- Recognizes safetensors, ckpt, pt, gguf, onnx, nunchaku and other model formats.

---

<a id="en-workflow-timer"></a>

### ⏱️ Ultra Tools Workflow Timer

A **run timer** you simply place on the canvas — no wires required.

- Shows elapsed time **live** while a run is in progress.
- On completion, adds to a **history of the last 100 runs** with **total count and average time**.
- History is kept separately for each workflow tab.
- Perfect for **before/after speed comparisons** when you change models, samplers, resolution or optimization settings.

---

### ❓ FAQ / Troubleshooting

**I installed it but the nodes don't show up.**
Fully restart ComfyUI and hard-refresh the browser (Ctrl+F5). For ZIP installs, make sure the layout is `custom_nodes/comfyui-Ultra-Tools/__init__.py` — not nested one folder deeper.

**Translation suddenly stopped working (HTTP 429).**
That's the free API's rate limit. Wait a little, or save an official API key under *Google Translate API settings*. With *return original text on failure* enabled, your workflow keeps running either way.

**Image Load won't let me register a folder on another drive.**
Since v2.0.2, registration is limited to ComfyUI `input` / `output` for Comfy Registry security policy. Move the images into `output`, or upload them.

**Wildcard Browser doesn't show my wildcard folder.**
Place it in `ComfyUI/models/wildcards`, or in a `wildcards` / `custom_wildcards` folder inside ComfyUI (e.g. Impact Pack). Model paths registered in `extra_model_paths.yaml` can be browsed too.

**How do I use my own font in Text Watermark?**
Copy the font file into `comfyui-Ultra-Tools/fonts/` and restart ComfyUI.

**Where can I find more detail?**
Per-node manuals are in the `메뉴얼` folder (Korean). Bug reports and suggestions are welcome in [Issues](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/issues) — English is fine.

---

### 🧩 Where did Ultra Image + PiD go?

Since v2.0.0, the image-generation and PiD (PixelDiT) upscaling node lives in its own pack, **[Ultra Image + PiD](https://github.com/Yamoon-jjang/comfyui-Ultra-Image-PiD)** — it was moved, not discontinued. Its model dependencies and update cycle differ from the utility nodes, so splitting it keeps Ultra Tools light and stable.

- Only that one node left Ultra Tools; the other 12 nodes keep the same IDs and behavior.
- Old workflows containing `UltraImagePiD` are **not** converted to the new `UltraStandaloneImagePiD` automatically. Install the standalone pack, swap the node in and reconnect it.

---

### 🔗 Companion Nodes

- [**Ultra Image + PiD**](https://github.com/Yamoon-jjang/comfyui-Ultra-Image-PiD) — generate with several image model families from one node, with per-model settings memory and optional PiD upscaling
- [**Ultra Qwen Image Editor**](https://github.com/Yamoon-jjang/comfyui-Ultra-Qwen-Image-Editor) — all-in-one image editing node for the Qwen Image Edit family
- [**Ultra MiniMax H3 Prompt**](https://github.com/Yamoon-jjang/comfyui-Ultra-MiniMax-H3-Prompt) — prompt builder for MiniMax H3 video (T2V / I2V / R2V); shares its API key with Translator

---

### 📝 Recent Changes

| Version | Changes |
|---|---|
| **2.0.9** | Local path privacy — Wildcard Browser and Image Load show ComfyUI-relative paths instead of real disk paths; Text Watermark uses bundled fonts only. Inputs/outputs and workflow compatibility unchanged. ([release notes](RELEASE_NOTES_v2.0.9.md)) |
| 2.0.2 | Image Load external folders limited to ComfyUI input / output (Registry security policy) |
| 2.0.0 | Image + PiD moved to a standalone pack (13 → 12 nodes) |

See [Releases](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases) for the full history.

---

### 🔞 Adult Content Notice

Prompt Composer and Prompt Styler include optional adult (18+) prompt options. They are **off by default** and apply only when you select them. They are intended for adult subjects only and must not be used to depict minors. Users are responsible for what they generate.

---

### 📄 License

- Code, manuals, example workflows and data files: **GNU GPL v3.0** (`LICENSE`)
- Fonts in the `fonts` folder are not covered by the GPL; each keeps its original license → [`fonts/FONTS_LICENSE.md`](fonts/FONTS_LICENSE.md)

Copyright (C) 2026 Yamoon-jjang
