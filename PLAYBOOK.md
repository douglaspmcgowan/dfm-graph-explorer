# PLAYBOOK — Building a Knowledge-Graph Explorer Website

This is the working playbook for building topic-clustered, force-directed
"map of frames" explorers like `dfm-graph-explorer`. It captures the
architecture, the decisions and their alternatives, the bugs we hit and
how to avoid them, the tools we used, and a step-by-step guide to
spinning up another one for a different topic / corpus.

The goal is so that the next time we build one of these — whether for
DFM, civic-tech, climate-policy reasoning, or any other knowledge graph
— we don't re-derive everything from scratch.

---

## 1. What we're building

A single-page web app that lets a researcher *browse* a knowledge graph
of "frames" (short claim-like statements extracted from a corpus). Three
zoom levels:

| Level | View | Purpose |
| --- | --- | --- |
| **L1** | All-frames map (~3.9k nodes) clustered by topic | Survey the whole space; spot dense regions; click a cluster |
| **L2** | One topic — its frames + intra-topic edges | Read the cluster; see internal structure; click a frame |
| **L3** | One frame — full text, evidence, inbound/outbound semantic neighbors | Read deeply; hop to neighbors |

The point is **emergent reading**: don't pre-curate the path; let the
researcher follow edges where their attention goes. So the UI lives or
dies on three things: (1) clusters being visually legible, (2)
navigation feeling cheap (sub-second hops), and (3) the L3 reading
experience being calm enough that they stay.

---

## 2. Architecture at 30,000 ft

```
  raw corpus
     │
     │  (1) extraction — LLM/heuristic pulls "frames" out of the corpus
     ▼
  frames table  ← short statements + metadata (author, source, frame_type)
     │
     │  (2) embedding + topic modeling (BERTopic / similar)
     ▼
  topics table  ← cluster id → human-readable label
     │
     │  (3) semantic edge construction — cosine over embeddings, threshold + top-k
     ▼
  edges table   ← source_frame, target_frame, weight
     │
     │  (4) export script bundles into JSON
     ▼
  graph_data.json  (single artifact, ~few MB gzipped)
     │
     │  (5) static frontend reads the JSON and renders
     ▼
  index.html  ← single-file SPA, no build step
```

**Single static artifact + single HTML file** is the headline choice.
No backend, no build pipeline, deploys via `vercel --prod`. The full
pipeline runs offline; the website is "just" a browser for the JSON.

---

## 3. Data shape

`graph_data.json` is the contract. Keep it tight:

```jsonc
{
  "frames":  [{ "id", "label", "frame_type", "topic_id", "se_site",
                "author_username", "body_md", "evidence_quotes": [...] }, ...],
  "topics":  [{ "topic_id", "label", "size", "top_frame_ids": [...] }, ...],
  "edges":   [{ "source", "target", "weight" }, ...]   // semantic, undirected
}
```

Conventions:

- **Stable ids.** Frame ids must be deterministic (hash of body or a
  source primary key) so URLs survive re-runs.
- **Topic id `-1`** by convention is BERTopic's outlier bucket. Don't
  filter it out silently — it's often the largest "topic" and surfaces
  important leftovers; just label it `Other / unclustered`.
- **Edges are pre-thresholded.** Don't ship cosine similarities of
  every pair — at 4k frames that's 16M edges. Threshold (e.g. > 0.45)
  and top-k per node (e.g. 8) before exporting. The site needs to
  render edges in real time; full graph is not viable.
- **`label` is short.** The all-frames canvas can't render long titles;
  keep the canonical label ≤ 80 chars and let `body_md` carry the rest.

---

## 4. Frontend architecture (single-file SPA)

`index.html` is the whole app — CSS, HTML scaffold, and JS in one file.
Everything is plain DOM + d3 v7 from a CDN. No bundler, no framework.

### Why single-file
- Zero build step; `vercel --prod` deploys instantly.
- Easy to hand to a collaborator: "open it in a browser."
- All modifications happen in one place; no module-graph reasoning.
- ~5k lines is fine. Past ~8k, split.

### Section layout inside `index.html`
The file is sectioned with numbered comments. Keep this convention if
you fork; it's the cheapest table of contents we have.

```
1.   Constants + global state
2.   Data loading + caching (fetch + parse)
3.   buildIndices(data)         ← O(n) precompute lookups
4.   render() dispatcher
5.   renderChrome (topbar/breadcrumb/legend/filters)
6.   renderLevel1            (topic overview SVG)
6b.  renderLevel1ForceGraph  (canvas force-directed all-frames map)
7.   renderLevel2            (single topic)
8.   renderLevel3            (single frame, reading view)
9.   Search
10.  Filters (frame_type, site, time)
11.  Chrome rendering helpers
12.  Utilities
13.  drawAllFramesCanvas     (the canvas force-graph engine itself)
14.  Boot
```

