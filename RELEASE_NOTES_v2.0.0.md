# Ultra Tools v2.0.0 — 12개 유틸리티 노드 / 12 utility nodes

## 🇰🇷 한국어

### 중요: Image + PiD 노드의 독립 분리 (삭제·폐지 아님)

이번 v2.0.0부터 **`Ultra Tools Image + PiD`는 Ultra Tools 통합 패키지에 포함되지 않습니다.** 기존 13개에서 **12개 노드**로 구성되며, 이미지 생성과 PixelDiT 업스케일 기능은 **`Ultra Image + PiD` 독립 커스텀 노드**로 분리했습니다. **독립 노드의 GitHub 공개 및 ComfyUI Manager 등록은 별도로 진행할 예정**입니다.

**분리 이유:** 모델별 이미지 생성·PiD 업스케일 기능은 유틸리티 도구들과 업데이트 주기·의존성이 다릅니다. 두 프로젝트를 독립적으로 관리해 안정성과 유지보수성을 높이기 위한 변경입니다.

**나머지 노드 12개는 그대로 유지합니다.** Textbox, Audio Fade, Translator, Model Viewer 2종, Wildcard Browser, Workflow Timer, Text Watermark, Image Watermark, Prompt Styler, Prompt Composer, Image Load의 등록 ID 및 실행 코드는 이전 버전과 동일합니다.

### 설치 / Manager 상태
- **권장 설치:** Git 저장소를 `ComfyUI/custom_nodes/`에 `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git`로 설치하거나 [공식 v2.0.0 ZIP](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases/download/v2.0.0/comfyui-Ultra-Tools-v2.0.0.zip)을 사용합니다.
- **Comfy Registry:** 버전 업로드 성공과 ComfyUI Manager에서 설치 가능한 Active 상태는 다릅니다. `Pending`/`Flagged`에서는 Manager 설치가 제한될 수 있으므로 Git 또는 ZIP을 사용하세요. [Registry 페이지](https://registry.comfy.org/publishers/yamoon-jjang/nodes/comfyui-ultra-tools)

### 기존 사용자 필독
- 이전 워크플로우의 `UltraImagePiD`는 새 독립판의 `UltraStandaloneImagePiD`로 **자동 전환되지 않습니다**. 독립판 설치 후 새 노드로 교체하고 소켓 연결·모델 설정을 확인하세요.
- **ZIP으로 수동 설치를 갱신할 때는** 기존 `ComfyUI/custom_nodes/comfyui-Ultra-Tools` 폴더를 백업 후 제거하고 새 폴더를 설치하세요. 단순 덮어쓰기에서는 삭제된 PiD 스크립트가 남습니다.
- **ComfyUI Manager 사용자**는 Manager의 업데이트 기능으로 갱신하고 ComfyUI를 재시작하세요.
- 기존 PiD 생성 기능이 자동으로 다른 노드에 흡수된 것은 아니며, **독립판을 설치하지 않은 환경에서는 사용할 수 없습니다**.

### 기타 변경
- PiD 관련 Python/JS, 번역 데이터, 전용 메뉴얼과 PiD 예제만 제거
- README 및 한국어·영어 설치 안내를 12개 노드 기준으로 정리
- 새로운 기본 예제: `이미지 워크플로우/Ultra_Tools_Image_Load_Preview.json` (Image Load → Preview Image)
- 나머지 노드의 모델·사용자 설정·워터마크·프롬프트 처리 로직은 변경하지 않음

## 🇺🇸 English

### Breaking change: Image + PiD moved to a standalone package (NOT discontinued)

Starting with v2.0.0, **`Ultra Tools Image + PiD` is no longer bundled with Ultra Tools.** The bundle contains **12 nodes instead of 13**. Generation and PixelDiT upscaling have moved to a standalone custom node named **`Ultra Image + PiD`**; its public GitHub/Manager release is planned separately.

**Why?** The model-specific image-generation/upscaling engine has different dependencies and maintenance requirements from the general utility nodes. Splitting them enables independent updates without disrupting the core utility collection.

**The remaining 12 nodes are unchanged:** Their node IDs, Python implementations, and frontend scripts are preserved.

**Installation and Registry status**
- Install from [Git](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools) or the [v2.0.0 install ZIP](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases/download/v2.0.0/comfyui-Ultra-Tools-v2.0.0.zip). Publishing a Registry version does not imply that it is Active or installable in ComfyUI Manager; Pending/Flagged may require review.

**Upgrade guidance**
- Old workflows referencing `UltraImagePiD` are **not automatically compatible** with the new `UltraStandaloneImagePiD`. Install the standalone package once released, then replace/reconnect the node and verify model selections.
- For ZIP/manual upgrades, back up and **remove the old `comfyui-Ultra-Tools` folder** before installing the new release. Overlay extraction may leave behind obsolete PiD scripts.
- For Manager upgrades, use the built-in update flow and restart ComfyUI.
- PiD functionality is **not bundled in this release**. It has not been silently moved into one of the remaining nodes.

**Other changes**
- Remove only PiD-specific code, localization, manual and sample workflow.
- Refresh README and bilingual installation guide for the 12-node bundle.
- Add an Image Load → Preview Image example.
- Preserve all remaining node implementations.

Repository: https://github.com/Yamoon-jjang/comfyui-Ultra-Tools
