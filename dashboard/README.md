# dashboard

`index.html` 한 파일로 된 정적 뷰어다. 외부 스크립트나 폰트를 쓰지 않는다. 서버 집계 JSON을 읽어 그린다. 읽는 JSON은 두 가지다.

- `GET /v1/aggregates/detail`: 기여자 상세 보기
- `GET /v1/overview`: 공개 개요 보기

## 기본 데이터: 샘플

샘플 파일:

- [`data/aggregates.sample.json`](data/aggregates.sample.json): 기여자 상세 샘플. 기본으로 열린다.
- [`data/overview.sample.json`](data/overview.sample.json): 공개 개요 샘플. `?view=overview`로 연다.

샘플에 든 데이터:

- **실제 공개 데이터:**
  - benchmark 셀: Aider polyglot 리더보드(고정 커밋 스냅샷, Apache-2.0)
  - preference 셀: LMArena arena-human-preference-55k 집계 개수(Apache-2.0, 전체 태스크 + coding 롤업만)
- **전부 합성(SYNTHETIC):**
  - field_report 셀과 페어 모드 결과: `example-model-*`, `example-harness-*` 같은 가상 이름으로, 결정적 의사난수로 만들었다.
  - 자기평가(`self_claim`)와 재시도 값도 합성이다.
  - 서버 비용은 합성 가격표로 계산했다.
  - usage 셀은 OpenRouter 모양의 합성 픽스처에서 왔다.

샘플 다시 만들기: `PYTHONPATH=server python3 -m modelreceipts_server make-sample`. 이 명령은 `docs/figures/self-vs-evidence.synthetic.svg`도 함께 만든다.

## 파라미터

- `?data=URL`: 다른 집계를 읽는다. 이때 보기 전환 메뉴는 숨긴다.
  - 로컬 서버의 `http://127.0.0.1:8787/`은 `?data=/v1/overview`로 이동한다.
  - 기여자 상세는 서명이 필요하므로 브라우저로 직접 읽지 못한다. `modelreceipts query`로 받은 JSON을 파일로 저장해서 연다.
- `?view=overview|detail`: 샘플의 보기를 고른다.
- `?theme=light|dark`
- `?layer=benchmark`: 셀 브라우저가 처음 보여 줄 층

브라우저는 `file://`에서 JSON을 fetch하지 못하므로 서버의 `/dashboard/` 경로로 연다. 불러오지 못하면 안내 카드가 나온다.

## 화면

1. **배너:** 데이터 라벨(`dataset.label`)
2. **타일:** 현장 보고 수, 공개된 현장 셀 / 전체, 순위가 뒤집힌 L2, 벤치마크 시드 레코드, 선호·사용량 시드 셀
3. **공개 개요 안내:** 공개 개요 보기에서만 보인다. 상세 조회 조건과 상세에서 추가로 볼 수 있는 항목을 보여 준다.
4. **자기평가 기반 순위 vs 증거 기반 순위:** slope chart와 표 보기
   - 서버의 `self_vs_evidence` 결과를 쓴다. 공개 임계를 넘은 field_report 셀만 들어간다.
   - 상세 보기에서만 보인다.
5. **페어 모드 맞대결:** A 승 / 무승부 / B 승 막대, A 점수와 Wilson CI, 표 보기
   - 색은 파랑↔빨강 발산 쌍에 중립 회색 가운데 값을 쓴다. 무승부 회색은 대비가 낮아서 숫자 라벨과 표 보기를 같이 둔다.
6. **시드 층:** 선호 승률(점 + 95% CI, 50% 기준선) 또는 사용량 점유율 막대, 표 보기. 시드 층은 현장 보고와 합치지 않는다.
7. **태스크 셀 브라우저:** 데이터 층 · L2 · 방법 · 정렬 필터
   - 비용은 클라이언트 보고값을 먼저 쓰고, 없으면 서버 가격표 값을 쓴다("서버"로 표시).
   - "다음 프롬프트 재시도" 열이 있다.
   - 비공개 셀은 사유를 표시한다(임계 미달 / 한 기여자 비중 초과).
   - 폭 560px 이하에서는 카드형으로 바뀐다.
8. **데이터 출처:** 시드의 URL·커밋·라이선스, SYNTHETIC 여부, 서버 가격표의 출처·기준일·검증 여부

## 스크린샷

`docs/screenshots/`의 4장(데스크톱/폰 × 라이트/다크)은 로컬 서버가 샘플 JSON을 서빙하는 상태에서 Playwright가 캐시한 Chromium headless shell로 찍었다(2026-09-28, 기여자 상세 보기, 데스크톱은 위쪽 2600px).

```bash
PYTHONPATH=server python3 -m modelreceipts_server serve --db /tmp/mr-shots.sqlite3 &
CH=$(ls -d ~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64)/chrome-headless-shell
$CH --no-sandbox --headless --hide-scrollbars --virtual-time-budget=4000 --window-size=1280,2600 \
  --screenshot=dashboard-desktop-light.png "http://127.0.0.1:8787/dashboard/?theme=light"
# 폰: --window-size=390,4104 (위쪽만)
```
