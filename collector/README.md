# modelreceipts collector (v1.0.0rc2)

Claude Code `Stop` 훅 payload를 받아 레코드(schema v0.2) 하나를 만들고 **로컬에서 미리보기만** 합니다(`hook`, 기본 경로). 전송은 별도 명령 `submit --endpoint URL`을 명시적으로 줄 때만 합니다.

네트워크 코드는 `submit.py` 한 곳에만 있습니다. 테스트가 다음 네 가지를 확인합니다.

1. 다른 모듈은 `socket`/`urllib`/`http`/`subprocess` 등을 import하지 않습니다.
2. `hook`은 `submit`을 import하지 않습니다.
3. 새 인터프리터에서 `hook`을 돌려도 네트워크 모듈이 로드되지 않습니다.
4. `--endpoint` 없는 `submit`은 연결을 한 번도 하지 않습니다.

- Python 3.10+, 표준 라이브러리만 씁니다. 테스트의 `jsonschema`·`cryptography` 교차 검증은 설치돼 있을 때만 돕니다.
- 스키마는 패키지 안(`modelreceipts/schemas/`)에도 들어 있어서 소스 체크아웃 밖에서도 동작합니다. CI가 `schema/`와 바이트 단위로 같은지 확인합니다.

## 명령

| 명령 | 하는 일 |
|---|---|
| `hook` | Stop payload(stdin 또는 `--payload`) → 레코드 미리보기. `--hook`이면 항상 exit 0에 stdout 비움. `--preview-dir`이면 파일로 저장 |
| `submit` | 미리보기 후, `--endpoint`가 있을 때만 서명해서 `POST /v1/records` |
| `keygen` | 로컬 Ed25519 설치 키 생성 (`0600`, 이미 있으면 덮어쓰지 않음) |
| `query` | 기여자 전용 상세 집계를 서명된 `GET /v1/aggregates/detail`로 조회 |
| `pair A B [--apply]` | 두 미리보기 레코드를 "같은 태스크, 다른 모델" 쌍으로 표시 (기본 dry run) |
| `install-hook` / `uninstall-hook` | Claude Code 설정 파일에 미리보기 전용 Stop 훅 추가/제거 (기본 dry run) |
| `validate FILES` | `.json`/`.jsonl` 검증. `schema_version`과 `kind`로 v0.1/v0.2/시드 셀 스키마를 자동 선택 |
| `migrate FILES (--out-dir D \| --stdout)` | v0.1 → v0.2 변환. 입력 파일은 바꾸지 않음 |
| `eval-classifier` | 합성 평가 세트로 분류기 클래스별 정밀도/재현율 ([`eval/`](eval/)) |
| `version` | 버전, 스키마 버전, 분류기·신호 규칙 id |

## 동작

```
stdin(Stop payload JSON) ──► transcript_path의 JSONL 파싱 (마지막 턴만)
                               ├─ model id, 토큰(스트리밍 중복 제거), API 호출 수, 지연
                               ├─ 도구 이름, 편집 파일 "개수", 테스트 명령 감지와 결과, git commit 성공 여부
                               ├─ 마지막 사용자 프롬프트 → 로컬 규칙 분류기 rules-v1 → (L1, L2) 폐쇄 코드
                               ├─ 에이전트 마지막 메시지 → claim-rules-v1 → 자기주장 점수 (self_assessment, 랭킹 제외)
                               └─ (--preview-dir) 이번 프롬프트 → retry-rules-v1 → 직전 턴 레코드의 user_retry_next_prompt 소급 기록
                           ──► schema v0.2 레코드 조립 (화이트리스트 필드만) ──► 스키마 검증 ──► 미리보기 출력
```

- **레코드에 들어가지 않는 것:** 프롬프트·응답·thinking 텍스트, 도구 인자와 결과, 파일 경로, cwd, 저장소·브랜치 이름, session id, 이메일. 텍스트는 메모리 안에서만 규칙에 넣고, 결과 값(코드, 불리언, 점수)과 규칙 id만 남깁니다.
- **MCP 도구 이름:** `mcp__서버__도구`는 사설 서버 이름이 드러날 수 있어 `mcp`로 뭉갭니다.

### 품질 신호

- **`retry-rules-v1`:** 다음 프롬프트가 다음 중 하나이면 직전 턴을 "재시도됨"으로 기록합니다.
  - 불만·재시도 표현(영어 정규식 + 한국어 키워드, 예: "still failing", "아직도", "되돌려")
  - 직전 프롬프트와 단어 Jaccard ≥ 0.6
