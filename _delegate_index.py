"""Delegate index.html rewrite to GPT-5.4.

The output is a single self-contained HTML file: chrome + three-level D3 navigation
over the DFM knowledge graph (topic -> frames in topic -> ego network of one frame).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from openai import OpenAI

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "index.draft.html"

PROMPT = r"""
You are drafting a single-file static web app: `index.html` for the "DFM Graph Explorer".

# Purpose
A dark-technical-product D3 graph explorer over a knowledge graph extracted from Stack Exchange engineering forum posts. Forked in spirit from the `atlas-gui` prototype (three-level navigation: Field -> Node Orientation -> Node Deep Dive), but rewritten for different data and a different color/typography system.

# Runtime contract
- Single HTML file, no build step. CSS + HTML + JS all inline.
- Loads `./graph_data.json` with fetch(). File:// fallback must show a clear error with instructions to run `python -m http.server`.
- D3 v7 from cdnjs. Google Fonts OK for now: Geist + JetBrains Mono.
- No framework. Vanilla JS. Modern ES (optional chaining, top-level await is fine).

# Data shape of `./graph_data.json` (already on disk)

```jsonc
{
  "meta": {
    "generated": ISO8601,
    "counts": { "frames": 3879, "posts": 1936, "authors": 1138, "threads": 911,
                "topics": 39, "outliers": 619, "semantic_edges": 4193 },
    "year_range": [2010, 2026]
  },
  "topics": [ // 39 entries
    {
      "id": "topic_0",
      "topic_id": 0,
      "label": "Precision hole-making",
      "keywords": ["..."],
      "n_frames": 410,
      "scope_distribution": { "machining_process": 177, "tooling": 131, ... },
      "frame_type_distribution": { "heuristic": 149, "observation": 116, "risk": 66, ... },
      "top_frame_ids": ["se-engineering-51725-a51726-0", ...]
    }
  ],
  "frames": [ // 3879 entries
    {
      "id": "se-engineering-51725-a51726-0",
      "label": "first sentence of main_point, capped 120c",
      "main_point": "full text",
      "source_quote": "verbatim forum snippet",
      "subject": "noun phrase",
      "scope": "machining_process | design_geometry | material | tooling | programming | shop_operations | quality | cost | machine_capability | other",
      "frame_type": "risk | heuristic | principle | case | workaround | observation | comparison | other",
      "applicability": "universal | context_dependent | situational",
      "epistemic_stance": "absolute_authoritative | direct_neutral | hedged_emphatic | tentative_subjective | narrative_implied",
      "post_role": "solution | question | context | ...",
      "topic_id": 0,
      "topic_label": "Precision hole-making",
      "post_id": "se-engineering-51725-a51726",
      "thread_url": "https://...",
      "thread_title": "...",
      "se_site": "engineering | electronics | robotics | mechanics | woodworking",
      "se_tags": ["aluminum", "lathe"],
      "post_score": 1,
      "is_accepted_answer": true,
      "post_date": "2022-07-15T06:56:41+00:00",
      "post_year": 2022,
      "author_username": "nicoguaro",
      "author_reputation": 115,
      "credibility_tier": "high | medium | low",
      "source_url": "thread_url#postId"
    }
  ],
  "semantic_edges": [ // 4193 entries, connect frames
    {
      "id": 0,
      "source": "frame_id_a",
      "target": "frame_id_b",
      "label": "SPECIFIES | MITIGATES | CAUSAL_LINK | CONTRADICTS",
      "direction": "A_to_B | B_to_A",
      "confidence": "high | medium | low",
      "reasoning": "LLM-written explanation, 1-2 sentences"
    }
  ]
}
```

# Three-level navigation

### Level 1 - Topic overview (default)
- Render the 39 topics as force-directed supernodes.
- Node radius scaled by sqrt(n_frames) between 10 and 44 px.
- Node color: dominant `frame_type` from `frame_type_distribution`. Use the frame-type palette below.
- Edges at Level 1: aggregate semantic edges by the topic of their source/target frames. An edge between two topics has `weight = count of frame-frame semantic edges crossing that topic pair`. Skip edges to topic_id -1 (outliers). Edges with weight < 2 are hidden by default; weight slider exposes threshold.
- Click a topic -> transition to Level 2 for that topic.
- Hover shows tooltip: label, n_frames, top 3 frame types with counts.

