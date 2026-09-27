# dashboard

`index.html` 한 파일짜리 정적 뷰어다. 외부 스크립트·폰트가 없고, **`GET /v1/aggregates` 형식의 JSON**을 읽어 그린다.

- 기본 데이터: [`data/aggregates.sample.json`](data/aggregates.sample.json)
  - benchmark 셀 = **실제 공개 데이터**: Aider polyglot 리더보드 (고정 커밋 스냅샷, Apache-2.0)
  - field_report 셀 = **전부 합성(SYNTHETIC)**: `example-model-*`, `example-harness-*` 가상 이름, 결정적 의사난수. 자기평가 값도 합성이다(실제 수집기는 모델에게 자기평가를 요청하지 않는다).
  - 상단 배너와 "데이터 출처" 카드가 JSON의 `dataset.label`, `sources`를 그대로 표시한다.
  - 다시 만들기: `PYTHONPATH=server python3 -m modelreceipts_server make-sample`
- `?data=URL`로 다른 집계를 읽는다. 로컬 서버를 띄우면 `http://127.0.0.1:8787/`이 `?data=/v1/aggregates`로 이동한다.
- `?theme=light|dark`, `?layer=benchmark`(셀 브라우저 첫 층) 파라미터를 지원한다.
- 브라우저는 `file://`에서 JSON을 fetch하지 못하므로 서버(`/dashboard/`)로 연다. 실패하면 안내 카드가 나온다.

화면

1. 타일: 현장 보고 수, 공개된 현장 셀 / 전체, 순위가 뒤집힌 L2, 벤치마크 시드 레코드
2. 자기평가 기반 순위 vs 증거 기반 순위 (slope chart + 표 보기). 공개 임계를 넘은 field_report 셀만 사용
3. 태스크 셀 브라우저: 데이터 층(field_report / benchmark) · L2 · 방법 · 정렬. 임계 미달 셀은 수치 없이 "비공개 셀"로만 표시. 폭 560px 이하에서는 카드형
4. 데이터 출처: 시드의 URL·커밋·라이선스, 현장 보고의 합성 여부

## 스크린샷

`docs/screenshots/`의 4장(데스크톱/폰 × 라이트/다크)은 로컬 서버가 샘플 JSON을 서빙하는 상태에서 Playwright가 캐시한 Chromium headless shell로 찍었다.

```bash
PYTHONPATH=server python3 -m modelreceipts_server serve --db /tmp/mr-shots.sqlite3 &
CH=$(ls -d ~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64)/chrome-headless-shell
$CH --no-sandbox --headless --hide-scrollbars --virtual-time-budget=3000 --window-size=1280,3200 \
  --screenshot=desktop-light.png "http://127.0.0.1:8787/dashboard/?theme=light"
# 폰: --window-size=390,5200. 아래쪽 빈 배경은 잘라 냈다.
```
