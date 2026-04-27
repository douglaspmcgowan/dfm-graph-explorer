# atlas_gui — Product Requirements Document
**Project:** IDETC26 Design Engineering Atlas  
**Researcher:** Caseysimone Ballestas, UC Berkeley Mechanical Engineering  
**Document status:** Approved by PI — ready for implementation  
**Last updated:** 2026-04-14 (v2 — three-level architecture)  
**Session that produced this:** claude.ai, PI + Claude planning conversation

---

## 1. What This Is

A read-only interactive visualization of the Design Engineering Atlas knowledge graph. The graph was extracted from 1,548 ASME DTM conference papers (1989–2025) using a multi-stage LLM pipeline. It maps the empirical design engineering literature as a network of subjects, tasks, problems, and cognitive constructs.

The GUI is the public-facing companion to the IDETC 2026 paper. Its purpose is to let researchers explore the field's structure — entering from any node, moving through the graph relationally, and seeing the literature that supports every connection.

The closest reference models are **Neurosynth** (neurosynth.org) — specifically its three-tab structure of Maps / Studies / Associations — and the **TensorFlow Embedding Projector** for interaction feel. The graph is a navigation device, not the destination. The deeper you go, the more it recedes in favor of scholarship.

---

## 2. Constraints — Non-Negotiable

- **Read-only.** Never modify `database.db` or any pipeline file.
- **Static build.** No backend server. Must work by opening `index.html` locally AND deploying to GitHub Pages or a lab static host with zero server infrastructure.
- **Single source of truth.** All graph data comes from one pre-exported JSON file (`graph_data.json`) produced by a one-time Python export script against `atlas_pipeline/pipeline_v2/database.db`.
- **Self-contained.** The GUI folder (`atlas_gui/`) must be portable — copy it anywhere, open `index.html`, it works.

---

## 3. Data

### Source
`atlas_pipeline/pipeline_v2/database.db` — SQLite, read-only, 173MB.  
See `atlas_pipeline/pipeline_v2/AUDIT.md` for full schema.

### Key counts
| Entity | Count |
|---|---|
| Total nodes | 228 |
| Subject nodes | 12 |
| Task nodes | 70 |
| Problem nodes | 80 |
| Construct nodes | 66 |
| Clean edges | 1,959 |
| Total edges in DB | 2,196 |
| Papers (total) | 1,548 |
| Papers (empirical) | 601 |
| Temporal range | 1989–2025 |

### Edge types (6)
6 typed relationship categories between node pairs. Edge weight = number of papers evidencing the connection.

### Export script requirements
`atlas_gui/export_graph.py`:
1. Connects read-only to `../atlas_pipeline/pipeline_v2/database.db`
2. Uses only the 1,959 clean edges
3. Per-node: id, label, type, description, paper_count, first_year, papers[]
4. Per-paper in node: title, authors, year, doi (if available)
5. Per-edge: source_id, target_id, edge_type, weight, years[], papers[]
6. Per-paper in edge: title, authors, year, doi — these are papers evidencing that specific node-pair relationship
7. Prints summary: node count, edge count, paper count, file size

---

## 4. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Framework | React (Vite) | Needed for three-level view state management |
| Graph rendering | D3.js force simulation | Fine-grained visual encoding control |
| Styling | CSS variables + custom CSS | Static deploy, dark theme control |
| Data | Pre-exported JSON | Zero runtime DB dependency |
| Build | `dist/` folder | Drop onto GitHub Pages or lab server |

No backend. No database at runtime. No API calls.

---

## 5. Visual Design

### Aesthetic
**Dark research instrument.** At Level 1, feels like looking at the field through a precision tool. At Level 3, feels like reading a Wikipedia page — clean, scholarly, structured.

- Background: `#0d0d0f`
- Node colors by type:
  - Subjects: `#4fc3f7` (blue)
  - Tasks: `#81c784` (green)
  - Problems: `#ffb74d` (amber)
  - Constructs: `#ce93d8` (purple)
- Edges: light grey, opacity + thickness = weight
- Typography: `IBM Plex Mono` for graph labels + UI chrome. Clean sans-serif for Level 3 reading view body.
- Node size: proportional to paper_count, hard minimum for clickability

---

## 6. Three-Level Information Architecture

The GUI has three levels. Each has a different visual register and purpose. The graph is a navigation device — it recedes as you go deeper.

```
LEVEL 1 — Field View         LEVEL 2 — Node Orientation      LEVEL 3 — Node Deep Dive
─────────────────────        ───────────────────────────      ────────────────────────
Full graph, 228 nodes        Ego network + right panel        Mini graph + reading view
"What is this field?"        "What is this node?"             "Tell me everything"
No panel                     ~320px panel, right              Graph 1/3, text 2/3
Entry: on load               Entry: click any node            Entry: Explore → button
Exit: click background       Exit: click background           Exit: breadcrumb
```

---

## 7. Interactions — Full Specification

### 7.1 Level 1 — Field View