### Level 2 - Frames within one topic
- Hard-filter to frames with `frame.topic_id == selected.topic_id`. (Typically 30-500 frames.)
- Nodes are frames. Radius ~5-9px. Color by `frame_type`.
- Edges: semantic edges whose both endpoints are in the topic. Smaller widths.
- Right-side panel opens (width 360px): topic label, n_frames, frame-type distribution bar, keyword list, top-5 frames as a scrollable list. Clicking a frame in the list = click on the graph node.
- Hover on a frame node: tooltip shows `label` (first sentence), frame_type badge, se_site, author_username + credibility dot.
- Click a frame node -> Level 3.
- Breadcrumb: "DFM Graph Explorer / {topic.label}".

### Level 3 - Frame deep-dive
- Graph area collapses to 1/3 on the left. Right 2/3 is a reading view.
- Graph: ego network = the selected frame + its semantic-edge neighbors (typically 0-20). Selected frame highlighted.
- Reading view (right 2/3), top to bottom:
  - Frame type badge (colored pill) + scope chip + applicability chip.
  - `label` as h2 (big).
  - Serif blockquote of `source_quote`. (Use Source Serif 4 or Georgia fallback. Italic. Accent-colored left border 2px, 12px padding-left.)
  - Meta row (monospace): author_username + credibility dot + "rep {author_reputation}" + se_site + post_date (YYYY-MM-DD). `source_url` link opens in new tab (labelled "Open on Stack Exchange ->").
  - Section: "Main point" with full `main_point` text (sans, normal).
  - Section: "Connected frames" grouped by semantic edge label (SPECIFIES / MITIGATES / CAUSAL_LINK / CONTRADICTS). For each group: a list of connected frame cards. Each card: neighbor frame `label`, frame_type dot, `confidence` tag, clickable "Why?" that reveals the edge's `reasoning` inline. Clicking a card navigates Level 3 to that neighbor (push history).
- Back button returns to Level 2 for the frame's topic.

# Chrome / Topbar
- Height 52px. Left: breadcrumb + search box (placeholder "Search frames, topics, authors..."). Right: legend (frame-type swatches) + optional TEMPORAL MODE toggle (year slider 2010-2026 appears when active, filters by post_year <= year).
- Frame-type filter pills (only on Levels 2+3): click to toggle each of the 8 frame types. Muted state = off.
- SE-site filter pills (only on Levels 2+3): 5 sites. Site pill color is the site's tint.
- Credibility dropdown: "All / Medium or higher / High only".
- Weight slider (Level 1 only): "Min. N shared semantic edges".

# Visual system (tokens)

```css
:root {
  --bg: #0a0a0b;              /* warm near-black */
  --surface: #131316;
  --surface-2: #1c1c20;
  --surface-3: #26262b;
  --border: rgba(255,255,255,0.07);
  --border-strong: rgba(255,255,255,0.12);
  --fg: #ececee;
  --fg-muted: #a0a0a8;
  --fg-faint: #6b6b72;

  --accent: #ff6b3d;           /* orange - USED ON <5% OF PIXELS, not indigo */
  --accent-soft: rgba(255,107,61,0.15);

  /* Frame-type palette (node colors) */
  --type-risk: #f87171;
  --type-heuristic: #60a5fa;
  --type-principle: #a78bfa;
  --type-case: #fbbf24;
  --type-workaround: #34d399;
  --type-observation: #94a3b8;
  --type-comparison: #f472b6;
  --type-other: #c084fc;

  /* SE site tints (subtle, used in filter pills and tooltip meta) */
  --site-engineering: #4fc3f7;
  --site-electronics: #81c784;
  --site-robotics: #ffb74d;
  --site-mechanics: #f48fb1;
  --site-woodworking: #a1887f;

  --radius-sm: 4px;
  --radius: 6px;
  --radius-lg: 10px;             /* NEVER larger, no rounded-2xl */
}
```

Typography:
```
--font-sans: "Geist", "Inter Tight", "Inter", system-ui, sans-serif;
--font-mono: "JetBrains Mono", "Geist Mono", ui-monospace, Menlo, monospace;
--font-serif: "Source Serif 4", Charter, Georgia, serif;
```
Load from Google Fonts (Geist, JetBrains Mono, Source Serif 4). Use `text-wrap: balance` on h1/h2, `text-wrap: pretty` on paragraphs. `font-optical-sizing: auto` on html. `font-variant-numeric: tabular-nums` on number columns. Mono for meta/breadcrumb/numerals; serif for blockquote only.

