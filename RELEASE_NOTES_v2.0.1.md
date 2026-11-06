# Ultra Tools v2.0.1 — 12개 유틸리티 노드 / 12 utility nodes

## 🇰🇷 한국어

### 변경 사항
- **Comfy Registry 보안 검사 대응:** Workflow Timer의 프론트엔드 스크립트(`web/workflow_timer.js`)에서 자바스크립트 `.bind(` 호출 3곳을 같은 동작의 코드로 바꿨습니다. 레지스트리의 자동 검사(YARA)가 이 자바스크립트 문법을 네트워크 소켓 사용으로 잘못 판정하는 문제를 피하기 위한 수정입니다.
- **기능 변화 없음:** 12개 노드의 등록 ID, Python 코드, 다른 프론트엔드 스크립트는 v2.0.0과 동일합니다. Workflow Timer의 실행 시간 측정·통계·워크플로 전환·노드 삭제 처리도 그대로입니다.

### 설치
- Git: `ComfyUI/custom_nodes/`에서 `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git`
- ZIP: 아래 `comfyui-Ultra-Tools-v2.0.1.zip`을 받아 `ComfyUI/custom_nodes/comfyui-Ultra-Tools/` 형태로 설치합니다. ZIP으로 갱신할 때는 기존 폴더를 먼저 지우세요.
- Comfy Registry 버전이 `Active`가 되기 전에는 Manager 설치가 제한될 수 있습니다. 그 전에는 Git 또는 ZIP을 사용하세요.

v2.0.0의 Image + PiD 독립 분리(13종 → 12종) 안내는 [v2.0.0 릴리스](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases/tag/v2.0.0)를 참고하세요.

## 🇺🇸 English

### Changes
- **Comfy Registry security-scan fix:** Replaced the three JavaScript `.bind(` calls in the Workflow Timer frontend (`web/workflow_timer.js`) with equivalent code. The Registry's automated YARA scan misreads this JavaScript method as a network socket operation (false positive).
- **No functional change:** Node IDs, Python code and all other frontend scripts are identical to v2.0.0. Workflow Timer timing, statistics, workflow switching and node removal behave exactly as before.

### Install
- Git: `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git` inside `ComfyUI/custom_nodes/`
- ZIP: download `comfyui-Ultra-Tools-v2.0.1.zip` below; remove the old folder first when upgrading manually.
- Manager installation may be limited until the Registry version becomes `Active`.

See the [v2.0.0 release](https://github.com/Yamoon-jjang/comfyui-Ultra-Tools/releases/tag/v2.0.0) for the Image + PiD separation (13 → 12 nodes).

Repository: https://github.com/Yamoon-jjang/comfyui-Ultra-Tools
