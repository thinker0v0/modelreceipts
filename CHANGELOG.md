# Changelog

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따른다. 버전은 pre-alpha 동안 `0.0.x`였고, 코드 완성 후보부터 `1.0.0-rcN`이다. 스키마 버전(`0.x`)은 따로 관리한다.

## [Unreleased]

## [1.0.0-rc3] - 2026-09-29 — 대시보드 최종 다듬기 (Codex 단계 → Opus 단계)

새 기능과 Python 코드 변경은 없다. 두 단계로 진행했다. Codex(GPT) 단계가 먼저 디자인 격차 10개를 고쳤고(`0c31c5c`), Claude Opus 단계가 그 결과를 검토해 보완했다. 격차별 결과는 [`docs/DESIGN_COMPARISON.md`](docs/DESIGN_COMPARISON.md), 검사 범위와 한계는 [`docs/QUALITY.md`](docs/QUALITY.md)에 있다. 로컬 후보이며, 배포와 push는 하지 않았다.

### Changed — Codex 단계
- 디자인 격차 10개와 조치를 `docs/DESIGN_COMPARISON.md`에 정리했다. 외부 접속 없이 기존 참고 문서의 패턴을 비교했다.
- 추가한 것: 섹션 이동, 스냅샷 시각, 필터 결과 요약·초기화, 행동 가능한 빈 상태, 로딩 자리표시와 요청 제한, 오류 복구.
- 다듬은 것: 모바일 표·선택기·터치 영역, 모델 열 고정, 결측값과 순위 설명, 산점도 축·경계 주석.
- 보강한 것: 이름 있는 키보드 표 스크롤, 상태 알림, 초점선, slope Esc 닫기, 산점도 툴팁 초기화.
- headless Chromium 전후 전체 페이지 8장을 저장했다. 재현 스크립트는 `dashboard/tools/check-ui.mjs`다.
- 버전: 수집기·서버·패키지 `1.0.0rc3`, 공개 표기 `1.0.0-rc3`.

### Changed — Opus 단계
Codex 조치 10개 중 9개를 보완하고 1개는 그대로 두었다. 새 격차 2개를 고쳤다.

- 헤더 아래: 섹션 링크와 스냅샷 시각을 도구 막대 한 줄로 합쳤다. 페어 모드 링크를 추가했고, 숨은 섹션으로 가는 링크는 감춘다. 시각은 `YYYY-MM-DD HH:MM UTC`로 표시하고, 히어로와 스냅샷 줄의 중복 표기를 뺐다.
- 로딩·오류:
  - 로딩 중 상단 띠를 중립색으로 바꿨다. 노랑은 합성 데이터 표시에만 쓴다.
  - 데이터가 오기 전 빈 보기 pill을 숨긴다.
  - 오류 화면의 행동 버튼을 정렬했다.
  - 샘플 자체가 실패했을 때 같은 실패로 돌아가는 링크를 숨긴다.
  - 시간 초과와 JSON 오류를 사람이 읽을 수 있는 문장으로 보여 준다.
- 빈 집계: `?` 자리표시가 새던 문구를 고쳤다(공개 기준, KPI). 데이터 층 선택기는 "데이터 없음"을 보여 주고, 셀이 없을 때 벤치마크 KPI가 출처를 주장하지 않는다.
- 산점도: 로그 가격 축을 1·3·10 눈금에 맞춰 양 끝에 가격 라벨이 붙게 했다. 폰에서도 눈금 4개가 나온다.
- slope 차트: 합성 워터마크 전용 줄을 두어 마지막 순위 라벨과 겹치지 않게 했다.
- 표:
  - 산점도 설명과 표 설명 사이에 구분선을 넣었다.
  - 폰 카드의 보조 지표를 360px 이상에서 두 열로 바꿨다(카드당 6줄 → 3줄). 360px 미만은 한 열이다.
  - 표 상자는 실제로 가로로 넘칠 때만 Tab 정지점과 "가로 스크롤" 영역이 된다.
- `check-ui.mjs`:
  - 모드를 `check`와 `keyviews:NAME`으로 바꿨다.
  - 스크롤바를 숨겨 390px·1440px 레이아웃을 그대로 찍는다. Codex 단계 캡처는 실제로 375px·1425px이었다.
  - 위 수정마다 검사를 추가하고, 결과를 `docs/screenshots/ui-checks.json`에 쓴다.
