"""One-shot delegation: ask GPT to draft export_graph.py based on concrete schemas.

We give GPT:
- The exact input data shapes (observed from live inspection)
- The target output schema (atlas-gui JSON, adapted for DFM fields)
- A list of requirements

We expect back: a single self-contained Python script.

Run:
    python _delegate_export.py

Writes: export_graph.draft.py (for review)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from openai import OpenAI

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "export_graph.draft.py"

MODEL_CANDIDATES = [
    os.environ.get("OPENAI_MODEL") or "",
    "gpt-5.4",
    "gpt-5",
    "gpt-5-mini",
    "gpt-4.1",
]
MODEL_CANDIDATES = [m for m in MODEL_CANDIDATES if m]

PROMPT = """You are drafting a one-off Python export script for a graph-explorer web app.

# Goal
Read Douglas's DFM knowledge graph from disk and emit a single `graph_data.json` file that a D3-based single-page app (modeled on the atlas-gui prototype) can consume directly via `fetch("./graph_data.json")`.

# Inputs (all paths absolute, read-only; never overwrite)
1. `C:/Users/dougl/Documents/dfm_scraping/provenance_graph.gpickle`
   - `networkx.MultiDiGraph`, 7864 nodes, 13148 edges.
   - Nodes have `node_type` in {Frame, Post, Author, Thread}.
   - Frame node attrs: `node_type='Frame'`, `frame_type` (risk|heuristic|principle|case|workaround|observation|comparison|other), `scope`, `subject`, `applicability`, `main_point`, `source_quote`, `epistemic_stance`, `post_role`, `example_value`, `example_context`, `thread_context`, `validated`.
   - Post node attrs: `node_type='Post'`, `post_type`, `post_position`, `post_date` (ISO string), `post_score`, `is_accepted_answer`, `se_tags`, `se_site`.
   - Author node attrs: `node_type='Author'`, `author_username`, `reputation`, `credibility_tier` (high|medium|low), `user_type`, `accept_rate`, `profile_link`.
   - Thread node attrs: `node_type='Thread'`, `thread_title`, `se_site`, `post_count`. The thread node id is the thread URL (starts with `https://...stackexchange.com/questions/...`).
   - Edge types in the gpickle: THREAD_CONTAINS_POST, POST_AUTHORED_BY, POST_CONTAINS_FRAME, SE_ANSWERS (structural); SPECIFIES, CAUSAL_LINK, CONTRADICTS, MITIGATES (semantic, already embedded).
   - Edge attrs: `edge_type`; semantic edges also have `label`, `direction`, `confidence`, `reasoning`.

2. `C:/Users/dougl/Documents/dfm_scraping/semantic_edges.json`
   - JSON object with keys `model`, `top_k`, `total_classified`, `total_edges`, `edges`.
   - Each edge entry: `{frame_a, frame_b, label, direction, confidence, reasoning}`.
   - 4193 entries total. This is authoritative for semantic-edge metadata — prefer it over the edge attrs already in the gpickle.

3. `C:/Users/dougl/Documents/dfm_scraping/topic_model_output.json`
   - JSON object with keys `metadata`, `topics`, `frame_assignments`.
   - `topics`: list of 40 entries (topic_id -1 through 38, where -1 is outliers). Each has `topic_id`, `label` (e.g. "0_Precision hole-making"), `keywords`, `n_frames`, `scope_distribution`, `frame_type_distribution`, `top_frames` (list of {frame_id, subject, main_point}).
   - `frame_assignments`: list of 3879 entries, each `{frame_id, topic_id, topic_label}`.

# Output: `C:/Users/dougl/My Drive (douglaspmcgowan@gmail.com)/UC Berkeley/Research/Claude Research Folder/dfm-graph-explorer/graph_data.json`

