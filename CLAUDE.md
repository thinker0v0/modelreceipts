# opensource — 태스크별 최적 모델 DB

## 목표 (최종 100%)
AI 에이전트가 실제 작업을 끝내면 (태스크 분류 코드, 모델, 방법/하네스, 비용, **검증 가능한 결과 증거**)를 공용 DB에 자동 기여하고,
기여자는 "내 태스크에 가장 결과가 좋은 모델×방법×비용"을 조회. 자체평가는 저장만 하고 기본 랭킹에서 제외.

## 확정된 방향 (사용자 선택 A, 2026-09-27)
- 1차 수집 경로: Claude Code `Stop` 훅, 코딩 태스크만.
- 원문 프롬프트/모델 출력은 전송하지 않음. 로컬에서 폐쇄형 분류 코드로 변환.
- 시드: Aider 리더보드, Arena 선호 데이터(집계), OpenRouter CC BY 랭킹. AA·LMSYS-Chat-1M 제외.
- 공개: 코드·스키마·k-임계 집계. 원시 레코드는 비공개. 게이트 = 공개 개요 + 기여자 전용 세분 조회.
- 근거: `research/2026-09-27-feasibility-report.md`, `research/notes/`.

## 현재 단계: v1.0.0-rc2 코드 완성 후보 (2026-09-28)

rc2는 새 기능 없이 품질·보안 자체 점검(`docs/QUALITY.md`)과 대시보드 재디자인(`docs/DESIGN_REFERENCES.md`)만 했다.

rc1에서 코드로 할 수 있는 로드맵 항목을 모두 구현했다. 목록:

- 훅 설치/제거 스크립트: dry-run 기본, `--settings` 필수, 실제 `~/.claude/settings.json`은 건드리지 않음
- 분류기 `rules-v1`과 합성 평가 세트
- 재시도·자기주장 신호
- 서버 가격표 비용(별도 테이블)
- 스키마 v0.2와 `migrate`/`validate`
- Ed25519 서명과 레이트 리밋
- Arena 55k 집계 시드, OpenRouter 임포터(합성 픽스처)
- 공개 개요 / 기여자 전용 상세 게이트
- 페어 모드와 자기평가 vs 증거 데모(합성)

남은 일은 사람이 할 일이다: [`docs/USER_TASKS.md`](docs/USER_TASKS.md) (배포, PyPI, 데이터 라이선스, 가격표 라이브 검증, OpenRouter 키, 기여자 모집, dogfooding).

테스트: `python3 -m unittest discover -s {collector,server,seeds}/tests` (79 / 60 / 21). 배포·원격·push 없음.
