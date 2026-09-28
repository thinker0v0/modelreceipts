# server — ingest API (v1.0.0-rc2, localhost only)

서버가 하는 일:

- **받기:** `POST /v1/records`로 **Ed25519 서명된** 레코드(schema v0.1·v0.2)를 받아 SQLite에 **append-only**로 저장합니다.
- **공개 개요:** `GET /v1/overview`로 누구나 볼 수 있는 집계를 돌려줍니다.
- **기여자 상세:** `GET /v1/aggregates/detail`로 최근 기여자만 볼 수 있는 상세 집계를 돌려줍니다.

어디에도 배포하지 않습니다. **127.0.0.1 / ::1 / localhost 외 주소에는 바인딩을 거부합니다.** 실제 배포는 TLS 종단 리버스 프록시 뒤에서 사람이 해야 합니다([`docs/USER_TASKS.md`](../docs/USER_TASKS.md) 참고).

## 왜 표준 라이브러리인가 (FastAPI 대신 `http.server` + `sqlite3`)

- **의존성 0개.** 수집기와 같은 원칙입니다(CONTRIBUTING: stdlib 우선). `pip install` 없이 체크아웃만으로 테스트와 데모가 돌고, 공급망 표면이 없습니다. Ed25519도 수집기의 순수 Python 구현(`modelreceipts.ed25519`)을 씁니다.
- **검증기 공유.** 서버는 수집기의 `modelreceipts.validate`와 `modelreceipts.signing`을 그대로 import합니다. 그래서 클라이언트와 서버가 "유효한 레코드"와 "유효한 서명"을 다르게 판단할 수 없습니다.
- **한계:**
  - `http.server`는 운영용이 아닙니다.
  - 순수 Python Ed25519는 상수 시간이 아닙니다. 서버는 공개 키로 검증만 하므로 비밀이 새지는 않지만, 느립니다(서명 검증 1건에 수 ms).
  - 트래픽이 커지면 ASGI 프레임워크와 `cryptography`로 옮깁니다. 저장 계층(`store.py`), 집계(`aggregate.py`), 가격(`prices.py`), 레이트 리밋(`ratelimit.py`)은 HTTP와 분리돼 있어 그대로 재사용할 수 있습니다.

## 실행

```bash
# 저장소 루트에서. DB 기본 경로: server/var/modelreceipts.sqlite3 (gitignore)
export PYTHONPATH=collector:seeds:server
python3 -m modelreceipts_server import-seed aider-polyglot     # 선택: 시드 적재 (멱등)
python3 -m modelreceipts_server import-seed arena-55k
python3 -m modelreceipts_server import-seed openrouter         # 합성 픽스처. 실제 export는 --input FILE
python3 -m modelreceipts_server serve --port 8787              # Ctrl+C로 종료
python3 -m modelreceipts_server aggregates --view overview     # 서버 없이 집계 JSON 출력
python3 -m modelreceipts_server make-sample                    # dashboard/data/*.sample.json + docs/figures/*.svg 재생성
python3 -m modelreceipts_server migrate-db --from old.sqlite3 --to new.sqlite3
```

### 설정

| 플래그 | 기본값 | 의미 |
|---|---|---|
| `--signatures required\|optional` | required | `required`는 서명 없는 POST를 401로 거부합니다. `optional`(로컬 개발용)은 옛 `X-ModelReceipts-Install` 헤더나 `anonymous`로 받습니다. |
| `--gate on\|off` | on | 상세 조회를 최근 90일 기여자에게만 엽니다. |
| `--prices FILE` | `data/prices.json` | 서버 비용을 재계산할 가격표입니다. |
| `--rate-per-hour` / `--burst` | 120 / 30 | 기여자별 토큰 버킷 |
| `--cell-daily-cap` | 50 | 기여자·셀당 24시간 레코드 상한 |
| `--new-contributors-per-hour` / `--new-contributor-burst` | 360 / 60 | DB에 레코드가 없는 기여자(처음 보는 키)가 함께 쓰는 공용 토큰 버킷. 요청마다 새 키를 만들어 기여자별 버킷을 피하는 것을 막습니다. |
| `--min-contributors` (`MR_MIN_CONTRIBUTORS`) | 5 | `field_report` 셀의 k |
| `--min-records` (`MR_MIN_RECORDS`) | 30 | `field_report` 셀의 n |
| `--max-contributor-share` | 0.5 | 한 기여자가 셀 레코드의 이 비율을 넘으면 비공개(`dominated_by_one_contributor`) |
| `--seed-min-contributors` / `--seed-min-records` | 1 / 30 | 시드 층(`benchmark`/`preference`)의 k·n. `usage`는 n=1입니다. |
| `--pair-min-pairs` / `--pair-min-contributors` | 10 / 3 | 페어 모드 결과를 공개하는 기준 |

k=5, n=30은 조사 보고서의 초기 제안값입니다. 시드는 이미 공개된 데이터이고 게시자가 하나라 k가 보호할 대상이 없으므로 k=1로 둡니다.

## API

### `POST /v1/records`

