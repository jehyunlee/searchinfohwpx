# search-info-hwpx

**주제별 주간동향 HWPX 보고서 자동 생성 스킬**

원하는 주제를 입력하면, 논문/뉴스/특허를 자동으로 검색하고 중복을 제거한 뒤, 한컴오피스(한글)에서 바로 열 수 있는 `.hwpx` 동향 보고서를 만들어줍니다.

## 주요 기능

- **어떤 주제든 OK**: "휴머노이드", "AI for Science", "양자컴퓨팅" 등 원하는 주제를 입력하세요.
- **자동 병렬 검색**: 논문, 뉴스, 특허를 3개 에이전트가 동시에 검색합니다.
- **중복 자동 제거**: 같은 URL이나 비슷한 제목(80% 이상 유사)은 자동으로 걸러냅니다.
- **HWPX 문서 출력**: 한글(.hwpx) 양식에 맞춰 보고서를 자동 생성합니다.
- **한국어 출력**: 영문 제목과 요약을 한국어로 번역하고, 음슴체(명사형 종결)로 작성합니다.
- **Zotero 연동 (선택)**: Zotero를 사용하는 분만 설정하면 됩니다. 없어도 보고서 생성에 전혀 지장 없습니다.

## 설치 방법

### 1단계: 스킬 복사

이 저장소를 Claude Code 스킬 디렉토리에 복사합니다:

```bash
git clone https://github.com/jehyunlee/searchinfohwpx.git ~/.claude/skills/search-info-hwpx
```

### 2단계: Python 패키지 설치

```bash
pip install lxml
```

### 3단계: 첫 실행 시 자동 설정

처음 실행하면 다음 두 가지를 물어봅니다:

1. **HWPX 양식 파일 경로** — 보고서의 틀이 되는 `.hwpx` 파일 경로
2. **출력 폴더 경로** — 생성된 보고서가 저장될 폴더

입력한 설정은 `config.json`에 저장되며, 다음부터는 다시 묻지 않습니다.
설정을 바꾸고 싶으면 `config.json`을 삭제하고 다시 실행하면 됩니다.

### Zotero 연동 (선택사항)

> Zotero를 사용하지 않는 분은 이 단계를 건너뛰세요. 보고서 생성에 영향 없습니다.

Zotero에 논문/특허를 자동 등록하려면:

1. https://www.zotero.org/settings/keys 에서 API 키를 발급받으세요.
2. 환경변수로 설정합니다:

```bash
# Windows (PowerShell)
$env:ZOTERO_API_KEY="여기에_발급받은_키_입력"

# Mac/Linux
export ZOTERO_API_KEY="여기에_발급받은_키_입력"
```

Zotero 사용자 ID(숫자)는 API 키로부터 **자동으로 알아냅니다** — 직접 찾을 필요 없습니다.

> 주의: API 키는 `config.json`에 저장되지 않습니다 (보안). 매 실행 시 환경변수에서 읽습니다.

## 사용법

Claude Code에서 다음과 같이 입력하세요:

```
/search-info-hwpx 휴머노이드
/search-info-hwpx AI for Science 2주
/search-info-hwpx 양자컴퓨팅 1개월
/search-info-hwpx quantum computing --no-zotero
/search-info-hwpx 로봇공학 출력폴더:D:/reports
```

| 입력 | 설명 |
|------|------|
| `휴머노이드` | 주제 (필수) |
| `2주`, `1개월` | 검색 기간 (생략 시 최근 8일) |
| `--no-zotero` | Zotero 등록 건너뛰기 |
| `출력폴더:경로` | 이번에만 다른 폴더에 저장 |

## 실행 흐름

```
주제 입력
  ↓
1. 키워드 자동 생성
2. 논문/뉴스/특허 병렬 검색 (3개 에이전트)
3. 중복 제거 + 한국어 가공
4. HWPX 문서 생성
5. 문서 검증
6. Zotero 등록 (설정한 경우만)
7. 완료 요약 출력
```

## HWPX 양식 파일

자신만의 `.hwpx` 양식 파일이 필요합니다. 양식에는 다음이 포함되어야 합니다:

- 제목줄: `"휴머노이드 분야 국내외 동향"` (이 텍스트가 입력한 주제로 교체됩니다)
- 날짜 자리: `{오늘날짜YY.MM.DD}`
- 반복 항목 블록: `□`, `※`, `○`, `-` 기호로 구성된 패턴

## 파일 구조

```
search-info-hwpx/
├── SKILL.md              # 스킬 정의 (워크플로우 명세)
├── config.json           # 사용자 설정 (git에 포함 안 됨)
├── scripts/
│   ├── build_hwpx.py     # HWPX 문서 빌더 (중복 제거 포함)
│   ├── fix_namespaces.py  # HWPX 네임스페이스 후처리
│   └── validate.py        # HWPX 구조 검증
├── .gitignore
└── README.md
```

## 필요 환경

**필수:**
- Python 3.8 이상
- `lxml` 패키지 (`pip install lxml`)
- Claude Code + `search-info` 스킬의 `info-searcher` 에이전트

**선택 (Zotero 사용 시):**
- `ZOTERO_API_KEY` 환경변수

## 라이선스

MIT