Shape:
```jsonc
{
  "meta": {
    "generated": ISO8601 UTC,
    "source": "provenance_graph.gpickle + semantic_edges.json + topic_model_output.json",
    "counts": {
      "frames": 3879, "posts": 1936, "authors": 1138, "threads": 911,
      "topics": 39, "outliers": 619,
      "semantic_edges": 4193
    },
    "year_range": [min_year, max_year]   // from post_date years
  },
  "topics": [
    {
      "id": "topic_0",
      "topic_id": 0,
      "label": "Precision hole-making",       // strip leading "N_" prefix
      "raw_label": "0_Precision hole-making",
      "keywords": [...],
      "n_frames": 410,
      "scope_distribution": {...},
      "frame_type_distribution": {...},
      "top_frame_ids": [...]                  // just the frame_ids
    },
    ...
  ],
  "frames": [
    {
      "id": "se-engineering-51725-a51726-0",
      "label": "",                             // first sentence of main_point, capped ~120 chars, else the subject
      "main_point": "...",
      "source_quote": "...",
      "subject": "...",
      "scope": "...",
      "frame_type": "heuristic",
      "applicability": "...",
      "epistemic_stance": "...",
      "post_role": "...",
      "topic_id": 0,                            // -1 if outlier
      "topic_label": "Precision hole-making",   // cleaned label; null if outlier
      "post_id": "se-engineering-51725-a51726",
      "thread_url": "https://engineering.stackexchange.com/questions/51725/...",
      "thread_title": "Machining small aluminium stock",
      "se_site": "engineering",
      "se_tags": ["aluminum", "lathe"],
      "post_score": 1,
      "is_accepted_answer": false,
      "post_date": "2022-07-15T06:56:41+00:00",
      "post_year": 2022,
      "author_username": "nicoguaro",
      "author_reputation": 115,
      "credibility_tier": "low",
      "source_url": "https://engineering.stackexchange.com/questions/51725/...#51726"   // thread_url + "#" + post numeric suffix if derivable; else thread_url
    },
    ...
  ],
  "semantic_edges": [
    {
      "id": 0,                                  // sequential
      "source": "se-engineering-51725-a51726-0",
      "target": "se-woodworking-8218-a8224-1",
      "label": "SPECIFIES",
      "direction": "B_to_A",
      "confidence": "medium",
      "reasoning": "..."
    },
    ...
  ]
}
```

# Requirements
- Use the venv python (stdlib + networkx; networkx is installed).
- Read everything with `encoding="utf-8"` explicitly.
- Load gpickle via `pickle.load(open(..., "rb"))`. Do NOT use `networkx.read_gpickle` (deprecated).
- Walk each Frame node, follow POST_CONTAINS_FRAME back to its Post (reverse edge), then POST_AUTHORED_BY and THREAD_CONTAINS_POST outward to Author/Thread. A Frame should have exactly one Post; a Post exactly one Author and one Thread. If any is missing, fill with safe defaults (None/empty string) but don't crash.
- For the `label` field on a Frame: take the first sentence of `main_point` (split on `. `), strip trailing period, cap at 120 chars with an ellipsis if longer. Fall back to `subject` if `main_point` is empty.
- For `topic_label`: strip the leading `N_` prefix from `raw_label`. If topic_id is -1, set topic_label to null.
- Build `post_year` from `post_date` if present (first 4 chars as int).
- `source_url`: Use `thread_url` + `#` + the post numeric fragment. The Post id looks like `se-engineering-51725-a51726` or `se-engineering-51725` (question post). Extract the last numeric suffix (`51726` or `51725`) and append as the anchor. If you can't parse, just use `thread_url`.
- For semantic edges: iterate the `edges` list in `semantic_edges.json`. Skip an edge if either frame_id isn't in the Frame set. Write `source` and `target` as-is (no re-orientation by direction — the JS side will interpret `direction`).
- Print a summary to stdout at the end: counts of each node type, edges, topics, size of output.
- Pretty-print JSON with `indent=2` but `ensure_ascii=False`. Write to the explicit OUTPUT path with `encoding="utf-8"`.
- Script must be runnable as: `venv/Scripts/python.exe export_graph.py` from anywhere. Use `Path(__file__).resolve().parent` for relative logic, but hardcode the input/output paths as `Path` literals (Windows forward-slash strings are fine in Python).

# Deliverable
Return the full Python script only. No markdown fences, no explanation, no preamble. Just the script source, ready to paste into `export_graph.py` and run. First line should be a short triple-quoted docstring or `#!/usr/bin/env python3`.
"""


def try_call(client: OpenAI, model: str) -> tuple[str, str]:
    """Returns (model_used, content). Raises on failure."""
    # Try new responses API first (better for newer models)
    try:
        resp = client.responses.create(
            model=model,
            input=PROMPT,
            reasoning={"effort": "medium"},
        )
        text = getattr(resp, "output_text", None)
        if text:
            return model, text
    except Exception as e:
        err = str(e)
        if "responses" not in err.lower() and "not found" not in err.lower():
            print(f"[{model}] responses API failed: {err[:200]}", file=sys.stderr)

    # Fall back to chat completions
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.2,
    )
    return model, resp.choices[0].message.content or ""


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    client = OpenAI()
    last_err = None
    for model in MODEL_CANDIDATES:
        try:
            print(f"Trying model: {model}", file=sys.stderr)
            used, content = try_call(client, model)
            if not content.strip():
                raise RuntimeError("empty response")
            # Strip code fences if the model added them despite instructions
            text = content.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                lines = lines[1:]  # drop opening fence line
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines)
            OUTPUT.write_text(text, encoding="utf-8")
            size = OUTPUT.stat().st_size
            print(f"[OK] wrote {OUTPUT} ({size} bytes) via {used}")
            return
        except Exception as e:
            last_err = e
            print(f"[{model}] failed: {e}", file=sys.stderr)
            continue
    print(f"All models failed. Last error: {last_err}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