- **소급 기록 방식:** 다음 턴의 훅이 `--preview-dir`의 상태 파일로 직전 레코드를 찾아 한 번만 채웁니다. 상태 파일 이름은 `.state/<transcript 경로 sha256 앞 32자>.json`입니다. 이미 제출한 레코드는 바꾸지 않습니다.
- **`claim-rules-v1`:** 에이전트가 스스로 성공을 주장했는지 봅니다. 점수는 명확한 성공 주장 1.0, 약한 주장 0.75, 불확실 0.5, 실패 인정 0.0, 판단 불가 `null`입니다.
  - `rater: "self_claim"`으로 기록합니다. **모델에게 자기평가를 묻지 않습니다.**
  - 서버는 이 점수를 별도 테이블에 두고 랭킹에서 뺍니다.

### 분류기

- **기본값:** `rules-v1`이 기본이고, `rules-v0`은 재현용으로 남겨 둡니다(`classify(summary, classifier="rules-v0")`).
- **기록:** 레코드의 `task.classifier`에 쓴 분류기가 남습니다.
- **정확도:** [`eval/RESULTS.md`](eval/RESULTS.md) (합성 세트이므로 실제 정확도 추정치가 아닙니다).

## 실행해 보기

```bash
# 저장소 루트에서
python3 -m unittest discover -s collector/tests -v

# 합성 fixture로 미리보기
sed "s|REPLACED_AT_TEST_TIME|$PWD/collector/tests/fixtures/synthetic_transcript.jsonl|" \
  collector/tests/fixtures/stop_payload.json | PYTHONPATH=collector python3 -m modelreceipts hook

# 검증 / 마이그레이션
PYTHONPATH=collector python3 -m modelreceipts validate schema/examples/*.json schema/examples/v0.1/*.json
PYTHONPATH=collector python3 -m modelreceipts validate --allow-seed-cells schema/examples/seed-cells/*.json
PYTHONPATH=collector python3 -m modelreceipts migrate --out-dir /tmp/v02 old-records/*.json
```

## opt-in 제출 (`submit`)과 설치 키

```bash
# 미리보기만 (전송 없음)
PYTHONPATH=collector python3 -m modelreceipts submit --record PREVIEW_DIR/<record_id>.json
# 로컬 서버로 전송: 미리보기를 먼저 출력하고, 그 JSON을 그대로 서명해 POST /v1/records
PYTHONPATH=collector python3 -m modelreceipts submit --record PREVIEW_DIR/<record_id>.json --endpoint http://127.0.0.1:8787
# 기여자 전용 상세 조회 (같은 키로 최근 90일 안에 제출했어야 함)
PYTHONPATH=collector python3 -m modelreceipts query --endpoint http://127.0.0.1:8787 --l2 coding.bugfix
```

- **입력:** `--payload`(Stop payload로 레코드를 새로 만듦) 또는 `--record`(이미 미리본 레코드 파일)
- **전송 조건:** `--endpoint`가 없으면 절대 보내지 않습니다. 스키마를 위반한 레코드도 보내지 않습니다.
- **주소 제한:** 기본은 `127.0.0.1`/`::1`/`localhost`만 허용합니다. 다른 주소는 `--allow-non-loopback`을 함께 줘야 합니다. 공개 서버는 아직 없습니다.
- **설치 키:**
  - 위치는 `--key-file`(기본 `~/.local/state/modelreceipts/install_key`)입니다. 실제로 보낼 때 처음 만들어지며, `O_EXCL`과 `0600`으로 씁니다.
  - 비밀 키는 파일 밖으로 나가지 않습니다. 요청에는 공개 키와 서명만 실립니다.
  - `.gitignore`가 `install_key*`를 막습니다.
  - 키를 잃으면 새 키는 새 기여자로 셉니다.
- **`--anonymous`:** 서명 없이 보냅니다. 서명을 요구하는 서버(기본)는 401로 거부합니다.
- **자동 제출 없음:** 훅 설정에 `submit`을 걸지 않습니다. 자동 제출은 조직 단위 끄기 스위치가 생긴 뒤에 다룹니다.

## 훅 설치 (`install-hook` / `uninstall-hook`)

```bash
# 1) 무엇이 바뀌는지 diff만 본다 (파일을 쓰지 않음)
PYTHONPATH=collector python3 -m modelreceipts install-hook --settings ~/.claude/settings.json
# 2) 사용자가 직접 적용: 백업을 만든 뒤, 터미널에서 확인을 입력해야 씀
PYTHONPATH=collector python3 -m modelreceipts install-hook --settings ~/.claude/settings.json --apply
# 제거도 같은 방식
PYTHONPATH=collector python3 -m modelreceipts uninstall-hook --settings ~/.claude/settings.json [--apply]
```