- 캡처: 기본 4장과 개요·빈 상태·오류·로딩 4장을 다시 찍었다. Codex → Opus 핵심 화면 3쌍을 `docs/screenshots/before_after/`에 추가했다. rc2 → Codex 전체 페이지 8장은 보존본으로 남겼다.

검증 (2026-09-29, Opus 단계 최종 코드):
- Python 테스트: collector 79, server 60, seeds 21, 총 160개 통과.
- Chromium UI 검사: `check` 모드 전체 통과, JavaScript 예외 0.

## [1.0.0-rc2] - 2026-09-28 — 품질·보안 점검과 대시보드 디자인

새 기능은 없다. 서버·수집기의 입력 처리를 스스로 점검해 찾은 버그를 고쳤고(버그마다 실패하는 테스트를 먼저 썼다), 타입 힌트와 안 쓰는 코드를 정리했으며, 대시보드를 다시 디자인했다. 점검 범위와 남은 일은 [`docs/QUALITY.md`](docs/QUALITY.md)에 있다.

테스트: collector 79, server 60, seeds 21 (합계 160) (Python 3.12, 로컬 실행).

### Security
- 음수 `Content-Length`(`-1`)가 크기 검사를 통과하고 본문을 EOF까지 읽어 64 KiB 한도를 우회했다. 이제 ASCII 숫자만 받고 나머지는 411로 연결을 닫는다.
- 깊게 중첩된 JSON(`RecursionError`)과 4300자리를 넘는 정수 리터럴(`ValueError`)이 처리기 밖으로 새어 응답 없이 연결이 끊겼다. 이제 `400 invalid_json`.
- `NaN`/`Infinity`를 JSON 파서와 검증기가 받아 저장했고, 상세 집계가 JSON이 아닌 `Infinity` 토큰을 내보냈다. 파싱과 검증 양쪽에서 거부하고, 응답은 `allow_nan=False`로 만든다.
- 2⁵³−1을 넘는 정수가 스키마 검증을 통과한 뒤 SQLite `OverflowError`로 연결이 끊겼다. 검증기가 I-JSON 범위를 강제한다.
- 정적 경로의 NUL 바이트가 `ValueError`로 연결을 끊었다. 이제 404.
- 예상하지 못한 예외는 고정된 `500 {"error":"internal_error"}`로 답하고 내부 정보를 싣지 않는다.
- 요청 경로의 제어 문자(ANSI 이스케이프 등)를 로그에서 이스케이프한다.
- 요청마다 새 키를 만들면 기여자별 토큰 버킷을 매번 새로 받아 레이트 리밋이 사실상 없었다. DB에 레코드가 없는 기여자는 공용 newcomer 버킷(기본 360/h, 버스트 60)을 함께 쓴다. `serve --new-contributors-per-hour`, `--new-contributor-burst`.
- 위수가 작은 Ed25519 공개 키(예: 항등원)는 비밀 키 없이 모든 메시지에 "맞는" 서명을 만들 수 있었다. 이런 키를 거부한다.
- 스키마 `pattern`의 `$`가 Python에서는 끝 줄바꿈 앞에서도 맞아 `"claude-code\n"` 같은 값이 통과했다. ECMA-262 의미대로 `\Z`로 바꿔 적용한다.
- 검증 오류 메시지가 큰 입력을 그대로 되돌려 보내지 않도록 60자에서 자른다.
- 클라이언트가 keep-alive 연결을 끊으면(`curl | head`) 서버가 파일 경로가 담긴 전체 traceback을 stderr에 찍었다. 연결 끊김은 조용히 넘기고, 그 밖의 연결 오류는 예외 종류 한 줄만 남긴다. README 빠른 시작을 실제로 돌리다 발견했다.
- `submit`/`query`가 HTTP 리다이렉트를 따라가지 않는다. 따라가면 loopback 검사를 거치지 않은 주소로 서명 헤더가 전달됐다.

### Added
- 고정 시드 무작위(property 스타일) 테스트: 레코드 변형 60건 HTTP 왕복, 정적 경로 80건, 서명 변조, 시각 허용 범위 경계, 토큰 버킷 상한, 자유 텍스트가 제약된 문자열 필드로 들어가지 못함.
- `server/tests/test_release.py`: 버전 문자열 일치, 대시보드 외부 리소스 없음, 접근성 기본 항목 확인.
- `docs/QUALITY.md`(점검 기록), `docs/DESIGN_REFERENCES.md`(디자인 참고).
- `records (contributor, received_at)` 인덱스.

