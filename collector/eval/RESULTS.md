# 분류기 평가 결과 (합성 평가 세트)

`PYTHONPATH=collector python3 -m modelreceipts eval-classifier --markdown`로 생성. 손으로 고치지 않는다.

> 평가 세트는 **전부 합성 예문**이고 같은 작성자가 규칙도 썼다. 실제 프롬프트에서의 정확도 추정치가 아니다. `test` 분할은 `rules-v1` 작업 전에 고정했고 규칙 조정에는 `dev`만 썼다. 자세한 한계: [README.md](README.md).

## 요약

| 분류기 | 분할 | n | 정확도(L2/L1 코드) | L1 정확도 | macro 정밀도 | macro 재현율 |
|---|---|---:|---:|---:|---:|---:|
| `rules-v0` | dev | 120 | 0.558 | 0.817 | 0.628 | 0.543 |
| `rules-v0` | test | 120 | 0.508 | 0.800 | 0.624 | 0.486 |
| `rules-v1` | dev | 120 | 1.000 | 1.000 | 1.000 | 1.000 |
| `rules-v1` | test | 120 | 0.675 | 0.883 | 0.838 | 0.679 |

## 클래스별 정밀도 / 재현율 — `dev` 분할

| 클래스 | 지지도 | `rules-v0` P | `rules-v0` R | `rules-v1` P | `rules-v1` R |
|---|---:|---:|---:|---:|---:|
| `agentic_ops` | 4 | — | 0.00 | 1.00 | 1.00 |
| `analysis_math` | 4 | 1.00 | 0.50 | 1.00 | 1.00 |
| `coding.bugfix` | 7 | 0.60 | 0.86 | 1.00 | 1.00 |
| `coding.config_devops` | 7 | 0.83 | 0.71 | 1.00 | 1.00 |
| `coding.docs` | 7 | 1.00 | 0.57 | 1.00 | 1.00 |
| `coding.explain` | 7 | 1.00 | 0.43 | 1.00 | 1.00 |
| `coding.feature` | 7 | 0.43 | 0.86 | 1.00 | 1.00 |
| `coding.migration` | 7 | 1.00 | 0.43 | 1.00 | 1.00 |
| `coding.other` | 7 | 0.23 | 0.71 | 1.00 | 1.00 |
| `coding.performance` | 7 | 1.00 | 0.43 | 1.00 | 1.00 |
| `coding.refactor` | 7 | 0.57 | 0.57 | 1.00 | 1.00 |
| `coding.review` | 7 | 1.00 | 0.71 | 1.00 | 1.00 |
| `coding.test` | 7 | 1.00 | 0.43 | 1.00 | 1.00 |
| `coding.ui` | 7 | 1.00 | 0.43 | 1.00 | 1.00 |
| `conversation` | 4 | — | 0.00 | 1.00 | 1.00 |
| `creative` | 4 | — | 0.00 | 1.00 | 1.00 |
| `data` | 4 | 1.00 | 0.75 | 1.00 | 1.00 |
| `education` | 4 | — | 0.00 | 1.00 | 1.00 |
| `other` | 4 | 0.20 | 1.00 | 1.00 | 1.00 |
| `research_qa` | 4 | 0.67 | 1.00 | 1.00 | 1.00 |
| `writing` | 4 | 0.67 | 1.00 | 1.00 | 1.00 |

`rules-v0` / dev 주요 혼동 (정답 → 예측, 건수): `coding.performance`→`coding.other` 4, `conversation`→`other` 4, `education`→`other` 4, `coding.migration`→`coding.other` 3, `creative`→`other` 3, `coding.refactor`→`coding.other` 2, `coding.test`→`coding.feature` 2, `coding.docs`→`coding.other` 2

## 클래스별 정밀도 / 재현율 — `test` 분할

| 클래스 | 지지도 | `rules-v0` P | `rules-v0` R | `rules-v1` P | `rules-v1` R |
|---|---:|---:|---:|---:|---:|
| `agentic_ops` | 4 | — | 0.00 | 0.67 | 1.00 |
| `analysis_math` | 4 | 1.00 | 0.25 | 1.00 | 0.50 |
| `coding.bugfix` | 7 | 0.71 | 0.71 | 1.00 | 0.57 |
| `coding.config_devops` | 7 | 0.67 | 0.57 | 0.71 | 0.71 |
| `coding.docs` | 7 | 1.00 | 0.43 | 1.00 | 0.71 |
| `coding.explain` | 7 | 1.00 | 0.43 | 1.00 | 0.71 |
| `coding.feature` | 7 | 0.50 | 0.43 | 0.80 | 0.57 |
| `coding.migration` | 7 | 0.75 | 0.43 | 0.88 | 1.00 |
| `coding.other` | 7 | 0.21 | 1.00 | 0.20 | 0.71 |
| `coding.performance` | 7 | 1.00 | 0.43 | 0.75 | 0.43 |
| `coding.refactor` | 7 | 0.80 | 0.57 | 1.00 | 0.57 |
| `coding.review` | 7 | 1.00 | 0.57 | 1.00 | 0.71 |
| `coding.test` | 7 | 1.00 | 0.71 | 1.00 | 0.71 |
| `coding.ui` | 7 | 0.75 | 0.43 | 0.80 | 0.57 |
| `conversation` | 4 | — | 0.00 | 1.00 | 0.25 |
| `creative` | 4 | — | 0.00 | 0.50 | 0.25 |
| `data` | 4 | 1.00 | 0.50 | 1.00 | 0.75 |
| `education` | 4 | — | 0.00 | 1.00 | 0.75 |
| `other` | 4 | 0.16 | 1.00 | 0.29 | 1.00 |
| `research_qa` | 4 | 0.80 | 1.00 | 1.00 | 1.00 |
| `writing` | 4 | 0.75 | 0.75 | 1.00 | 0.75 |

`rules-v0` / test 주요 혼동 (정답 → 예측, 건수): `conversation`→`other` 4, `coding.feature`→`coding.other` 3, `coding.refactor`→`coding.other` 3, `coding.review`→`coding.other` 3, `coding.migration`→`coding.other` 3, `coding.performance`→`coding.other` 3, `coding.ui`→`coding.other` 3, `analysis_math`→`other` 3

`rules-v1` / test 주요 혼동 (정답 → 예측, 건수): `coding.feature`→`coding.other` 3, `coding.refactor`→`coding.other` 3, `coding.performance`→`coding.other` 3, `creative`→`other` 3, `conversation`→`other` 3, `coding.bugfix`→`coding.other` 2, `coding.test`→`coding.other` 2, `coding.review`→`coding.other` 2

지지도 = 그 분할에서 정답이 해당 클래스인 예시 수. 예측이 한 번도 없으면 정밀도는 `—`.

