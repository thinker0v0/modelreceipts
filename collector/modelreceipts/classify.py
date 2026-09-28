"""Local rule-based task classifiers (taxonomy ``t0.1``).

Maps a prompt + tool activity to CLOSED codes (L1, L2). The prompt text is
only inspected locally; the output contains nothing but the codes.

* ``rules-v0``: first-match keyword rules in a fixed priority order (frozen).
* ``rules-v1`` (default): weighted keyword scores per class, ties broken by a
  fixed priority; a narrower "is this coding?" gate (Bash alone is not coding),
  and rules for the non-coding L1 codes v0 could not emit (conversation,
  creative, education, agentic_ops). Tuned on the ``dev`` split of the
  SYNTHETIC eval set only; see ``collector/eval/RESULTS.md``.

Deliberately simple and transparent. Expect misclassifications; the
classifier id is recorded in every record so later versions can re-weight
old records.
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


# ---------------------------------------------------------------------------
# rules-v1
# ---------------------------------------------------------------------------
# Each class: list of (regex, weight). Regexes are case-insensitive and may be
# Korean. Score = sum of weights of matching patterns. Highest score wins;
# ties go to the class listed first in the priority tuple.

_V1_L2: dict[str, list[tuple[str, int]]] = {
    "coding.test": [
        (r"\b(unit|integration|e2e|end-to-end|regression|snapshot)\s+tests?\b", 3),
        (r"\b(write|add|create|generate|missing|more)\s+(\w+\s+){0,2}tests?\b", 2),
        (r"\btest\s+coverage\b|\bcoverage\b", 2),
        (r"테스트\s*(코드|케이스)?\s*(를|을)?\s*(작성|추가|만들|늘려)|커버리지|e2e\s*테스트|단위\s*테스트|fixture|parametrize", 3),
    ],
    "coding.migration": [
        (r"\bmigrat(e|ion|ing)\b|마이그레이션", 3),
        (r"\b(upgrade|bump)\b|업그레이드|버전\s*(을\s*)?올려", 2),
        (r"\bport\b.*\bto\b|\bfrom\s+\S+\s+(\d[\d.]*\s+)?to\s+\S+", 1),
        (r"breaking changes?|교체|(으로|로)\s*옮겨", 2),
    ],
    "coding.performance": [
        (r"\b(performance|optimi[sz]e|slow|speed\s*up|latency|throughput|bundle\s+size|memory usage)\b", 3),
        (r"\bn\+1\b|N\+1", 3),
        (r"성능|최적화|느려|느림|속도|메모리\s*(사용량|누수)|빠르게", 3),
    ],
    "coding.docs": [
        (r"\b(readme|docs?|documentation|docstrings?|changelog|contributing(\.md)?)\b", 3),
        (r"^\s*document\b|\bcomments?\b", 2),
        (r"문서|주석|리드미|설명서|가이드", 3),
    ],
    "coding.config_devops": [
        (r"\b(docker(file)?|github actions|ci|cd|workflow|deploy(ment)?|pipeline|kubernetes|k8s|nginx|terraform|makefile|pre-commit|lint(ing|er)?)\b", 3),
        (r"\b(config(uration)?|set\s*up|environment variables?|env vars?)\b", 1),
        (r"배포|도커|파이프라인|워크플로|매니페스트|환경\s*변수|환경\s*구성|설정\s*(파일|좀|을)", 3),
    ],
    "coding.ui": [
        (r"\b(ui|ux|css|layout|components?|buttons?|screen|responsive|dark mode|styling|style|modal|animation|font|line height|colou?r|placeholder)\b", 2),
        (r"화면|디자인|레이아웃|버튼|컴포넌트|다크\s*모드|스타일|색상|폰트|입력칸|애니메이션", 2),
    ],
    "coding.refactor": [
        (r"\b(refactor(ing)?|clean\s*up|restructure|rename|simplify|dedupe|extract|dead code|readab(le|ility))\b", 2),
        (r"리팩터|리팩토링|구조\s*개선|정리해|중복\s*(코드|제거)|쪼개|변수명|알아보기\s*쉽게|읽기\s*쉽게", 2),
    ],
    "coding.bugfix": [
        (r"\b(fix(es|ed)?|bugs?|broken|fail(s|ing|ed)?|error|exception|traceback|regression)\b", 2),
        (r"\b(crash(es|ing)?|off-by-one|null pointer|does nothing|not working|doesn't work)\b", 2),
        (r"버그|오류|에러|고쳐|안\s*돼|깨졌|실패|예외|수정해|밀려", 2),
    ],
    "coding.feature": [
        (r"\b(add|implement|create|build|support|introduce|new feature|endpoint|flag|option)\b", 1),
        (r"추가|구현|만들어|기능|지원해|할\s*수\s*있게|되게\s*해", 1),
    ],
    "coding.other": [
        (r"\b(merge conflicts?|rebase|commit|cherry-pick|sample data|mock data|dummy data)\b", 3),
        (r"충돌|커밋|샘플\s*데이터|더미\s*데이터", 3),
    ],
}
_V1_L2_PRIORITY = ("coding.test", "coding.migration", "coding.performance", "coding.docs",
                   "coding.config_devops", "coding.ui", "coding.other", "coding.refactor",
                   "coding.bugfix", "coding.feature")

# Read-only turns (no file edits) check these first.
_V1_READONLY: dict[str, list[tuple[str, int]]] = {
    "coding.review": [
        (r"\b(review|audit|critique|look over|any bugs|security issues?)\b", 3),
        (r"리뷰|검토|문제\s*(없는지|있는지)|놓친|봐\s*줄래|봐\s*줘", 3),
    ],
    "coding.explain": [
        (r"\b(explain|what does|how does|why does|walk me through|understand|what is the difference)\b", 3),
        (r"설명|무슨\s*뜻|뭐야|어떻게\s*동작|이해|왜\s|파악|요약|구조", 3),
    ],
}

_V1_CODING_HINT = re.compile(
    r"\b(code|codebase|function|class|module|repo(sitory)?|script|compile|build|tests?|api|bugs?|python|kotlin|java|"
    r"typescript|javascript|rust|golang|sql|regex|git|commit|merge|rebase|branch|diff|pr|pull request|"
    r"stack trace|css|html|react|npm|pip|cli|endpoint)\b"
    r"|\b\w+\.(py|js|ts|tsx|jsx|kt|java|go|rs|rb|php|cs|cpp|md|sh|sql)\b",  # file names
    re.IGNORECASE | re.ASCII,  # ASCII: "README에" still has a word boundary before the particle
)
_V1_CAMEL = re.compile(r"\b[a-z]{2,}[A-Z][A-Za-z]+\b", re.ASCII)  # camelCase identifiers (case-sensitive)
_V1_CODING_HINT_KO = ("코드", "함수", "클래스", "모듈", "저장소", "레포", "빌드", "컴파일", "스크립트",
                      "테스트", "에러 메시지", "스택", "쿼리", "브랜치", "커밋", "의존성", "패키지")
_V1_CODE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Grep", "Glob", "Read"}

_V1_L1: dict[str, list[tuple[str, int]]] = {
    "conversation": [
        (r"^\W*(hi|hello|hey|thanks|thank you)\b|\bhow'?s it going\b|\bhow are you\b", 3),
        (r"안녕|고마워|감사해|심심|얘기(나)?\s*하자|기분이", 3),
    ],
    "education": [
        (r"\bteach me\b|\bquiz\b|\blike i'?m \d+\b|\bexplain\b.*\b(to a|for a|like)\b", 3),
        (r"가르쳐|퀴즈|암기|수준으로\s*설명|설명하듯", 3),
    ],
    "creative": [
        (r"\b(haiku|poem|story|lyrics|fiction|novel|names for|come up with)\b", 3),
        (r"동화|소설|세계관|시\s*써|아이디어|이름\s*(을\s*)?(지어|추천)", 3),
    ],
    "agentic_ops": [
        (r"\b(inbox|calendar|book a meeting|schedule a|folder|photos|archive)\b", 3),
        (r"받은편지함|메일함|캘린더|일정|폴더|보관\s*처리|예약", 3),
    ],
    "data": [
        (r"\b(csv|dataframe|spreadsheets?|pandas|datasets?|etl|excel)\b", 3),
        (r"데이터\s*정리|엑셀|스프레드시트|데이터셋|결측치", 3),
    ],
    "analysis_math": [
        (r"\b(analy[sz]e|statistics?|regression|prove|proof|calculate|math|probability|equation|integral)\b", 3),
        (r"분석|통계|계산|수학|확률|증명|풀어", 3),
    ],
    "writing": [
        (r"\b(write|draft|rewrite|translate|summari[sz]e|email|essay|blog|proofread)\b", 2),
        (r"작성해|번역|요약|이메일|메일|글|써\s*줘|초안", 2),
    ],
    "research_qa": [
        (r"\b(research|compare|find out|look up|what is)\b", 2),
        (r"조사|비교|찾아|알려", 2),
    ],
}
_V1_L1_PRIORITY = ("conversation", "education", "creative", "agentic_ops", "data", "analysis_math",
                   "writing", "research_qa")


def _best(text: str, table: dict[str, list[tuple[str, int]]], priority: tuple[str, ...]) -> str | None:
    best, best_score = None, 0
    for code in priority:
        score = sum(w for rx, w in table[code] if re.search(rx, text, re.IGNORECASE | re.ASCII))
        if score > best_score:
            best, best_score = code, score
    return best


def _classify_v1(summary: TurnSummary) -> tuple[str, str | None]:
    text = summary.prompt_text or ""
    tools = set(summary.tools_used)
    edited = summary.files_touched > 0
    hinted = bool(_V1_CODING_HINT.search(text) or _V1_CAMEL.search(text)) or any(k in text for k in _V1_CODING_HINT_KO)
    # Bash or MCP alone is not evidence of coding (file chores, mail, calendars).
    coding = edited or bool(summary.test_calls) or bool(tools & _V1_CODE_TOOLS) or hinted

    if not coding:
        return (_best(text, _V1_L1, _V1_L1_PRIORITY)
                or ("agentic_ops" if tools & {"mcp", "Bash"} else "other")), None

    if not edited:
        code = _best(text, _V1_READONLY, ("coding.review", "coding.explain"))
        if code:
            return "coding", code
    return "coding", _best(text, _V1_L2, _V1_L2_PRIORITY) or "coding.other"


# Registered classifiers. Old versions stay available so archived records can be
# re-evaluated against the exact rules that produced them.
CLASSIFIERS = {"rules-v0": _classify_v0, "rules-v1": _classify_v1}


def classify(summary: TurnSummary, classifier: str | None = None) -> tuple[str, str | None]:
    """Return (l1, l2) closed codes for the last turn using ``classifier`` (default: current)."""
    from . import CLASSIFIER_ID

    return CLASSIFIERS[classifier or CLASSIFIER_ID](summary)
