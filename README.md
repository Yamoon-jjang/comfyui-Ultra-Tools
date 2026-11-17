# 🧰 comfyui-Ultra-Tools

**ComfyUI를 더 편하게 쓰기 위한 12개 실용 커스텀 노드 모음 — v2.0.9.**
프롬프트 작성·스타일 조합, 이미지 탐색과 불러오기, 번역, 글자·이미지 워터마크, 모델 용량 확인, 워크플로우 실행 시간 기록, 오디오 페이드 등 자주 반복하는 작업을 간편하게 처리합니다. 기능은 노드별로 독립적이며 필요한 곳에 골라 연결할 수 있습니다.

- ✅ **추가 pip 설치 없음** — ComfyUI에 기본 포함된 라이브러리만 사용합니다.
- ✅ **한국어 / 영어 UI 자동 전환** — ComfyUI 언어 설정을 따릅니다.
- ✅ **노드별 상세 메뉴얼 포함** — `메뉴얼` 폴더에 노드별 한국어 설명서와 통합 설치 안내(KO/EN)가 있습니다.
- ✅ **Image Load 예제 워크플로우 포함** — `이미지 워크플로우/Ultra_Tools_Image_Load_Preview.json`

> 🇺🇸 English summary is at the [bottom of this page](#english-summary).

---

## ⚠️ v2.0.0 중요 변경: Image + PiD 독립 분리 (기능 폐지 아님)

**기존 13종 중 `Ultra Tools Image + PiD` 1종만 통합팩에서 분리되어, 이 버전에는 12종이 포함됩니다.** 기존 Textbox, Translator, Prompt Styler/Composer, Image Load, 워터마크, Model Viewer, Timer, Audio Fade 등 **나머지 12개 노드의 실행 코드와 등록 ID는 변경하지 않았습니다.**

- **왜 분리했나요?** 이미지 생성·PixelDiT 업스케일 노드는 모델별 의존성과 갱신 주기가 다른 유틸리티 노드와 다릅니다. 독립적인 설치와 업데이트를 지원하고 나머지 Ultra Tools를 가볍고 안정적으로 유지하기 위해 분리했습니다.
- **이제 어디서 사용하나요?** `Ultra Image + PiD`라는 **독립 커스텀 노드**로 분리했습니다. **GitHub 공개·Manager 등록은 별도로 진행할 예정**이므로 이 Ultra Tools 릴리즈에 포함됐다고 생각하지 마세요.
- **기존 워크플로우는?** 과거 `UltraImagePiD`가 있던 워크플로우는 자동으로 새 `UltraStandaloneImagePiD`로 변환되지 않습니다. 독립판 설치 후 노드를 교체하고 입력·출력 연결 및 모델 설정을 확인해야 합니다.
- **업데이트 시 주의:** ZIP을 기존 폴더에 그대로 덮어쓰면 삭제된 `ultra_image_pid.py`, `web/ultra_image_pid.js` 파일이 남을 수 있습니다. 기존 폴더를 백업 후 삭제하고 새 `comfyui-Ultra-Tools` 폴더를 설치하세요. ComfyUI Manager로 설치했다면 Manager의 업데이트 절차를 따르세요.
- 이 변경은 **Image + PiD에만 해당**하며 다른 12종의 워크플로우는 변경할 필요가 없습니다.

**🇬🇧 English:** v2.0.0 separates **Image + PiD** from Ultra Tools (13 → 12 nodes); **it is not discontinued**. The other 12 node IDs and runtime implementations remain unchanged. The standalone **Ultra Image + PiD** package will be published separately, not as part of this release. Old `UltraImagePiD` workflows are **not** auto-migrated to `UltraStandaloneImagePiD`: replace and reconnect the node. When upgrading from a ZIP, remove the old Ultra Tools directory first to avoid leftover scripts.

---

## 📦 설치 / Installation

**① Git 설치 — Registry가 Pending/Flagged일 때도 사용할 수 있는 방법**

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git
```

이미 Git으로 설치했다면 `comfyui-Ultra-Tools` 폴더에서 `git pull`로 업데이트합니다. Git으로 관리되는 삭제 파일은 업데이트 과정에서 제거됩니다. 기존 폴더에 사용자 수정 파일이 있다면 먼저 백업하세요.

**② GitHub 릴리즈 ZIP 수동 설치**

[**v2.0.9 설치용 ZIP**](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases/download/v2.0.9/comfyui-Ultra-Tools-v2.0.9.zip)을 받아 압축을 풀어 `ComfyUI/custom_nodes/comfyui-Ultra-Tools/` 형태로 설치합니다. 압축 내부 최상위 폴더는 `comfyui-Ultra-Tools`입니다.

**중요:** 이전 버전 ZIP을 수동으로 설치했다면 기존 폴더를 백업 후 **삭제하고** 새 폴더를 넣어야 합니다. 기존 폴더에 덮어쓰기만 하면 분리된 PiD의 `ultra_image_pid.py` 또는 `web/ultra_image_pid.js`가 남을 수 있습니다.

**③ ComfyUI Manager / Registry**

[Comfy Registry의 Ultra Tools 페이지](https://registry.comfy.org/publishers/yamoon-jjang/nodes/comfyui-ultra-tools)에 버전이 게시되어 있더라도 `Pending` 또는 `Flagged`이면 Manager에서 설치 가능하다는 보장은 없습니다. **Active가 확인된 경우에만 Manager 설치·업데이트를 이용**하고, 그 전에는 위 Git 또는 릴리즈 ZIP을 사용하세요. Registry 심사 상태는 개발자가 임의로 바꿀 수 없습니다.

설치·업데이트 후에는 ComfyUI를 완전히 재시작하고 브라우저를 새로고침(Ctrl+F5)하세요. 별도의 pip 패키지 설치는 요구하지 않으며 ComfyUI에 기본 포함된 라이브러리를 사용합니다.

**Image + PiD 분리 안내:** v2.0.0에는 이미지 생성·PiD 업스케일 노드가 포함되지 않습니다. 독립 `Ultra Image + PiD`는 나중에 별도로 공개합니다. 기존 `UltraImagePiD` 워크플로우는 `UltraStandaloneImagePiD`로 자동 변환되지 않습니다.

**🇬🇧 English:** Install with `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git` into `ComfyUI/custom_nodes/`, or use the [v2.0.9 ZIP](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases/download/v2.0.9/comfyui-Ultra-Tools-v2.0.9.zip). For manual ZIP upgrades, remove the old folder before extracting. Manager/Registry installation depends on the version becoming `Active`. Restart ComfyUI afterward. Image + PiD has moved to a separately released package; legacy workflows are not automatically converted.

---

## 🗂️ 한눈에 보기

| 분류 | 노드 | 한 줄 요약 |
|---|---|---|
| ✍️ 프롬프트 | [Prompt Composer](#prompt-composer) | 메뉴만 골라 **장면 프롬프트를 처음부터 조립** |
| ✍️ 프롬프트 | [Prompt Styler](#prompt-styler) | 내 프롬프트는 그대로 두고 **스타일·분위기만 모델 문법에 맞게 입힘** |
| ✍️ 프롬프트 | [Textbox](#textbox) | 노드 하나에 텍스트 칸 **최대 32개**, 칸마다 독립 입·출력 |
| ✍️ 프롬프트 | [Translator](#translator) | 워크플로우 안에서 바로 **번역** (API 키 없이도 동작) |
| ✍️ 프롬프트 | [Wildcard Browser](#wildcard-browser) | 와일드카드 폴더를 탐색하고 **`__폴더/파일__` 호출문을 클릭 한 번에 복사** |
| 📁 이미지 | [Image Load](#image-load) | Load Image에 **썸네일 브라우저 + output 폴더 직접 불러오기** 추가 |
| 🏷️ 마무리 | [Text Watermark](#text-watermark) | 두 줄 문단형 **글자 워터마크** (외곽선·글로우·회전) |
| 🏷️ 마무리 | [Image Watermark](#image-watermark) | 로고·서명 **이미지 워터마크** (타일 반복·블렌드·그림자) |
| 🔊 오디오 | [Audio Fade](#audio-fade) | 생성 오디오 **시작 부분 팝·찌직음 제거** |
| 📊 관리 | [Model Viewer](#model-viewer) | 현재 워크플로우가 쓰는 **모델과 용량** 확인 |
| 📊 관리 | [Model Viewer (All)](#model-viewer) | 모델 폴더 전체를 **종류별로 스캔**해 큰 파일 찾기 |
| ⏱️ 관리 | [Workflow Timer](#workflow-timer) | 실행 시간 **실시간 표시 + 기록 + 평균** |

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
- **분위기 22종(+랜덤 3종) × 스타일 34종**: 누아르, 고딕 로맨스, 사이버펑크, 골든아워, 빈티지 필름 같은 분위기 스타일과 수채화, 유화, 목탄, 연필, 수묵, 픽셀아트, 미니어처 디오라마, 3D 피규어, 치비 같은 화풍 스타일이 있습니다. `분위기에 맞춰 자동`을 고르면 분위기에 어울리는 스타일을 노드가 골라 줍니다.
- **구도 15종 · 렌즈 느낌 17종**으로 화면 범위와 카메라 느낌을 지정합니다.
- **단독 장면 만들기**: 주요 대상(인물·커플·그룹·배경만·제품/사물), 장소, 시간, 날씨, 소품, 조명을 조합합니다. `장면 디테일 보강`을 켜면 장면을 더 풍부하게 채워 줍니다.
- 메뉴 표시 범위(기본 / 상세 / 전체)를 고를 수 있어, 처음 쓰는 분은 기본 메뉴만, 익숙한 분은 전체 메뉴를 쓰면 됩니다.
- **충돌 정리**: 수채화를 골랐는데 원문에 "photorealistic, DSLR" 같은 말이 있으면 스타일이 약해집니다. 이럴 때 충돌하는 표현을 완화해 줍니다.
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
- Pony / Illustrious / Anima의 rating·source 태그가 서로 충돌해서 결과가 이상해진 경험이 있는 분

**주요 기능**
- Composer와 같은 모델 형식, 분위기, 스타일, 구도, 렌즈 체계를 씁니다.
- **스타일 반영 방식 3단계**(원본 보존 / 균형 적용 / 스타일 우선)로 원본을 얼마나 지킬지 정합니다.
- **합치는 위치 선택**: 원문 뒤에 붙이기(권장), 앞에 붙이기, 스타일 문구만 출력하기 중에서 고릅니다. 스타일 문구만 뽑아 다른 프롬프트 빌더와 섞어 쓸 수도 있습니다.
- `(watercolor wash:1.3)` 같은 **가중치 문법과 괄호를 최대한 보존**하고, 깨진 괄호나 쉼표도 안전하게 처리합니다.
- 수채화, 연필, 수묵 같은 **사진이 아닌 스타일에는 "카메라·렌즈·실사" 문구가 자동으로 섞이지 않게** 막아 줍니다.
- Pony / ILXL / Anima의 **rating·source 태그 충돌을 자동 정리**합니다. 예를 들어 `rating_safe`와 `rating_explicit`이 함께 들어가는 일을 막습니다.
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
- **＋ 텍스트 추가**로 칸을 최대 **32개**까지 늘립니다. `Text N`은 항상 `IN N → OUT N`으로 짝지어지고, 서로 섞이지 않습니다.
- **입력을 연결해도 칸이 회색 읽기 전용으로 바뀌지 않습니다.** 실행 후 실제로 받은 문자열이 칸에 표시되니, 바로 확인하고 복사하고 고칠 수 있습니다.
- 중간 칸만 골라 **× 삭제**할 수 있습니다. 뒤쪽 칸의 연결은 그대로 유지됩니다.
- **⋀ ⋁ 버튼으로 순서를 바꾸면** 내용, 이름, 연결선이 함께 따라 움직입니다.
- 이름을 클릭해 **직접 이름 붙이기**("행동", "배경" 등)를 하면 출력 단자 이름도 같이 바뀝니다.
- 칸마다 **Copy 버튼**이 있습니다.
- 칸 개수와 내용은 워크플로우에 저장되어 그대로 복원됩니다. JSON처럼 생긴 문자열을 넣어도 그냥 텍스트로 안전하게 취급합니다.

---

<a id="translator"></a>

## 🌐 Ultra Tools Translator

워크플로우 안에서 텍스트를 바로 번역하는 가벼운 번역 노드입니다. 기본 설정은 **한국어로 번역**입니다.

**주요 기능**
- **API 키 없이도** MyMemory 공개 번역 API로 바로 쓸 수 있습니다. Google Cloud Translation API 키를 저장하면 `google` 서비스가 공식 Google API를 먼저 사용합니다(실패 시 MyMemory).
- 무료 번역에서 `HTTP 429`(요청 과다) 제한이 걸리면, 공식 **Google Cloud Translation API Key**를 선택해서 등록할 수 있습니다. 이 키는 워크플로우 파일이 아니라 **이 PC의 ComfyUI 설정에만 저장**됩니다. 그래서 워크플로우를 공유해도 키가 따라가지 않습니다.
- API Key가 있으면 공식 API를 먼저 쓰고, Key가 없거나 실패하면 MyMemory 공개 API로 번역합니다.
- **줄바꿈 유지** 옵션이 있어, 줄 단위로 관리하는 프롬프트도 구조가 깨지지 않습니다.
- **번역 실패 시 원문 그대로 출력** 옵션을 켜면 번역이 실패해도 워크플로우가 멈추지 않습니다.
- 20개 언어를 지원합니다. 원문 언어는 자동 감지됩니다.
- Ultra MiniMax H3 Prompt 노드와 같은 API Key를 공유하므로, 한쪽에서 저장하면 다른 쪽에도 다시 입력할 필요가 없습니다.

---

<a id="wildcard-browser"></a>

## 🃏 Ultra Tools Wildcard Browser

와일드카드 폴더를 **한 단계씩 탐색**하다가 파일을 클릭하면, 그 파일의 호출문(`__01_Natural/K-Pop/female_singer__`)이 **바로 클립보드에 복사**됩니다.

**이런 분께 좋습니다**
- Impact Pack의 `와일드카드 처리기`에서 **"추가할 와일드카드" 목록이 안 나오거나, 클릭해도 삽입되지 않는** 분. 이 노드로 복사해서 붙여넣으면 해결됩니다.
- 와일드카드 파일이 수천 개라 정확한 경로를 찾기 어려운 분

**주요 기능**
- 폴더를 클릭해 들어가고 `📁 ..`으로 나오는 **단계별 탐색**을 합니다. 하위 파일을 한꺼번에 쏟아내지 않아 큰 폴더도 깔끔하게 볼 수 있습니다.
- `.txt` `.yaml` `.yml` `.json`만 표시합니다. 이름이 같고 확장자만 다른 파일은 하나로 묶습니다.
- 심볼릭 링크와 Windows 정션을 지원하고, **순환 링크는 자동으로 차단**합니다.
- 워크플로우를 다시 열면 마지막으로 보던 하위 폴더 위치를 기억해 둡니다.
- 보안을 위해 **ComfyUI 모델 폴더(`extra_model_paths.yaml` 포함)와 ComfyUI 안의 `wildcards` 폴더(Impact Pack 등)** 안에서만 탐색합니다. 기본 경로는 `models/wildcards`입니다.
- 생성 과정에는 참여하지 않는 노드라서, 와일드카드 드라이브가 빠져 있어도 **이미지 생성은 실패하지 않습니다.**

---

<a id="image-load"></a>

## 📁 Ultra Tools Image Load

ComfyUI 기본 **Load Image를 그대로 기반으로** 하고, 이미지를 고르는 화면을 크게 개선한 노드입니다. 출력(IMAGE / MASK)이 기본 노드와 똑같아서 **기존 Load Image 자리에 그대로 바꿔 끼우면** 됩니다.

**주요 기능**
- **썸네일 브라우저**
  - 썸네일 보기와 목록 보기를 전환할 수 있습니다.
  - 파일명 검색과 폴더 필터가 있고, 썸네일 크기 슬라이더로 크기를 조절합니다.
  - 창 크기와 보기 설정은 다음에 열 때도 그대로 유지됩니다.
  - 해상도도 함께 표시되고, 비율이 다른 이미지도 잘리지 않고 전체가 보입니다.
- **output 폴더 직접 불러오기**: ComfyUI output 안의 폴더를 등록하면 input 폴더로 **복사하지 않고** 원래 위치에서 바로 불러옵니다. 폴더는 여러 개 등록할 수 있고, 하위 폴더도 함께 보입니다. (v2.0.2부터 Comfy Registry 보안 정책에 따라 ComfyUI 밖의 드라이브·폴더는 등록할 수 없습니다.)
- 더블클릭으로 즉시 적용하고, Ctrl/Shift 클릭으로 여러 장을 선택해 **한꺼번에 삭제**할 수 있습니다.
- 우클릭 메뉴의 새 탭에서 열기, 다른 이름으로 저장, 이미지 복사는 썸네일이 아니라 **원본 해상도**로 동작합니다.
- 썸네일은 화면에 보이는 곳 위주로 먼저 불러와서, 이미지가 많아도 빠르게 넘겨 볼 수 있습니다.

> ⚠️ 삭제 기능은 실제 원본 파일을 영구 삭제합니다. 삭제 전에 표시되는 파일 목록을 꼭 확인하세요.

---

<a id="text-watermark"></a>

## ✒️ Ultra Tools Text Watermark

이미지에 **두 줄 구성의 문단형 텍스트 워터마크**를 넣습니다. 예를 들어 위에는 제작자명, 아래에는 사이트 주소를 넣는 식입니다.

**주요 기능**
- Text 1과 Text 2는 서로 **다른 글꼴, 크기, 색, 정렬, 스타일**을 쓸 수 있습니다. 여러 줄도 됩니다.
- 텍스트마다 **외곽선**을 따로 지정하고, **글로우**도 텍스트별로 켤 수 있습니다.
- 위아래 / 좌우 배치, 블록 간격, 전체 불투명도, 9방향 위치, X/Y 미세 조정, **회전**을 지원합니다.
- 패키지에 한글 손글씨체와 영문 필기체를 포함한 **글꼴 15종이 들어 있습니다.** `fonts` 폴더에 원하는 글꼴을 넣으면 목록에 추가됩니다. 폴더가 비어 있으면 시스템 글꼴을 자동으로 사용합니다.

---

<a id="image-watermark"></a>

## 🖼️ Ultra Tools Image Watermark

로고, 서명, 아이콘 이미지를 워터마크로 합성합니다.

**주요 기능**
- 노드의 **업로드/선택 버튼**으로 워터마크 파일을 바로 고릅니다. 기존처럼 Load Image를 연결해도 됩니다. 투명 PNG / WebP의 투명도는 자동으로 적용됩니다.
- **투명 여백을 뺀 실제 로고 크기 기준**으로 크기를 맞춥니다. 큰 투명 캔버스에 작은 로고가 있어도 로고가 지나치게 작아지지 않습니다.
- 색상 반전, 단색 틴트, 외곽선, 그림자, 경계 부드럽게 처리를 지원합니다.
- 블렌드 모드 5종(normal / multiply / screen / overlay / soft light)이 있습니다.
- **타일 반복**: 격자로 채우는 full과 엇갈리게 채우는 diagonal을 고르고, 간격과 회전을 조절해 저작권 보호용 패턴을 만들 수 있습니다.
- 워터마크가 들어간 영역을 **MASK로도 출력**합니다.
- 메모리가 폭증할 만한 극단적인 조합은 결과를 몰래 줄이지 않고, **실행 전에 명확히 알려 줍니다.**

> 💡 추천 순서: 원본 → **Image Watermark**(반복 로고) → **Text Watermark**(제작자 문구) → Save Image

---

<a id="audio-fade"></a>

## 🔊 Ultra Tools Audio Fade

생성된 오디오의 시작과 끝에 **페이드 인 / 아웃**을 적용합니다. MiniMax H3처럼 오디오 시작 순간에 **팝·찌직 소리**가 들어가는 경우를 위해 만들었습니다.

- AUDIO 선 중간에 끼워 넣기만 하면 됩니다. 기본값은 페이드 인 0.15초입니다.
- 곡선 4종(smooth / linear / equal_power / exponential)이 있습니다.
- **길이, 샘플레이트, 영상과의 싱크는 절대 바꾸지 않습니다.** 원본 데이터도 덮어쓰지 않습니다.
- 아주 짧은 클립에서 인과 아웃 시간의 합이 클립보다 길면, 두 페이드가 겹치지 않도록 비율을 유지한 채 자동으로 줄입니다.

---

<a id="model-viewer"></a>

## 📊 Ultra Tools Model Viewer / Model Viewer (All)

모델 파일을 확인하는 **정보 표시용 노드 2종**입니다. 파일을 옮기거나 지우는 기능은 없어서 안심하고 쓸 수 있습니다.

- **Model Viewer**: 지금 열려 있는 워크플로우가 **실제로 쓰고 있는 모델**을 찾아, 종류별로 파일명과 크기를 보여 줍니다. 워크플로우를 다른 사람에게 줄 때 필요한 모델 목록을 확인하기 좋습니다.
- **Model Viewer (All)**: 모델 폴더 전체를 Checkpoint, UNET, LoRA, VAE, Text Encoder, ControlNet, Upscale 같은 **종류별로 스캔**해, 개수와 총 용량, 큰 파일 순위를 보여 줍니다. 디스크 정리에 유용합니다.
- safetensors, ckpt, gguf, onnx 등 다양한 모델 형식을 인식합니다.

---

<a id="workflow-timer"></a>

## ⏱️ Ultra Tools Workflow Timer

캔버스에 올려 두기만 하면 되는 **실행 시간 측정기**입니다. 연결선이 필요 없습니다.

- 실행 중에는 경과 시간을 **실시간으로** 보여 줍니다.
- 끝나면 **기록(최근 100회)**과 **총 횟수·평균 시간**이 쌓입니다.
- 워크플로우 탭마다 기록이 따로 관리됩니다.
- 모델, 샘플러, 해상도, 최적화 설정을 바꿨을 때 **전후 속도를 비교**하기 좋습니다.

---

## 🔞 성인용 옵션 안내

Prompt Composer와 Prompt Styler에는 성인(18+) 대상의 선택형 프롬프트 옵션이 있습니다. **기본값은 꺼져 있고**, 사용자가 직접 선택했을 때만 적용됩니다. 성인 인물만을 대상으로 하며 미성년자 묘사에는 사용할 수 없습니다. 생성물에 대한 책임은 사용자에게 있습니다.

---

## 📄 라이선스

- 코드, 메뉴얼, 예제 워크플로우, 데이터 파일: **GNU GPL v3.0** (`LICENSE`)
- `fonts` 폴더의 글꼴: GPL 적용 대상이 아니며, 각 글꼴의 원래 라이선스를 따릅니다. → [`fonts/FONTS_LICENSE.md`](fonts/FONTS_LICENSE.md)

Copyright (C) 2026 Yamoon-jjang

---

<a id="english-summary"></a>

## 🇺🇸 English Summary

**comfyui-Ultra-Tools** is a collection of 12 carefully refined ComfyUI nodes. No extra pip packages are needed. The UI switches between Korean and English automatically.

**Install:** Clone the [Git repository](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools) or download the [v2.0.9 install ZIP](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases/download/v2.0.9/comfyui-Ultra-Tools-v2.0.9.zip). Registry publication does not guarantee Manager installation until a version becomes Active; Git and ZIP installation work independently of Registry review. When updating older manually extracted ZIPs, remove the old folder first.

**Since v2.0.0:** Image + PiD has been separated as **Ultra Image + PiD** and is not included in this 12-node collection. Its public standalone release will follow separately. The included example is Image Load → Preview Image; select an existing image before running.

| Node | What it does |
|---|---|
| **Prompt Composer** | Builds full scene prompts from menus (subject, location, time, weather, props, framing, lens, 22 moods × 34 styles), or styles an existing prompt. Outputs model-specific positive/negative prompts for 9 model formats (natural-language and tag-based). |
| **Prompt Styler** | Keeps your prompt intact and adds mood/style/framing/lens in the right syntax for each model. Preserves weighted syntax `(tag:1.3)`, keeps photo/lens terms out of painterly styles, and resolves Pony/Illustrious/Anima rating and source tag conflicts. |
| **Textbox** | Up to 32 independent text slots in one node (IN N → OUT N). Inputs stay editable and visible, rows can be reordered, renamed, copied, and deleted individually. |
| **Translator** | In-workflow translation (default: to Korean). Works without an API key via the public MyMemory API; an optional Google Cloud key is stored locally, never in workflows. Can preserve line breaks and fall back to the original text on error. |
| **Wildcard Browser** | Browse wildcard folders step by step and copy `__folder/file__` with one click. A workaround when Impact Pack's wildcard list fails. |
| **Image Load** | A drop-in Load Image replacement with a thumbnail/list browser, search, folder filter, and ComfyUI output sub-folders loaded in place without copying (since v2.0.2, folders outside ComfyUI input/output can no longer be registered). Supports multi-select delete and original-resolution open/save/copy. |
| **Text Watermark** | Two-block text watermark with per-text font, outline, and glow, plus layout, rotation, and opacity controls. 15 fonts bundled. |
| **Image Watermark** | Logo watermark with upload button, alpha-aware sizing, tint, stroke, shadow, 5 blend modes, full/diagonal tiling, and a MASK output. |
| **Audio Fade** | Non-destructive fade in/out to remove start-of-audio pops (e.g. MiniMax H3). Never changes length, sample rate, or sync. |
| **Model Viewer / (All)** | Shows the models the current workflow uses, or scans all model folders by category with sizes. |
| **Workflow Timer** | Live run timer with a history of the last 100 runs and the average time, tracked per workflow. |

**Adult content notice:** Prompt Composer and Prompt Styler include optional adult (18+) prompt options. They are **off by default**, intended for adult subjects only, and must not be used to depict minors.

**License:** GPL-3.0 for code. Bundled fonts keep their own licenses (see `fonts/FONTS_LICENSE.md`).
