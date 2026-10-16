# comfyui-Ultra-Tools

ComfyUI용 유틸리티 노드 13종 모음입니다. / A collection of 13 utility nodes for ComfyUI.

| 노드 | 설명 |
|---|---|
| Ultra Tools Textbox | 여러 줄 텍스트 입력·정리 |
| Ultra Tools Translator | 프롬프트 번역 |
| Ultra Tools Prompt Styler | 모델 계열별 스타일·분위기 프롬프트 생성 |
| Ultra Tools Prompt Composer | 장면·렌즈·구도·스타일 조합 프롬프트 생성 |
| Ultra Tools Image + PiD | 이미지 저장 + 모델 계열별 설정 기억 |
| Ultra Tools Image Load | 썸네일 브라우저가 있는 이미지 불러오기 |
| Ultra Tools Text Watermark | 글자 워터마크 |
| Ultra Tools Image Watermark | 이미지 워터마크 |
| Ultra Tools Model Viewer / Model Viewer (All) | 워크플로우·전체 모델 크기 보기 |
| Ultra Tools Wildcard Browser | 와일드카드 파일 탐색 |
| Ultra Tools Workflow Timer | 워크플로우 실행 시간 측정 |
| Ultra Tools Audio Fade | 오디오 페이드 인/아웃 |

자세한 사용법은 `메뉴얼` 폴더, 예제 워크플로우는 `이미지 워크플로우` 폴더를 참고하세요.

## 설치 / Installation

- **ComfyUI Manager**: `Ultra Tools` 검색 후 설치
- **수동 설치**:
  ```
  cd ComfyUI/custom_nodes
  git clone https://github.com/Yamoon-jjang/comfyui-Ultra-Tools
  ```
  추가로 설치할 pip 패키지는 없습니다. (ComfyUI 기본 라이브러리만 사용)

## 성인용 프롬프트 옵션 안내 / Adult content notice

Prompt Styler와 Prompt Composer에는 **성인(adult) 대상의 선택형 프롬프트 옵션**(`adult_tone`, `adult_wardrobe` 등)이 들어 있습니다.

- 모든 성인 옵션의 기본값은 꺼짐(`default` / `auto`)이며, 사용자가 직접 선택했을 때만 프롬프트에 반영됩니다.
- 성인 표현은 성인 인물만을 대상으로 합니다. 미성년자를 묘사하는 용도로 사용하는 것은 금지됩니다.
- 생성물에 대한 책임은 사용자에게 있으며, 사용하는 모델의 라이선스와 거주 지역의 법률을 따라야 합니다.

The Prompt Styler and Prompt Composer nodes include optional prompt options for adult (18+) content. They are **off by default** and only apply when selected by the user. They are intended for adult subjects only; depicting minors is prohibited. Users are responsible for their outputs and must comply with model licenses and local laws.

## 라이선스 / License

- 코드(Python/JavaScript), 메뉴얼, 예제 워크플로우, 데이터 파일: **GNU General Public License v3.0** (`LICENSE`)
- `fonts` 폴더의 글꼴: GPL 적용 대상이 아니며 각 글꼴의 원래 라이선스를 따릅니다. → `fonts/FONTS_LICENSE.md`

Copyright (C) 2026 Yamoon-jjang
