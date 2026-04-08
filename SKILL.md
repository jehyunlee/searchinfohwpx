---
name: search-info-hwpx
description: "주제별 주간동향 HWPX 보고서 자동 생성. 논문/뉴스/특허 병렬 검색 → 중복 제거 → Zotero 등록(선택) → HWPX 문서 생성. 트리거: '주간동향', '동향 hwpx', 'weekly report', '{주제} 동향', 'search-info-hwpx'."
---

# Search Info HWPX — 주제별 주간동향 HWPX 보고서

임의의 주제에 대해 논문/뉴스/특허를 병렬 검색하고, 중복을 제거한 뒤, HWPX 동향 보고서를 자동 생성하는 통합 스킬.

## 입력 파라미터

| 파라미터 | 필수 | 설명 | 예시 |
|---------|------|------|------|
| `주제` (topic) | Yes | 동향 조사 주제 | "휴머노이드", "AI for Science", "양자컴퓨팅" |
| `기간` (period) | No | 검색 기간 (기본: 8일) | "2주", "1개월", "8days" |
| `--no-zotero` | No | Zotero 등록 건너뛰기 | |

사용자가 주제를 전달한다. 누락 시 반드시 물어본다.

## 초기 설정 (Phase 0)

스킬 디렉토리에 `config.json`이 없으면 **첫 실행 시 사용자에게 설정을 물어본다**.

**config.json 경로**: `{이 스킬 디렉토리}/config.json`

```json
{
  "zotero_user_id": "1356104",
  "hwpx_template": "C:/path/to/양식.hwpx",
  "output_dir": "C:/path/to/output/"
}
```

**설정 항목 및 질문:**

| 항목 | 질문 | 기본값 |
|------|------|--------|
| `hwpx_template` | "HWPX 양식 파일(.hwpx) 경로를 입력해주세요" | 없음 (필수) |
| `output_dir` | "출력 파일을 저장할 디렉토리 경로를 입력해주세요" | 없음 (필수) |

**Zotero 설정 (자동):**

`zotero_user_id`는 사용자에게 묻지 않는다. 대신 다음 절차로 자동 획득한다:

1. `ZOTERO_API_KEY` 환경변수 확인
2. 환경변수가 있으면 → `GET https://api.zotero.org/keys/{ZOTERO_API_KEY}` 호출
3. 응답의 `userID` 필드를 `config.zotero_user_id`에 저장
4. 환경변수가 없으면 → Zotero 연동 건너뜀 + 안내 메시지 출력:
   "Zotero 연동을 원하시면 ZOTERO_API_KEY 환경변수를 설정하세요. API 키는 https://www.zotero.org/settings/keys 에서 발급받을 수 있습니다."

**Zotero API Key 규칙:**
- `ZOTERO_API_KEY` 환경변수에서 읽는다
- config.json에 API key를 **저장하지 않는다** (`zotero_user_id`만 저장)
- 환경변수가 없으면 Zotero 기능을 건너뛴다
- 이후 실행 시 config에 `zotero_user_id`가 있어도 `ZOTERO_API_KEY` 환경변수가 없으면 Zotero를 건너뛴다

**설정 완료 후:**
- config.json을 스킬 디렉토리에 저장
- 이후 실행에서는 config.json을 읽어서 경로를 사용
- 설정 변경이 필요하면 config.json을 직접 편집하거나 삭제 후 재실행

## 경로 규칙

config.json에서 읽은 값을 사용한다:

| 항목 | 소스 |
|------|------|
| HWPX 양식 | `config.hwpx_template` |
| 출력 디렉토리 | `config.output_dir` |
| 출력 파일명 | `{output_dir}/{YYMMDD}_{topic_slug}_주간동향.hwpx` |
| 빌드 스크립트 | `{이 스킬 디렉토리}/scripts/build_hwpx.py` |
| HWPX 후처리 | `{이 스킬 디렉토리}/scripts/fix_namespaces.py`, `scripts/validate.py` |
| 작업 디렉토리 | `_workspace/` (현재 프로젝트 내) |