- All 228 nodes, force-directed, dark canvas
- All 1,959 clean edges, opacity/thickness by weight
- Top bar: search + entity type filter pills + edge weight slider + TEMPORAL MODE
- Legend: bottom-left, 4 swatches with name + count
- No panel visible
- Click any node → Level 2

### 7.2 Level 1 → Level 2 transition

- Clicked node + direct neighbors: full opacity, remain
- All other nodes: **disappear entirely** (hard filter, not dim)
- All non-neighbor edges: disappear
- Graph re-centers on ego network
- Right panel slides in (~320px)
- Click canvas background → Level 1 (full graph restores)

### 7.3 Level 2 — Node Orientation Panel

**Header**
- Node label (large, entity color)
- Entity type badge (colored pill)
- "Explore →" button right-aligned → Level 3
- "← Back to field" link

**About**
- Entity description (from DB)
- "First appeared: [year]"
- "Appears in [N] papers"

**Connections ([N])**
- Sorted by edge weight descending
- Each row: [colored dot] [neighbor label] — [N] papers co-occur · [edge type, small]
- Hover tooltip: "N papers reference both nodes"
- Click row → **accordion expands** showing that edge's papers:
  - Year (bold) + title + authors + DOI link if available
  - Label: "Papers evidencing this connection"
  - Click again to collapse. One open at a time.

**Papers ([N])**
- Label: "All papers referencing this node"
- Year (bold) + title + authors + DOI link
- Sorted year descending, scrollable

### 7.4 Level 2 → Level 3

- Click "Explore →" in panel header
- Graph shrinks to left ~1/3 (mini ego network, interactive)
- Reading view expands to right ~2/3
- Breadcrumb: "Design Engineering Atlas / [Node label]"

### 7.5 Level 3 — Node Deep Dive

Visual register: Wikipedia/Notion. Clean, structured, generous spacing, clear section hierarchy.

**Header**
- Node label (large display)
- Entity type badge
- "First appeared [year]" · "Appears in [N] papers"

**About this [entity type]**
- Full description from DB

**Connections — by entity type**
Four collapsible sections: Connected Subjects / Tasks / Problems / Constructs
Each section lists connections sorted by weight.
Each connection expandable (accordion) → edge papers with full citation + DOI.

**All Papers**
- Complete chronological list (newest first)
- Year | Title (linked if DOI) | Authors
- Scrollable

**Mini graph (left 1/3)**
- Ego network, interactive
- Click neighbor → that node's Level 2
- Spatial context while reading

### 7.6 Search (all levels)

- Fuzzy match on node labels as user types
- Dropdown: up to 8 results with entity color dot
- Selecting → Level 2 for that node
- Keyboard: arrows, Enter, Escape

### 7.7 Entity type filters (Level 1 only)

- 4 toggle pills, entity colors, shows count
- Unchecking hides nodes + their edges
- At least one type must stay checked
- Persist on return to Level 1

### 7.8 Edge weight slider (Level 1 only)

- Range: 0 to max weight. Default: 0.
- Dragging right hides edges below threshold
- Label: "Min. N papers"

### 7.9 Temporal mode (Level 1 only)

- Toggle "TEMPORAL MODE" in top bar
- Year slider 1989–2025 appears at canvas bottom
- Shows nodes first seen ≤ year, edges with ≥1 paper ≤ year
- Edge weight = papers ≤ year
- Toggle off → full graph

### 7.10 Graph physics

- D3 forceSimulation: charge, link (length by weight), center, collision
- Stabilizes on load. Draggable nodes. Scroll zoom, drag pan.
- "Reset layout" button

---

## 8. Export Script JSON Structure

```json
{
  "meta": {
    "generated": "ISO timestamp",
    "node_count": 228,
    "edge_count": 1959,
    "paper_count": 601,
    "year_range": [1989, 2025]
  },
  "nodes": [
    {
      "id": "node_id_from_db",
      "label": "Analogical Reasoning",
      "type": "construct",
      "description": "Pipeline-generated description of this node",
      "paper_count": 14,
      "first_year": 1995,
      "papers": [
        {
          "title": "Full paper title",
          "authors": "Smith, J., Jones, A.",
          "year": 2003,
          "doi": "10.1115/DETC2003-12345"
        }
      ]
    }
  ],
  "edges": [
    {
      "source": "node_id_a",
      "target": "node_id_b",
      "type": "task_construct",
      "weight": 8,
      "years": [1998, 2003, 2007],
      "papers": [
        {
          "title": "Full paper title",
          "authors": "Smith, J.",
          "year": 1998,
          "doi": "10.1115/DETC1998-5678"
        }
      ]
    }
  ]
}
```

---

## 9. File Structure

