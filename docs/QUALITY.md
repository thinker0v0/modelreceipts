# 품질·보안 및 화면 점검 (v1.0.0-rc3, 2026-09-29)

rc3는 대시보드 최종 다듬기이며 두 단계로 진행했다. 먼저 Codex 단계(`0c31c5c`)가 작업하고, 이어서 Claude Opus 단계가 그 결과를 검토하고 보완했다. 격차별 결과는 [디자인 비교](DESIGN_COMPARISON.md)에 있다. 두 단계 모두 로컬 문서와 코드만 비교했고, 외부 서비스 화면은 열어 보지 않았다.

## rc3 — Opus 단계 (최종)

Codex 단계의 수정 10개를 하나씩 검토했다.

- 그대로 둔 것: 1개(필터 요약).
- 보완한 것: 9개. 결함 예시는 다음과 같다.
  - 로딩 중 노란 띠가 합성 색 규칙을 어김
  - 헤더에 빈 pill이 보임
  - 빈 집계에서 `?` 자리표시가 새어 나옴
  - 숨은 섹션으로 가는 링크
  - 가격 축 왼쪽 끝에 눈금이 없음
  - 폰 카드가 6줄로 길어짐
  - 넘치지 않는 표가 Tab 정지점이 됨
- 새로 고친 격차: 2개(slope 워터마크 겹침, 캡처 폭 불일치).

통계 산식, 팔레트, 합성 표시 위치와 개수는 바꾸지 않았다. 브라우저 검사를 새로 추가했고, 수정할 때마다 해당 동작을 검사로 확인했다.

| 영역 | 검사 | 결과 |
|---|---|---|
| 전체 Python 테스트 | 디렉터리마다 따로 `python3 -m unittest discover -s …/tests` 실행 (2026-09-29, Python 3.12) | collector 79 / server 60 / seeds 21, 총 160개 통과. Opus 단계는 Python 코드를 바꾸지 않았다. |
| 반응형 | Chromium CDP, 스크롤바 숨김, 320·375·390·640·768·1024·1440px | 페이지 가로 넘침 없음. 폰 카드 보조 지표는 390px에서 두 열, 320px에서 한 열 |
| 글자 대비 | 두 테마에서 ink·ink-2·muted·accent·over-text·under-text 대 surface·surface-2·page, 합성·공개 태그 색 | 가장 낮은 값: 라이트 4.81:1, 다크 5.79:1. 검사한 조합은 모두 AA 4.5:1 이상. 전체 접근성 인증은 아님 |
| 차트 | slope 워터마크가 모든 순위 라벨보다 아래(데스크톱·폰 × 라이트·다크), 산점도 가격 눈금 3개 이상 | 통과 |
| 키보드·상태 | 산점도 화살표와 Esc, slope Esc, reduced motion, 필터 초기화·층 변경, 표 스크롤 영역(1440px은 정지점 없음, 768px은 region으로 초점 이동) | 통과 |
| 빈 집계·오류·지연 | 빈 응답(`?` 없음, "데이터 없음" 선택지, 숨은 섹션 링크 없음), 로컬 404(빈 pill 없음, 재시도, 샘플로 복구), 15초 초과(사람이 읽을 수 있는 메시지), 1.5초 지연(중립 띠, 빈 pill 없음) | 통과 |
| 브라우저 오류 | 위 화면·동작에서 Runtime.exceptionThrown 수집 | JavaScript 미처리 예외 0 |
| 캡처 | 기본 4장, 개요·빈 상태·오류·로딩 4장 갱신, Codex → Opus 핵심 화면 3쌍 | [before_after/README.md](screenshots/before_after/README.md) |

재현: `node dashboard/tools/check-ui.mjs <chrome-headless-shell> check`. 결과는 [ui-checks.json](screenshots/ui-checks.json)에 기록된다. 전후 캡처 방법은 [스크린샷 안내](screenshots/before_after/README.md)에 있다. 두 코어를 공유하므로 Chromium은 한 번에 하나만 띄웠고, 테스트 스위트는 차례로 실행했다. 외부·유료 API, 자격증명, 실제 transcript, 실제 `~/.claude` 파일은 쓰지 않았다.

한계는 다음과 같다.

