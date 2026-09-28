"""Local, rule-based quality signals. Text is inspected in memory only; the
record receives a boolean / a score and the rule-set id, never the text.

* ``retry-rules-v1`` -- was the NEXT user prompt a retry or a complaint about the
  previous turn? (behavioural evidence, used by rankings as a negative signal)
* ``claim-rules-v1`` -- does the agent's own final message CLAIM success?
  This is a self-assessment. It is stored in ``outcome.self_assessment`` with
  ``rater = "self_claim"`` and is excluded from rankings by default; its value is
  the research comparison "what the agent said" vs "what the evidence shows".
"""

from __future__ import annotations

import re

_FLAGS = re.IGNORECASE | re.ASCII

# ---- retry-rules-v1 -------------------------------------------------------
_RETRY_EN = re.compile(
    r"\b(still (fail\w*|broken|not|wrong|the same|doesn'?t|getting|seeing)|same (error|problem|issue|bug)|"
    r"(doesn'?t|does not|didn'?t|did not) work|not working|isn'?t (fixed|working)|not fixed|"
    r"try again|that'?s (wrong|not (it|right|what))|not what i (asked|wanted|meant)|wrong again|"
    r"you broke|broke (it|the|something)|revert (that|this|it|your)|undo (that|this|it|your)|roll ?back)\b",
    _FLAGS,
)
_RETRY_KO = (
    "아직도", "여전히", "그대로야", "그대로네", "또 에러", "또 안", "또 실패", "안 되잖", "안되잖", "안 돼", "안돼",
    "안 되는데", "안되는데", "틀렸", "잘못했", "잘못 고쳤", "되돌려", "원래대로", "롤백", "그게 아니라", "그게 아니고",
    "다시 해", "다시 고쳐", "다시 확인", "고쳐지지", "안 고쳐", "안고쳐", "망가졌", "깨졌",
)
_WORD = re.compile(r"[0-9A-Za-z가-힣_]+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _WORD.findall(text or "") if len(t) > 1}


def near_duplicate(a: str, b: str, threshold: float = 0.6) -> bool:
    """True if two prompts share most of their words (re-asking the same thing)."""
    ta, tb = _tokens(a), _tokens(b)
    if len(ta) < 3 or len(tb) < 3:
        return False
    return len(ta & tb) / len(ta | tb) >= threshold


def detect_retry(next_prompt: str, previous_prompt: str | None = None) -> bool:
    """retry-rules-v1: complaint/retry wording, or a near-duplicate of the previous prompt."""
    text = next_prompt or ""
    if _RETRY_EN.search(text) or any(k in text for k in _RETRY_KO):
        return True
    return bool(previous_prompt) and near_duplicate(text, previous_prompt)


# ---- claim-rules-v1 -------------------------------------------------------
_CLAIM_OK_EN = re.compile(
    r"\b(all (\d+ )?tests? (now )?pass(ed|es|ing)?|tests? (now )?pass(ed|es|ing)?|(is|are) (now )?(fixed|working|passing)|"
    r"works now|now works|successfully|i('?ve| have) (fixed|implemented|added|resolved|completed)|"
    r"task (is )?complete)\b|\b(fixed|implemented|resolved|completed|done)[.!]"
    r"|(^|[.!?]\s+)(fixed|implemented|resolved|done)\b",
    _FLAGS,
)
_CLAIM_OK_KO = ("완료했", "완료되었", "완료됐", "해결했", "해결되었", "수정했습니다", "수정 완료", "통과합니다", "통과했",
                "모두 통과", "구현했습니다", "구현 완료", "고쳤습니다", "성공적으로", "잘 동작", "정상 동작", "정상적으로 동작")
_CLAIM_FAIL_EN = re.compile(
    r"\b(couldn'?t|could not|unable to|was not able to|wasn'?t able to|failed to|still fail(s|ing)?|"
    r"(did not|didn'?t) (work|pass|fix)|remains? (broken|failing)|not (yet )?(fixed|resolved)|blocked by|i gave up)\b",
    _FLAGS,
)
_CLAIM_FAIL_KO = ("못했", "실패했", "해결하지 못", "여전히 실패", "아직 실패", "통과하지 못", "막혔", "해결되지 않", "동작하지 않")
_HEDGE = re.compile(r"\b(should (now )?work|might|may need|probably|i think|not sure|untested|haven'?t (run|tested))\b", _FLAGS)
_HEDGE_KO = ("것 같", "아마", "확인하지 못", "테스트하지 않", "테스트는 안")


def extract_claim(final_text: str) -> float | None:
    """claim-rules-v1: 1.0 = claims success, 0.75 = hedged success, 0.5 = mixed,
    0.0 = admits failure, None = no claim either way."""
    text = final_text or ""
    ok = bool(_CLAIM_OK_EN.search(text)) or any(k in text for k in _CLAIM_OK_KO)
    fail = bool(_CLAIM_FAIL_EN.search(text)) or any(k in text for k in _CLAIM_FAIL_KO)
    if ok and fail:
        return 0.5
    if fail:
        return 0.0
    if ok:
        hedged = bool(_HEDGE.search(text)) or any(k in text for k in _HEDGE_KO)
        return 0.75 if hedged else 1.0
    return None