`{YYMMDD}`는 오늘 날짜 (예: `260406`).
`{topic_slug}`: 주제에서 공백→`_`, 특수문자 제거 (예: "AI for Science" → "AI_for_Science").

## 워크플로우

### Phase 1: 준비

1. **config.json 로드** — 없으면 Phase 0(초기 설정) 실행
2. 날짜 계산:
```
오늘: YYYY-MM-DD
기간 시작일: DATE_CUTOFF (기본 8일 전)
YYMMDD: 오늘 날짜의 YY+MM+DD
YY.MM.DD: 오늘 날짜의 YY.MM.DD (문서 헤더용)
topic_slug: 주제에서 파일명용 slug 생성
```

3. **키워드 자동 생성:**
주제명에서 검색 키워드를 자동 도출한다. 에이전트 프롬프트에 포함할 키워드 목록:
- 주제의 영문명/한글명 양쪽
- 주제의 핵심 하위 분야 3-5개
- 주요 기업/기관명 5-10개 (해당 분야에서 알려진 주체들)

예시 (주제: "휴머노이드"):
- 키워드: `humanoid robot`, `humanoid locomotion`, `bipedal robot`, `whole-body control`
- 기업: `Tesla Optimus`, `Figure AI`, `Unitree`, `Boston Dynamics`

예시 (주제: "AI for Science"):
- 키워드: `AI for science`, `scientific discovery AI`, `AI-driven research`, `machine learning science`
- 기관: `DeepMind`, `Meta AI`, `Google Research`, `Microsoft Research`

### Phase 2: 검색 (3개 에이전트 병렬)

`_workspace/` 디렉토리 생성 후 3개 `info-searcher` 에이전트를 `run_in_background`로 동시 실행:

| 에이전트 | 검색 대상 | 출력 |
|---------|----------|------|
| paper-searcher | arXiv, Semantic Scholar 등 논문 | `_workspace/paper_results.json` |
| news-searcher | 기술/일반 매체 뉴스 | `_workspace/news_results.json` |
| patent-searcher | Google Patents, USPTO 등 특허 | `_workspace/patent_results.json` |

각 에이전트에게 Phase 1에서 생성한 키워드를 전달한다.

각 에이전트 결과 JSON 형식:
```json
[
  {
    "source": "동향 주체 (기업/기관명)",
    "title_en": "원본 영문 제목",
    "title": "한국어 제목",
    "date": "YYYY-MM-DD",
    "url": "원본 URL",
    "summary": "한국어 핵심내용 2-3문장",
    "type": "paper|news|patent"
  }
]
```

### Phase 3: 중복 제거 및 결과 가공

3개 JSON을 읽고 **중복 제거** 후 가공하여 `_workspace/processed_items.json` 생성.

#### 중복 제거 규칙 (매우 중요)

다음 기준으로 중복을 판별하고 제거한다:

1. **URL 동일**: 완전히 같은 URL → 하나만 유지 (더 상세한 summary를 가진 것 선택)
2. **제목 유사도**: 영문 제목(title_en)을 정규화(소문자, 구두점 제거)한 뒤 80% 이상 겹치면 동일 건으로 판정
3. **내용 동일**: 서로 다른 매체가 같은 사건/발표를 보도한 경우 → 가장 원본에 가까운 소스 하나만 유지
   - 우선순위: 공식 발표/논문 > 전문매체 > 일반매체
   - 예: 같은 Tesla Optimus 발표를 Reuters, TechCrunch, 블로그가 각각 보도 → 공식 소스 또는 가장 상세한 보도 1건만 유지

중복 제거 후 제거된 건수를 로그에 기록한다.

#### 가공 규칙

1. **날짜 필터**: `DATE_CUTOFF` 이후 항목만 포함
2. **source 매핑**: 뉴스의 경우 언론사가 아닌 동향의 주체 기업/기관명 사용
   - 예: Washington Post → Tesla, Fortune → Figure AI
   - 논문: 첫 번째 저자 소속 또는 `arXiv` 등 원본 소스 유지
   - 특허: 출원인/회사명 사용
