# rc2 → rc3 Codex 단계

동일한 저장소 샘플, Chromium headless shell, 배율 1로 캡처했다. 외부 웹사이트나 실제 transcript는 사용하지 않았다. 전후 이미지는 전체 페이지이며, `../dashboard-phone-*.png`는 README 가독성을 위해 위쪽 3000px만 담는다.

| 조건 | 전 (rc2) | 후 (rc3) |
|---|---|---|
| 1440px · 라이트 | [before](before-desktop-light.png) | [after](after-desktop-light.png) |
| 1440px · 다크 | [before](before-desktop-dark.png) | [after](after-desktop-dark.png) |
| 390px · 라이트 | [before](before-phone-light.png) | [after](after-phone-light.png) |
| 390px · 다크 | [before](before-phone-dark.png) | [after](after-phone-dark.png) |

현재 코드에서 수정 후 캡처와 UI 검증을 다시 실행하는 명령(저장소 루트, Node 22 이상):

```bash
H=$(ls -d ~/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/ | head -1)
node dashboard/tools/check-ui.mjs "${H}chrome-headless-shell" after
```

`before`는 수정 전 코드에서 이미 촬영한 보존본이다. 현재 코드로 `before`를 실행하면 보존본을 덮어쓰므로 전후 비교 재현 시 각각 해당 코드 리비전에서 실행해야 한다.

드라이버는 127.0.0.1의 임시 포트만 사용하고 종료 시 서버와 Chromium을 닫는다. 프로필·임시 파일은 gitignore된 `server/var/ui/` 아래에 둔다. `before-checks.json`, `after-checks.json`은 캡처 조건과 검사 결과다. 추가 상태 캡처는 상위 폴더의 `dashboard-{overview,empty,error,loading}-phone.png`다.
