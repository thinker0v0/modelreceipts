# seeds — 공개 데이터 시드

콜드스타트용 공개 데이터를 schema v0.2 레코드(벤치마크) 또는 **집계 시드 셀**(`seed_cell.v0.2`, 선호·사용량)로 바꾼다. 모든 시드는 `source.source_type`이 `field_report`가 **아니므로** 사용자 기여 증거와 섞이지 않는다. 서버는 시드를 HTTP로 받지 않고, 운영자가 로컬에서 `import-seed`로만 적재한다.

| 층 | 소스 | `source_type` | 상태 |
|---|---|---|---|
| 벤치마크 사전분포 | Aider polyglot leaderboard | `benchmark` | **구현** |
| 선호 기반 승률 | LMArena `arena-human-preference-55k` | `preference` | **구현** (집계 셀만 커밋) |
| 사용 비중 | OpenRouter 랭킹 데이터 | `usage` | **임포터 구현**, 실제 데이터 미취득 (합성 픽스처로 시험) |

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
- 리더보드에 없는 값(`committed`, `tool_error_count`, `turns`, 캐시 토큰, 보고되지 않은 토큰, `retry_detector`)은 스키마 v0.2에서 **`null`(알 수 없음)**로 둔다. v0.1 시절의 `false`/`0` 자리표시값은 `modelreceipts migrate`가 `null`로 바꾼다(`collector=seed-import`인 레코드만).
- provider는 표시 이름 기반 추정이다. route는 명령에 `openrouter/`가 있으면 `openrouter`, 별도 API base면 `proxy`, 나머지는 `unknown`.

```bash
# 요약 + 전 레코드 스키마 검증 (약 15.5k건, 수 초)
PYTHONPATH=seeds python3 -m modelreceipts_seeds aider-polyglot
# 서버 DB에 적재 (멱등)
PYTHONPATH=server python3 -m modelreceipts_server import-seed aider-polyglot
# 스냅샷 갱신은 사람이 한다: SOURCE.json의 fetch_command로 새 커밋을 받고 commit/sha256/retrieved_at을 고친 뒤 테스트
```

## LMArena `arena-human-preference-55k` (구현)

- 출처·라이선스·해시: [`data/arena-55k/SOURCE.json`](data/arena-55k/SOURCE.json)
  - Hugging Face `lmarena-ai/arena-human-preference-55k`, 리비전 `18c298340948c0e7f7727399fd459cca6ce0ca6f` (2024-05-17), 2026-09-28 취득
  - 라이선스: 이 리비전의 데이터셋 카드가 `license: apache-2.0`을 선언한다. 인용: Chiang et al., arXiv:2403.04132.
  - 원본 `train.csv`(184 MB, 모델 응답 포함)의 sha256을 기록했다. **원본은 재배포하지 않는다.**
- 커밋된 것은 [`data/arena-55k/cells.jsonl`](data/arena-55k/cells.jsonl)(1,373셀, sha256을 `SOURCE.json`에 고정)뿐이다.
  - 셀 = `(L1, L2, 모델)`별 대결·승·패·무 **개수**와 승률 `(승 + 무/2) / 대결`
  - 각 대결의 프롬프트는 수집기의 `rules-v1` 분류기로 **메모리 안에서** 분류한다. 프롬프트·응답·대결 id는 어디에도 쓰지 않는다(테스트가 합성 CSV로 확인).
  - 각 대결은 `(L1, L2)`, `(L1, 전체)`, `(전체 태스크)` 세 롤업에 한 번씩 들어간다. 57,477 대결 중 코딩으로 분류된 것은 7,673개다.
  - "tie"와 "tie (both bad)"는 모두 무승부로 센다. 자기 자신과의 대결과 라벨이 깨진 행은 건너뛴다.
- 주의: **선호는 결과 증거가 아니다.** 별도 층(`preference`)으로만 보여 주고 현장 보고와 합치거나 같이 순위를 매기지 않는다. 모델은 2023–2024년 것이고, `rules-v1`은 도구 활동이 없는 채팅 프롬프트에서 텍스트만 보므로 L1/L2 분할은 근사다.
- 140k 판(`arena-human-preference-140k`)은 프롬프트 CC-BY-4.0, 모델 출력은 각 제공사 약관이라 조건이 섞여 있어 이번에는 받지 않았다. `VisionArena-Battle` 등 해지 가능한 커스텀 약관 데이터셋은 쓰지 않는다.

```bash
PYTHONPATH=seeds python3 -m modelreceipts_seeds arena-55k                  # 커밋된 셀 검증·요약 (sha256 확인)
PYTHONPATH=server python3 -m modelreceipts_server import-seed arena-55k    # 서버 DB에 적재 (멱등)
# 셀 재생성 (사람이, 원본을 받은 뒤): SOURCE.json의 fetch_command → 아래 → cells_sha256 갱신
PYTHONPATH=seeds python3 -m modelreceipts_seeds arena-55k --rebuild-from train.csv
```

## OpenRouter 사용 비중 (임포터 구현, 실제 데이터 없음)

- 연구 노트 기준 랭킹 데이터는 CC BY 4.0이지만, JSON export는 **OpenRouter API 키가 필요**하고 엔드포인트·필드 이름을 1차 문서로 확인하지 못했다. 그래서 **이 저장소는 실제 데이터를 받지 않았다.** 웹 페이지 스크래핑이나 라이선스가 불분명한 미러도 쓰지 않는다.
- [`data/openrouter/usage.synthetic.json`](data/openrouter/usage.synthetic.json): **합성 픽스처**(가상 모델 이름, CC0). 임포터와 대시보드 샘플 시험용이다.
- 입력 형식(실제 export를 확인한 뒤 이 형태로 맞춘다):

  ```json
  {"period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
   "rows": [{"model": "<vendor>/<model>", "tokens": 123}, {"model": "other", "tokens": 456}]}
  ```

  같은 모델의 여러 행(일별)은 합친다. `other`(롱테일)는 전체 합계에만 들어가고 셀은 없다. 셀 = 모델별 토큰, 점유율, 순위.
- 실제 export를 사람이 받은 경우: `PYTHONPATH=server python3 -m modelreceipts_server import-seed openrouter --input export.json`. `source_id`는 파일 sha256으로 `openrouter-usage@<sha12>`가 된다. 공개할 때는 "Data: OpenRouter, CC BY 4.0"을 표기하고 현재 약관을 확인한다([`docs/USER_TASKS.md`](../docs/USER_TASKS.md)).
- 사용량은 **채택도**이지 품질 신호가 아니다. `usage` 층으로만 보여 준다.

## 테스트

```bash
python3 -m unittest discover -s seeds/tests -v
```

`test_seeds.py`(Aider, 미니 YAML, 제외 소스)와 `test_cells.py`(Arena 합성 CSV 집계·원문 미포함·sha256 검사, 커밋된 셀 검증, OpenRouter 픽스처·오류 입력, Aider v0.2 null, CLI).
