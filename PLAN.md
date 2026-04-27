# Plan — DFM Graph Explorer

## 0. TL;DR

Fork the atlas-gui prototype (dark-theme, three-level D3 graph explorer, single HTML file), rewrite the data pipeline to read from Douglas's DFM knowledge graph instead of the design-engineering atlas, and adapt the node/edge schema, UI chrome, and scale-handling for a 7,864-node graph (vs atlas-gui's 228). Deploy static to Vercel as `dfm-graph-explorer.vercel.app`.

Four "hard" decisions, resolved below:

| # | Question | Answer |
|---|---|---|
| 1 | How to handle 35× more nodes than atlas-gui? | Topic-level Level 1 (39 topics), frame-level on drill-down, canvas if SVG chugs, pre-computed Gephi positions as a starting layout |
| 2 | Single-file D3 or Vite+React? | Single-file first (atlas-gui pattern), migrate to Vite+React if three-level state management bites |
| 3 | Color scheme? | Keep atlas-gui's 4 semantic colors but reassigned to frame-type (8 colors) OR frame-category (4 colors, grouped). Add one orange UI accent per `BUILD_PLAN_V2.md` for chrome |
| 4 | Where does data come from? | `provenance_graph.gpickle` (networkx) + `semantic_edges.json`. Optional live Neo4j for dev. Gephi's `.gexf` only if we want pre-computed positions |

---

## 1. Goal & scope

### In scope (v1)
- **Graph explorer** — a dark-theme, force-directed graph of the DFM knowledge graph, with three levels: Field / Node / Deep-Dive, same pattern as atlas-gui
- **Source-quote preview** — every frame has a `source_quote` field. Hovering a connection should reveal the verbatim forum-post snippet (NotebookLM-style)
- **Credibility surfacing** — each post has an author reputation tier. Low-credibility frames should be visually distinguished or filterable
- **SE-site filter** — posts come from 5 Stack Exchange sites (engineering, electronics, robotics, mechanics, woodworking). Filter pill per site
- **Temporal mode** — atlas-gui has this; we should keep it (posts have created_at dates)
- **Static deploy** — zero backend at runtime. All data pre-exported to one JSON

### Out of scope (v1 — do NOT build)
- RAG agent UI (that lives in `dfm-kg-agent.streamlit.app` — keep it there for now)
- Authoring / edit UI
- Neo4j live-query from the browser
- Embedding-space view (UMAP/t-SNE projection from Qdrant vectors) — v2 candidate, noted in §8
- Mobile layout — atlas-gui skips it, we do too for v1
- The four analysis modes from the Streamlit app — those belong to `BUILD_PLAN_V2.md`, not here

### Success criteria

- [ ] User can open `index.html` (or the Vercel URL) and see a legible overview of the graph
- [ ] User can click any node and get a panel with description, neighbors sorted by edge weight, and source-quote expansion
- [ ] User can search any frame/post/author/topic and jump to it
- [ ] Graph is playable — force sim stable on load, pan/zoom, drag-draggable nodes
- [ ] Page loads in <3 sec on a cold visit (CDN D3, pre-compressed JSON)
- [ ] Deployed at a stable `.vercel.app` URL

---

## 2. The reference site (atlas-gui)

Full source is cloned at `reference/atlas-gui/`. Five files:

| File | What it is | Use it for |
|---|---|---|
| `preview.html` | 1,481-line single-file D3 app. CSS + HTML + JS inline | Copy wholesale as the starting point for our `index.html` |
| `graph_data.json` | 2.4MB exported graph — their 228 nodes, 1,959 edges | Reference for the JSON schema we need to match (or consciously diverge from) |
| `export_graph.py` | 11KB Python script. Reads SQLite → writes `graph_data.json` | Adapt the patterns; rewrite to read from our `.gpickle` / Neo4j |
| `PRD.md` | 15KB. Their product requirements doc (three-level architecture spec) | The spec we're adapting — read in full before building |
| `README.md` | 1KB. Short — just the data contract | Skim |

