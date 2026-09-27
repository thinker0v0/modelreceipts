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

## 현재 단계: pre-alpha 약 10% (2026-09-27, Round 2)
Round 1(<5%): 이름, README, 스키마 v0.1 + 검증기, dry-run 수집기, 대시보드 목업.
Round 2(~10%): stdlib ingest 서버(`server/`, 127.0.0.1 전용, append-only SQLite, k·n 임계 집계), 수집기 opt-in `submit --endpoint`,
Aider polyglot 시드(`seeds/`), 집계 JSON 기반 대시보드 + 라벨 붙은 샘플, CHANGELOG, CI 워크플로(미push).
테스트: `python3 -m unittest discover -s {collector,server,seeds}/tests`. 배포·원격·push 없음.
