# Ultra Prompt Composer data 폴더 안내

이 폴더에는 `🎨 Ultra Prompt Composer`가 사용하는 데이터 정의 파일이 들어 있습니다.
Python 본체에도 기본값이 포함되어 있으므로 일부 JSON 파일이 없더라도 노드가 바로 중단되지 않도록 설계되어 있지만, 배포본에서는 이 폴더의 파일을 함께 유지하는 것이 좋습니다.

## 주요 파일

- `model_profiles.json`  
  모델별 프롬프트 구성 방식과 negative 기본값을 정의합니다.

- `mood_families.json`  
  큰 분위기 계열을 정의합니다.

- `style_dna.json`  
  각 스타일의 anchor, lighting, color, composition, texture 문구를 정의합니다.

- `auto_style_by_mood.json`  
  분위기 선택 시 자동으로 연결될 스타일을 정의합니다.

- `lens_presets.json`  
  렌즈와 화면 느낌을 정의합니다.

- `scene_framing.json`  
  close portrait, waist-up, full body 같은 화면 범위와 구도를 정의합니다.

- `adult_wardrobe.json`  
  성인 의상 관련 선택지를 정의합니다.

- `explicitness.json`  
  성인 톤의 기본 표현 방향을 정의합니다.

## 수정 시 주의

- JSON 문법이 깨지면 ComfyUI 로딩 시 문제가 생길 수 있습니다.
- 키 이름을 바꾸면 기존 워크플로우와 호환되지 않을 수 있습니다.
- 화면에 표시되는 한국어 라벨은 `web/prompt_composer_locale.js`에서도 함께 관리됩니다.
- 단순 표시명만 바꾸는 경우에도 내부 키와 언어파일 매칭을 함께 확인하는 것이 좋습니다.
