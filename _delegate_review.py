"""Ask GPT-5.4 (thinking) to review dfm-graph-explorer for improvements.

Sends the key files (index.html, export_graph.py, data shape summary) and asks
for a prioritized list of improvements: bugs, accessibility, performance,
code-quality, UX gaps. NOT asking it to rewrite — only to list and justify.

Run:
    python _delegate_review.py
Writes: review_report.md
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from openai import OpenAI

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "review_report.md"

MODEL_CANDIDATES = [
    os.environ.get("OPENAI_MODEL") or "",
    "gpt-5.4",
    "gpt-5",
    "gpt-5-mini",
    "gpt-4.1",
]
MODEL_CANDIDATES = [m for m in MODEL_CANDIDATES if m]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_prompt() -> str:
    index_html = read_text(HERE / "index.html")
    export_py = read_text(HERE / "export_graph.py")

    graph = json.loads((HERE / "graph_data.json").read_text(encoding="utf-8"))
    meta = graph.get("meta", {})
    shape = {
        "meta_keys": list(meta.keys()),
        "topic_count": len(graph.get("topics", [])),
        "frame_count": len(graph.get("frames", [])),
        "semantic_edge_count": len(graph.get("semantic_edges", [])),
        "sample_topic_keys": list((graph.get("topics") or [{}])[0].keys()),
        "sample_frame_keys": list((graph.get("frames") or [{}])[0].keys()),
        "sample_edge_keys": list((graph.get("semantic_edges") or [{}])[0].keys()),
    }

    return f"""You are reviewing a single-file D3 knowledge-graph explorer
(`dfm-graph-explorer`) for a UC Berkeley PhD researcher. The goal of this review
is to produce a SHORT, PRIORITIZED list of improvements — not a rewrite, not
line-by-line nitpicks.

# Project context
- It's a fork/adaptation of an atlas-gui prototype, reskinned for a
  7,864-node Stack-Exchange-derived DFM knowledge graph.
- Single HTML file, no build step, D3 v7, static deploy target is Vercel.
- Dark warm-black theme, orange accent (#ff6b3d), Geist + JetBrains Mono +
  Source Serif 4. Max radius 10px, grain overlay, compact.
- Three-level navigation: (1) 39 topic supernodes, (2) ~100–400 frames inside
  a topic, (3) single-frame deep-dive with source quote + ego network.
- Frame types: risk, heuristic, principle, case, workaround, observation,
  comparison, other (each has a color).
- Semantic edges: SPECIFIES, MITIGATES, CAUSAL_LINK, CONTRADICTS.
- Data currently ships as one 8.1 MB `graph_data.json` fetched on load.
  (We are about to split it into topics.json + per-topic bundles + a search
  index — flag this in your review if you want.)

# What's working (verified in browser)
- Level 1 renders 39 topic supernodes.
- Level 2 renders ~400 frame nodes in a proper force layout (we just fixed
  a corner-collapse bug: nodes started at exact same anchor, charge explosion
  hit wall-clamp, velocity wasn't zeroed).
- Level 3 renders source-quote hero + connected frames + ego network.
- Frame-type pills, site pills, credibility dropdown, temporal year slider
  all toggle correctly.
- Search input exists. Breadcrumb, back button, tooltip work.

# What I want from you
Read both files and the data-shape summary below. Return a Markdown report
with these sections, using concise bullet points. Cite file:line when
possible.

1. **Critical bugs / correctness issues** (things that will break or produce
   wrong output). Include regressions you suspect but can't fully verify.
2. **Accessibility** (keyboard nav, aria, focus, contrast). Be specific.
3. **Performance** (things that matter beyond gzip — e.g. per-tick work,
   large selectAll, redundant renders, memory).
4. **Code smell / maintainability** (duplication, unclear state, magic
   numbers that should be constants). Keep to the top 5 — no bikeshedding.
5. **UX gaps** (missing affordances, confusing interactions, things that
   a researcher audience would find frustrating).
6. **Deployment / data-split advice** (should we really split? any pitfalls
   with the gzip-over-Vercel path?).

For each item: one-line description, severity (🔴 critical / 🟡 important /
🟢 nice-to-have), and a one-line fix suggestion. Skip anything that's clearly
subjective taste.

Please keep the total under ~600 lines. If you have to choose, prefer
specific + actionable over comprehensive.

# Data shape (observed)
```json
{json.dumps(shape, indent=2)}
```

# export_graph.py (the script that produced graph_data.json)
```python
{export_py}
```

# index.html (the web app)
```html
{index_html}
```

---
Begin the review below.
"""


def call_model(client: OpenAI, prompt: str) -> tuple[str, str]:
    errors: list[str] = []
    for model in MODEL_CANDIDATES:
        try:
            resp = client.responses.create(
                model=model,
                input=prompt,
                reasoning={"effort": "medium"},
            )
            text = getattr(resp, "output_text", None)
            if not text:
                parts: list[str] = []
                for item in getattr(resp, "output", []) or []:
                    for block in getattr(item, "content", []) or []:
                        t = getattr(block, "text", None)
                        if t:
                            parts.append(t)
                text = "\n".join(parts)
            if text:
                return model, text
            errors.append(f"{model}: empty output")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{model}: {exc}")
    raise RuntimeError("All models failed:\n" + "\n".join(errors))


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY not set")
    client = OpenAI()
    prompt = build_prompt()
    model, text = call_model(client, prompt)
    header = f"<!-- model: {model} -->\n\n"
    OUTPUT.write_text(header + text, encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(text)} chars, model={model})")


if __name__ == "__main__":
    main()
