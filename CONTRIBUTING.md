# Contributing

ModelReceipts는 v1.0.0-rc3(코드 완성 후보)이다. 아직 실제 데이터가 없어서 스키마(0.x)와 분류 체계가 바뀔 수 있다.

## 지금 도움이 되는 것

- **dogfooding:** 자기 컴퓨터에서 훅을 설치해 미리보기 레코드를 확인하고, 이상한 값이나 빠진 신호를 알려 주기. 실제 내용은 올리지 않는다.
- 스키마 v0.2 필드에 대한 의견. 특히 `outcome.evidence`에 넣을 만한 검증 가능한 신호
- `rules-v1` 분류기, `retry-rules-v1`·`claim-rules-v1` 규칙의 오분류 사례. 프롬프트 원문 대신 **합성 예문**으로 제보한다(`collector/eval/`의 평가 세트에 `dev` 예시로 추가할 수 있다. `test` 분할은 고정이다).
- Claude Code transcript 형식 변화로 파서가 깨지는 경우 (구조만 설명하고 실제 내용은 올리지 않기)

## 규칙

- **실제 transcript, 프롬프트, 코드, 경로, 자격증명을 이슈·PR·fixture에 넣지 않는다.** 테스트 fixture는 합성 데이터로 만든다.
- 수집기의 네트워크 코드는 `collector/modelreceipts/submit.py`에만 둔다. 기본 `hook` 경로에서 전송하게 만드는 변경은 받지 않는다(테스트가 막는다).
- 런타임 Python 코드는 표준 라이브러리만 쓴다. `requirements-dev.txt`는 테스트 교차 검증 전용이다. 의존성이 꼭 필요하면 이슈에서 먼저 논의한다.
- 새 시드 소스는 라이선스·고정 커밋(또는 스냅샷 날짜)·sha256을 `SOURCE.json`에 기록한다. Artificial Analysis와 LMSYS-Chat-1M은 받지 않는다.
- PR 전에 실행:

  ```bash
  python3 -m unittest discover -s collector/tests -v
  python3 -m unittest discover -s server/tests -v
  python3 -m unittest discover -s seeds/tests -v
  PYTHONPATH=collector python3 -m modelreceipts validate schema/examples/*.json schema/examples/v0.1/*.json
  PYTHONPATH=collector python3 -m modelreceipts validate --allow-seed-cells schema/examples/seed-cells/*.json
  # 분류기 규칙을 바꿨다면 평가 보고서를 재생성한다 (CI가 차이를 검사)
  PYTHONPATH=collector python3 -m modelreceipts eval-classifier --markdown > collector/eval/RESULTS.md
  # 서버 집계 로직이나 시드를 바꿨다면 샘플과 데모 그림을 재생성해 커밋한다 (CI가 차이를 검사)
  PYTHONPATH=server python3 -m modelreceipts_server make-sample
  ```

- 스키마를 바꾸면 `schema_version`, 예시, 검증기 테스트, `collector/modelreceipts/schemas/`의 사본을 함께 갱신한다. 필요하면 `migrate.py`도 고친다.
- 개발과 테스트에서 실제 `~/.claude/settings.json`이나 `~/.claude/projects/`를 읽거나 쓰지 않는다. 훅 설치 테스트는 임시 디렉터리를 쓴다.
- 설치 키(`install_key*`)와 가격표 외의 비밀 값은 커밋하지 않는다. 가격표를 고칠 때는 `source.url`, `as_of`, `verified_live`를 함께 갱신한다.

## 라이선스

기여한 코드는 저장소 라이선스(Apache-2.0, 잠정)를 따른다.