### State model
A single `state` object, mutated in place, plus `render()` reads it and
re-renders. No reactive framework; plain `if (state.level === 2) ...`.
URL hash mirrors `state` (`#/topic/12/frame/abc`) so back/forward and
deep links work.

### Index precompute (`buildIndices`)
On data load, build:
- `frameById: Map`
- `topicById: Map`
- `framesByTopic: Map<topicId, Frame[]>`
- `edgesByTopic: Map<topicId, Edge[]>` — only intra-topic edges
- `semanticEdgesByFrame: Map<frameId, Edge[]>` — for L3 hop list
- `adjacencyByTopic: Map<topicId, Map<frameId, Set<neighborId>>>` —
  for sub-topic clustering at L2

This is the biggest perf trick. Once built (ms), every render is a
lookup, never a scan.

---

## 5. The force-graph engine — three layouts

This is the part with the most landmines. We support three layouts at
L1 (chosen via the advanced menu), and a localized force-graph at L2:

### 5a. Spiral (default)
Each topic gets one anchor on a phyllotaxis spiral
(`r = R_STEP * sqrt(i+1)`, `angle = i * 137.5°`, sorted by descending
member count). Each frame is pulled toward its topic's anchor with
`forceX/Y`. **No ring** — clusters interleave because consecutive sizes
are never adjacent on the spiral.

**Why this beats a ring**: a ring sorted by topic id puts the four
biggest BERTopic clusters next to each other → mega-blob on one side,
empty middle. The spiral gives even canvas usage for free.

### 5b. Semantic
Run a *mini* simulation on just the 39 topic anchors, using
inter-topic edge weights as link strengths. After ~250 ticks, freeze
those positions and use them as anchors for the main 3.9k-node sim.
Result: topics that frequently link sit close on the canvas.

Cost: ~50ms one-time. Worth it.

### 5c. Natural / Pure edge physics
**No anchors.** Just `forceLink` + `forceManyBody` + collide + center.
Clusters emerge because intra-topic edges are denser than inter-topic
ones.

The tuning that actually works (after several iterations):

```js
.force("link", d3.forceLink(links).distance(10).strength(0.7))
.force("charge", d3.forceManyBody().strength(-9).distanceMax(120))
.force("center", d3.forceCenter(cx, cy))
.velocityDecay(0.6)
.alphaDecay(0.022)
```

The non-obvious lever was `distanceMax(120)` on the charge force.
Without it, every node weakly pushes every other node across the whole
canvas → the graph just expands until it hits the edges, no visible
clusters. Capping the repulsion radius makes it a *local* force; nodes
only push their immediate neighbors apart, so cohesion comes from the
links and the clusters separate visibly.

After the simulation settles in natural mode, we draw rounded-pill
labels at the centroids of the top-3 largest topics so the user has
something to read against the emergent geography.

### 5d. L2 sub-topic localized force graph
Same engine, restricted to one topic's frames + intra-topic edges.
Used to spot sub-clusters within a single topic.

---

## 6. Critical pitfalls — bugs we already paid for

These cost real time. If you're forking this codebase, read them.

### 6a. `forceCollide.strength()` coerces with `+value`
d3-force v7's collide does `strength = +value`. If you pass a function
(`collide.strength(d => 0.5 + ticks/80)`), `+function` is `NaN`, and
the simulation silently produces `NaN` positions, which renders as a
blank canvas with no errors. **Always pass a number.** If you want
ramped strength, update it from inside `simulation.on("tick", ...)` by
calling `collide.strength(numericValue)`.

### 6b. Canvas vs SVG at 4k nodes
SVG at ~4k nodes is fine for static, painful when interactive (hover
re-flows, zoom slows). We use Canvas + a quadtree-backed hit test for
the all-frames map. SVG is fine for L1 topic overview (39 cards) and
L2/L3 panels.

### 6c. Reload-thrash on back-navigation
Every time the user came back to L1, we rebuilt the simulation from
scratch — the layout would visibly relax again, and the eye-anchor the
user had memorized was gone. Fix: cache positions keyed by
`(layout, frames.length, first-8 frame ids joined)`. On re-render,
seed nodes from the cache; if the simulation didn't really change,
positions are pixel-identical.

Module-level handles for cleanup:
```js
let _allFramesTeardown = null;        // L1 canvas
let _topicCanvasTeardown = null;      // L2 canvas
let _forceGraphPositionCache = null;  // { key, positions: Map }
```