### What atlas-gui does well, keep
- **Three-level IA** (Field → Node Orientation → Node Deep Dive)
- **Hard-filter on click** — non-neighbor nodes *disappear*, not dim. Makes the ego network readable
- **Accordion edge-papers** — each connection expands to reveal the papers evidencing it. Maps 1:1 to our "papers" → "source_quotes/posts"
- **CSS-variable color system** — four node colors driven by `--subject / --task / --problem / --construct`. Easy to re-theme
- **Dark grid layout** — 52px topbar + main flex row with (graph-area | deep-dive | detail-panel)
- **Zoom/pan via d3.zoom on SVG root `<g>`** — clean, standard
- **File:// fallback** — works when opened locally without a server
- **Temporal mode** — year slider, filters nodes by `first_year ≤ year` and edges by year. Maps 1:1 to our post dates

### What atlas-gui misses for our use case
1. **Scale.** At 7,864 nodes, force sim + SVG will chug. Need canvas rendering or node clustering.
2. **Node-type taxonomy.** Their 4 types (subject/task/problem/construct) don't match our structural types (Frame/Post/Author/Thread) or our semantic subtypes (8 frame types + 39 topics + 3,292 subject clusters).
3. **Source-quote preview.** Their "papers" are citations; ours are verbatim forum snippets. The UI should show the quote inline, not just the title.
4. **Credibility/provenance.** Our authors have reputation tiers. Atlas-gui has none.
5. **Structural + semantic edges coexist.** Atlas-gui has one edge type. We have 2 edge buckets: structural (Frame→Post, Post→Thread, Post→Author) and semantic (SPECIFIES, MITIGATES, CAUSAL_LINK, CONTRADICTS). Need to either collapse or visually separate.

See §8 for what we add on top.

---

## 3. The data — where it lives, what's in it

**Full field-by-field details:** `reference/USER_KG_POINTERS.md`

### Key numbers (from `dfm_scraping/CLAUDE.md`)

| | Count |
|---|---|
| Frames extracted | 3,879 |
| Posts | 1,936 |
| Authors | 1,138 |
| Threads | 911 |
| Graph nodes (total) | 7,864 |
| Structural edges | 8,776 |
| Semantic edges | 4,272 (SPECIFIES 2,111 + MITIGATES 1,206 + CAUSAL_LINK 625 + CONTRADICTS 330) |
| Subject clusters | 3,292 |
| Topics (BERTopic) | 39 topics + 619 outliers |
| Embedding vectors | 11,637 (3,879 × 3 collections in Qdrant) |

### Source options (pick one primary)

| Source | Format | Notes |
|---|---|---|
| `Documents/dfm_scraping/provenance_graph.gpickle` | networkx pickle | **Primary.** Directly loadable in Python. Rebuilt by `build_graph.py` |
| `Documents/dfm_scraping/semantic_edges.json` | JSON | Load alongside the gpickle for semantic edges |
| Neo4j Aura (`neo4j+s://e9cb6c7f.databases.neo4j.io`) | Cypher | Live. Credentials in `dfm_scraping/Neo4j-e9cb6c7f-Created-2026-02-19.txt`. Good for dev-time queries, don't hit it at page load |
| `Documents/dfm_scraping/Clusters_Att_2.gexf` | Gephi XML (8.8MB) | Has **pre-computed 2D positions** from Gephi ForceAtlas2. Could seed our D3 layout. Read-only |
| Qdrant vector DB | binary | 11,637 vectors × 3 collections. Source of truth for embedding view (v2) |

**Recommendation:** write `export_graph.py` that reads the gpickle + semantic_edges.json → emits `graph_data.json`. If we want pre-seeded positions for the initial layout (avoids an awkward settling animation on 7,864 nodes), also parse the GEXF's `<viz:position>` tags.

---

## 4. Schema mapping — atlas-gui → DFM

Our schema is richer. We need to collapse, filter, or selectively expose fields.

### Atlas-gui node shape → our node shape