### Changed
- 대시보드 재디자인([`docs/DESIGN_REFERENCES.md`](docs/DESIGN_REFERENCES.md)):
  - 히어로 요약(자기평가 1위 ≠ 증거 1위인 L2 수, 가장 큰 과대평가)과 KPI 4개
  - 시그니처 "자기평가 순위 vs 증거 순위" slope chart: L2 칩, 한 문장 캡션, 키보드 초점과 툴팁
  - 태스크 셀 리더보드: 순위와 통계적 순위, n·k 배지, 모든 행이 같은 축을 쓰는 CI 막대, 비공개 셀 배지
  - 비용 대 통과율 산점도: 로그 비용 축, CI 수염, 비용 대비 최선 경계, 키보드 탐색
  - 사용량 시드는 한 줄 100% 점유율 막대로, 선호 시드는 확대 축의 CI 막대로
  - 합성 표시를 상단 띠·히어로·KPI·카드·차트 워터마크에 반복
  - 다크/라이트, 640px 이하 카드 레이아웃, AA 대비, 건너뛰기 링크, `aria-live`, reduced motion
  - 스크린샷 4장 재촬영(데스크톱 전체 페이지, 폰 위쪽 3000px)
- README 빠른 시작이 `mktemp -d` 임시 디렉터리만 쓰고, 서버를 백그라운드로 띄운 뒤 마지막에 정리한다. 새 임시 디렉터리 사본에서 처음부터 끝까지 실행해 확인했다.
- 타입 힌트 정리(ed25519 `Point`, 집계·앱·저장소·수집기·시드 도우미), 안 쓰는 지역 변수 제거.
- 버전: 수집기와 서버 모두 `1.0.0rc2`.

## [1.0.0-rc1] - 2026-09-28 — 코드 완성 후보

로드맵에서 코드로 할 수 있는 항목을 모두 구현했다. 남은 일은 사람이 해야 하는 일로, 배포, PyPI 게시, 데이터 라이선스, 기여자 모집, 실데이터 수집이다([`docs/USER_TASKS.md`](docs/USER_TASKS.md)). 실제 사용자 데이터는 아직 없고, 샘플의 현장 보고는 모두 합성이다.

테스트: collector 69, server 42, seeds 21 (Python 3.12, 로컬 실행).

### Added

**수집기 (`collector`)**
- `install-hook` / `uninstall-hook`: Claude Code 설정 파일에 미리보기 전용 Stop 훅을 넣고 뺀다.
  - `--settings` 필수, 기본은 dry-run diff. `--apply`를 주면 터미널 확인을 받은 뒤 타임스탬프 백업과 원자적 쓰기를 한다.
  - 멱등하고, 우리 항목만 깨끗하게 제거하며, 다른 훅과 키는 보존한다. 테스트는 임시 디렉터리만 쓴다.
- 분류기:
  - `rules-v1`: 가중 키워드 점수, 우선순위 동점 처리, 좁힌 코딩 게이트. **기본값**이 되었다.
  - `rules-v0`은 재현용으로 보존한다.
- 분류기 평가:
  - 합성 평가 세트 240개(`collector/eval/`, dev 120 / test 120, test는 rules-v1 작업 전에 고정)와 `eval-classifier` 명령
  - 고정 test 분할 결과: rules-v0 정확도 0.508 / L1 0.800, rules-v1 0.675 / 0.883. rules-v1은 dev에서 1.000으로 과적합이다.
- 품질 신호:
  - `retry-rules-v1`: 다음 프롬프트가 불만·재시도 표현이거나 직전 프롬프트와 거의 같으면 표시한다. `--preview-dir` 상태 파일로 직전 레코드에 소급 기록한다.
  - `claim-rules-v1`: 에이전트 마지막 메시지의 성공 주장 점수를 `self_assessment`에 넣는다(`rater: self_claim`, 랭킹 제외).
- Ed25519 설치 키: 순수 Python RFC 8032 구현으로, 테스트 벡터 1–3과 `cryptography` 교차검증을 통과한다.
  - `keygen` 명령을 추가했다.
  - `submit`이 모든 요청에 서명한다(`--key-file`이 `--install-id-file`을 대체). 키 파일은 `0600`이고 `.gitignore`에 `install_key*`를 넣었다.
