# 이름 후보 (Naming)

상태: **잠정(provisional)**. 2026-09-27 기준 `ModelReceipts`를 임시 이름으로 사용한다.
상표·GitHub 조직명·PyPI/npm 패키지명 충돌 조사는 아직 하지 않았다. 공개 전에 확인이 필요하다.

## 선택: ModelReceipts (`modelreceipts`)

- 한 줄 설명: *"AI가 '다 됐어요'라고 말하면, 영수증을 보여 주세요."*
- "영수증(receipts)"은 두 가지를 동시에 가리킨다.
  1. **증거** — 영어 관용구 "show me the receipts"(말 말고 증거를 대라). 테스트 통과, 커밋, 되돌리기 같은 결과 증거.
  2. **비용** — 토큰과 달러. 이 DB가 "결과 × 방법 × 비용"을 한 레코드로 묶는다는 점과 맞는다.
- 사용처: README 제목, Python 패키지 `modelreceipts`, 저장소 이름 `modelreceipts`(제안).

## 대안

| 이름 | 장점 | 단점 |
|---|---|---|
| **ProofCell** | "태스크 셀마다 증거"라는 조회 단위를 그대로 드러냄 | 뜻이 바로 오지 않음, 생물학 용어처럼 들림 |
| **TaskProof** | 직관적, 짧음 | 일반 명사 조합이라 검색·상표 차별성 약함 |
| **OutcomeLedger** | append-only 기록과 결과 중심이라는 설계를 표현 | 길고, "ledger"가 블록체인 연상 |
| **Evidex** | 짧고 브랜드성 있음 (evidence + index) | 기존 제품명과 겹칠 가능성 높음, 뜻 설명 필요 |

## 결정 필요

- 공개 저장소 이름 (예: `thinker0v0/modelreceipts`) 및 공개/비공개 여부.
- 이름 충돌 조사 후 확정 또는 대안으로 교체. 교체 시 README 제목, `collector/pyproject.toml`, `collector/modelreceipts/` 패키지명, 대시보드 제목을 함께 바꾼다.