3. **제목 번역**: 영문 제목을 한국어로 짧고 전문성 있게 번역
4. **source-title 중복 제거**: source가 title 시작부에 반복되면 삭제
5. **summary 음슴체**: 서술형 종결을 명사형/음슴체로 변환
   - 예: "~을 달성했다" → "~을 달성", "~중이다" → "~중"
6. **정렬**: 날짜 내림차순 (최신이 맨 위)

### Phase 4: Zotero 등록 (선택)

`--no-zotero` 플래그가 없고, `ZOTERO_API_KEY` 환경변수가 존재할 때만 실행.
`config.zotero_user_id`가 없으면 `/keys/{key}` API로 자동 획득 후 config에 저장한다.

1. Zotero Web API로 컬렉션 목록 조회:
```python
# Zotero API: GET /users/{config.zotero_user_id}/collections
# 환경변수 ZOTERO_API_KEY 사용
```

2. **주제명과 동일한 이름의 컬렉션이 있는지 확인** (대소문자 무시)
   - 있으면: 해당 컬렉션에 논문/특허 항목 추가
   - **없으면: Zotero 업로드 건너뛰고 사용자에게 알림** (컬렉션 자동 생성하지 않음)

3. 업로드 대상: 논문과 특허만 (뉴스는 제외)
4. 각 항목에 대해 Zotero 아이템 생성:
   - 논문: itemType=journalArticle 또는 preprint
   - 특허: itemType=patent
5. 기존 등록된 항목과 URL/DOI로 중복 체크하여 이미 있는 항목은 건너뛰기

### Phase 5: HWPX 빌드

```bash
PYTHONUTF8=1 python "{스킬디렉토리}/scripts/build_hwpx.py" \
  --template "{config.hwpx_template}" \
  --output "{config.output_dir}/{YYMMDD}_{topic_slug}_주간동향.hwpx" \
  --data "_workspace/processed_items.json" \
  --today "{YY.MM.DD}" \
  --title "{주제} 분야 국내외 동향"
```

`--title` 파라미터로 문서 제목을 지정한다. 양식의 "휴머노이드 분야 국내외 동향"이 이 값으로 교체된다.

### Phase 6: 후처리 + 검증

```bash
PYTHONUTF8=1 python "{스킬디렉토리}/scripts/fix_namespaces.py" "{출력파일}"
PYTHONUTF8=1 python "{스킬디렉토리}/scripts/validate.py" "{출력파일}"
```

### Phase 7: 요약 출력

```
============================================
  {주제} 주간동향 생성 완료
============================================
파일: {YYMMDD}_{topic_slug}_주간동향.hwpx
수록: 뉴스 N건, 논문 N건, 특허 N건 (총 N건)
중복 제거: N건 제거됨
기간: {DATE_CUTOFF} ~ {오늘}
Zotero: {컬렉션명}에 N건 등록 / 컬렉션 없어 건너뜀 / 미설정
검증: PASS
============================================
```

## HWPX 양식 구조

양식은 반복 패턴으로 구성:

```
□ {주체기관}, {한국어 동향 제목}({MM.DD})
   ※ {URL} ← 하이퍼링크 (HWPX fieldBegin/fieldEnd)
  ○ {핵심내용 요약}
    - {상세 설명}
```

**서식 규칙:**
- 본문 텍스트: `spacing="0"` (자간 자동조절 금지)
- URL 텍스트: `spacing="-5"` (자간 자동조절 허용)
- URL 하이퍼링크: HWPX 네이티브 fieldBegin/fieldEnd + `HWPHYPERLINK_TYPE_URL`
- 중간 섹션 제목 없음 (뉴스/논문/특허 구분 없이 날짜순 통합 나열)

## 의존성

- `search-info` 스킬의 `info-searcher` 에이전트 타입
- `fix_namespaces.py`, `validate.py` (이 스킬의 `scripts/` 디렉토리에 포함)
- Python 패키지: `lxml` (validate.py에서 사용)