```jsonc
// ATLAS-GUI
{
  "id": "node_id",
  "label": "Analogical Reasoning",
  "type": "subject|task|problem|construct",
  "description": "text",
  "paper_count": 14,
  "first_year": 1995,
  "papers": [ {title, authors, year, doi} ]
}

// OURS — option A: Frame as primary node
{
  "id": "frame_xxx",
  "label": "first-line summary of main_point",
  "type": "risk|heuristic|principle|case|workaround|observation|comparison|other",
  "description": "main_point (full)",
  "source_quote": "verbatim forum snippet",
  "subject": "normalized subject cluster name",
  "topic": "BERTopic-labeled topic",
  "scope": "ScopeDomain value",
  "applicability": "universal|contextual|...",
  "epistemic_stance": "...",
  "post_count": 1,  // frames are atomic; always 1 post backs them
  "first_year": 2015,  // from parent post
  "credibility_tier": "high|medium|low",
  "se_site": "engineering|electronics|robotics|mechanics|woodworking",
  "post": { url, thread_title, author_username, reputation, created_at, post_score }
}
```

### Atlas-gui edge shape → our edge shape

```jsonc
// ATLAS-GUI
{
  "source": "id_a", "target": "id_b",
  "type": "subject_task|task_construct|...",
  "weight": 8,
  "years": [1998, 2003],
  "papers": [...]
}

// OURS — semantic edges only (structural edges are implicit: frame-in-post-by-author-in-thread)
{
  "source": "frame_xxx", "target": "frame_yyy",
  "type": "SPECIFIES|MITIGATES|CAUSAL_LINK|CONTRADICTS",
  "confidence": "high|medium|low",
  "weight": 1  // each semantic edge asserts one specific relationship
}
```

### Decision: level-1 node is Topic, not Frame

**Problem:** 3,879 frames rendered as a force graph = unreadable hairball. Even with aggressive filters, hovering over cluster centers gives nothing useful.

**Solution:** Level 1 shows 39 **topic-level supernodes** (from BERTopic output `topic_model_output.json`). Each topic has:
- A BERTopic-assigned label (LLM-labeled via gpt-4.1-mini per `CLAUDE.md`)
- A frame_type distribution (pie/dots on the node)
- A frame_count

Click a topic → Level 2 shows the topic's frames (usually 50-200, still readable). Click a frame → Level 3 opens a reading view with the full source_quote, thread context, connected frames via semantic edges.

**Alt option if 39 topics feels too coarse:** show top-N subject clusters (from `normalize_subjects.py`, `subject_clusters.json`). Pick N such that the graph stays readable (~150-300 nodes). Subject clusters are finer-grained than topics.

**Pick one and commit.** Starting with topics (39) is simpler. Escalate to subject clusters if topic-level feels too abstract when testing.

---

## 5. Scale problem — 7,864 nodes is a lot

### Why this matters

Atlas-gui runs fine at 228 nodes with SVG + d3-force. Benchmarks from the community:
- **SVG + d3-force** starts chugging around 1,000-2,000 visible elements
- **Canvas + d3-force** holds up to 10,000-20,000 nodes with careful tick throttling
- **WebGL/regl/Cosmograph** scales to 100k+, but is overkill and complicates the single-file deploy

### Our strategy

**Phase 1 (Level 1): always show summary nodes, not frames.**
Only 39 topic supernodes visible. SVG is fine. Same tech as atlas-gui's preview.html.

**Phase 2 (Level 2): topic drill-in.**
On topic click, hard-filter to that topic's frames (usually 50-200). Still SVG, still d3-force.

**Phase 3 (Level 3): single-node deep-dive.**
Only one frame + its ego network. ~5-20 nodes. Trivial.

So: **we never render 7,864 nodes simultaneously in v1.** Scale is handled by the hierarchy, not by the renderer.

### Seed positions from Gephi

The `Clusters_Att_2.gexf` has 2D positions computed by Gephi's ForceAtlas2 layout. If we want Level 1 to appear pre-laid-out (no awkward settling), parse `<viz:position>` for the topic-level nodes and seed `fx`/`fy` or initial `x`/`y` in d3-force. Let d3-force run a few ticks to stabilize, then release.

