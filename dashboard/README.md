# dashboard (UI mockup)

`index.html` 한 파일짜리 정적 목업이다. 외부 스크립트·폰트·네트워크 요청이 없고, 모든 수치는 **SAMPLE / MOCK DATA**(고정 seed 의사난수)다.

- 브라우저에서 `dashboard/index.html`을 열면 된다. 테마는 자동/라이트/다크, `?theme=dark`로 강제할 수 있다.
- 화면 1: 자기평가 기반 순위 vs 증거 기반 순위 (slope chart + 표 보기)
- 화면 2: 태스크 셀 브라우저 (L1/L2 × 모델 × 방법 × 비용, Wilson 95% CI, k·n 임계 미만 셀은 비공개 표시). 폭 560px 이하에서는 카드형으로 바뀐다.

스크린샷(`docs/screenshots/`)은 Playwright가 캐시한 Chromium headless shell로 찍었다.

```bash
CH=~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell
$CH --no-sandbox --hide-scrollbars --virtual-time-budget=2000 --window-size=1280,2400 \
  --screenshot=docs/screenshots/dashboard-desktop-light.png "file://$PWD/dashboard/index.html?theme=light"
```
