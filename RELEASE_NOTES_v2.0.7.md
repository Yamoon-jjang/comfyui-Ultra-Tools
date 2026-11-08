# Ultra Tools v2.0.7 — 12개 유틸리티 노드 / 12 utility nodes

## 🇰🇷 한국어

### v2.0.7 변경 사항
- Comfy Registry 자동 검사(yara_scan)가 Image Load의 변수 이름을 네트워크 코드로 잘못 판단한 문제를 고쳤습니다. **노드 기능은 v2.0.6과 같습니다.**
  - 원인: 썸네일 크기 확인 중인 항목을 담는 변수 `dimensionRequests`의 `.delete(` 호출이 Python 네트워크 라이브러리 호출 `requests.delete(`와 같은 글자로 인식됐습니다(대소문자 구분 없음).
  - 수정: 변수 이름만 `pendingDimensionProbes`로 바꿨습니다. 동작은 바뀌지 않았습니다.

### 설치
- Git: `ComfyUI/custom_nodes/`에서 `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git`
- ZIP: 아래 `comfyui-Ultra-Tools-v2.0.7.zip`을 받아 `ComfyUI/custom_nodes/comfyui-Ultra-Tools/` 형태로 설치합니다. ZIP으로 갱신할 때는 기존 폴더를 먼저 지우세요.

## 🇺🇸 English

### Changes in v2.0.7
- Fixed a Comfy Registry automated scan (yara_scan) false positive in Image Load. **Node behaviour is identical to v2.0.6.**
  - Cause: the `.delete(` call on the variable `dimensionRequests` matched the Python network call pattern `requests.delete(` (case-insensitive).
  - Fix: the variable was renamed to `pendingDimensionProbes`; nothing else changed.

### Install
- Git: `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git` inside `ComfyUI/custom_nodes/`
- ZIP: use `comfyui-Ultra-Tools-v2.0.7.zip` below; remove the old folder first when upgrading manually.
