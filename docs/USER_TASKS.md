# 사람이 해야 하는 일 (v1.0.0-rc1 이후)

코드로 할 수 있는 로드맵 항목은 v1.0.0-rc1에서 모두 구현했습니다. 아래 일은 **계정, 돈, 법적 판단, 사람과의 관계**가 걸려 있어서 에이전트가 대신하지 않았습니다. 순서는 권장 순서입니다.

## 1. 데이터 라이선스 결정

- **정할 것:** 공개 집계(`/v1/overview`, 대시보드, 나중의 덤프)에 붙일 라이선스. 후보는 **CC-BY-4.0**과 **CDLA-Permissive-2.0**입니다. 코드 라이선스는 Apache-2.0(잠정)입니다.
- **확인할 것:**
  - 시드 출처의 조건과 충돌하지 않는지
    - Aider: Apache-2.0
    - LMArena 55k: Apache-2.0, 인용 필요
    - OpenRouter: CC BY 4.0, 표기 필요
  - 기여자 동의 문구. 제출하는 레코드가 이 라이선스로 집계·공개된다는 안내를 `submit` 미리보기와 README에 넣습니다.
- **결정 후 할 일:** README "라이선스" 절 갱신, `LICENSE-DATA` 추가, 집계 JSON에 `license` 필드 추가(코드 작업은 작음).

## 2. 가격표 검증

- `server/modelreceipts_server/data/prices.json`은 claude-api 스킬에 캐시된 가격표(기준일 2026-06-24)에서 옮겼고, `verified_live: false`입니다.
- **할 일:**
  1. <https://platform.claude.com/docs/en/about-claude/pricing> 라이브 페이지와 대조합니다.
  2. 값·`as_of`·`retrieved_at`을 고치고 `verified_live: true`로 바꿉니다.
  3. `price_table_id`를 새 날짜로 올립니다. 기존 레코드의 서버 비용은 append-only라 그대로 남고, 새 표 id로 구분됩니다.
- Bedrock·Vertex 등 다른 경로의 가격표가 필요하면 별도 파일로 추가합니다. 지금은 `route=direct`만 계산합니다.

## 3. 실제 배포

- **현재 코드의 제약:** 서버는 loopback에만 바인딩합니다. 공개 운영에 필요한 것은 다음과 같습니다.
  - 도메인과 TLS 종단 리버스 프록시(예: Caddy/nginx). 프록시가 `127.0.0.1:8787`로 넘깁니다.
  - DB 백업(`server/var/*.sqlite3` 파일 단위 백업. append-only라 증분 복사가 쉽습니다)과 디스크 모니터링
  - 운영 salt 보관: DB의 `meta.contributor_salt`. 잃으면 기여자 연속성이 끊깁니다.
  - 서비스 관리(systemd 등), 로그 보관 정책. 요청 로그에는 IP와 헤더가 없습니다.
- **트래픽이 늘면 옮길 것:** `http.server`와 순수 Python Ed25519는 운영용으로 약합니다. ASGI + `cryptography`로 옮기는 것은 코드 작업이지만, 호스팅 선택은 사람이 합니다.
- **운영 설정을 정합니다.** 기본값은 다음과 같습니다.
  - `--signatures required`, `--gate on`
  - 임계 k=5, n=30, 한 기여자 비중 ≤ 0.5
  - 레이트 리밋 120/h, 버스트 30, 셀 일일 상한 50
- **공개 서버가 생기면 수집기의 loopback 제한을 풉니다.** 지금은 `--allow-non-loopback`이 필요합니다. 정식 엔드포인트를 허용 목록에 넣는 코드 변경은 작습니다.
- **하지 말 것:** 비용이 드는 호스팅 계약, 도메인 구매, 인증서 발급은 에이전트가 하지 않았습니다.

## 4. PyPI 게시

- `collector/pyproject.toml`은 `1.0.0rc1`이고, 스키마를 `package-data`로 포함합니다.
- **할 일:**
  1. PyPI 이름 `modelreceipts`를 확보합니다.
  2. Trusted Publishing(GitHub Actions OIDC)을 설정합니다. 토큰을 저장소에 두지 않습니다.
  3. 깨끗한 환경에서 `python -m build`로 wheel을 만들고 다음을 확인합니다.
     - `modelreceipts version`
     - `validate`
     - `install-hook --settings /tmp/x.json`(dry-run)
  4. TestPyPI에 먼저 올리고, 그다음 PyPI에 올립니다.