### 6d. Tab title leaking page state
`document.title = frame.label` everywhere meant the chrome tab said
"If the motor bearings can suppor…" — terrible for tab-switching and
bookmarks. **Pin the tab title to the site name; let the breadcrumb
carry the page state.**

### 6e. Breadcrumb + search bar collision
At L3 the breadcrumb is `← / TopicLabel / FrameLabel`. With long
strings + a search bar to the right, both crumbs would crash into
the search. Three-part fix: cap the L3 frame label at 28 chars,
`max-width: min(28vw, 280px)` on `.crumb.current`, and a separate
`max-width: min(22vw, 240px)` on the L3 topic crumb (it's a button,
not `.current`, so it needs its own rule).

### 6f. d3 drag conflicts with d3 zoom
If you wire `d3.drag()` onto the same canvas that already has
`d3.zoom()`, drag never fires — zoom captures the pointer. Use
`drag.filter(event => event.button === 0 && event.shiftKey)` or
mount drag-with-pick on a different event phase. We currently ship
the drag toggle as a no-op; revisit if needed.

### 6g. Topic-1 (the BERTopic outlier bucket)
It's almost always the largest. Don't render it bigger or hide it —
both hide the structure. Just let it pack and label it explicitly.

### 6h. Vercel cleanUrls + `index.html`
With `cleanUrls: true`, request `/` and Vercel serves `index.html`.
Make sure the `Cache-Control` header on `index.html` is
`max-age=0, must-revalidate` so users actually pick up your deploys.
Cache the JSON data with `max-age=3600` separately.

---

## 7. Decisions log (with the alternative)

| Decision | What we chose | What we rejected | Why |
| --- | --- | --- | --- |
| Build tool | None — single HTML file | Vite/Next | Zero build, infinite collaborator-portability |
| Framework | None, plain DOM + d3 | React/Svelte | At 5k LOC, framework overhead > savings |
| Render | Canvas at L1, SVG/DOM at L2/L3 | All-SVG | Canvas hits 60fps at 4k nodes, SVG doesn't |
| Layout default | Phyllotaxis spiral anchors | Ring sort by id | Big clusters interleave instead of bleeding into one mega-blob |
| Cluster algo | BERTopic | Pre-defined taxonomy | Emergent, no a-priori curation |
| Outlier bucket | Show as topic `-1` "Other" | Hide | Often largest; hiding warps the picture |
| State | Single mutable object + URL hash | Redux/Zustand | One developer, in-file scope is fine |
| Edges | Pre-thresholded + top-k per node | Ship full cosine matrix | 16M edges → unusable |
| Tab title | Static "DFM Graph Explorer" | Per-page | Bookmarks, tab-switching legibility |
| Position cache | Filter-fingerprint keyed | Always recompute | Layout should feel "still there" on back-nav |
| Deploy | Vercel `--prod`, zero config | S3/Pages | Cleanest UX for previews + custom domain |

---

## 8. Tooling

| Tool | Used for | Notes |
| --- | --- | --- |
| Python (offline) | Pipeline: extraction, embedding, BERTopic, edge build, JSON export | One-off scripts; results checked into repo |
| BERTopic | Topic modeling | Set `min_topic_size` to corpus size / 50 as a starting point |
| sentence-transformers | Embeddings | `all-mpnet-base-v2` is a solid default |
| d3 v7 (CDN) | Force simulation, drag, zoom, scales | Pin a version; don't `@latest` |
| HTML Canvas 2D | All-frames render | `getContext("2d")` + manual transform |
| Vercel | Hosting | `vercel.json` with `cleanUrls` + headers |
| GitHub | Source | Plus a `data/` directory with the JSON |
| Claude Code | All in-editor work | See `delegation` notes below |
| Codex (codex-rescue subagent) | Bulk refactors > 200 lines, diagnostic second-passes | Hand off with a written spec, not a chat-style prompt |

### Codex delegation triggers
From `CLAUDE-delegation.md`: any task ≥ 75 LOC, ≥ 500 words, new file
from scratch, or 5+ file edits. The force-graph rework (3 layouts,
position cache, tab title, drag toggle) crossed that line; we wrote a
detailed spec → Codex generated → Claude verified each section with
`Read` before deploying.

---

## 9. Performance budget

These are the numbers that have to hold for the UX to feel right:

| Metric | Target | Where it bites |
| --- | --- | --- |
| L1 first paint | < 800ms after data load | User opens app |
| L1 sim settle | < 4s for 4k nodes | First impression |
| Hover hit-test | < 8ms | Tooltip latency |
| L1 → L2 transition | < 200ms | Click feedback |
| L2 → L3 transition | < 200ms | Click feedback |
| `graph_data.json` size | < 4 MB gzipped | First load on slow connection |