### Performance backstop

If we do want a "see all frames" view later (v2), swap `<svg>` for `<canvas>` and use `d3.forceSimulation` with a custom `tick` that draws paths on canvas. No SVG elements. Handles 10k nodes at 60fps. Reference: `ai-industry-map-explorer/src/ClusterMap.tsx` already does a similar HTML-layer + SVG-layer hybrid.

---

## 6. Tech stack decision

**Start:** atlas-gui's pattern exactly — single `index.html` with CSS + HTML + JS inline, D3 v7 from cdnjs, data from `./graph_data.json`.

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
  // your code
</script>
```

**Migrate to Vite+React ONLY when:**
- Three-level state management becomes unreadable in vanilla JS (plausible around 800+ lines)
- We want routing (v2: a separate `/embed` page for the embedding view)
- We want shared components (we don't yet)

Vite+React stack is already proven in `ai-industry-map-explorer/` — copy its `package.json` and `vite.config.ts` verbatim when we migrate. But **don't migrate prematurely.** The atlas-gui reference at 1,481 lines is already showing the single-file approach scales further than you'd think.

---

## 7. Aesthetic decisions

**Full distilled guidance:** `reference/PLAYBOOK_EXTRACTS.md`. Below: only what's locked in for this project.

### Temperature: dark technical product (not editorial essay)

Tool, not a read. Matches the reference site. Matches CAD users' habitat. Matches `ai-industry-map-explorer`, which is the closest stack analog from Douglas's portfolio.

### Color tokens (start here — override if needed)

Keep atlas-gui's semantic colors for nodes. They're already well-chosen:

```css
:root {
  --bg: #0a0a0b;            /* near-black, slightly warm, per BUILD_PLAN_V2 */
  --surface: #131316;
  --surface-2: #1c1c20;
  --stroke: #2a2d36;         /* hairlines */
  --text: #eceff4;
  --muted: #aab0bd;

  /* Node colors — assigned by primary grouping.
     If topics on level 1: pick 8 hues. If frame_type on level 2: use these 8. */
  --risk:         #f87171;   /* red */
  --heuristic:    #60a5fa;   /* blue */
  --principle:    #a78bfa;   /* purple */
  --case:         #fbbf24;   /* amber */
  --workaround:   #34d399;   /* green */
  --observation:  #94a3b8;   /* gray */
  --comparison:   #f472b6;   /* pink */
  --other:        #c084fc;   /* lavender */

  /* One accent for UI chrome. Orange per BUILD_PLAN_V2. Not indigo. */
  --accent: #ff6b3d;
  --accent-soft: rgba(255, 107, 61, 0.15);
}
```

### Type

One sans + one mono. Atlas-gui uses Arial (lazy). We do better:

```css
--font-sans: "Inter Tight", "Inter", system-ui, sans-serif;
--font-mono: "JetBrains Mono", "IBM Plex Mono", ui-monospace, Menlo, monospace;
```

Mono for: breadcrumb text, frame_type labels on nodes, temporal year label, status chips. Everything else sans.

For the deep-dive reading view (Level 3), switch to **serif for the source_quote**:
```css
--font-serif: "Source Serif 4", Charter, Georgia, serif;
```
Editorial touch only where the user is actually reading prose. Same pattern as `idetc-paper-site`.

### Anti-checklist (do NOT do)

Taken from `explainer_site_playbook.md`, `BUILD_PLAN_V2.md`, and practitioner sources referenced there:

- No aurora/mesh gradients
- No glowing radial blobs behind anything
- No `bg-clip-text` on headings
- No `rounded-2xl` on any element (cap at 10px radius)
- No Lucide icons untouched — custom SVG glyphs or skip icons entirely
- No uniform 300ms animation on everything — motion only for spatial changes
- No indigo-500 / purple gradient accent (the #1 AI-slop giveaway in 2026)
- No cool slate/zinc grays — warm darks only
- No flat `rgba(0,0,0,0.1)` shadow-md on every card
- No `#FF4B4B` Streamlit red. No centered-730px reading column for tool chrome.