- 참고: 에이전트 환경에는 `pip`/`wheel`이 없어서 **wheel 빌드는 확인하지 못했습니다.** 테스트는 소스 체크아웃 기준입니다.
- 서버(`modelreceipts_server`)와 시드는 아직 패키지로 만들지 않았습니다. 저장소 체크아웃 기준으로 씁니다.

## 5. OpenRouter 실제 데이터

- **필요한 것:** OpenRouter API 키(사용자 계정). 키는 저장소나 파일에 넣지 않습니다.
- **확인할 것:**
  - 랭킹 export 엔드포인트와 필드 이름
  - 현재 데이터 약관(CC BY 4.0 여부, 재배포와 집계 공개 범위)
- **할 일:**
  1. export를 받습니다.
  2. `seeds/modelreceipts_seeds/openrouter.py`의 입력 형식(`{"period", "rows": [{"model", "tokens"}]}`)으로 변환합니다.
  3. `import-seed openrouter --input FILE`로 적재합니다.
  4. 공개하려면 원본 URL·날짜·sha256을 새 `SOURCE.json`에 기록하고 "Data: OpenRouter, CC BY 4.0"을 표기합니다.

## 6. 법적·프라이버시 검토

- 다음 문서를 한 번은 사람이 검토하는 것이 좋습니다.
  - 개인정보 처리 안내
    - 수집 항목: 폐쇄형 코드, 모델 id, 토큰, 지연, 불리언 증거
    - 보관 기간
    - 공개 키 해시
  - 기여자 동의
  - 탈퇴 처리: append-only와 충돌합니다. 기여자 해시 단위 비공개 처리를 정책으로 정해야 합니다.
- Arena 데이터: 모델 출력은 각 제공사 약관을 따릅니다. 저장소에는 개수만 있지만, 인용과 고지 문구를 확인합니다.
- 해커톤이나 회사 제출물로 쓸 때 소속 기관의 오픈소스 공개 절차가 있는지 확인합니다.

## 7. 실제 설정에 훅 적용과 dogfooding

- **이 저장소의 개발과 테스트는 실제 `~/.claude/settings.json`을 건드리지 않았습니다.** 적용은 사용자가 직접 합니다.

  ```bash
  PYTHONPATH=collector python3 -m modelreceipts install-hook --settings ~/.claude/settings.json          # diff 확인
  PYTHONPATH=collector python3 -m modelreceipts install-hook --settings ~/.claude/settings.json --apply  # 백업 + 확인 입력
  ```

- 1~2주 동안 미리보기(`~/.local/state/modelreceipts/preview/`)만 쌓고 다음을 점검합니다.
  - 분류가 맞는지(실제 정확도는 이것으로만 알 수 있습니다)
  - 재시도·자기주장 규칙이 맞게 잡는지
  - 원문이 새지 않는지
- 괜찮으면 로컬 서버에 `submit`해서 첫 실제 레코드를 만듭니다. **여기서부터가 "실데이터" 로드맵 항목입니다.**
- 실제 프롬프트는 이슈·PR에 올리지 않고, 오분류는 합성 예문으로 옮겨 `collector/eval/`의 `dev`에 추가합니다.

## 8. 기여자 모집

- **목표(보고서 기준):** 외부 설치 인스턴스 두 자릿수. 코딩 L2 셀 몇 개가 k=5, n=30을 넘으면 "자기평가 순위 ≠ 증거 순위"를 실데이터로 처음 보여 줄 수 있습니다.
- **채널:** Claude Code 사용자 커뮤니티, 해커톤 참가자, 사내 개발자. 페어 모드는 같은 태스크를 두 모델로 돌리는 자발적 참여가 필요합니다.
- **안내할 것:** 무엇이 전송되고 무엇이 전송되지 않는지(README "프라이버시 원칙"), 설치 키의 의미, 기여자 전용 상세 조회라는 보상.

## 9. GitHub push와 릴리스

- 로컬 커밋만 있습니다. push와 태그(`v1.0.0-rc1`)는 메인 세션이나 사용자가 `gh auth login` 뒤에 합니다.
- CI(`.github/workflows/ci.yml`)는 push 후 처음 돕니다. Python 3.10에서 실제로 도는지 확인합니다. 로컬은 3.12에서만 실행했습니다.
