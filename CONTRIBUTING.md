# Contributing

ModelReceipts는 pre-alpha 단계다. 스키마와 분류 체계가 자주 바뀔 수 있다.

## 지금 도움이 되는 것

- 스키마 v0.1 필드에 대한 의견 (특히 `outcome.evidence`에 넣을 만한 검증 가능한 신호)
- 코딩 L2 분류 코드와 `rules-v0` 규칙의 오분류 사례 (프롬프트 원문 대신 **합성 예문**으로 제보)
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
  PYTHONPATH=collector python3 -m modelreceipts validate schema/examples/*.json
  # 서버 집계 로직이나 시드를 바꿨다면 샘플을 재생성해 커밋한다 (CI가 차이를 검사)
  PYTHONPATH=server python3 -m modelreceipts_server make-sample
  ```

- 스키마를 바꾸면 `schema_version`과 예시, 검증기 테스트를 함께 갱신한다.

## 라이선스

기여한 코드는 저장소 라이선스(Apache-2.0, 잠정)를 따른다.
