# Ultra Tools v2.0.6 — 12개 유틸리티 노드 / 12 utility nodes

## 🇰🇷 한국어

### v2.0.6 변경 사항
- Comfy Registry 자동 검사에서 잘못 걸린 부분을 정리했습니다. **노드 기능은 v2.0.5와 같습니다.**
  - Text Watermark: Windows 글꼴 폴더를 찾는 방식을 바꿨습니다. ComfyUI가 실행되는 드라이브의 `Windows\Fonts`를 먼저 찾고, 없으면 `C:\Windows\Fonts`를 씁니다.
  - Image Load: 썸네일 브라우저와 노드 미리보기가 이미지를 표시하는 요소를 만드는 방식만 바꿨습니다. 화면과 동작은 같습니다.
  - 저장소 관리용 파일(`.github`, 릴리즈 노트)은 Registry 패키지에 넣지 않습니다.
- 예전 버전별 릴리즈 노트 파일을 정리했습니다. 이전 변경 내역은 GitHub 릴리즈 페이지에서 볼 수 있습니다.

### 설치
- Git: `ComfyUI/custom_nodes/`에서 `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git`
- ZIP: 아래 `comfyui-Ultra-Tools-v2.0.6.zip`을 받아 `ComfyUI/custom_nodes/comfyui-Ultra-Tools/` 형태로 설치합니다. ZIP으로 갱신할 때는 기존 폴더를 먼저 지우세요.

## 🇺🇸 English

### Changes in v2.0.6
- Cleaned up the parts that the Comfy Registry automated scan flagged by mistake. **Node behaviour is identical to v2.0.5.**
  - Text Watermark: the Windows font folder is now located as `Windows\Fonts` on the drive ComfyUI runs from, falling back to `C:\Windows\Fonts`.
  - Image Load: only the way the thumbnail browser and node preview create their image elements changed; display and behaviour are the same.
  - Repository maintenance files (`.github`, release notes) are no longer included in the Registry package.
- Removed the old per-version release note files. Earlier change history remains on the GitHub Releases page.

### Install
- Git: `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git` inside `ComfyUI/custom_nodes/`
- ZIP: use `comfyui-Ultra-Tools-v2.0.6.zip` below; remove the old folder first when upgrading manually.