If any of these slips, profile before adding features. The position
cache exists because the L1 → L2 → L1 round trip used to feel like
a 3-second reload.

---

## 10. Reusing this for a new topic / corpus

Step-by-step to spin up a sibling explorer:

1. **Decide your "frame".** What is the atomic readable unit? A
   sentence? A claim? A paragraph? The whole pipeline keys off this.
   For DFM it's "design-for-manufacturing principles, heuristics,
   risks, examples" — short imperative-mood statements.
2. **Define `frame_type` enum.** 3–6 categories. They drive color
   coding and filter pills. Keep it tight; people can't track 12 colors.
3. **Run the pipeline:**
   - Extract frames from the corpus (LLM with a strict schema; cache
     intermediates per source doc).
   - Embed (mpnet or your favorite).
   - BERTopic on the embeddings.
   - Build cosine edges, threshold, top-k.
   - Export `graph_data.json`.
4. **Sanity check the JSON before touching the frontend:**
   - Counts: frames vs topics vs edges.
   - Distribution of `frame_type`.
   - Topic size histogram (if 90% of frames are in one topic, raise
     `min_topic_size` and re-run).
   - Edge density per node (median should be 4–10).
5. **Fork `index.html`.** Search-replace the title, the favicon SVG
   colors (3 nodes — pick palette colors that map to your `frame_type`
   palette), and the legend copy.
6. **Tune the colors.** Edit the CSS variables block at the top.
   Don't scatter hex codes through the file.
7. **Boot it locally:** `python -m http.server 8000` → open
   `localhost:8000`. **Don't** use `file://` — it blocks `fetch()`.
8. **Tune the natural-layout simulation.** Different corpora need
   different parameters. Start from the values in §5c. If clusters
   don't separate, lower `link.distance` and raise `link.strength`. If
   one cluster is a black hole sucking everything in, raise
   `charge.strength` (less negative) and lower `distanceMax`.
9. **Deploy:** `vercel --prod`.
10. **First-30-min QA:**
    - Tab title stays static across L1/L2/L3 navigation.
    - Favicon shows in the tab.
    - Back/forward through breadcrumb works; URL hash updates.
    - Force-graph toggle off → keyboard-accessible topic overview.
    - Search works at every level.
    - All three layouts render without NaN nodes.
    - L2 force-graph for at least 3 topics.
    - Mobile: topbar wraps, breadcrumb wraps.

---

## 11. Things we did **not** do (and might want to)

Listed so the next iteration doesn't re-invent the question.

- **Server-side data tier.** Everything's static. If the corpus grows
  past ~10k frames, consider tiling the all-frames view (load only
  visible cluster's frames at L1).
- **Authoring / edit-in-place.** Read-only by design. If you want
  curation workflows, build a separate tool that re-emits the JSON.
- **Real keyboard navigation in canvas mode.** ARIA fallback exists
  (toggle the force graph off → SVG topic overview is keyboard-
  navigable), but canvas itself isn't. This is the biggest open
  accessibility debt.
- **Multi-user "shared cursor" / annotations.** Out of scope; would
  require a backend.
- **Time slider.** Filter pills handle frame_type and site; we have
  date filters in code but no slider. If your corpus has strong
  temporal structure, build one.
- **Drag enabled by default.** Toggle ships off because of the d3
  drag/zoom conflict (§6f). Worth fixing properly later.

---

## 12. File map (this repo)

```
dfm-graph-explorer/
├── index.html              ← the entire frontend (~4.9k lines)
├── PLAYBOOK.md             ← this file
├── README.md               ← short user-facing intro
├── PLAN.md                 ← in-flight task list (working doc)
├── vercel.json             ← deploy config
├── graph_data.json         ← (or in data/) — the bundled artifact
├── data/                   ← split JSON or per-topic files if you tile
├── export_graph.py         ← pipeline → JSON
├── split_graph_data.py     ← (optional) tile the JSON for big corpora
├── _delegate_*.py          ← internal helpers
└── reference/              ← design notes, screenshots, source PDFs
```

---

## 13. Working agreements (operator → AI assistant)

For Claude/Codex collaborators on this codebase:

- **`index.html` is hand-edited.** Don't regenerate it from a template;
  always `Edit` specific blocks.
- **Visual changes ship with a screenshot.** Render the page after
  any CSS positioning change. Code review alone misses overlap.
- **Verify Codex's diff before deploying.** Read every changed range
  with `Read` after a hand-off.
- **Deploy command:** `vercel --prod --yes` from the project root.
- **Don't print API keys / tokens.** Vercel auth is in env; pass it
  through, never echo.
- **Out-of-scope ideas → mention in chat, don't fix.** This codebase
  has had too many unsolicited refactors and they erase the prior
  visual tuning.
