# seeds — 공개 데이터 시드

콜드스타트용 공개 데이터를 schema v0.1 레코드로 바꾼다. 모든 시드 레코드는 `source.source_type`이 `field_report`가 **아니므로** 사용자 기여 증거와 섞이지 않는다. 서버는 시드를 HTTP로 받지 않고, 운영자가 로컬에서 `import-seed`로만 적재한다.

| 층 | 소스 | `source_type` | 상태 |
|---|---|---|---|
| 벤치마크 사전분포 | Aider polyglot leaderboard | `benchmark` | **구현** |
| 선호 기반 승률 | LMArena `arena-human-preference-140k` / `-55k` | `preference` | 문서만 (아래) |
| 사용 비중 | OpenRouter 랭킹 데이터 | `usage` | 문서만 (아래) |

**영구 제외:** Artificial Analysis 데이터(무료 API도 재배포와 "모델 선택 가이드" 경쟁 제품 금지), LMSYS-Chat-1M(라이선서가 해지할 수 있는 커스텀 약관). 근거: [`research/2026-09-27-feasibility-report.md`](../research/2026-09-27-feasibility-report.md). 테스트가 `seeds/data/`에 이 둘이 없음을 확인한다.

## Aider polyglot (구현)

- 스냅샷: [`data/aider-polyglot/polyglot_leaderboard.yml`](data/aider-polyglot/polyglot_leaderboard.yml) — 수정 없이 보관.
- 출처·고정 커밋·sha256·라이선스: [`data/aider-polyglot/SOURCE.json`](data/aider-polyglot/SOURCE.json)
  - `Aider-AI/aider@cb6a152e5ee27fbc77ac499d5e628ccd74a5fa2a` (이 파일의 마지막 변경, 2025-10-04), 2026-09-27 취득
  - 라이선스 Apache-2.0 (저장소 `LICENSE.txt`). 벤치마크 문제·모델 출력은 포함하지 않는다.
  - **참고:** 이 리더보드 파일은 2025-10 이후 갱신되지 않았다. 2026년 모델은 없다.
- 임포터는 네트워크를 쓰지 않는다. 스냅샷의 sha256이 `SOURCE.json`과 다르면 멈춘다.
- YAML은 표준 라이브러리만으로 읽는다(`miniyaml.py`, 이 파일이 쓰는 부분집합만 지원하고 나머지는 오류). PyYAML이 있으면 테스트가 결과를 교차 검증한다.

### 매핑

| 리더보드 | 레코드 |
|---|---|
| 행 1개 (`test_cases`개 연습문제) | 레코드 `test_cases`개 (연습문제 1개 = 레코드 1개). id는 uuid5로 결정적이라 재적재해도 중복되지 않음 |
| `pass_num_1`, `pass_num_2` | `tests_passed=true, test_runs=1` × pass_num_1, `true, 2` × (pass_num_2−pass_num_1), 나머지 `false, 2` |
| `model` (표시 이름) | `model.id` = 표시 이름 slug (예: `claude-3-7-sonnet-20250219-32k-thinking-tokens`) — 설정 변형을 구분 |
| `edit_format` | `method.harness` = `aider-<edit_format>` (`aider-diff`, `aider-whole`, `aider-architect`, …) |
| `total_cost`, `seconds_per_case` | 연습문제당 `cost_usd_client`, `latency_ms`. **`total_cost: 0`은 "보고 안 됨"으로 보고 `null`** |
| `reasoning_effort`, `versions`, `date` | `model.effort`, `source.client_version`, `submitted_at` |
| — | `task` = `coding` / `coding.feature` (Exercism "명세대로 구현"에 대한 **근사** 매핑), classifier `seed:aider-polyglot` |

- 통과율 = `pass_num_2 / test_cases`(실제로 돈 연습문제 기준). Aider가 공개한 `pass_rate_2`는 몇 행에서 분모를 `total_tests`로 쓰거나 내림해 최대 0.4pp 다르다.
- 스키마 v0.1에서 null이 안 되는데 리더보드에 없는 값(`committed`, `tool_error_count`, `turns`, 대부분 행의 토큰)은 `false`/`0` 자리표시값으로 채운다. 서버는 benchmark 셀에서 이 필드를 집계하지 않는다(`commit_rate: null`). → 스키마 v0.2에서 nullable로 바꿀지 결정 필요.
- provider는 표시 이름 기반 추정이다. route는 명령에 `openrouter/`가 있으면 `openrouter`, 별도 API base면 `proxy`, 나머지는 `unknown`.

```bash
# 요약 + 전 레코드 스키마 검증 (약 15.5k건, 수 초)
PYTHONPATH=seeds python3 -m modelreceipts_seeds aider-polyglot
# 서버 DB에 적재 (멱등)
PYTHONPATH=server python3 -m modelreceipts_server import-seed aider-polyglot
# 스냅샷 갱신은 사람이 한다: SOURCE.json의 fetch_command로 새 커밋을 받고 commit/sha256/retrieved_at을 고친 뒤 테스트
```

## LMArena 선호 데이터 (계획, 미구현)

- 대상: [`lmarena-ai/arena-human-preference-140k`](https://huggingface.co/datasets/lmarena-ai/arena-human-preference-140k) (프롬프트 CC-BY-4.0, 모델 출력은 각 제공사 약관), [`arena-human-preference-55k`](https://huggingface.co/datasets/lmarena-ai/arena-human-preference-55k) (Apache-2.0).
- 방법: 배틀을 로컬에서 폐쇄형 L1/L2 코드로 분류한 뒤 **(L2, 모델) 단위 승률·표본 수만** 저장한다. 프롬프트·응답 원문은 저장하거나 재배포하지 않는다.
- `source_type=preference`. 선호는 결과 증거가 아니므로 증거 기반 순위에 섞지 않고 별도 층으로 표시한다.
- 미해결: 레코드 1건 = 배틀 1건으로 펼칠지, 스키마 v0.2에 "집계 시드 셀" 타입을 둘지. 배틀은 "통과/실패"가 아니라 쌍대 비교라 v0.1 `evidence`에 억지로 넣지 않는 편이 낫다.
- `VisionArena-Battle` 등 해지 가능한 커스텀 약관 데이터셋은 쓰지 않는다.

## OpenRouter 사용 비중 (계획, 미구현)

- 대상: OpenRouter 랭킹 데이터(CC BY 4.0). 일별 상위 50개 모델 토큰 사용량 + "other" 1행. 연구 노트 기준 JSON API는 **OpenRouter API 키가 필요**하다 — 키 발급·보관은 사용자 결정 사항이며 이 저장소에는 넣지 않는다.
- 품질·성공 정보가 없는 **채택도** 지표다. `source_type=usage`로만 싣고 순위 신호로 쓰지 않는다. 표기: "Data: OpenRouter, CC BY 4.0".
- 미해결: 엔드포인트 경로와 인용 형식은 1차 문서로 재확인 필요(연구 노트 Gaps).