- **본문:** 레코드 JSON 1건. `Content-Type: application/json`, 최대 64 KiB. `Content-Length`는 ASCII 숫자만 받습니다(음수·부호·`Transfer-Encoding`은 411).
- **JSON:** 엄격하게 읽습니다. `NaN`/`Infinity`, 너무 깊은 중첩, 4300자리를 넘는 정수 리터럴은 `400 invalid_json`입니다. 스키마 검증은 ±(2⁵³−1)을 넘는 정수와 문자열 끝의 줄바꿈도 거부합니다.
- **서명 헤더** (`modelreceipts submit`이 붙입니다):
  - `X-ModelReceipts-Key`: 공개 키(base64url)
  - `X-ModelReceipts-Timestamp`: 유닉스 초. ±300초 안이어야 합니다.
  - `X-ModelReceipts-Signature`: 아래 메시지의 Ed25519 서명

  서명하는 메시지:

  ```text
  modelreceipts-v1\nMETHOD\nPATH?QUERY\nTIMESTAMP\nsha256hex(body)
  ```

- **기여자:** DB별 salt로 해시한 공개 키를 씁니다(`k:…`). 비밀 키와 공개 키 원문은 저장하지 않습니다.
- **처리 순서:** 서명 검증 → 기여자별 토큰 버킷 → (처음 보는 기여자면) 공용 newcomer 버킷 → JSON → 스키마 검증 → 셀 일일 상한 → 저장.
- **서명 키:** 위수가 작은 점(small-order point, 예: 항등원)인 공개 키는 거부합니다. 이런 키로는 비밀 키 없이도 서명이 맞아 보일 수 있습니다.
- **받는 `source_type`:** `field_report`만 받습니다. 시드 층은 운영자가 로컬에서 `import-seed`로만 넣습니다.

| 응답 | 의미 |
|---|---|
| `201 {"status":"stored","record_id":…,"signed":true,"server_cost":{…}}` | 저장됨 |
| `400 schema_validation_failed` + `details` | 스키마 위반 (예: `$: unexpected property 'prompt'`) |
| `400 invalid_json` / `415` / `411` / `413` | 전송 형식 문제 |
| `401 signature_required` / `401 bad_signature` | 서명 없음 / 서명·시각·본문 불일치 |
| `409 duplicate_record_id` | 같은 id는 다시 쓸 수 없습니다 (덮어쓰기 없음) |
| `429 rate_limited` / `429 new_contributor_rate_limited` / `429 cell_daily_cap` + `Retry-After` | 기여자별 레이트 리밋 / 처음 보는 기여자 공용 예산 / 셀 일일 상한 |
| `500 {"error":"internal_error"}` | 예상하지 못한 오류. 내부 정보(경로, 예외 메시지)는 응답에 넣지 않고, 로그에도 예외 종류만 남깁니다. |
| `405` | `PUT`/`PATCH`/`DELETE`: 수정·삭제 경로는 없습니다 |

### `GET /v1/overview` (공개, `GET /v1/aggregates`는 별칭)

- **현장 보고:** L1 × 모델로만 합쳐 `n`, `k`, `tests.tested`, `tests.pass_rate`(점추정), 지연 중앙값을 냅니다. L2, 하네스, CI, 비용, 자기평가, 재시도, 페어 모드는 빠집니다.
- **시드:** 공개 데이터이므로 상세와 같은 형태로 냅니다(benchmark 셀, `seed_cells`).
- **`gate` 블록:** 상세 조회 방법과 추가로 볼 수 있는 항목을 적어 둡니다.
- **CORS:** `Access-Control-Allow-Origin: *`

### `GET /v1/aggregates/detail` (기여자 전용)

- **접근 조건:** `GET`을 설치 키로 서명해야 합니다(`modelreceipts query --endpoint URL`). 그 키로 최근 90일 안에 `field_report`를 한 건 이상 저장했어야 합니다.
  - 서명 없음·잘못된 서명: `401 contributors_only`
  - 기여 없음: `403 contributors_only`
- **쿼리:** `source_type`, `l1`, `l2`, `level`(`l2` 기본, `l1`이면 롤업). 서명 메시지에는 쿼리 문자열도 들어갑니다.
- **응답 필드:**

