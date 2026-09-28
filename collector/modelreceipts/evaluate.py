"""Classifier accuracy evaluation on the hand-labeled SYNTHETIC eval set.

``python3 -m modelreceipts eval-classifier [--classifier ID ...] [--split dev|test|all] [--markdown]``

The eval set (``collector/eval/classifier_eval.synthetic.jsonl``) is written by
the project, not collected from users. Scores measure rule regressions on that
set; they are NOT an estimate of accuracy on real prompts (see eval/README.md).

Label unit = the combined code: the coding L2 code for coding examples, the L1
code otherwise (non-coding L1 has no L2 in taxonomy t0.1).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from .classify import CLASSIFIERS, classify
from .transcript import ToolCall, TurnSummary

EVAL_PATH = Path(__file__).resolve().parents[1] / "eval" / "classifier_eval.synthetic.jsonl"


def load_examples(path: Path = EVAL_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def summary_for(example: dict) -> TurnSummary:
    """Rebuild the tool activity the example describes (no real transcript involved)."""
    calls: list[ToolCall] = []
    for i in range(int(example.get("files_touched", 0))):
        calls.append(ToolCall(name="Edit", file_path=f"synthetic/file{i}", is_error=False))
    for _ in range(int(example.get("test_calls", 0))):
        calls.append(ToolCall(name="Bash", command="python3 -m pytest", is_error=False))
    have = {c.name for c in calls}
    for name in example.get("tools", []):
        if name not in have:
            calls.append(ToolCall(name="mcp__synthetic__tool" if name == "mcp" else name))
    return TurnSummary(prompt_text=example["prompt"], tool_calls=calls)


def label_of(l1: str, l2: str | None) -> str:
    return l2 if l1 == "coding" else l1


def evaluate(examples: list[dict], classifier: str) -> dict:
    gold, pred = [], []
    for ex in examples:
        l1, l2 = classify(summary_for(ex), classifier=classifier)
        gold.append(label_of(ex["l1"], ex["l2"]))
        pred.append(label_of(l1, l2))
    labels = sorted(set(gold) | set(pred))
    per_class = {}
    for lab in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == lab and p == lab)
        fp = sum(1 for g, p in zip(gold, pred) if g != lab and p == lab)
        fn = sum(1 for g, p in zip(gold, pred) if g == lab and p != lab)
        prec = tp / (tp + fp) if tp + fp else None
        rec = tp / (tp + fn) if tp + fn else None
        f1 = 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if prec is not None and rec is not None else None)
        per_class[lab] = {"support": tp + fn, "predicted": tp + fp, "tp": tp,
                          "precision": prec, "recall": rec, "f1": f1}
    supported = [v for v in per_class.values() if v["support"]]
    macro = {
        "precision": sum(v["precision"] or 0.0 for v in supported) / len(supported),
        "recall": sum(v["recall"] or 0.0 for v in supported) / len(supported),
    }
    l1_correct = sum(1 for g, p in zip(gold, pred)
                     if (g.startswith("coding.") and p.startswith("coding.")) or g == p)
    errors = Counter((g, p) for g, p in zip(gold, pred) if g != p)
    return {
        "classifier": classifier,
        "n": len(gold),
        "accuracy": sum(1 for g, p in zip(gold, pred) if g == p) / len(gold),
        "l1_accuracy": l1_correct / len(gold),
        "macro": macro,
        "per_class": per_class,
        "top_confusions": errors.most_common(8),
    }


def _fmt(x: float | None) -> str:
    return "—" if x is None else f"{x:.2f}"


def to_markdown(results: dict[tuple[str, str], dict], classifiers: list[str], splits: list[str]) -> str:
    out = ["# 분류기 평가 결과 (합성 평가 세트)", "",
           "`PYTHONPATH=collector python3 -m modelreceipts eval-classifier --markdown`로 생성. 손으로 고치지 않는다.",
           "", "> 평가 세트는 **전부 합성 예문**이고 같은 작성자가 규칙도 썼다. 실제 프롬프트에서의 정확도 추정치가 아니다."
           " `test` 분할은 `rules-v1` 작업 전에 고정했고 규칙 조정에는 `dev`만 썼다. 자세한 한계: [README.md](README.md).",
           "", "## 요약", "", "| 분류기 | 분할 | n | 정확도(L2/L1 코드) | L1 정확도 | macro 정밀도 | macro 재현율 |",
           "|---|---|---:|---:|---:|---:|---:|"]
    for c in classifiers:
        for s in splits:
            r = results[(c, s)]
            out.append(f"| `{c}` | {s} | {r['n']} | {r['accuracy']:.3f} | {r['l1_accuracy']:.3f} | "
                       f"{r['macro']['precision']:.3f} | {r['macro']['recall']:.3f} |")
    for s in splits:
        out += ["", f"## 클래스별 정밀도 / 재현율 — `{s}` 분할", "",
                "| 클래스 | 지지도 | " + " | ".join(f"`{c}` P | `{c}` R" for c in classifiers) + " |",
                "|---|---:|" + "---:|---:|" * len(classifiers)]
        labels = sorted(set().union(*(results[(c, s)]["per_class"] for c in classifiers)))
        for lab in labels:
            sup = max(results[(c, s)]["per_class"].get(lab, {}).get("support", 0) for c in classifiers)
            cells = []
            for c in classifiers:
                pc = results[(c, s)]["per_class"].get(lab, {})
                cells += [_fmt(pc.get("precision")), _fmt(pc.get("recall"))]
            out.append(f"| `{lab}` | {sup} | " + " | ".join(cells) + " |")
        for c in classifiers:
            conf = results[(c, s)]["top_confusions"]
            if conf:
                out += ["", f"`{c}` / {s} 주요 혼동 (정답 → 예측, 건수): " +
                        ", ".join(f"`{g}`→`{p}` {n}" for (g, p), n in conf)]
    out += ["", "지지도 = 그 분할에서 정답이 해당 클래스인 예시 수. 예측이 한 번도 없으면 정밀도는 `—`.", ""]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="modelreceipts eval-classifier",
                                     description="Per-class precision/recall on the SYNTHETIC eval set.")
    parser.add_argument("--classifier", action="append", choices=sorted(CLASSIFIERS),
                        help="repeatable; default: all registered classifiers")
    parser.add_argument("--split", choices=["dev", "test", "all"], action="append",
                        help="repeatable; default: dev and test")
    parser.add_argument("--data", type=Path, default=EVAL_PATH)
    parser.add_argument("--markdown", action="store_true", help="print a Markdown report (RESULTS.md)")
    parser.add_argument("--json", action="store_true", help="print raw JSON results")
    args = parser.parse_args(argv)

    examples = load_examples(args.data)
    classifiers = args.classifier or sorted(CLASSIFIERS)
    splits = args.split or ["dev", "test"]
    results = {}
    for c in classifiers:
        for s in splits:
            subset = examples if s == "all" else [e for e in examples if e["split"] == s]
            results[(c, s)] = evaluate(subset, c)

    if args.json:
        print(json.dumps({f"{c}/{s}": r for (c, s), r in results.items()}, ensure_ascii=False, indent=2, default=str))
    elif args.markdown:
        print(to_markdown(results, classifiers, splits))
    else:
        print("SYNTHETIC eval set — regression check, not a real-world accuracy estimate.")
        for (c, s), r in results.items():
            print(f"{c:10s} {s:5s} n={r['n']:3d} acc={r['accuracy']:.3f} l1_acc={r['l1_accuracy']:.3f} "
                  f"macroP={r['macro']['precision']:.3f} macroR={r['macro']['recall']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
