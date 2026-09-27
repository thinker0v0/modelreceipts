# Record schema v0.1

`record.v0.1.schema.json` (JSON Schema draft 2020-12) — 에이전트 작업 1회(한 턴)를 기록한다.
근거: `research/2026-09-27-feasibility-report.md`의 v0.1 초안.

## 설계 원칙

| 원칙 | 스키마에서 |
|---|---|
| 결과 증거가 1급 신호 | `outcome.evidence`는 **필수**. 테스트 감지/통과, 커밋, 도구 오류 수, (후속) 되돌리기·재시도 |
| 자기평가는 격리 | `outcome.self_assessment`는 선택, `x-ranking: excluded-by-default`. 기본 랭킹에 쓰지 않고 "자기평가 vs 증거" 연구에만 쓴다 |
| 모름 ≠ 실패 | 증거 필드는 `null`(알 수 없음)과 `false`를 구분한다 |
| 원문 없음 | 모든 객체가 `additionalProperties: false`. `privacy.content_included`, `privacy.identifiers_included`는 `const false` |
| 폐쇄형 분류 | `task.l1`(10개), `task.l2`(코딩 12개). L1이 coding이 아니면 L2는 `null` (`if/then/else`) |
| 방법은 모델만큼 중요 | `method.harness`, `workflow_tags`, `tools_used`(이름만) |
| 서빙 경로 기록 | `model.route` — 같은 가중치도 경로마다 점수가 다를 수 있다 |
| 교란 공변량 | `task.difficulty_prior`(편집 파일 수, 첫 호출 컨텍스트 토큰) |
| 시드와 분리 | `source.source_type` = `field_report` / `benchmark` / `preference` / `usage` |
| 비용 이중 기록 | `cost_usd_client`(클라이언트 보고)와 `cost_usd_server`(서버 재계산)를 따로 저장 |

## 예시 (`examples/`)

값은 모두 **합성(synthetic)** 이며 실제 측정이 아니다. `example-model-*`는 가상의 모델 id다.

1. `01-stop-hook-bugfix-tests-passed.json` — Stop 훅, 버그 수정, 테스트 통과 + 커밋
2. `02-self-assessment-disagrees-with-evidence.json` — 자기평가 0.95인데 테스트 실패·재시도. 이 불일치가 프로젝트의 핵심 관찰 대상
3. `03-pair-mode-refactor.json` — 같은 작업을 두 모델로 돌린 쌍대 모드 레코드(`pairing.pair_id`)

검증: `PYTHONPATH=collector python3 -m modelreceipts validate schema/examples/*.json`

## 버전 정책 (잠정)

`schema_version`은 semver. 필드 추가·enum 확장은 minor, 의미 변경·삭제는 major. 분류 체계는 `taxonomy_version`(`t0.1`)으로 별도 관리한다.
