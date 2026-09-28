"""Static SVG demo figure (stdlib only): self-assessment ranking vs evidence ranking,
plus pair-mode head-to-head, drawn from the DETAILED sample aggregate.

The field reports in that sample are SYNTHETIC; the figure says so in its title
and footer. Output: ``docs/figures/self-vs-evidence.synthetic.svg``.
Regenerate: ``PYTHONPATH=collector:seeds:server python3 -m modelreceipts_server make-figure``.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

# Colors: validated pair from the dashboard (blue <-> red, neutral gray midpoint).
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#6f6d68", "#e1e0d9", "#c3c2b7", "#fcfcfb"
OVER, UNDER, SAME = "#e34948", "#2a78d6", "#898781"
DIV_A, DIV_MID, DIV_B = "#2a78d6", "#d3d1c8", "#e34948"
FONT = "system-ui, -apple-system, 'Segoe UI', 'Noto Sans KR', sans-serif"


def _t(x, y, text, size=13, anchor="start", fill=INK, weight=400) -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}">{escape(str(text))}</text>')


def _pct(v) -> str:
    return "—" if v is None else f"{v * 100:.0f}%"


def render(detail: dict, task: str = "coding.bugfix") -> str:
    sve = {t["task"]: t["models"] for t in detail.get("self_vs_evidence", [])}
    models = sve.get(task, [])
    pairs = [p for p in detail.get("pairwise", {}).get("results", []) if p["l2"] == task]
    W, pad = 960, 24
    slope_h = 60 + 44 * max(len(models), 1)
    pair_h = 50 + 58 * max(len(pairs), 1)
    H = 70 + slope_h + pair_h + 40
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="{FONT}" role="img" aria-labelledby="t d">',
           f'<title id="t">SYNTHETIC demo: self-assessment ranking vs evidence ranking ({escape(task)})</title>',
           '<desc id="d">Drawn from dashboard/data/aggregates.sample.json. All field reports are synthetic '
           '(example-model-*); not a measurement of any real model.</desc>',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>',
           _t(pad, 30, f"자기평가 순위 vs 증거 순위 — {task}", 18, weight=650),
           f'<rect x="{pad + 410}" y="15" width="92" height="20" rx="5" fill="#fff4d6"/>',
           _t(pad + 456, 30, "SYNTHETIC", 12, "middle", "#6b4a00", 700),
           _t(pad, 52, "왼쪽: 에이전트가 스스로 주장한 성공 점수(self_claim)의 순위 · 오른쪽: 마지막 테스트 통과율의 순위. "
                       "빨강 = 자기평가가 과대평가, 파랑 = 증거가 더 높음.", 12, fill=INK2)]
    # --- slope chart
    top, xl, xr = 90, 300, W - 300
    out.append(_t(xl, top - 12, "자기평가 순위", 12, "end", INK2, 600))
    out.append(_t(xr, top - 12, "증거 순위 (테스트 통과율)", 12, "start", INK2, 600))
    for x in (xl + 8, xr - 8):
        out.append(f'<line x1="{x}" x2="{x}" y1="{top - 4}" y2="{top + 44 * len(models)}" stroke="{AXIS}"/>')
    y = lambda r: top + (r - 0.5) * 44  # noqa: E731
    for m in sorted(models, key=lambda m: m["rank_by_self"] == m["rank_by_evidence"], reverse=True):
        moved = m["rank_by_evidence"] - m["rank_by_self"]
        c = OVER if moved > 0 else UNDER if moved < 0 else SAME
        y1, y2 = y(m["rank_by_self"]), y(m["rank_by_evidence"])
        out.append(f'<line x1="{xl + 8}" y1="{y1:.1f}" x2="{xr - 8}" y2="{y2:.1f}" stroke="{c}" stroke-width="2" '
                   f'stroke-linecap="round"/>')
        for cx, cy in ((xl + 8, y1), (xr - 8, y2)):
            out.append(f'<circle cx="{cx}" cy="{cy:.1f}" r="5" fill="{c}" stroke="{SURFACE}" stroke-width="2"/>')
        arrow = " ▼" if moved > 0 else " ▲" if moved < 0 else ""
        out.append(_t(xl - 6, y1 + 4, f"{m['model']}  {_pct(m['self_mean'])}", 13, "end"))
        out.append(_t(xr + 6, y2 + 4, f"{_pct(m['pass_rate'])}  {m['model']}{arrow}", 13))
    # --- pairwise
    py = 70 + slope_h + 10
    out.append(_t(pad, py, f"페어 모드 맞대결 — {task} (같은 태스크를 두 모델로 돌린 쌍, 마지막 테스트 결과)", 15, weight=650))
    lx = pad
    for label, col in (("A 승", DIV_A), ("무승부", DIV_MID), ("B 승", DIV_B)):
        out.append(f'<rect x="{lx}" y="{py + 12}" width="14" height="10" rx="3" fill="{col}"/>')
        out.append(_t(lx + 20, py + 21, label, 12, fill=INK2))
        lx += 90
    bx, bw = 300, W - 300 - 190
    for i, p in enumerate(pairs):
        yy = py + 44 + i * 58
        short = lambda m: m.replace("example-", "")  # noqa: E731
        out.append(_t(pad, yy + 15, f"A {short(p['model_a'])}  vs  B {short(p['model_b'])}", 13, weight=600))
        decided = p["a_wins"] + p["ties"] + p["b_wins"]
        x = bx
        for n, col in ((p["a_wins"], DIV_A), (p["ties"], DIV_MID), (p["b_wins"], DIV_B)):
            if n:
                w = bw * n / decided
                out.append(f'<rect x="{x:.1f}" y="{yy}" width="{w:.1f}" height="20" fill="{col}" stroke="{SURFACE}" '
                           f'stroke-width="2"/>')
                x += w
        lo, hi = p["a_score_ci95"]
        out.append(_t(bx + bw + 10, yy + 15, f"A 점수 {_pct(p['a_score'])} ({_pct(lo)}–{_pct(hi)})", 12, fill=INK2))
        out.append(_t(bx, yy + 36, f"A {p['a_wins']}승 · 무승부 {p['ties']} · B {p['b_wins']}승 · 판정 불가 "
                                   f"{p['undecided']} · {p['pairs']}쌍 · 기여자 {p['k']}", 11, fill=MUTED))
    out.append(_t(pad, H - 16, "SYNTHETIC — 샘플 생성기가 만든 가짜 현장 보고(example-model-*)입니다. 실제 모델의 측정값이 아닙니다. "
                               "출처: dashboard/data/aggregates.sample.json", 11, fill=MUTED))
    out.append("</svg>")
    return "\n".join(out) + "\n"