- 실제 스크린 리더, Chromium 외 브라우저, axe 같은 자동 접근성 검사기로는 확인하지 않았다.
- 참고 서비스의 현재 화면은 다시 보지 않았다.
- 이번 작업은 보안 감사가 아니다. 아래 rc2의 남은 운영 위험은 그대로 남아 있다.
- 다른 모델 계열(GPT, Claude)이 앞 단계 결과를 검토했지만, 둘 다 AI 에이전트다. 사람의 디자인 검토를 대신하지 못한다.

## rc3 — Codex 단계

[디자인 비교](DESIGN_COMPARISON.md)의 10개 격차를 수정했다. 이 절의 기록은 Codex 단계 당시의 것이다. 이후 Opus 단계에서 보완한 내용은 위 절에 있다.

| 영역 | 검사 | 결과 |
|---|---|---|
| 전체 Python 테스트 | 각 디렉터리를 따로 `python3 -m unittest discover -s …/tests` 실행 | collector 79 / server 60 / seeds 21, 총 160개 통과 |
| 반응형 | Chromium CDP, 320·375·390·640·768·1024·1440px | 샘플 상세의 페이지 가로 넘침 없음; 모바일 보조값 한 열과 CI 줄바꿈 |
| 글자 대비 | 두 테마에서 ink·ink-2·muted·accent·over-text·under-text 대 surface·surface-2·page, 합성·공개 태그 색을 계산 | 검사한 조합 모두 WCAG AA 4.5:1 이상. 전체 접근성 인증을 뜻하지 않음 |
| 키보드·상태 | 산점도 화살표와 Esc, slope Esc, 표 스크롤 초점, 필터 초기화·층 변경, reduced motion | CDP 단언 통과. 상태 live region과 aria-busy 유지 |
| 데이터 없음·오류·지연 | 빈 합성 응답, 로컬 404, 재시도와 샘플 이동, 1.5초 지연, 15초 초과 요청 | 빈 데이터와 조건 불일치 안내 분리, 오류 복구, 로딩 해제 확인 |
| 브라우저 오류 | 위 화면·동작의 Runtime.exceptionThrown 수집 | JavaScript 미처리 예외 0 |
| 캡처 | 지정된 headless Chromium, 127.0.0.1 전용 임시 서버 | 기본 4장 갱신, 전후 전체 페이지 8장, 개요·빈 상태·오류·로딩 4장 보존 |
| 생성물·스키마 | 예시 8개 검증, 패키지 스키마 비교, 분류기 보고서 및 샘플·SVG 재생성 비교 | 모두 일치 |
| 버전·문서 | 수집기·서버·패키지·README·화면·CHANGELOG | `1.0.0rc3` / `1.0.0-rc3` 일치, 로컬 커밋만 |

재현: [스크린샷 안내](screenshots/before_after/README.md), [기계 검사 결과](screenshots/before_after/after-checks.json)(Codex 단계 당시의 기록). 드라이버는 이후 Opus 단계에서 `check`/`keyviews:NAME` 모드로 바뀌었다. 두 코어를 공유하므로 Chromium 하나와 테스트 스위트 순차 실행으로 제한했다. 테스트 임시 파일과 브라우저 프로필은 프로젝트의 `server/var/ui/`에 두었다. 외부·유료 API, 자격증명, 실제 transcript, 실제 `~/.claude` 파일을 사용하지 않았다.

한계: 실제 스크린 리더·다른 브라우저·axe 검사는 수행하지 않았다. 이번 라운드는 아래 rc2 보안 점검을 새로 시행한 보안 감사가 아니며, 남은 운영 위험도 그대로다.

---

## rc2 점검 기록 (2026-09-28)

rc2는 새 기능 없이 서버와 수집기를 스스로 점검한 라운드입니다. 이 문서는 **무엇을 확인했고, 무엇을 고쳤고, 무엇이 남았는지** 적습니다. 외부 보안 감사가 아니며, 같은 작성자가 코드와 점검을 모두 했다는 한계가 있습니다.

규칙:

- 실제 버그는 **실패하는 테스트를 먼저 쓰고** 고쳤습니다. 회귀 테스트는 `collector/tests/test_hardening.py`와 `server/tests/test_hardening.py`에 있고, 주석에 `Bug (rc1):`로 표시했습니다.
- 무작위 테스트는 표준 라이브러리 `random`에 **고정 시드**(`20260928`)를 써서 실패를 재현할 수 있습니다.
- 실제 transcript, 실제 `~/.claude` 설정, 외부 API는 쓰지 않았습니다. 모든 입력은 합성입니다.

## 1. 확인한 것

