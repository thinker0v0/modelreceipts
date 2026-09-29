# 전후 캡처 — rc2 → rc3 Codex 단계 → rc3 Opus 단계

모든 캡처는 저장소 샘플 데이터를 headless Chromium(배율 1)으로 찍었다. 외부 웹사이트, 실제 transcript, 실제 `~/.claude` 파일은 쓰지 않았다.

## 2차: Codex 단계(`0c31c5c`) → Opus 단계 (핵심 화면 3개)

두 코드를 **같은 드라이버**(현재 `dashboard/tools/check-ui.mjs`, 스크롤바 숨김)로 찍었기 때문에 폭과 조건이 같다.

| 화면 | Codex 단계 | Opus 단계 | 볼 곳 |
|---|---|---|---|
| 1440px · 라이트 · 상단 | [codex-desktop-top](codex-desktop-top.png) | [opus-desktop-top](opus-desktop-top.png) | 섹션 링크와 스냅샷을 합친 도구 막대, UTC 표기, 히어로 날짜 중복 제거, slope 워터마크 여백 |
| 390px · 다크 · 산점도와 리더보드 | [codex-phone-cells-dark](codex-phone-cells-dark.png) | [opus-phone-cells-dark](opus-phone-cells-dark.png) | 가격 축 양 끝 눈금, 산점도와 표 설명 사이 구분선, 카드 보조 지표 두 열 |
| 390px · 라이트 · 셀이 없는 집계 | [codex-phone-empty](codex-phone-empty.png) | [opus-phone-empty](opus-phone-empty.png) | `?` 자리표시 제거, 숨은 섹션 링크 제거, 벤치마크 KPI 문구 |

재현 방법(저장소 루트, Node 22 이상):

```bash
H=$(ls -d ~/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/ | head -1)
# Opus 단계(현재 코드)
node dashboard/tools/check-ui.mjs "${H}chrome-headless-shell" keyviews:opus
# Codex 단계: 해당 리비전의 dashboard/만 임시 폴더에 풀고, 그 폴더에서 현재 드라이버를 실행
tmp=$(mktemp -d) && git archive 0c31c5c dashboard | tar -x -C "$tmp"
(cd "$tmp" && node "$OLDPWD/dashboard/tools/check-ui.mjs" "${H}chrome-headless-shell" keyviews:codex)
cp "$tmp"/docs/screenshots/before_after/codex-*.png docs/screenshots/before_after/
```

오류·로딩·개요 상태는 상위 폴더의 `dashboard-{error,loading,overview,empty}-phone.png`에 있다. 이 캡처들은 모두 Opus 단계 코드로 다시 찍었다. 기계 검사 결과는 [`../ui-checks.json`](../ui-checks.json)에 있다.

## 1차: rc2 → rc3 Codex 단계 (전체 페이지, 보존본)

Codex 단계가 `0c31c5c` 시점의 드라이버(`before`/`after` 모드)로 찍은 전체 페이지다. 당시 드라이버는 스크롤바를 숨기지 않아서, 실제 레이아웃 폭이 "1440px"은 1425px, "390px"은 375px이다. 현재 드라이버에는 이 모드가 없다. 다시 찍으려면 해당 리비전의 드라이버를 써야 한다.

| 조건 | 전 (rc2) | 후 (rc3 Codex 단계) |
|---|---|---|
| 1440px · 라이트 | [before](before-desktop-light.png) | [after](after-desktop-light.png) |
| 1440px · 다크 | [before](before-desktop-dark.png) | [after](after-desktop-dark.png) |
| 390px · 라이트 | [before](before-phone-light.png) | [after](after-phone-light.png) |
| 390px · 다크 | [before](before-phone-dark.png) | [after](after-phone-dark.png) |

`before-checks.json`과 `after-checks.json`은 1차 캡처 조건과 Codex 단계의 검사 결과다.

드라이버는 127.0.0.1 임시 포트만 쓰고, 끝나면 서버와 Chromium을 닫는다. 브라우저 프로필과 임시 파일은 gitignore된 `server/var/ui/` 아래에 둔다.
