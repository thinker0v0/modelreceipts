"""Local rule-based task classifier (``rules-v0``, taxonomy ``t0.1``).

Maps a prompt + tool activity to CLOSED codes (L1, L2). The prompt text is
only inspected locally; the output contains nothing but the codes.

Deliberately simple and transparent: keyword rules in Korean and English,
evaluated in a fixed priority order. Expect misclassifications; the
classifier id is recorded so later versions can re-weight old records.
"""

from __future__ import annotations

import re

from .transcript import TurnSummary

# (L2 code, English word-boundary regex, Korean substrings). First match wins.
_L2_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    ("coding.test", r"\b(write|add|create|generate|missing)\s+(unit\s+|integration\s+|e2e\s+)?tests?\b|\btest coverage\b",
     ("테스트 작성", "테스트 추가", "테스트를 작성", "테스트를 추가", "테스트 코드", "커버리지")),
    ("coding.bugfix", r"\b(fix|bug|broken|crash(es|ing)?|fail(s|ing|ed)?|error|exception|traceback|regression)\b",
     ("버그", "오류", "에러", "고쳐", "안 돼", "안돼", "깨졌", "실패", "예외")),
    ("coding.performance", r"\b(performance|optimi[sz]e|slow|speed\s*up|latency|memory leak)\b",
     ("성능", "최적화", "느려", "느림", "메모리 누수")),
    ("coding.refactor", r"\b(refactor(ing)?|clean\s*up|restructure|rename|simplify|dedupe)\b",
     ("리팩터", "리팩토링", "구조 개선", "정리해", "중복 제거")),
    ("coding.migration", r"\b(migrat(e|ion)|upgrade|bump\s+(the\s+)?version|port\s+(it\s+)?to)\b",
     ("마이그레이션", "업그레이드", "이전해", "버전 올려")),
    ("coding.config_devops", r"\b(docker(file)?|ci|cd|github actions|workflow|deploy(ment)?|pipeline|kubernetes|k8s|nginx|terraform|config(uration)?)\b",
     ("배포", "도커", "설정", "환경 구성", "파이프라인")),
    ("coding.docs", r"\b(readme|docs?|documentation|docstrings?|changelog|comments?)\b",
     ("문서", "주석", "리드미", "설명서")),
    ("coding.ui", r"\b(ui|ux|css|layout|component|button|screen|responsive|dark mode|styling)\b",
     ("화면", "디자인", "레이아웃", "버튼", "컴포넌트", "다크 모드")),
    ("coding.feature", r"\b(add|implement|create|build|support|introduce|new feature|endpoint)\b",
     ("추가", "구현", "만들어", "기능", "지원해")),
]

# Only used when the turn edited no files (read-only activity).
_READONLY_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    ("coding.review", r"\b(review|audit|critique|look over)\b", ("리뷰", "검토", "코드 봐")),
    ("coding.explain", r"\b(explain|what does|how does|why does|walk me through|understand)\b",
     ("설명", "뭐야", "무엇", "어떻게 동작", "이해")),
]

_CODING_HINT = re.compile(
    r"\b(code|function|class|module|repo|script|compile|build|test|api|bug|python|kotlin|java|typescript|javascript|rust|golang|sql)\b",
    re.IGNORECASE,
)
_CODING_HINT_KO = ("코드", "함수", "클래스", "모듈", "저장소", "레포", "빌드", "컴파일", "스크립트", "테스트")
_CODING_TOOLS = {"Bash", "Edit", "Write", "MultiEdit", "NotebookEdit", "Grep", "Glob", "Read"}

# Non-coding L1 fallbacks (L2 is null for these in taxonomy t0.1).
_L1_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    ("data", r"\b(csv|dataframe|spreadsheet|pandas|dataset|etl)\b", ("데이터 정리", "엑셀", "스프레드시트")),
    ("analysis_math", r"\b(analy[sz]e|statistics?|regression|proof|calculate|math)\b", ("분석", "통계", "계산", "수학")),
    ("writing", r"\b(write|draft|rewrite|translate|summari[sz]e|email|essay|blog)\b", ("작성해", "번역", "요약", "이메일", "글")),
    ("research_qa", r"\b(research|compare|find out|look up|what is)\b", ("조사", "비교", "찾아", "알려")),
]


def _match(text: str, regex: str, korean: tuple[str, ...]) -> bool:
    return bool(re.search(regex, text, re.IGNORECASE)) or any(k in text for k in korean)


def _classify_v0(summary: TurnSummary) -> tuple[str, str | None]:
    text = summary.prompt_text or ""
    tools = set(summary.tools_used)
    edited = summary.files_touched > 0
    coding = edited or bool(summary.test_calls) or bool(tools & _CODING_TOOLS) or bool(_CODING_HINT.search(text))
    coding = coding or any(k in text for k in _CODING_HINT_KO)

    if not coding:
        for l1, rx, ko in _L1_RULES:
            if _match(text, rx, ko):
                return l1, None
        return "other", None

    if not edited:
        for code, rx, ko in _READONLY_RULES:
            if _match(text, rx, ko):
                return "coding", code
    for code, rx, ko in _L2_RULES:
        if _match(text, rx, ko):
            return "coding", code
    return "coding", "coding.other"


# Registered classifiers. Old versions stay available so archived records can be
# re-evaluated against the exact rules that produced them.
CLASSIFIERS = {"rules-v0": _classify_v0}


def classify(summary: TurnSummary, classifier: str | None = None) -> tuple[str, str | None]:
    """Return (l1, l2) closed codes for the last turn using ``classifier`` (default: current)."""
    from . import CLASSIFIER_ID

    return CLASSIFIERS[classifier or CLASSIFIER_ID](summary)