| 영역 | 확인 방법 | 결과 |
|---|---|---|
| 제출 크기와 전송 형식 | 음수·부호·비숫자 `Content-Length`, `Transfer-Encoding`, 64 KiB 초과, 잘못된 `Content-Type`을 원시 소켓으로 보냄 | 음수 길이 우회 **버그 → 수정** |
| JSON 파싱 한도 | 깊은 중첩(3만 단계), 5만 자리 정수, `NaN`/`Infinity` | 연결 끊김 2건, 비유한 수 저장 1건 **버그 → 수정** |
| 스키마 입력 검증 | 필드 무작위 변형 60건을 HTTP로 왕복(타입 뒤섞기, 2⁶³, 1e308, 경로 문자열, SQL 모양 문자열, 빈 객체) | 큰 정수 저장 실패 **버그 → 수정**. 수정 후 항상 알려진 상태 코드 + 올바른 JSON, 201이면 반드시 스키마 통과 |
| 문자열 필드로 원문이 새는지 | 공백·줄바꿈·따옴표·한글을 섞은 무작위 텍스트 300개를 제약된 문자열 필드(모델 id, 하네스, L2, 분류기, 버전, effort)에 넣음 | 모두 거부. 단, 끝 줄바꿈 한 개는 통과하던 **버그 → 수정** |
| 프라이버시 보장 | 스키마의 모든 문자열 필드가 `enum`/`const`/`pattern`/`format`으로 묶였는지 기계적으로 확인. 로그 내용 확인 | 자유 텍스트 필드 없음. 로그에는 메서드·경로·상태만. 제어 문자 이스케이프 **추가** |
| 서명 검증 경계 | 서명·키·본문·경로·시각을 무작위로 1비트씩 변조(12건), 시각 ±300/±301초, 5000자리 시각, 실수 시각, 비ASCII 키, 긴 서명, 31바이트 키, 빈 헤더 | 모두 거부. 위수가 작은 공개 키(항등원 등)로 위조 서명이 통과하던 **버그 → 수정** |
| 레이트 리밋 우회 | 요청마다 새 키(키 돌려쓰기), 시계가 거꾸로 가는 경우, 무작위 도착 간격에서 허용 건수 상한 | 키 돌려쓰기 우회 **버그 → 수정**. 토큰 버킷은 `burst + 경과시간 × 속도`를 넘지 않음 |
| 시계 어긋남(clock skew) | 서명 시각 창 ±300초 경계, 토큰 버킷은 `monotonic`, 셀 일일 상한과 게이트는 서버 시각(`received_at`) | 클라이언트가 보낸 시각을 한도 계산에 쓰는 곳 없음 |
| SQL 주입 | `store.py`의 모든 쿼리 검토 | 값은 전부 `?` 매개변수. f-string으로 들어가는 것은 코드 상수(열·테이블 이름)뿐. SQL 모양 문자열은 데이터로만 저장·거부됨(테스트) |
| 정적 파일 경로 조작 | `..`, `%2e%2e`, `//`, `\`, `%00`, 원시 NUL 바이트를 섞은 무작위 경로 80건 | 저장소 밖 파일은 절대 안 나감. NUL 바이트에서 연결이 끊기던 **버그 → 수정** |
| 오류 응답의 내부 정보 | 저장소 계층에서 경로가 담긴 예외를 일부러 일으킴 | 처리되지 않은 예외가 연결을 끊던 **버그 → 수정**(고정된 500 본문). 검증 오류가 큰 입력을 되돌려 보내던 문제도 60자로 자름 |
| 서버 로그 | README 빠른 시작을 실제로 실행 | `curl \| head`가 연결을 끊으면 파일 경로가 담긴 traceback이 찍히던 **버그 → 수정** |
| 수집기 전송 경로 | 302를 돌려주는 로컬 서버 | 리다이렉트를 따라가 loopback 검사를 건너뛰고 서명 헤더를 넘기던 **버그 → 수정** |
| 정적 품질 | ruff/pyflakes가 없어 표준 라이브러리 `ast`로 안 쓰는 import·지역 변수·타입 힌트 누락을 찾음 | 안 쓰는 지역 변수 4개 제거, 타입 힌트 보강. 안 쓰는 import 없음 |
| 버전 문자열 | `1.0.0rc1`/`rc1` 전수 검색 | 모두 `1.0.0rc2`/`v1.0.0-rc2`로. 앞으로 어긋나면 `server/tests/test_release.py`가 실패 |
| 문서 | README 빠른 시작을 **새 임시 디렉터리 사본**에서 `bash -e`로 처음부터 끝까지 실행 | 끝까지 성공(exit 0). 테스트 160개, 서명 제출 201, 공개 개요·기여자 상세 200, 훅 dry-run, 검증·변환·분류기 평가 |
| CI 단계 | `.github/workflows/ci.yml`의 비테스트 단계(예시 검증, 스키마 사본 비교, 시드 전수 검증, 분류기 보고서·샘플·그림 최신 여부)를 로컬에서 실행 | 모두 통과 |
| 대시보드 | headless Chromium + CDP로 키보드 초점·툴팁·필터·테마·reduced motion 확인, WCAG 대비 계산 | 외부 리소스 없음(테스트), 글자 대비 AA |

## 2. 고친 것 (회귀 테스트)

| # | 버그 | 영향 | 수정 | 테스트 |
|---|---|---|---|---|
| 1 | 음수 `Content-Length`가 크기 검사를 통과해 `rfile.read(-1)`이 EOF까지 읽음 | 64 KiB 한도 우회, 메모리 사용 무제한 | ASCII 숫자 1–9자리만 허용, 아니면 411 + 연결 닫기 | `TransportLimitsTest.test_negative_content_length_is_refused_without_reading_the_body` |
| 2 | 깊은 중첩 JSON의 `RecursionError`가 처리기 밖으로 샘 | 응답 없이 연결 끊김, 서버 로그에 traceback | `parse_json_body`가 400으로 변환 | `test_deeply_nested_json_gets_400_not_a_dropped_connection` |
| 3 | 4300자리 초과 정수의 `ValueError`(JSONDecodeError 아님)가 샘 | 같음 | 같음 | `test_huge_integer_literal_gets_400` |
| 4 | `NaN`/`Infinity`가 파싱·검증을 통과해 저장됨 | 상세 집계가 JSON이 아닌 `Infinity`를 출력 → 대시보드·클라이언트 파싱 실패 | `parse_constant`로 거부, 검증기가 비유한 수 거부, 응답은 `allow_nan=False` | `test_nan_and_infinity_literals_are_not_json`, `test_non_finite_numbers_are_rejected` |
| 5 | 2⁵³−1을 넘는 정수가 검증 통과 | SQLite `OverflowError` → 연결 끊김 | 검증기가 I-JSON 범위 강제 | `test_integer_too_large_for_storage_gets_400`, `test_integers_outside_the_interoperable_range_are_rejected` |
| 6 | 정적 경로의 NUL 바이트 | `ValueError` → 연결 끊김 | NUL이면 404, `resolve()` 예외도 404 | `test_nul_byte_in_static_path_gets_404` |
| 7 | 처리되지 않은 예외 | 연결 끊김, 클라이언트는 원인을 모름 | 모든 GET/POST에 마지막 방어선: 고정 `500 {"error":"internal_error"}`, 로그에는 예외 종류만 | `InternalErrorTest` |
| 8 | 로그에 경로의 제어 문자가 그대로 찍힘 | 로그 위조·터미널 색 조작 | 출력 불가 문자를 `\xNN`으로 | `LogInjectionTest` |
| 9 | 요청마다 새 키를 만들면 기여자별 버킷을 매번 새로 받음 | 레이트 리밋이 사실상 없음 | DB에 레코드가 없는 기여자는 공용 newcomer 버킷(360/h, 버스트 60) | `NewContributorLimitTest` |
| 10 | 위수가 작은 Ed25519 공개 키 허용 | 항등원 키 + (R=항등원, s=0)은 모든 메시지에 "맞는" 서명 → 비밀 키 없는 "검증된" 기여자 | `8·A = 항등원`이면 거부 | `SignatureEdgeTest.test_small_order_public_key_cannot_verify` |
| 11 | `pattern`의 `$`가 끝 줄바꿈 앞에서도 맞음(Python `re` vs ECMA-262) | `"claude-code\n"` 같은 값이 저장·집계 키로 들어감 | 문자 클래스 밖의 `$`를 `\Z`로 바꿔 컴파일(캐시) | `test_pattern_dollar_does_not_accept_a_trailing_newline` |
| 12 | 검증 오류가 입력을 통째로 되돌려 보냄 | 60 KB 값이 오류 응답에 그대로 | `repr`을 60자에서 자름 | `test_error_messages_truncate_echoed_values`, `test_validation_errors_do_not_echo_large_input` |
| 13 | `submit`/`query`가 30x 리다이렉트를 따라감 | loopback 전용 검사가 첫 주소에만 적용, 서명 헤더가 다른 주소로 전달 | 리다이렉트를 따르지 않고 상태 코드를 그대로 보고 | `RedirectTest` |
| 14 | 클라이언트 연결 끊김마다 traceback 출력 | 로그 소음, 파일 경로 노출 | 서버 클래스의 `handle_error`가 연결 끊김은 무시, 그 밖은 한 줄 | `ClientDisconnectTest` |

추가한 성질(property) 테스트: 레코드 무작위 변형(`RandomizedServerTest.test_random_mutations`), 정적 경로(`test_random_static_paths_never_escape_the_dashboard`), 서명 변조(`test_random_tampering_is_always_rejected`), 시각 창 경계, 잘못된 헤더, 토큰 버킷 상한과 역행 시계(`TokenBucketPropertyTest`), 제약 필드의 자유 텍스트 거부.

테스트 수(2026-09-28, Python 3.12, 로컬): collector 69 → **79**, server 42 → **60**, seeds **21**, 합계 132 → **160**.

## 3. 남은 것

코드로 고칠 수 있지만 이번 라운드에서 하지 않은 것, 그리고 사람이 결정해야 하는 것입니다.

- **서명 검증 비용이 레이트 리밋보다 먼저 듭니다.** 서명 검증(순수 Python, 요청당 수십 ms)을 한 뒤에야 기여자를 알 수 있어, 잘못된 서명을 대량으로 보내면 CPU를 씁니다. 운영에서는 리버스 프록시의 IP 단위 제한이나 `cryptography`로 교체가 필요합니다(`docs/USER_TASKS.md` 3번).
- **느린 클라이언트(slowloris).** `ThreadingHTTPServer`는 연결마다 스레드를 만들고 소켓 타임아웃은 15초입니다. 동시 연결 수 상한이 없습니다. loopback 전용이라 지금은 리버스 프록시가 막아야 합니다.
- **서명된 GET의 재사용.** 기여자 상세 조회의 서명은 ±300초 안에서 같은 경로로 다시 쓸 수 있습니다(읽기 전용이라 영향은 조회 권한 재사용에 그침). nonce 저장은 하지 않았습니다.
- **newcomer 버킷의 부작용.** 잘못된 요청을 보내는 새 키도 공용 예산을 씁니다. 공격 중에는 진짜 신규 기여자가 잠시 429를 받을 수 있습니다. 운영 로그를 보고 기본값을 정해야 합니다.
- **키는 여전히 공짜입니다.** 키 돌려쓰기는 속도만 늦출 뿐 Sybil을 막지 못합니다(보고서 위험 #3). 사람 단위 증명은 범위 밖입니다.
- **집계는 요청마다 전체 행을 다시 계산합니다.** 시드 1.5만 행에서는 문제없지만 레코드가 늘면 캐시가 필요합니다.
- **검증기와 `jsonschema`의 차이.** rc2 검증기는 끝 줄바꿈과 2⁵³ 초과 정수를 거부해 `jsonschema`(Python `re` 사용)보다 엄격합니다. CI의 교차검증은 이런 입력을 쓰지 않아 영향이 없지만, 새 교차검증 사례를 넣을 때는 이 차이를 알아야 합니다. `with-dev-deps` CI 조합은 로컬에 `pip`가 없어 이번에도 돌리지 못했습니다.
- **Python 3.10.** 로컬은 3.12만 있습니다. 3.10 호환 문법만 썼지만 실제 실행은 CI(push 후)에서 처음 확인됩니다.
- **정적 분석 도구.** ruff·pyflakes·mypy가 설치돼 있지 않아 AST 기반 수동 점검만 했습니다. `requirements-dev.txt`에 넣고 CI에서 돌리는 것은 다음 작업입니다.
- **대시보드 자동 접근성 검사.** 대비는 계산했고 키보드 동작은 CDP로 확인했지만 axe 같은 자동 검사기는 돌리지 않았습니다. 실제 스크린 리더로 읽어 본 적도 없습니다.
- **순수 Python Ed25519는 상수 시간이 아니고 감사를 받지 않았습니다.** 운영 전 교체가 필요합니다(기존 항목).