- `query`: 서명된 `GET /v1/aggregates/detail`로 기여자 전용 상세 조회를 한다.
- `pair A B [--apply]`: 두 미리보기 레코드를 페어 모드 쌍으로 표시한다.
- 검증과 변환:
  - `validate`가 `.jsonl`을 읽고, `schema_version`과 `kind`로 스키마를 자동 선택한다(`--allow-seed-cells`, `--only-version`).
  - `migrate` 명령: v0.1 → v0.2, 입력 파일을 바꾸지 않는다.
- 스키마를 패키지 데이터(`modelreceipts/schemas/`)로 포함했다.

**스키마**
- `record.v0.2.schema.json`:
  - 시드가 모르는 값(토큰, `turns`, `test_runs`, `committed`, `tool_error_count`)을 nullable로 바꿨다.
  - `evidence.retry_detector`와 `self_assessment.extractor`를 필수로 추가했다.
  - `rater`에 `self_claim`을 추가했다.
  - `cost_usd_server`와 `install_key_sig`를 `null`로 고정했다(서버 쪽으로 이동).
- `seed_cell.v0.2.schema.json`: 선호(승·패·무)와 사용량(토큰·점유율·순위) 집계 셀
- 예시를 v0.2로 바꾸고 v0.1 원본을 `examples/v0.1/`에 보존했다. 합성 시드 셀 예시도 추가했다.

**서버 (`server`)**
- 서명과 한도:
  - Ed25519 서명 검증. `--signatures required`가 기본이고, 기여자 = salt 해시한 공개 키다.
  - 기여자별 토큰 버킷(120/h, 버스트 30)과 기여자·셀별 24시간 상한(50). 초과하면 `429` + `Retry-After`를 돌려준다.
- 서버 비용:
  - 가격표 JSON(`data/prices.json`: 출처 URL, 기준일 2026-06-24, `verified_live: false`, `route=direct`만)을 추가했다.
  - 서버가 재계산한 비용은 `server_costs` 테이블에 따로 저장하고, 재계산이 안 되면 사유를 남긴다. 클라이언트 보고값은 그대로 둔다.
- `self_assessments` 테이블: 자기평가를 랭킹 열과 분리해 저장한다.
- 조회:
  - 공개 `GET /v1/overview`: L1 × 모델 점추정과 공개 시드. `/v1/aggregates`는 이 경로의 별칭이다.
  - 기여자 전용 `GET /v1/aggregates/detail`: 서명이 필요하고, 최근 90일 안에 현장 보고가 있어야 한다. 서명이 없으면 401, 기여가 없으면 403이다.
  - 셀 공개 조건에 한 기여자 비중 상한(기본 0.5, `dominated_by_one_contributor`)을 추가했다.
- 집계:
  - 페어 모드 맞대결 집계: 마지막 테스트 결과 기준, 쌍 ≥ 10이고 기여자 ≥ 3일 때 공개한다.
  - `self_vs_evidence` 순위 비교
  - 셀별 서버 비용과 다음 프롬프트 재시도율
- 시드 셀:
  - `seed_cells` 테이블을 추가했다. 선호 셀에는 Wilson CI를 붙이고 대결 30회 미만은 비공개로 한다.
  - `import-seed arena-55k | openrouter [--input]`
- DB 업그레이드:
  - 옛 DB를 열면 열과 테이블을 추가만 한다(`user_version = 2`).
  - `migrate-db --from --to`: 복사 방식이고 salt를 유지한다.
  - 옛 NOT NULL 열에 v0.2 null을 넣으려 하면 `LegacyDatabase` 오류와 함께 안내가 나온다.
- `make-sample`이 상세·개요 샘플 두 개와 `docs/figures/self-vs-evidence.synthetic.svg`(표준 라이브러리 SVG, 합성 라벨)를 만든다.

**시드 (`seeds`)**
- LMArena `arena-human-preference-55k`:
  - 대상: 리비전 18c2983, Apache-2.0, 원본 sha256 기록, 원본은 재배포하지 않는다.
  - 57,477 대결을 로컬 `rules-v1`로 분류해 1,373개 `(L1, L2, 모델)` 셀의 **개수만** 커밋했다(sha256 고정).
  - `--rebuild-from train.csv`로 다시 만들 수 있다.
- OpenRouter 사용 비중 임포터:
  - 실제 데이터는 API 키와 약관 확인이 필요해 받지 않았다.
  - **합성 픽스처**로 시험했고, 운영자가 받은 export는 `--input`으로 적재한다.