- **`--settings`는 필수입니다.** 기본값이 없어서 어떤 파일을 고칠지 항상 직접 지정합니다.
- **dry-run 기본:** `--apply`가 없으면 unified diff만 출력합니다.
- **`--apply`의 확인 절차:**
  - 표준 입력이 터미널이 아니면 거부합니다. `--yes` 같은 우회 플래그는 없습니다.
  - 쓰기 전에 `<settings>.modelreceipts-backup-<UTC시각>`으로 백업합니다.
  - 임시 파일에 쓴 뒤 `os.replace`로 바꾸고, 원래 파일 권한을 유지합니다.
- **멱등성과 제거:**
  - 이미 설치돼 있으면 아무것도 바꾸지 않습니다.
  - 다른 훅과 다른 설정 키는 그대로 둡니다.
  - 제거는 이 도구가 넣은 항목(`-m modelreceipts hook … --hook`)만 지웁니다. 비게 된 `Stop`/`hooks` 키는 정리합니다.
- **설치되는 명령:**

  ```text
  PYTHONPATH=<collector> <python> -m modelreceipts hook --hook --preview-dir <dir>
  ```

  - 미리보기 전용입니다. 네트워크를 쓰지 않습니다.
  - timeout은 10초입니다.
  - `--hook`이면 항상 exit 0이고 stdout을 비웁니다. Claude Code가 Stop 훅의 stdout JSON을 훅 제어로 해석하기 때문입니다.
- **권장 위치:** 레포 로컬 `.claude/settings.json`보다 사용자 설정을 권장합니다(연구 노트: OTel 보강 변수는 사용자 설정에서만 적용).
- **이 저장소의 개발과 테스트는 실제 `~/.claude/settings.json`을 읽거나 쓰지 않았습니다.** 테스트는 임시 디렉터리만 씁니다.

## 페어 모드

같은 태스크를 두 모델로 각각 돌리고, 두 미리보기 파일을 짝지웁니다.

```bash
PYTHONPATH=collector python3 -m modelreceipts pair PREVIEW/a.json PREVIEW/b.json          # 검사만
PYTHONPATH=collector python3 -m modelreceipts pair PREVIEW/a.json PREVIEW/b.json --apply  # 공통 pair_id 기록
```

- **거부 조건:** 모델이 같거나, L2가 다르거나, 이미 다른 `pair_id`가 있으면 거부합니다.
- **기록 내용:** `--apply`는 두 파일에 같은 uuid4 `pairing.pair_id`를 쓰고 `source.collector`를 `pair-mode`로 바꿉니다.
- **집계:** 서버가 두 레코드의 마지막 테스트 결과로 맞대결을 집계합니다.

## 알려진 한계

- **레코드 범위:** "마지막 사용자 프롬프트 이후의 한 턴"입니다. 서브에이전트 transcript(`isSidechain`)는 제외합니다.
- **`tests_passed`:** 턴 안에서 **마지막으로 감지된** 테스트 명령의 `is_error`로 판단합니다. 테스트 명령 감지는 정규식 기반입니다.
- **`user_retry_next_prompt`:** `--preview-dir`을 쓸 때만 다음 턴에 채워집니다. 세션의 마지막 턴은 `null`로 남습니다.
- **`reverted_within_7d`:** 항상 `null`입니다(범위 밖).
- **비용:** transcript에 비용이 없어 `cost_usd_client`는 `null`입니다. 서버가 토큰과 가격표로 따로 재계산합니다.
- **`route`:** 환경변수 이름(`CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `ANTHROPIC_BASE_URL`)으로만 추정합니다.
- **규칙 기반 신호:** 재시도·자기주장 규칙은 단순한 규칙이라 놓치거나 잘못 잡을 수 있습니다. 그래서 규칙 id를 함께 기록해, 나중에 다시 계산하거나 필터링할 수 있게 했습니다.
- **transcript 형식:** 공개 안정 API가 아닙니다. 파서는 모르는 줄을 건너뛰도록 방어적으로 작성했습니다.
- **Ed25519 구현:** 순수 Python이라 상수 시간이 아닙니다. 설치 키는 Sybil 방지용 식별자일 뿐이고 고가치 비밀이 아니라는 전제입니다.
