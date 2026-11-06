# Ultra Tools v2.0.2 — 12개 유틸리티 노드 / 12 utility nodes

## 🇰🇷 한국어

### 변경 사항: Image Load의 외부 폴더를 ComfyUI output 안으로 제한
Comfy Registry가 v2.0.0을 `arbitrary-file-read, path-traversal`(임의 파일 읽기·경로 이탈) 사유로 보류했습니다. 원인은 **Ultra Tools Image Load**의 외부 폴더 기능이 드라이브 전체를 탐색하고, ComfyUI 밖의 파일까지 읽을 수 있는 구조였기 때문입니다. 이번 버전에서는 그 범위를 ComfyUI 폴더 안으로 좁혔습니다.

- **+ 폴더 추가** 화면이 드라이브 목록 대신 **ComfyUI input / output** 폴더에서 시작합니다. 그 밖으로는 올라가거나 이동할 수 없습니다.
- 등록할 수 있는 폴더는 **ComfyUI output 폴더와 그 하위 폴더**뿐입니다. input 폴더 이미지는 하위 폴더까지 이미 모두 표시되므로 따로 등록할 필요가 없습니다.
- **2.0.1 이하에서 ComfyUI 밖의 폴더(다른 드라이브, 다운로드 폴더 등)를 등록해 두었다면, 그 폴더는 더 이상 표시되지 않습니다.** 이런 이미지는 `choose file to upload`로 input에 올리거나, output 폴더 안으로 옮긴 뒤 등록하세요.
- output 폴더 안의 바로가기(심볼릭 링크·정션)가 output 밖을 가리키면, 그 대상 파일은 표시·불러오기·삭제하지 않습니다.
- 썸네일·원본 보기·삭제 기능도 같은 범위 안에서만 동작합니다.

### 그대로인 것
- input 폴더(하위 폴더 포함) 이미지의 목록, 썸네일, 검색, 정렬, 폴더 필터, 원본 열기·저장·복사, 다중 선택 삭제, 노드 프리뷰는 v2.0.1과 똑같이 동작합니다.
- 다른 11개 노드는 v2.0.1과 동일합니다. v2.0.1의 Workflow Timer 수정(레지스트리 자동 검사 오탐 회피)도 그대로 포함되어 있습니다.

### 설치
- Git: `ComfyUI/custom_nodes/`에서 `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git`
- ZIP: 아래 `comfyui-Ultra-Tools-v2.0.2.zip`을 받아 `ComfyUI/custom_nodes/comfyui-Ultra-Tools/` 형태로 설치합니다. ZIP으로 갱신할 때는 기존 폴더를 먼저 지우세요.
- Comfy Registry 버전이 `Active`가 되기 전에는 Manager 설치가 제한될 수 있습니다.

## 🇺🇸 English

### Change: Image Load extra folders are limited to ComfyUI output
Comfy Registry flagged v2.0.0 for `arbitrary-file-read, path-traversal`. The cause was **Ultra Tools Image Load**: its external-folder feature could browse whole drives and read files outside ComfyUI. This release limits that scope.

- The **+ Add folder** browser now starts at **ComfyUI input / output** instead of the drive list, and cannot navigate outside them.
- Only **ComfyUI output and its sub-folders** can be registered. Input images, including sub-folders, are already listed in full.
- **Folders outside ComfyUI that were registered in v2.0.1 or earlier are no longer shown.** Upload those images with `choose file to upload`, or move them into the output folder and register it.
- Symlinks/junctions inside output that point outside it are not listed, loaded or deleted.
- Thumbnail, original-view and delete routes follow the same limits.

### Unchanged
- Input-folder listing, thumbnails, search, sort, folder filter, original open/save/copy, multi-delete and node preview behave exactly as in v2.0.1.
- The other 11 nodes are identical to v2.0.1, including the Workflow Timer fix from v2.0.1.

### Install
- Git: `git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools.git` inside `ComfyUI/custom_nodes/`
- ZIP: download `comfyui-Ultra-Tools-v2.0.2.zip` below; remove the old folder first when upgrading manually.
- Manager installation may be limited until the Registry version becomes `Active`.

Repository: https://github.com/Yamoon-jjang/comfyui-Ultra-Tools
