# dashboard

`index.html` 한 파일로 된 정적 뷰어다. 외부 스크립트·폰트·CDN·추적 코드를 쓰지 않는다. 서버 집계 JSON을 읽어 그린다. 읽는 JSON은 두 가지다.

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

디자인 참고와 접근성 기준은 [`docs/DESIGN_REFERENCES.md`](../docs/DESIGN_REFERENCES.md)에 있다.

1. **출처 띠(맨 위, 항상 보임):** 합성 데이터가 섞였는지와 실제 공개 데이터의 이름. `dataset.label` 원문은 펼쳐서 본다.
2. **히어로:** 큰 숫자 하나(자기평가 1위 ≠ 증거 1위인 L2 수, 공개 개요에서는 공개된 현장 셀 수)와 가장 큰 과대평가 한 줄, 보조 KPI 4개. 합성 값에는 태그가 붙는다.
3. **공개 개요 안내:** 공개 개요 보기에서만 보인다. 상세 조회 조건과 상세에서 추가로 보는 항목.
4. **자기평가 순위 vs 증거 순위(시그니처):** L2 칩, slope chart, 한 문장 캡션, 표 보기
   - 서버의 `self_vs_evidence` 결과를 쓴다. 공개 임계를 넘은 field_report 셀만 들어간다. 상세 보기에서만 보인다.
   - 선은 Tab으로 하나씩 초점을 받고 툴팁을 연다.
5. **태스크 셀 리더보드:** 필터 한 줄(데이터 층 · L2 · 방법 · 정렬)이 아래 두 화면에 함께 적용된다.
   - **비용 대 통과율 산점도:** 로그 비용 축, CI 수염, 비용 대비 최선 경계와 그 위 셀의 직접 라벨. 초점을 준 뒤 ←/→/Home/End/Esc.
   - **리더보드 표:** 순위와 통계적 순위, n·k 배지, 모든 행이 같은 0–100% 축을 쓰는 CI 막대, 커밋, 재시도, 비용($/태스크, $/성공, `*` = 서버 가격표 재계산), 지연, 자기평가(참고)
   - 비공개 셀은 "비공개" 배지와 사유(임계 미달 / 한 기여자 비중 초과)만 보인다.
   - 폭 640px 이하에서는 카드형으로 바뀐다.
6. **페어 모드 맞대결:** A 승 / 무 / B 승 막대, A 점수와 Wilson CI, 표 보기. 색은 파랑↔빨강 발산 쌍에 중립 회색 가운데 값.
7. **시드 층:** 선호 승률(점 + 95% CI, 50% 기준선, 확대 축) 또는 사용량 점유율(한 줄 100% 막대 + 범례), 표 보기. 시드 층은 현장 보고와 합치지 않는다.
8. **데이터 출처:** 시드의 URL·커밋·라이선스, SYNTHETIC 여부, 서버 가격표의 출처·기준일·검증 여부

## 스크린샷

`docs/screenshots/`의 4장(데스크톱/폰 × 라이트/다크)은 로컬 서버가 샘플 JSON을 서빙하는 상태에서 Playwright가 캐시한 Chromium headless shell로 찍었다(2026-09-28, 기여자 상세 보기). 데스크톱은 페이지 전체(1280×4224), 폰은 위쪽 3000px(390×3000)이다.

```bash
PYTHONPATH=server python3 -m modelreceipts_server serve --db /tmp/mr-shots.sqlite3 --port 8791 &
H=$(ls -d ~/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/ | head -1)
${H}chrome-headless-shell --no-sandbox --headless --hide-scrollbars --virtual-time-budget=5000 --window-size=1280,4224 \
  --screenshot=dashboard-desktop-light.png "http://127.0.0.1:8791/dashboard/?theme=light"
# 폰: --window-size=390,3000
kill %1   # 서버 종료
```
