# 분류기 평가 세트 (SYNTHETIC)

`classifier_eval.synthetic.jsonl`은 **전부 합성 예문**이다. 실제 사용자 프롬프트·transcript에서 가져온 문장은 하나도 없다.
프로젝트 작성자(에이전트)가 손으로 쓰고 손으로 라벨을 붙였다.

한 줄 = 한 예시:

```json
{"id": "t031", "split": "test", "prompt": "…", "files_touched": 2, "tools": ["Edit", "Bash"], "test_calls": 1, "l1": "coding", "l2": "coding.bugfix"}
```

| 필드 | 뜻 |
|---|---|
| `split` | `dev`(규칙 조정용) / `test`(보고용, 규칙 조정에 쓰지 않음) |
| `prompt` | 합성 사용자 프롬프트 (한국어·영어 혼합) |
| `files_touched`, `tools`, `test_calls` | 그 턴에서 일어난 것으로 가정한 도구 활동 — 분류기는 편집 여부와 도구 이름도 본다 |
| `l1`, `l2` | 정답 라벨 (taxonomy t0.1). 코딩이 아니면 `l2`는 `null` |

## 절차와 한계 (정직하게)

1. `test` 분할은 `rules-v1` 작업을 시작하기 **전에** 커밋해 고정했다(git 이력에서 확인 가능). `rules-v1`은 `dev`만 보고 조정했다.
2. 그래도 같은 작성자가 예문과 규칙을 모두 썼고, 예문을 쓸 때 `rules-v0`의 규칙을 이미 알고 있었다. 이 점수는 **실제 사용자 프롬프트에서의 정확도 추정치가 아니다.** 규칙 변경의 회귀를 잡는 용도로 쓴다.
3. 표본이 작다(클래스당 수 건). 클래스별 수치의 불확실성이 크다.

실행:

```bash
PYTHONPATH=collector python3 -m modelreceipts eval-classifier                 # 두 분류기, 두 분할 요약
PYTHONPATH=collector python3 -m modelreceipts eval-classifier --markdown > collector/eval/RESULTS.md
```