```jsonc
{
  "api": "modelreceipts.aggregates/v1", "view": "detail",
  "thresholds": {"field_report": {"min_contributors": 5, "min_records": 30, "max_contributor_share": 0.5}, "pairs": {…}, …},
  "price_table": {"price_table_id": "anthropic-api@2026-06-24", "source": {"url": "…", "as_of": "…", "verified_live": false}, "sha256": "…"},
  "cells": [{
    "source_type": "field_report", "l1": "coding", "l2": "coding.bugfix", "model": "…", "method": "claude-code",
    "n": 42, "k": 7,
    "tests": {"tested": 36, "passed": 25, "pass_rate": 0.6944, "ci95": [0.531, 0.82], "tested_share": 0.857},
    "cost_usd_per_task": {"client_mean": 0.14, "server_mean": 0.12, "reported": 20, "server_computed": 42},
    "cost_usd_per_success": 0.2, "server_cost_usd_per_success": 0.18,
    "retry_next_prompt": {"observed": 30, "rate": 0.2},
    "commit_rate": 0.6, "tool_errors_mean": 1.1, "latency_ms_median": 91000,
    "self_assessment": {"n": 30, "mean": 0.9, "excluded_from_ranking": true}
  }],
  "suppressed": [{"…": "…", "reason": "below_threshold | dominated_by_one_contributor"}],
  "pairwise": {"results": [{"l2": "coding.bugfix", "model_a": "…", "model_b": "…", "pairs": 24, "k": 6,
                            "a_wins": 1, "b_wins": 5, "ties": 12, "undecided": 6, "a_score": 0.39, "a_score_ci95": [0.2, 0.61]}]},
  "self_vs_evidence": [{"task": "coding.bugfix", "models": [{"model": "…", "rank_by_self": 1, "rank_by_evidence": 3, …}],
                        "rank_changes": 5, "top_differs": true}],
  "seed_cells": {"cells": [{"source_type": "preference", "model": "…", "battles": 1403, "win_rate": 0.40, "win_rate_ci95": […]}], …}
}
```

- **셀 키:** `(source_type, l1, l2, model.id, method.harness)`. `source_type`이 키에 들어 있어 시드와 현장 보고가 **절대 합쳐지지 않습니다.**
- **비공개 셀:** 키와 사유만 나오고 수치는 하나도 나오지 않습니다.
- **순위 신호:** `tests.pass_rate`와 Wilson 95% CI를 씁니다. `self_assessment`는 참고로만 싣고 `excluded_from_ranking: true`로 표시합니다.
- **페어 모드:** 같은 `pair_id`를 가진 두 레코드의 마지막 테스트 결과로 승패를 정합니다. 둘 다 통과하거나 둘 다 실패하면 무승부이고, 한쪽이라도 테스트가 없으면 판정 불가입니다. 모델 순서는 이름순으로 정규화합니다.
- **`self_vs_evidence`:** 공개된 field_report 셀만 모델 단위로 합쳐 자기평가 평균 순위와 통과율 순위를 비교합니다.

### 기타

- `GET /healthz`
- `GET /` → `/dashboard/?data=/v1/overview`
- `GET /dashboard/*` → `dashboard/` 정적 파일(경로 탈출 차단)

요청 로그에는 클라이언트 주소도, 헤더도 남기지 않습니다.

## 저장소

- **테이블:** `records`, `seed_sources`, `seed_cells`, `server_costs`, `self_assessments`. 모두 `BEFORE UPDATE/DELETE` 트리거가 걸려 있어 SQL로도 수정·삭제가 막힙니다(테스트로 확인).
- **신호 분리:**
  - 레코드 원문은 받은 그대로 `body`에 저장합니다.
  - 서버가 가격표로 재계산한 비용은 `server_costs`에 따로 둡니다. 재계산이 안 되면 `cost_usd = NULL`과 함께 `reason`(`route_not_covered` / `model_not_in_table` / `tokens_missing`)을 남깁니다.
  - 자기평가는 `self_assessments`에 따로 둡니다.
  - 클라이언트가 보고한 비용은 바꾸지 않습니다.
- **가격표** (`modelreceipts_server/data/prices.json`):
  - `price_table_id`: `anthropic-api@2026-06-24`
  - 출처 URL과 기준일을 기록합니다.
  - `verified_live: false`: 라이브 페이지와 대조하는 일은 사람이 해야 합니다.
  - `route=direct`에만 적용합니다. Bedrock·Vertex 등은 가격이 달라 NULL로 둡니다.
  - 모델 id는 가장 긴 접두사로 매칭합니다.
- **스키마 업그레이드:**
  - 옛 DB(v1)를 열면 새 열과 테이블을 **추가만** 합니다(`user_version = 2`).
  - 옛 DB는 `committed` 등에 NOT NULL이 남아 있습니다. 그래서 v0.2의 null 레코드를 넣으면 `LegacyDatabase` 오류와 함께 `migrate-db` 안내가 나옵니다.
  - `migrate-db`는 원본을 읽기 전용으로 열고 **새 파일로 복사**합니다. 이때 본문을 v0.2로 바꾸고 salt를 유지하며, 기존 파일은 덮어쓰지 않습니다.

## 테스트

```bash
python3 -m unittest discover -s server/tests -v
```

- `test_server.py`: 저장, 집계, HTTP 기본
- `test_v1.py`: 서명, 게이트, 레이트 리밋, 셀 상한, 서버 비용, 신호 분리, 지배 기여자, 페어 모드, 시드 셀, DB 마이그레이션, 샘플·그림 최신 여부
- `test_hardening.py`(rc2): 전송 한도, 엄격한 JSON, 500 처리, 로그 이스케이프, 연결 끊김 로그, 키 돌려쓰기 방지, 고정 시드 무작위 변형·정적 경로·토큰 버킷 성질
- `test_release.py`(rc2): 버전 문자열 일치, 대시보드 외부 리소스 없음, 접근성 기본 항목
