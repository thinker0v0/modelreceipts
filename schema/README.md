# Record schema v0.2 (+ v0.1)

| 파일 | 대상 |
|---|---|
| `record.v0.2.schema.json` | 에이전트 작업 1회(한 턴) 레코드. **현재 버전** |
| `record.v0.1.schema.json` | 이전 버전. 서버와 검증기가 계속 받는다 (`schema_version`으로 구분) |
| `seed_cell.v0.2.schema.json` | 집계 시드 셀(`kind: "seed_cell"`): 선호(승·패·무)나 사용량(토큰·점유율·순위) |

- 형식: JSON Schema draft 2020-12
- 근거: `research/2026-09-27-feasibility-report.md`의 v0.1 초안
- 수집기 패키지 안(`collector/modelreceipts/schemas/`)에 바이트 단위로 같은 사본이 있다. 스키마를 고치면 둘 다 바꾼다(CI가 `cmp`로 확인).

## 설계 원칙

| 원칙 | 스키마에서 |
|---|---|
| 결과 증거가 1급 신호 | `outcome.evidence`는 **필수**다. 담는 것: 테스트 감지와 통과, 커밋, 도구 오류 수, 다음 프롬프트 재시도(+ `retry_detector`), (후속) 되돌리기 |
| 자기평가는 격리 | `outcome.self_assessment`는 선택이고 `x-ranking: excluded-by-default`다. `rater`(`self_claim`/`self_llm`/`judge_llm`/`user`)와 `extractor`(`claim-rules-v1` 등)를 기록한다. 서버는 이 값을 별도 테이블에 저장한다 |
| 모름 ≠ 실패 | 증거 필드는 `null`(알 수 없음)과 `false`를 구분한다. v0.2는 시드가 모르는 값(`committed`, `tool_error_count`, `turns`, 토큰, `test_runs`)도 `null`로 둘 수 있다 |
| 원문 없음 | 모든 객체가 `additionalProperties: false`다. `privacy.content_included`와 `privacy.identifiers_included`는 `const false` |
| 폐쇄형 분류 | `task.l1`(10개), `task.l2`(코딩 12개). L1이 coding이 아니면 L2는 `null`이다(`if/then/else`). 분류기 id를 `task.classifier`에 남긴다 |
| 방법은 모델만큼 중요 | `method.harness`, `workflow_tags`, `tools_used`(이름만) |
| 서빙 경로 기록 | `model.route`. 같은 가중치도 경로마다 점수가 다를 수 있다 |
| 교란 공변량 | `task.difficulty_prior`(편집 파일 수, 첫 호출 컨텍스트 토큰), `pairing.pair_id`(페어 모드) |
| 시드와 분리 | `source.source_type`은 `field_report` / `benchmark` / `preference` / `usage` 중 하나다. 선호·사용량은 레코드가 아니라 `seed_cell`로 저장한다 |
| 비용 이중 기록 | 클라이언트는 `cost_usd_client`만 보낸다. v0.2에서는 `cost_usd_server`와 `install_key_sig`가 `null` 고정이다. 서버가 계산하는 값과 서명은 레코드 본문이 아니라 서버 쪽 테이블과 HTTP 헤더에 둔다 |

## v0.1 → v0.2 변경

- **nullable로 바뀐 필드:** `usage.turns`, 토큰 4종, `evidence.test_runs`, `evidence.committed`, `evidence.tool_error_count`
- **추가:** `evidence.retry_detector`. 필수이며 값은 `retry-rules-vN` / `manual` / `synthetic` / `null`
- **자기평가:** `self_assessment.extractor`가 필수가 되었다. `rater`에 `self_claim`이 추가되었다.
- **`null` 고정:** `usage.cost_usd_server`, `source.install_key_sig`
- **새 스키마:** `seed_cell.v0.2.schema.json`
- **변환:** `python3 -m modelreceipts migrate FILES --out-dir DIR`
  - 입력 파일은 바꾸지 않는다.
  - 시드 레코드(`collector=seed-import`)의 자리표시값만 `null`로 바꾼다.
  - 현장 보고의 `false`/`0`은 실제 관측값일 수 있으므로 그대로 둔다.
  - 무엇을 바꿨는지 기록으로 남긴다.

## 예시 (`examples/`)

값은 모두 **합성(synthetic)** 이며 실제 측정이 아니다. `example-model-*`는 가상의 모델 id다.

1. `01-stop-hook-bugfix-tests-passed.json`: Stop 훅, 버그 수정, 테스트 통과 + 커밋
2. `02-self-assessment-disagrees-with-evidence.json`: 에이전트는 성공을 주장했지만(`self_claim` 0.95) 테스트가 실패했고 다음 프롬프트에서 재시도됐다. 이 불일치가 프로젝트의 핵심 관찰 대상이다.
3. `03-pair-mode-refactor.json`: 같은 작업을 두 모델로 돌린 페어 모드 레코드(`pairing.pair_id`)
4. `v0.1/`: 위 세 개의 v0.1 원본(호환성 시험용)
5. `seed-cells/preference-cell.json`, `seed-cells/usage-cell.json`: 합성 시드 셀

검증:

```bash
PYTHONPATH=collector python3 -m modelreceipts validate schema/examples/*.json schema/examples/v0.1/*.json
PYTHONPATH=collector python3 -m modelreceipts validate --allow-seed-cells schema/examples/seed-cells/*.json
```

## 버전 정책

- `schema_version`은 semver를 따른다. 필드 추가·enum 확장은 minor, 의미 변경·삭제는 major다.
- 0.x 동안은 minor에서도 nullable 확대 같은 호환 변경을 할 수 있다.
- 서버는 받는 버전을 명시적으로 나열한다(`/healthz`의 `schema_versions`).
- 분류 체계는 `taxonomy_version`(`t0.1`)으로 따로 관리한다.
