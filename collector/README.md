# modelreceipts collector (dry run)

Claude Code `Stop` 훅 payload를 받아 레코드 하나를 만들고 **로컬에서 미리보기만** 한다.
v0.1에는 전송 코드가 없다. `socket`/`urllib`/`http`/`subprocess` 등을 import하지 않는다는 것을 테스트가 확인한다.

- Python 3.10+, 표준 라이브러리만 사용 (테스트의 `jsonschema` 교차 검증은 설치돼 있을 때만 실행)
- 소스 체크아웃에서 실행한다. 스키마 파일을 `../schema/`에서 읽으므로 pip 배포는 아직 지원하지 않는다.

## 동작

```
stdin(Stop payload JSON) ──► transcript_path의 JSONL 파싱 (마지막 턴만)
                               ├─ model id, 토큰(스트리밍 중복 제거), API 호출 수, 지연
                               ├─ 도구 이름, 편집 파일 "개수", 테스트 명령 감지와 결과, git commit 성공 여부
                               └─ 마지막 사용자 프롬프트 → 로컬 규칙 분류기 → (L1, L2) 폐쇄 코드
                           ──► schema v0.1 레코드 조립 (화이트리스트 필드만) ──► 스키마 검증 ──► 미리보기 출력
```

레코드에 들어가지 **않는** 것: 프롬프트·응답·thinking 텍스트, 도구 인자와 결과, 파일 경로, cwd, 저장소·브랜치 이름, session id, 이메일.
MCP 도구 이름(`mcp__서버__도구`)은 사설 서버 이름이 드러날 수 있어 `mcp`로 뭉갠다.

## 실행해 보기

```bash
# 저장소 루트에서
python3 -m unittest discover -s collector/tests -v

# 합성 fixture로 미리보기
sed "s|REPLACED_AT_TEST_TIME|$PWD/collector/tests/fixtures/synthetic_transcript.jsonl|" \
  collector/tests/fixtures/stop_payload.json | PYTHONPATH=collector python3 -m modelreceipts hook

# 레코드 파일 검증
PYTHONPATH=collector python3 -m modelreceipts validate schema/examples/*.json
```

## 훅 설치 방법 (문서만 — 이 저장소는 사용자 설정을 건드리지 않는다)

직접 설치하려면 **사용자 설정** `~/.claude/settings.json`의 `hooks`에 아래 항목을 손으로 추가한다.
`/ABS/PATH`는 이 저장소를 체크아웃한 절대 경로로 바꾼다.

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "PYTHONPATH=/ABS/PATH/collector python3 -m modelreceipts hook --hook --preview-dir ~/.local/state/modelreceipts/preview",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

- `--hook`: 항상 exit 0, stdout은 비워 둔다. Claude Code는 Stop 훅의 stdout JSON을 훅 제어(`decision` 등)로 해석할 수 있으므로 미리보기는 파일 또는 stderr로만 낸다.
- `--preview-dir`: 턴마다 `<record_id>.json`을 로컬에 쓴다. 이 폴더 밖으로 나가는 것은 없다.
- 제거: 추가한 항목을 지우면 끝이다. 미리보기 폴더는 직접 삭제한다.
- 레포 로컬 `.claude/settings.json`보다 사용자 설정을 권장한다(연구 노트: OTel 보강 변수는 사용자 설정에서만 적용).

## 알려진 한계 (v0.1)

- 레코드 범위는 "마지막 사용자 프롬프트 이후의 한 턴"이다. 서브에이전트 transcript(`isSidechain`)는 제외한다.
- `tests_passed`는 턴 안에서 **마지막으로 감지된** 테스트 명령의 `is_error`로 판단한다. 테스트 명령 감지는 정규식 기반이다.
- `user_retry_next_prompt`, `reverted_within_7d`는 Stop 시점에 알 수 없어 `null`이다(후속 단계에서 채움).
- 비용은 transcript에 없으므로 `null`. 서버 가격표 재계산과 OTel 보강은 다음 단계.
- `route`는 환경변수 이름(`CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `ANTHROPIC_BASE_URL`)으로만 추정한다.
- transcript 형식은 공개 안정 API가 아니다. 파서는 모르는 줄을 건너뛰도록 방어적으로 작성했다.
