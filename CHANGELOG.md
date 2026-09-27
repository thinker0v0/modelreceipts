# Changelog

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따른다. 버전은 pre-alpha 동안 `0.0.x`.

## [Unreleased]

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