**대시보드**
- 보기 전환: 공개 개요 / 기여자 상세 샘플
- 새 카드: 페어 모드 맞대결 카드(표 보기 포함), 시드 층 카드(선호 승률 + CI, 사용량 점유율)
- 비용 표시: 서버 비용 대체 표시와 가격표 출처
- 셀 표: 재시도 열, 비공개 사유
- 스크린샷 4장을 다시 찍었다.

**문서**
- `docs/USER_TASKS.md`: 사람이 해야 하는 일
- README(상태, 로드맵, 빠른 시작, 구조)와 각 폴더 README를 갱신했다.

### Changed
- 수집기가 schema v0.2 레코드를 만든다. 서버와 검증기는 v0.1도 계속 받는다.
- Aider 시드가 v0.2 `null`을 쓴다. 자리표시값 `false`/`0`을 없앴다.
- CI:
  - v0.1·v0.2·시드 셀 예시를 검증하고, 패키지 스키마 사본이 같은지 확인한다.
  - Arena·OpenRouter 시드를 검증한다.
  - 분류기 보고서와 두 샘플, 데모 그림이 최신인지 확인한다.
- 버전: 수집기와 서버 모두 `1.0.0rc1`, 개발 상태 Beta.

### Security
- 서명 없는 제출은 기본 거부한다. 설치 id를 스스로 선언하던 방식은 `--signatures optional`(로컬 개발용)에서만 남는다.
- 서명 메시지에 메서드, 경로와 쿼리, 시각(±300초), 본문 sha256을 넣어 다른 요청으로 재사용할 수 없게 했다.
- 순수 Python Ed25519는 상수 시간이 아니다. 서버는 검증만 하고, 설치 키는 Sybil 방지용 식별자라는 전제를 문서에 적었다.

## [0.0.2] - 2026-09-27 — pre-alpha ~10%

로컬 루프가 처음으로 끝까지 돈다: 수집기 미리보기 → opt-in 제출 → localhost 서버 저장 → k·n 임계 집계 → 대시보드.

### Added
- `server/`: 표준 라이브러리 ingest 서버. `POST /v1/records`(스키마 v0.1 검증, `field_report`만, 중복 id 409), `GET /v1/aggregates`(셀 = source_type × L1/L2 × 모델 × 하네스, Wilson 95% CI, 기여자 k·레코드 n 임계, source_type별 설정 가능). SQLite append-only(UPDATE/DELETE 트리거 차단), 설치 id는 salt 해시로만 저장, 127.0.0.1/::1 외 바인딩 거부, 요청 로그에 클라이언트 주소 없음.
- `collector`: `submit (--payload|--record) [--endpoint URL]` — 항상 미리보기, `--endpoint`가 있을 때만 전송, loopback만 허용(`--allow-non-loopback`로 해제), 스키마 위반 레코드는 전송 안 함.
- `seeds/`: Aider polyglot 리더보드 스냅샷(Aider-AI/aider@cb6a152, Apache-2.0, sha256 고정)과 임포터(69행 → 15,518 `benchmark` 레코드). stdlib 미니 YAML 파서. Arena·OpenRouter 시드는 설계만 문서화.
- `dashboard/data/aggregates.sample.json`: 실제 Aider 벤치마크 셀 + 합성 현장 보고(`example-model-*`)로 만든 샘플, `make-sample`로 재생성.
- `.github/workflows/ci.yml`(Python 3.10/3.12 × stdlib-only/교차검증 의존성), `requirements-dev.txt`(테스트 전용, 버전 고정), 이 CHANGELOG.

### Changed
- 대시보드가 페이지 안의 목업 난수 대신 집계 JSON(`?data=URL`)을 그린다. 배너·출처 카드가 데이터의 라벨을 그대로 표시하고, 임계 미달 셀은 수치 없이 표시한다. 스크린샷 4장 재촬영.
- 무네트워크 테스트: "수집기 전체에 네트워크 코드 없음" → "`submit.py`만 네트워크 가능, 기본 `hook` 경로는 새 인터프리터에서도 네트워크 모듈을 불러오지 않음, `--endpoint` 없이는 연결 0회".
- 수집기 버전 0.0.2.

## [0.0.1] - 2026-09-27 — pre-alpha <5%

### Added
- 레코드 JSON Schema v0.1(증거 1급 필드, 자기평가 격리, 원문·식별자 금지)과 합성 예시 3개.
- 표준 라이브러리 검증기와 dry-run `Stop` 훅 수집기(전송 코드 없음).
- 대시보드 UI 목업(목업 데이터), README, CONTRIBUTING, 타당성 조사 보고서.