```
atlas_gui/
├── README.md
├── PRD.md                     ← this document
├── preview.html               ← throwaway prototype (do not ship)
├── export_graph.py            ← one-time DB export
├── graph_data.json            ← exported data
├── package.json
├── vite.config.js
├── index.html
└── src/
    ├── main.jsx
    ├── App.jsx                    # level state (1|2|3) + selected node
    ├── components/
    │   ├── GraphCanvas.jsx        # D3 force graph, all levels
    │   ├── TopBar.jsx             # search + filters + temporal
    │   ├── Legend.jsx             # Level 1 color legend
    │   ├── NodePanel.jsx          # Level 2 right panel
    │   ├── DeepDiveView.jsx       # Level 3 reading view
    │   ├── ConnectionRow.jsx      # accordion connection item
    │   └── PaperRow.jsx           # paper citation row
    ├── hooks/
    │   ├── useGraphData.js        # load + parse graph_data.json
    │   ├── useGraphSimulation.js  # D3 simulation state
    │   └── useNavigation.js       # level state + selected node
    └── styles/
        ├── global.css
        └── variables.css
```

---

## 10. What v1 Does NOT Include

Deferred — do not build:
- No natural language query interface
- No relationship deep-dive (Level 3 for an edge) — v2
- No subgraph export
- No user accounts or saved states
- No embedding view (t-SNE, UMAP)
- No cross-corpus comparison
- No mobile layout

---

## 11. Definition of Done — v1

**Export**
- [ ] `export_graph.py` runs, produces valid `graph_data.json`
- [ ] Descriptions, proper titles/authors, DOIs included
- [ ] Edge papers[] correctly populated per edge
- [ ] Summary: 228 nodes, 1,959 edges, 601 papers

**Level 1**
- [ ] 228 nodes, colored by type, sized by paper_count
- [ ] Edge weight encoding (opacity + thickness)
- [ ] Search, filters, weight slider functional
- [ ] Temporal mode functional

**Level 2**
- [ ] Hard-filter ego network on click
- [ ] Panel: description, connections (accordion), papers
- [ ] Accordion shows edge-specific papers
- [ ] "Explore →" navigates to Level 3
- [ ] Background click returns to Level 1

**Level 3**
- [ ] Graph 1/3 left, reading view 2/3 right
- [ ] Connections organized by entity type, collapsible
- [ ] All papers list with DOI links
- [ ] Breadcrumb navigation
- [ ] Mini graph interactive

**Build**
- [ ] `npm run build` produces working `dist/`
- [ ] Works via `python -m http.server`
- [ ] GitHub Pages deploy (stretch)

---

## 12. Rules for Every Implementation Agent

1. Read this PRD fully before doing anything.
2. Read `atlas_gui/README.md` and `atlas_pipeline/pipeline_v2/AUDIT.md`.
3. Never modify `database.db` or anything in `atlas_pipeline/`.
4. Never write a backend server.
5. One bounded job per session. Confirm understanding before acting.
6. `preview.html` is a visual reference only — do not port its code into React.
7. Before exiting: update `PROJECT.md` + write dated log entry to `log/`.
8. If DB schema doesn't match PRD, stop and report to PI.
9. This PRD is the source of truth.

---

## 13. Cursor Agent Prompt (copy-paste ready)

```
You are a frontend implementation agent for the atlas_gui,
IDETC26 Design Engineering Atlas, Caseysimone Ballestas, UC Berkeley.

BEFORE DOING ANYTHING read in this order:
1. atlas_gui/PRD.md — source of truth
2. atlas_gui/README.md — data contract
3. atlas_pipeline/pipeline_v2/AUDIT.md — DB schema
4. PROJECT.md — current state
5. Most recent file in log/
Then state your understanding. Do not act until PI confirms.

YOUR JOB THIS SESSION:
[PI: insert one bounded task below]


HARD CONSTRAINTS:
- Never modify database.db or atlas_pipeline/
- Never write a backend server
- Never run pipeline stages
- preview.html is reference only — do not copy into React
- All code in atlas_gui/

WHEN DONE:
- Update PROJECT.md (what changed, new next_action)
- Write log/YYYY-MM-DD-session-summary.md
- Stop.
```

---

## 14. preview.html Update Prompt (paste into Cursor now)

```
Update atlas_gui/preview.html to match PRD v2 decisions.
Do NOT start the React app yet. This is still the prototype.
Make changes in this order, showing result after each:

1. HARD FILTER ON CLICK
Non-neighbor nodes must disappear entirely on node click.
Not dimmed — removed from view. Only ego network visible.
Graph re-centers. Click background → full graph restores.

2. ENTITY DESCRIPTION IN PANEL
Show node description field from graph_data.json in panel,
below type badge and paper count.
Skip if null/empty — no placeholder text.

3. PROPER PAPER TITLES
Papers list shows: title + authors + year.
No filenames. Title as clickable DOI link if doi present.
Show "[title unavailable]" only if title is genuinely missing.

4. EDGE-SPECIFIC PAPERS IN ACCORDION
Accordion expansion shows papers from that edge's papers[]
array — not the node's full paper list.
Label: "Papers evidencing this connection"

5. BREADCRUMB
Top-left, subtle:
- Default: "Design Engineering Atlas"  
- After node click: "Design Engineering Atlas / [node label]"
Visual scaffolding only — not full navigation yet.
```

---

*PRD v2 — 2026-04-14. Three-level architecture: Field / Node Orientation / Node Deep Dive. Hard-filter ego network. Accordion edge papers. Entity descriptions. Proper citations with DOIs. Do not modify without PI approval.*