### Yes-do

- Grain overlay at 3-5% (one-line upgrade, hides flat flatness)
- Hairlines (rgba 8-12% alpha) between panels, never boxed cards
- Single accent color used on <5% of pixels (the `--accent` orange)
- Varied spacing per section, never uniform
- `prefers-reduced-motion` honored
- Pre-computed graph positions (no awkward settle on load)
- Typewriter/mono for all numerals, section markers, meta
- Source-quote reading view uses serif + 65ch max-width + `text-wrap: pretty`

---

## 8. What to ADD beyond atlas-gui

Value-add features Douglas has data for, atlas-gui doesn't. Prioritized.

### 8.1 Source-quote hover preview (P0 — must have)

Every frame has a `source_quote` (verbatim forum snippet, enforced by Pydantic schema in `schema_se.py`). When the user hovers a connection (edge) or a frame in the Level 2 connections list, show the quote inline with:
- The quote text (italic serif)
- Author username + credibility tier dot
- Thread title (linked)
- Year

Reference pattern: NotebookLM's scroll-to-quote, Perplexity's favicon + title + freshness chips (cited in `BUILD_PLAN_V2.md §2`).

### 8.2 Credibility surfacing (P1)

Each post has an author `reputation` number → `credibility_tier` (high/medium/low, computed upstream). Visual treatment options:
- **Filter pill** in topbar: "Min. credibility: [all / medium+ / high]"
- **Dot on the connection row** next to author name — opacity or size by tier
- **Badge in detail panel** — "High-credibility source (rep 12,400)"

Pick one. Start with the filter pill — matches atlas-gui's existing pill vocabulary.

### 8.3 SE-site filter (P1)

5 source sites: engineering / electronics / robotics / mechanics / woodworking. One pill per site, toggleable. Pattern: atlas-gui's existing type-filter pill pattern. Just relabel and recolor.

### 8.4 Structural vs semantic edge toggle (P2)

Our graph has two edge buckets. In Level 1/2, default to semantic only (4,272 edges) — they're the interesting relationships. Toggle: "Show structural edges (frame→post→author→thread)" — for anyone wanting to see provenance chains.

### 8.5 Embedding projection view (P3 — v2 candidate)

Second route (`/embed` or toggle in topbar): 2D UMAP or t-SNE of the 3,879 frame embeddings. Each point colored by frame_type. Hover: frame preview. Click: jumps back into the graph view at that frame.

Requires a one-time offline computation:
```python
# dim reduction of Qdrant vectors → positions.json
import umap
vectors = load_qdrant_vectors("frame_embeddings")
positions = umap.UMAP(n_neighbors=15, min_dist=0.1).fit_transform(vectors)
# save as { frame_id: [x, y] } → positions.json
```

Defer to v2 unless P0/P1 goes fast.

### 8.6 Quote-search (P3)

Full-text search over `source_quote` fields, not just labels. Opens a results list with highlighted matches. Requires client-side flexsearch or lunr — adds ~30KB to the bundle. Worth it only after v1 lands.

---

## 9. Physics & performance

### Force simulation parameters (start with atlas-gui's, tune)

```js
const sim = d3.forceSimulation(nodes)
  .force("charge", d3.forceManyBody().strength(-300))
  .force("link", d3.forceLink(edges).id(d => d.id).distance(d => 50 + 200/(d.weight || 1)))
  .force("center", d3.forceCenter(width/2, height/2))
  .force("collision", d3.forceCollide().radius(d => d.r + 4));
```

### Scale-dependent tuning

- **Level 1 (39 topic nodes):** stronger charge (-600), longer link distance. Spacious.
- **Level 2 (50-200 frame nodes):** standard charge (-300). Standard.
- **Level 3 (ego network, 5-20 nodes):** weak charge (-150), short links. Compact.

### Seeding from Gephi positions (optional, polish)

Parse `Clusters_Att_2.gexf` once offline, extract top-level topic positions, emit `positions.json`. On load:

```js
nodes.forEach(n => {
  const seed = positions[n.id];
  if (seed) { n.x = seed.x * SCALE; n.y = seed.y * SCALE; }
});
sim.alphaTarget(0.3).alpha(0.3);  // light settle
setTimeout(() => sim.alphaTarget(0), 1500);  // fix in place
```

### When to switch to canvas

Only if a v2 "show all frames" view is built. For v1 with hierarchical reveal, SVG is fine.

---

## 10. Phase-by-phase build

Each phase is a few hours. Ship after each.

### Phase 1 — Clone and strip (30 min)
1. `cp reference/atlas-gui/preview.html ./index.html`
2. Strip atlas-gui-specific labels ("Design Engineering Atlas" breadcrumb, etc.)
3. Delete their `graph_data.json` ref; expect our own later
4. Verify it still loads (empty graph, no data) — smoke test the chrome only

### Phase 2 — Data export (2-3 hours)
1. Create `export_graph.py` in this folder:
   ```python
   import pickle, json
   import networkx as nx
   from pathlib import Path

   DFM = Path(r"C:\Users\dougl\Documents\dfm_scraping")
   G = pickle.load(open(DFM / "provenance_graph.gpickle", "rb"))
   semantic_edges = json.load(open(DFM / "semantic_edges.json"))
   topics = json.load(open(DFM / "topic_model_output.json"))
   # ... assemble graph_data.json matching schema in §4
   ```
