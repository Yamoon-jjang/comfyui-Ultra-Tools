# Ultra Tools v2.0.9 — 12개 유틸리티 노드 / 12 utility nodes

## 🇰🇷 한국어

### v2.0.9 변경 사항 — 로컬 경로 정보 보호
- **Wildcard Browser**
  - ComfyUI가 알고 있는 폴더 안에서만 탐색합니다: `models` 폴더와 등록된 모델 폴더(`extra_model_paths.yaml` 포함), 그 모델 루트, ComfyUI 폴더 안의 `wildcards` / `custom_wildcards` 폴더(Impact Pack 등).
  - 기본 경로를 `models/wildcards`(ComfyUI 폴더 기준)로 바꾸고, 개인 환경 경로 예시를 문서에서 정리했습니다.
  - 오류 메시지에 시스템 경로가 들어가지 않습니다.
- **Image Load**
  - 폴더 탐색 화면과 등록 폴더 목록에 실제 디스크 경로 대신 `output/하위폴더` 같은 ComfyUI 기준 경로만 표시합니다.
  - 허용 범위 밖의 경로는 존재 여부와 관계없이 같은 안내로 거절합니다.
- **Model Viewer**: 다른 Ultra Tools 기능과 같은 요청 확인을 적용했습니다.
- **Text Watermark**: 동봉된 `fonts` 폴더의 글꼴만 사용합니다(시스템 글꼴 폴더는 읽지 않음).
- **Prompt Composer / Prompt Styler**: 언어 감지에 ComfyUI 언어 설정 값만 사용합니다.
- **Translator**: 안내 문구를 현재 동작(공식 API → MyMemory)에 맞게 정리했습니다.
- 모든 노드의 입력·출력과 워크플로우 호환성은 v2.0.8과 같습니다.

### 설치
- Git: `ComfyUI/custom_nodes/`에서 `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git`
- ZIP: 아래 `comfyui-Ultra-Tools-v2.0.9.zip`을 받아 `ComfyUI/custom_nodes/comfyui-Ultra-Tools/` 형태로 설치합니다. ZIP으로 갱신할 때는 기존 폴더를 먼저 지우세요.

## 🇺🇸 English

### Changes in v2.0.9 — local path privacy
- **Wildcard Browser** only browses folders ComfyUI knows about: the `models` folder and registered model folders (including `extra_model_paths.yaml`), their models root, and `wildcards` / `custom_wildcards` folders inside ComfyUI (e.g. Impact Pack). The default path is now `models/wildcards`, and error messages no longer include system paths.
- **Image Load** shows ComfyUI-relative paths such as `output/sub` instead of real disk paths, and refuses paths outside input/output with the same message whether or not they exist.
- **Model Viewer** uses the same request check as the other Ultra Tools features.
- **Text Watermark** uses only the bundled `fonts` folder (system font folders are not read).
- **Prompt Composer / Prompt Styler** detect the language from ComfyUI's locale setting only.
- **Translator** help text now matches its behavior (official API, then MyMemory).
- Node inputs/outputs and workflow compatibility are unchanged from v2.0.8.

### Install
- Git: `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git` inside `ComfyUI/custom_nodes/`
- ZIP: use `comfyui-Ultra-Tools-v2.0.9.zip` below; remove the old folder first when upgrading manually.
