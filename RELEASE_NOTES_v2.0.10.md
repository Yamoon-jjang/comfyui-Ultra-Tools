# Ultra Tools v2.0.10 — 12개 유틸리티 노드 / 12 utility nodes

## 🇰🇷 한국어

### v2.0.10 변경 사항
- **Wildcard Browser**: 운영체제가 열기를 거부한 폴더(권한 없음 등)를 선택했을 때 오류 안내에 디스크 전체 경로가 표시되던 문제를 고쳤습니다. 이제 "폴더를 읽을 수 없습니다."만 표시합니다.
- **Model Viewer / Model Viewer (All)**: 모델 목록 요청에도 다른 Ultra Tools 기능과 같은 요청 확인(ComfyUI 화면에서 보낸 요청인지 확인)을 적용했습니다.
- **Image Load**: 이미지 목록 요청에도 같은 요청 확인을 적용했습니다.
- 모든 노드의 입력·출력과 워크플로우 호환성은 v2.0.9와 같습니다.
- 업데이트 후 Model Viewer에 `HTTP 403`이 보이면 ComfyUI 화면을 한 번 새로고침(Ctrl+F5)해 주세요.

### 설치
- Git: `ComfyUI/custom_nodes/`에서 `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git`
- ZIP: 아래 `comfyui-Ultra-Tools-v2.0.10.zip`을 받아 `ComfyUI/custom_nodes/comfyui-Ultra-Tools/` 형태로 설치합니다. ZIP으로 갱신할 때는 기존 폴더를 먼저 지우세요.

## 🇺🇸 English

### Changes in v2.0.10
- **Wildcard Browser**: when the operating system refused to open a folder (for example, no permission), the error text shown in the node included the full disk path. It now shows a fixed message only.
- **Model Viewer / Model Viewer (All)**: the model list requests now use the same request check as the other Ultra Tools features.
- **Image Load**: the image list request now uses the same request check.
- Node inputs/outputs and workflow compatibility are unchanged from v2.0.9.
- If Model Viewer shows `HTTP 403` right after updating, reload the ComfyUI page once (Ctrl+F5).

### Install
- Git: `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git` inside `ComfyUI/custom_nodes/`
- ZIP: use `comfyui-Ultra-Tools-v2.0.10.zip` below; remove the old folder first when upgrading manually.