2. Output schema per §4. Write to `./graph_data.json`.
3. Validate: open in index.html — should render as a pile of unconnected dots (expected — force hasn't run yet)

### Phase 3 — Topic-level Level 1 (2-3 hours)
1. Make the 39 topic supernodes render
2. Aggregate topic → sum of frame counts for node size
3. Aggregate semantic edges by topic pair for Level 1 edges (weight = count of frame-to-frame edges crossing the topic boundary)
4. Wire filter pills (frame_type), search, weight slider
5. Acceptance: graph loads in <2s, pan/zoom smooth, search finds topics

### Phase 4 — Level 2 drill-in (3-4 hours)
1. Click topic → hard-filter to frames within that topic (atlas-gui's hard-filter pattern, unchanged)
2. Right-side detail panel: topic description, connected topics, frame list
3. Acceptance: topic → frames transition smooth, panel matches atlas-gui layout

### Phase 5 — Level 3 deep-dive (3-4 hours)
1. Click frame in panel → Explore → button → 1/3 + 2/3 split
2. Left: ego network (frame + neighbors via semantic edges, interactive)
3. Right: reading view
   - Frame label
   - Frame type badge
   - Full `source_quote` (serif, blockquote styling)
   - Author + reputation + thread + SE site (meta row)
   - Connected frames grouped by semantic edge type (SPECIFIES / MITIGATES / etc.), each expandable to show that connection's evidence
4. Acceptance: reads like Wikipedia. Source quote is the hero.

### Phase 6 — SE-site filter + credibility filter + temporal mode (2 hours)
1. Add topbar pills for SE sites
2. Add credibility threshold dropdown
3. Keep atlas-gui's temporal mode, point it at post `created_at` instead of paper year
4. Acceptance: can isolate "high-credibility heuristics from engineering.stackexchange, last 3 years"

### Phase 7 — Deploy (30 min)
1. `vercel --prod --yes --name dfm-graph-explorer`
2. Update `dpm-sites/index.html` — new card 07 (after `ai-schools-of-thought-explorer`)
3. Update `vercel-sites.md` reference doc
4. Smoke test on mobile (expect broken — not scoped for v1, just confirm graceful degradation to a message)

### Phase 8 — Polish pass (4-6 hours)
1. Grain overlay
2. Type hierarchy review
3. Empty states (no search results, unfiltered-to-zero)
4. Loading state (actual meaningful progress, not a spinner)
5. Favicon (SVG data URI with some mark — maybe a stylized "dfm" mono glyph)
6. Meta tags for social sharing

### Phase 9+ — v2 features
In order of value: embedding view → quote-search → mobile layout → ???

---

## 11. File tree (to build)

```
dfm-graph-explorer/
├── README.md                    ← orientation (exists)
├── PLAN.md                      ← this file (exists)
├── index.html                   ← single-file app, fork of preview.html (Phase 1)
├── graph_data.json              ← output of export_graph.py (Phase 2)
├── positions.json               ← optional Gephi-seed positions (Phase 2)
├── export_graph.py              ← Python, reads .gpickle → writes graph_data.json (Phase 2)
├── favicon.svg                  ← SVG data URI (Phase 8)
├── styles/                      ← only if index.html grows past ~1500 lines; otherwise keep inline
│   └── (empty for now)
├── src/                         ← only if we migrate to Vite+React
│   └── (empty for now)
├── reference/
│   ├── atlas-gui/
│   │   ├── preview.html         ← THE reference (exists, 51KB)
│   │   ├── graph_data.json      ← schema reference (exists, 2.4MB)
│   │   ├── export_graph.py      ← pipeline reference (exists, 11KB)
│   │   ├── PRD.md               ← spec we're adapting (exists, 15KB)
│   │   └── README.md            ← exists
│   ├── USER_KG_POINTERS.md      ← where our data lives, field-by-field (exists)
│   └── PLAYBOOK_EXTRACTS.md     ← distilled playbook guidance (exists)
└── .vercel/                     ← created by first `vercel` run
```

---

## 12. Open questions (flag for user)

Only ask if you actually get stuck. Otherwise make the default and move on.

1. **Topic labels vs subject-cluster labels for Level 1?** BERTopic's LLM-labels can be uneven. If they look bad on inspection, fall back to top-N subject clusters. Decide after seeing `topic_model_output.json`.
2. **Include structural edges or semantic only?** Default: semantic only in v1 (cleaner graph). Add structural as a toggle in v2.
3. **Keep atlas-gui's exact color palette or introduce frame_type colors?** Default above is frame_type (8 colors). If rendering looks busy, collapse to 4 categories (Diagnostic = risk+observation+comparison, Prescriptive = heuristic+workaround, Explanatory = principle+case, Other).
4. **Where to host the live Neo4j for any optional live queries?** Already on Aura — free tier. No action needed for v1.

---

## 13. How to run the future session

Open Claude Code in this directory. Give it this prompt:

> Read `README.md`, then `PLAN.md`, then `reference/USER_KG_POINTERS.md`. Then start Phase 1 from `PLAN.md §10`. When you finish each phase, run the acceptance check listed, commit, and move to the next. Stop and ask if a decision from §12 becomes load-bearing.

That's it. This document is the contract.

---

## Appendix A — Links and reference

- **Atlas-gui live:** https://caseysimoneb.github.io/IDETC26-atlas-gui/preview.html
- **Atlas-gui repo:** https://github.com/caseysimoneb/IDETC26-atlas-gui
- **User's Streamlit app (current KG explorer):** https://dfm-kg-agent.streamlit.app/
- **User's DFM scraping folder:** `C:\Users\dougl\Documents\dfm_scraping\`
- **Neo4j Aura console:** https://console.neo4j.io
- **Vercel project dashboard:** https://vercel.com/douglas-mcgowans-projects

## Appendix B — Related prior art in Douglas's work

- `ai-industry-map-explorer/` — Vite+React+D3+framer-motion. Closest technical precedent if we migrate off single-file.
- `idetc-paper-site/` — the IDETC paper companion, renders three KG figures statically. Look at how they rendered the KG for visual inspiration.
- `viz-research-hub/` — "Ways of Thinking" reference library. Sections on knowledge graphs, embedding spaces, explorable explanations — skim before Phase 8 polish.
- `dfm_scraping/BUILD_PLAN_V2.md` — 82KB planning doc for rebuilding the Streamlit app. **Related but different project.** Contains the aesthetic research (anti-slop, provenance patterns, perceptually-uniform color) we're adopting. Skim §2 (aesthetic) and §4 (research-backed UX rules).
- `dfm_scraping/DRAFT-MD-25-1709-1.pdf` — the IDETC paper itself. Read abstract + Sec 3 (method) to ground the terminology.
