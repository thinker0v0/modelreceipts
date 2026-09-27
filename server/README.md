# server — ingest API (pre-alpha, localhost only)

`POST /v1/records`로 schema v0.1 레코드를 받아 SQLite에 **append-only**로 저장하고, `GET /v1/aggregates`로 k·n 임계값을 적용한 셀 통계를 돌려준다. 어디에도 배포하지 않는다. **127.0.0.1 / ::1 / localhost 외 주소에는 바인딩을 거부한다.**

## 왜 표준 라이브러리인가 (FastAPI 대신 `http.server` + `sqlite3`)

- **의존성 0개.** 수집기와 같은 원칙(CONTRIBUTING: stdlib 우선). `pip install` 없이 체크아웃만으로 테스트·데모가 돈다. 공급망 표면이 없다.
- **검증기 공유.** 서버는 수집기의 `modelreceipts.validate`를 그대로 import한다. 클라이언트와 서버가 "유효한 레코드"를 다르게 판단할 수 없다.
- 지금 필요한 엔드포인트는 두 개이고 트래픽은 로컬 한 명이다. FastAPI+uvicorn(+pydantic)은 이 규모에서 얻는 것보다 고정·갱신할 의존성이 많다.
- **한계:** Python 문서가 말하듯 `http.server`는 운영용이 아니다(기본 보안 검사만 함). 외부 공개가 필요해지는 시점(설치 키 서명, 레이트 리밋, TLS 종단)에 ASGI 프레임워크로 옮기고 버전을 고정한다. 저장 계층(`store.py`)과 집계(`aggregate.py`)는 HTTP와 분리돼 있어 그대로 재사용한다.

## 실행

```bash
# 저장소 루트에서. DB 기본 경로: server/var/modelreceipts.sqlite3 (gitignore)
PYTHONPATH=server python3 -m modelreceipts_server import-seed aider-polyglot   # 선택: 시드 적재 (멱등)
PYTHONPATH=server python3 -m modelreceipts_server serve --port 8787            # Ctrl+C로 종료
# 브라우저: http://127.0.0.1:8787/  → 이 서버의 집계를 그리는 대시보드
```

임계값은 플래그나 환경변수로 바꾼다.

| 플래그 | 환경변수 | 기본값 | 적용 대상 |
|---|---|---|---|
| `--min-contributors` | `MR_MIN_CONTRIBUTORS` | 5 | `field_report` 셀의 기여자 수 k |
| `--min-records` | `MR_MIN_RECORDS` | 30 | `field_report` 셀의 레코드 수 n |
| `--seed-min-contributors` | `MR_SEED_MIN_CONTRIBUTORS` | 1 | 시드 층(`benchmark`/`preference`/`usage`) k |
| `--seed-min-records` | `MR_SEED_MIN_RECORDS` | 30 | 시드 층 n |

k=5, n=30은 조사 보고서의 초기 제안값이다. 시드는 이미 공개된 데이터이고 게시자가 하나라 k가 보호하는 대상이 없으므로 기본 k=1, n은 작은 표본을 막기 위해 유지한다.

## API

### `POST /v1/records`

- 본문: 레코드 JSON 1건, `Content-Type: application/json`, 최대 64 KiB.
- 선택 헤더 `X-ModelReceipts-Install`: 클라이언트가 만든 무작위 설치 id. 서버는 **DB별 salt로 해시한 값만** 저장한다. 없으면 모든 레코드가 하나의 `anonymous` 기여자로 묶인다(k를 부풀릴 수 없게).
- `source_type`은 `field_report`만 받는다. 시드 층은 HTTP로 넣을 수 없다.

| 응답 | 의미 |
|---|---|
| `201 {"status":"stored","record_id":…}` | 저장됨 |
| `400 schema_validation_failed` + `details` | 스키마 위반 (예: `$: unexpected property 'prompt'`) |
| `400 invalid_json` / `415` / `411` / `413` | 전송 형식 문제 |
| `409 duplicate_record_id` | 같은 id는 다시 쓸 수 없다 (덮어쓰기 없음) |
| `405` | `PUT`/`PATCH`/`DELETE` — 수정·삭제 경로는 없다 |

### `GET /v1/aggregates`

쿼리: `source_type`(field_report|benchmark|preference|usage), `l1`, `l2`, `level`(l2 기본 | l1 롤업). 응답의 핵심 필드:

```jsonc
{
  "thresholds": {"field_report": {"min_contributors": 5, "min_records": 30}, "benchmark": {…}},
  "totals": {"records_by_source_type": {"field_report": 1, "benchmark": 15518, …}},
  "sources": [{"source_id": "aider-polyglot@cb6a152", "url": "…", "commit_sha": "…", "license": "Apache-2.0", …}],
  "cells": [{
    "source_type": "field_report", "l1": "coding", "l2": "coding.bugfix", "model": "…", "method": "claude-code",
    "n": 42, "k": 7,
    "tests": {"tested": 36, "passed": 25, "pass_rate": 0.6944, "ci95": [0.531, 0.82], "tested_share": 0.857},
    "cost_usd_per_task": {"client_mean": 0.14, "server_mean": null, "reported": 42},
    "cost_usd_per_success": 0.2, "latency_ms_median": 91000,
    "commit_rate": 0.6, "tool_errors_mean": 1.1,
    "self_assessment": {"n": 30, "mean": 0.9, "excluded_from_ranking": true}
  }],
  "suppressed": [{"source_type": "field_report", "l1": "coding", "l2": "coding.test", "model": "…", "method": "…", "reason": "below_threshold"}]
}
```

- 셀 = `(source_type, l1, l2, model.id, method.harness)`. `source_type`이 키에 들어 있어 시드와 현장 보고가 **절대 합쳐지지 않는다.**
- 임계 미만 셀은 키만 나오고 n·k 등 **어떤 수치도 내보내지 않는다.**
- 순위 신호는 `tests.pass_rate`(마지막 테스트 명령 결과가 있는 레코드 기준)와 Wilson 95% CI. `self_assessment`는 참고로만 싣고 `excluded_from_ranking: true`.
- benchmark 셀은 시드가 보고하지 않는 필드(`commit_rate`, `tool_errors_mean`, `self_assessment`)를 `null`로 둔다.
- 집계는 공개 층이므로 `Access-Control-Allow-Origin: *`를 붙인다.

### 기타

`GET /healthz`, `GET /` → `/dashboard/?data=/v1/aggregates`, `GET /dashboard/*` → `dashboard/` 정적 파일(경로 탈출 차단).
요청 로그에는 클라이언트 주소를 남기지 않는다.

## 저장소

- `records`, `seed_sources` 테이블에 `BEFORE UPDATE/DELETE` 트리거가 걸려 있어 SQL로도 수정·삭제가 막힌다(테스트로 확인).
- 레코드 원문은 `body` 열에 그대로, 집계용 열(l1, l2, 모델, 하네스, 증거, 비용…)은 삽입 시 추출.
- 시드 레코드는 `seed_source_id`로 출처(`seed_sources`: URL, 커밋, sha256, 라이선스)와 연결된다.

## 아직 없는 것

설치 키 서명(Sybil 방지 — 지금의 설치 id는 스스로 선언한 값이라 위조 가능), 레이트 리밋, 기여자 전용 세분 조회 게이트, 서버 가격표 기반 `cost_usd_server` 재계산, TLS, 배포.

## 테스트

```bash
python3 -m unittest discover -s server/tests -v
```
