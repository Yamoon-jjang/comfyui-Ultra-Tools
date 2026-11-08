# Ultra Tools v2.0.8 — 12개 유틸리티 노드 / 12 utility nodes

## 🇰🇷 한국어

### v2.0.8 변경 사항
- **Translator**: 공식 API만 사용하도록 정리했습니다.
  - `google` 서비스는 사용자가 저장한 **Google Cloud Translation API(공식)** 키로 번역하고, 실패하거나 키가 없으면 **MyMemory 공개 API**를 사용합니다.
  - 비공식 Google 웹 번역 경로 두 곳을 제거했고, 모든 요청은 `ComfyUI-Ultra-Tools-Translator`라는 자기 이름으로 보냅니다.
  - 텍스트는 사용자가 노드를 실행할 때만 선택한 번역 서비스로 전송됩니다.
- **Translator API 키 저장**: ComfyUI `user` 폴더의 설정 파일만 읽고 씁니다. 다른 노드 팩의 코드를 불러오거나 호출하지 않습니다. (같은 작성자의 Ultra MiniMax H3 Prompt와 같은 파일 형식이라 키 하나를 함께 쓸 수 있습니다.)
- 그 밖의 노드는 v2.0.7과 같습니다.

### 설치
- Git: `ComfyUI/custom_nodes/`에서 `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git`
- ZIP: 아래 `comfyui-Ultra-Tools-v2.0.8.zip`을 받아 `ComfyUI/custom_nodes/comfyui-Ultra-Tools/` 형태로 설치합니다. ZIP으로 갱신할 때는 기존 폴더를 먼저 지우세요.

## 🇺🇸 English

### Changes in v2.0.8
- **Translator** now uses official APIs only.
  - The `google` service translates with the user's own **Google Cloud Translation API (official)** key and falls back to the **public MyMemory API** when no key is saved or the call fails.
  - The two unofficial Google web translation routes were removed; every request identifies itself as `ComfyUI-Ultra-Tools-Translator`.
  - Text is sent to the chosen translation service only when the user runs the node.
- **Translator API key storage** only reads and writes a config file in the ComfyUI `user` folder. It no longer loads or calls code from any other node pack. (The file format matches the same author's Ultra MiniMax H3 Prompt, so one key can serve both.)
- All other nodes are unchanged from v2.0.7.

### Install
- Git: `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git` inside `ComfyUI/custom_nodes/`
- ZIP: use `comfyui-Ultra-Tools-v2.0.8.zip` below; remove the old folder first when upgrading manually.