Anti-checklist (DO NOT):
- No aurora/mesh gradients, no glowing radial blobs.
- No bg-clip-text on headings.
- No rounded-2xl.
- No uniform 300ms animations. Use 120ms in / 240ms out.
- No indigo-500/purple accent.
- No cool slate/zinc grays.
- No flat shadow-md on every card.
- No centered-730px reading column; panels are flush left inside their region.
- No emoji in the UI.

# Interactions
- Force simulation: forceLink + forceManyBody + forceCenter + forceCollide. Tune per level:
  - Level 1 (39 nodes): charge -600, link distance 120-200.
  - Level 2 (30-500): charge -180, distance 30-60.
  - Level 3 (1-20): charge -120, distance 40.
- Zoom/pan on svg root g via d3.zoom, scaleExtent [0.2, 8].
- Drag behavior on nodes (fix x/y during drag, release after).
- Use `prefers-reduced-motion` to disable transitions and use alphaTarget(0) immediately after layout settles.
- On Level 2 entry, transition nodes from their old positions to new layout over ~400ms (not a hard cut).
- Tooltip: uses CSS variables; fixed position; asymmetric transition (120ms in, 240ms out).

# Grain overlay (required)
A `<div class="grain">` first child of body, `aria-hidden="true"`, fixed full-viewport, opacity 0.035, mix-blend-mode overlay, an SVG fractal noise data URI. This is the dark-theme grain trick from the playbook.

# Accessibility
- `:focus-visible` style with 2px accent outline and 3px offset.
- Buttons and clickable nodes keyboard-operable where possible.
- `aria-label`s on svg and on filter controls.

# File structure
One file, inlined CSS and JS. Organize the JS into these named functions/sections (roughly):

1. Module-level constants: color maps, frame-type order, se-site order.
2. `loadData()` -> parsed graph_data.
3. `buildIndices(data)` -> { frameById, topicById, framesByTopic, semanticEdgesByFrame, adjacencyByTopic }.
4. `state` object: { level, selectedTopicId, selectedFrameId, activeFrameTypes, activeSeSites, credibilityMin, minTopicEdgeWeight, temporalMode, activeYear, history }.
5. `render()` - top-level router that picks renderLevel1/2/3 based on state.
6. `renderLevel1(data, idx, state)` - draws 39 topic supernodes with aggregated edges.
7. `renderLevel2(topicId, data, idx, state)` - draws frames within topic + side panel.
8. `renderLevel3(frameId, data, idx, state)` - ego network + reading view.
9. `openTopic(id)`, `openFrame(id)`, `goBack()` - navigation helpers that push to state.history.
10. Search indexing (simple client-side includes-match over frame.label/main_point/subject/author_username + topic.label).
11. Filter pill rendering + event binding.
12. Utilities: escapeHtml, formatDate, lookupTopicLabel.

Do NOT preserve atlas-gui's variable names. Rewrite cleanly. Do keep its overall dark-topbar + graph-area + right-panel layout pattern.

# Deliverable
Return the full `index.html` as one string. No markdown fences, no extra commentary, no preamble. Just the HTML source. It should load cleanly when served via `python -m http.server` from the file's directory, assuming `graph_data.json` is present.

Aim for ~1500-2500 lines. Prioritize: Level 1 working cleanly, Level 2 working cleanly, Level 3 rendering source_quote + semantic-edge reasoning. Filters and temporal mode can be stubbed (render the controls, leave no-op handlers) if time is tight - but ship Level 1/2/3 core working.

First line: `<!DOCTYPE html>`.
""".strip()


def try_call(client: OpenAI, model: str) -> tuple[str, str]:
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
        err = str(e).lower()
        if "responses" not in err and "not found" not in err:
            print(f"[{model}] responses-api failed: {e}", file=sys.stderr)
    # fallback
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.3,
    )
    return model, resp.choices[0].message.content or ""


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    client = OpenAI()
    models = [os.environ.get("OPENAI_MODEL") or "", "gpt-5.4", "gpt-5", "gpt-5-mini", "gpt-4.1"]
    models = [m for m in models if m]
    last_err = None
    for model in models:
        try:
            print(f"Trying model: {model}", file=sys.stderr)
            used, content = try_call(client, model)
            if not content.strip():
                raise RuntimeError("empty response")
            text = content.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines)
            OUTPUT.write_text(text, encoding="utf-8")
            print(f"[OK] wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes) via {used}")
            return
        except Exception as e:
            last_err = e
            print(f"[{model}] failed: {e}", file=sys.stderr)
    print(f"All models failed: {last_err}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
