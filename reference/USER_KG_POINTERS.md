# USER_KG_POINTERS — Where Douglas's DFM knowledge graph lives

Everything this explorer site renders comes from one of the files below. No scraping, no API calls, no Python at runtime. Export → static JSON → ship.

This doc is field-by-field accurate as of 2026-03-08 (last graph rebuild). If any file has been regenerated since, re-check node counts with `_diagnostics.py` before trusting the numbers here.

---

## 0. The shortest path

**If you want to build the explorer today, you need two files:**

1. `C:\Users\dougl\Documents\dfm_scraping\provenance_graph.gpickle` — networkx `MultiDiGraph` with every node + structural edge. 5.4MB.
2. `C:\Users\dougl\Documents\dfm_scraping\semantic_edges.json` — 4,272 LLM-inferred semantic edges (SPECIFIES / MITIGATES / CAUSAL_LINK / CONTRADICTS). 2.0MB.

Everything else is optional enrichment (topics, clusters, positions, vectors, live Neo4j).

**Export step:** run a short Python script in `C:\Users\dougl\Documents\dfm_scraping\` (where `venv` is already set up) that loads the gpickle, merges `semantic_edges.json`, and writes a single `graph_data.json` matching the atlas-gui JSON shape. See PLAN.md §4 for the schema mapping and §10 Phase 2 for the expected output fields.

---

## 1. Data source inventory

All paths are inside `C:\Users\dougl\Documents\dfm_scraping\` unless noted.

| # | File | Size | Format | What it is | Use when |
|---|---|---|---|---|---|
| 1 | `provenance_graph.gpickle` | 5.4 MB | networkx pickle | 7,864 nodes + 8,776 structural edges. The canonical graph. | **Always** — this is the master. Load via `networkx.read_gpickle()`. |
| 2 | `provenance_graph.gexf` | varies | GEXF XML | Same graph, GEXF format. Gephi-compatible. | Tooling that prefers XML over pickle. |
| 3 | `provenance_graph_slim.gexf` | smaller | GEXF XML | Slimmed version (drops heavy attrs). | Quick Gephi previews. |
| 4 | `provenance_graph_slim_topics.gexf` | smaller | GEXF XML | Slim + topic labels. | Topic-level exploration in Gephi. |
| 5 | `Clusters_Att_2.gexf` | 8.8 MB | GEXF XML | Graph with **pre-computed ForceAtlas2 x/y positions** from Gephi + clustering attrs. | **Position seeding for the explorer** — skips the force-sim warm-up. |
| 6 | `semantic_edges.json` | 2.0 MB | JSON array | 4,272 LLM-inferred edges: SPECIFIES 2,111 · MITIGATES 1,206 · CAUSAL_LINK 625 · CONTRADICTS 330. | Always merge with gpickle to get the full graph. |
| 7 | `topic_model_output.json` | 608 KB | JSON object | 39 BERTopic topics + 619 outliers (16%), LLM-labeled via gpt-4.1-mini. Per topic: `label`, `keywords`, `n_frames`, `scope_distribution`, `frame_type_distribution`, `top_frames` (5 each). | **Level 1 supernode data** (see PLAN.md §5 — hierarchical reveal). |
| 8 | `subject_clusters.json` | 1.8 MB | JSON object | 3,292 subject clusters (from 3,870 unique subjects, 0.30 threshold, 10 blocked pairs). | Subject-grouping for Level 2 drill-in. |
| 9 | `example_cache.json` | 344 KB | JSON object | 4 pre-computed DFM reports (full `DFMReportV2` schema). | Demo queries, smoke tests, fallback when backend is offline. |
| 10 | `schema_se.py` | — | Python | Pydantic v2 schemas: `KnowledgeFrame`, `SEAuthorFrame`, `SEPostExtractionResult`, `ExtractionOutput`. Controlled vocab Literals. | Source of truth for field names + enum values. Mirror into TypeScript types. |
| 11 | `dfm_report_schema.py` | — | Python | Report-side schemas: `DFMReportV2`, `DisciplineSection`, `ReasoningChain`, `ChainedFrame`, `ContradictionEntryV2`. | Only matters if the explorer ever renders generated reports. |
| 12 | `CLAUDE.md` | — | Markdown | Pipeline overview, env vars, data volumes, Streamlit deploy notes. | Session onboarding; answers "how was this built?" |
| 13 | `extractions_se_all.json` | large | JSON | Raw extraction output per post. **Do not hand-edit** (pipeline regenerates). | Deep-dive if a frame looks wrong and you need to verify the original LLM call. |

### Not in this folder, but part of the stack

| Resource | Where | What it holds |
|---|---|---|
| **Neo4j Aura** | `neo4j+s://e9cb6c7f.databases.neo4j.io` | Full graph (structural + semantic edges) for Cypher querying. Credentials in `Neo4j-e9cb6c7f-Created-2026-02-19.txt`. |
| **Qdrant Cloud** | see `push_to_qdrant_cloud.py` | 11,637 vectors across 3 collections (`frames_knowledge`, `frames_subject`, `frames_quote`). Powers semantic search. |
| **Streamlit app** | `https://dfm-kg-agent.streamlit.app/` | Live RAG agent. Source of truth for "how the pipeline currently surfaces this data." |
| **Git repo** | `github.com/douglaspmcgowan/dfm-kg-agent` (or equivalent — check `git remote -v` in `dfm_scraping/`) | Full pipeline source. |

---

## 2. Node types and counts (from CLAUDE.md, authoritative)

| Node type | Count | Key fields | Notes |
|---|---|---|---|
| **Frame** | 3,879 | `frame_type`, `scope`, `subject`, `source_quote`, `main_point`, `applicability`, `epistemic_stance`, `example_value`, `example_context`, `post_score`, `is_accepted_answer` | The atoms. Every claim in the graph is a Frame. |
| **Post** | 1,936 | `post_id`, `thread_url`, `post_role`, `post_score`, `is_accepted_answer`, `post_date`, `se_tags`, `se_site` | The raw forum posts. Frames are EXTRACTED_FROM posts. |
| **Author** | 1,138 | `author_username`, `reputation`, `user_type`, `accept_rate`, `author_credibility_tier` | SE authors. Credibility tier: high (rep ≥ 10000) / medium (≥ 1000) / low. |
| **Thread** | 911 | `thread_title`, `thread_url`, `se_site`, `se_tags` | The conversations. Posts are IN_THREAD threads. |
| **Total** | **7,864** | | Scale challenge — see PLAN.md §5. |

Structural edges (8,776 total): `EXTRACTED_FROM` (frame→post), `AUTHORED_BY` (post→author), `IN_THREAD` (post→thread), `ANSWERS` (answer-post → question-post).

---

## 3. Frame schema — the important fields

Full definitions in `schema_se.py`. This section is the compressed version for the explorer UI.

### 3.1 FrameType (8 values)

Used as the primary color dimension in the graph.

| Value | One-line definition | Suggested color role |
|---|---|---|
| `risk` | condition(s) → failure mode or operational limitation | danger red |
| `heuristic` | personal practice/preference with rationale, OR directed advice | advisory blue |
| `principle` | causal explanation WHY something happens | insight purple |
| `case` | specific real-world job or incident narrative | warm amber |
| `workaround` | non-standard fix for a stated limitation | action green |
| `observation` | empirical/factual/definitional claim — no action, no cause | neutral slate |
| `comparison` | weighs two or more options/approaches | contrast pink |
| `other` | explained in `extraction_rationale` | dim gray |

### 3.2 ScopeDomain (10 values)

Secondary filter dimension. Maps roughly to "what engineering discipline."

`design_geometry` · `machining_process` · `material` · `tooling` · `programming` · `shop_operations` · `quality` · `cost` · `machine_capability` · `other`

### 3.3 Applicability (3 values)

- `universal` — true across virtually all instances of the subject (basic physics, definitional).
- `context_dependent` — **default** — true within the subject under specific contexts (material, brand, operation).
- `situational` — specific to a particular shop/machine config or installed option.

### 3.4 EpistemicStance (5 values)

How the claim is phrased. Useful as a credibility dimension.

- `absolute_authoritative` — must/always/never, no hedges.
- `direct_neutral` — default; stated as fact, technical tone.
- `hedged_emphatic` — personal hedges + strong internal language ("I hate X").
- `tentative_subjective` — weak language (might, usually, I think).
- `narrative_implied` — inferred from a story, not directly stated.

### 3.5 CredibilityTier (3 values)

Per-author, derived from SE reputation.

- `high` — reputation ≥ 10,000 (close/reopen privileges).
- `medium` — reputation ≥ 1,000 (established).
- `low` — everything else.

### 3.6 Fields that make the explorer worth visiting

If the visualization surfaces nothing else, it must surface these per Frame:

1. **`source_quote`** — verbatim text from the post. **This is the most important field.** Hover or click on a frame node should reveal the quoted passage. (NotebookLM-tier provenance pattern — see PLAYBOOK_EXTRACTS.md §5.)
2. **`main_point`** — the 1–2 sentence synthesized claim. Goes in the node label.
3. **`subject`** — concise noun phrase. Good secondary label / grouping key.
4. **`author_username` + `author_credibility_tier`** — who said it + how credible.
5. **`se_site`** — which Stack Exchange community (engineering, electronics, woodworking, robotics, mechanics).
6. **`is_accepted_answer`** + **`post_score`** — community validation signals.
7. **`source_url`** — deep-link back to the original thread.

Anything less and it's just a force-directed hairball.

---

## 4. Edge types

### 4.1 Structural edges (8,776 total, in gpickle directly)

| Edge | From → To | Cardinality | Meaning |
|---|---|---|---|
| `EXTRACTED_FROM` | Frame → Post | N:1 | Which post this claim came from. |
| `AUTHORED_BY` | Post → Author | N:1 | Post's author. |
| `IN_THREAD` | Post → Thread | N:1 | Post's parent thread. |
| `ANSWERS` | Post → Post | N:1 | Answer post → question post (SE site structure). |

### 4.2 Semantic edges (4,272 total, in `semantic_edges.json`)

LLM-inferred (gpt-5) relationships **between frames**. This is the value-add layer — the "connect the dots" that makes the graph more than a post browser.

| Label | Count | From → To shape | Meaning |
|---|---|---|---|
| `SPECIFIES` | 2,111 | specific → general | B provides a specific context that narrows when A's general rule applies. |
| `MITIGATES` | 1,206 | mitigation → risk | A provides a technique that prevents or reduces B's stated risk. |
| `CAUSAL_LINK` | 625 | cause → effect | A describes a cause/mechanism that produces B's effect. |
| `CONTRADICTS` | 330 | — | A and B give opposing guidance on the same point. |

Each edge in `semantic_edges.json` has:

```json
{
  "frame_a": "se-engineering-51725-a51726-0",
  "frame_b": "se-woodworking-8218-a8224-1",
  "label": "SPECIFIES",
  "direction": "B_to_A",
  "confidence": "medium",
  "reasoning": "B provides a specific context ... Thus B specifies a case of A."
}
```

The `reasoning` field is human-readable and should be surfaced on edge hover in the explorer (this is a differentiator vs atlas-gui which has no semantic edges). Top-level metadata: `model`, `top_k`, `total_classified`, `total_edges`.

---

## 5. Topic model (level 1 of hierarchical reveal)

Lives in `topic_model_output.json`. 39 topics + 619 outliers (~16%).

Each topic entry:

```json
{
  "topic_id": 0,
  "label": "0_Precision hole-making",
  "keywords": ["Precision hole-making"],
  "n_frames": 410,
  "scope_distribution": { "machining_process": 177, "tooling": 131, ... },
  "frame_type_distribution": { "heuristic": 149, "observation": 116, ... },
  "top_frames": [
    { "frame_id": "...", "subject": "...", "main_point": "..." },
    ...
  ]
}
```

**Use:** Level 1 of the explorer shows 39 topic supernodes, not 7,864 frames. Size by `n_frames`. Color by dominant `scope` or `frame_type`. Click a topic → drill into its frames (Level 2). See PLAN.md §5 for the full scale strategy.

---

## 6. Subject clusters

Lives in `subject_clusters.json`. 3,292 canonical subjects derived from 3,870 unique raw subjects (cosine threshold 0.30, 10 blocked pairs).

Use: secondary grouping key within a topic. A topic like "Precision hole-making" might contain 30+ subject clusters (drill selection, reamer use, thread engagement, etc.). Makes Level 2 browsable rather than a 410-node blob.

---

## 7. Pre-computed layout positions (Gephi ForceAtlas2)

`Clusters_Att_2.gexf` (8.8 MB) has `<viz:position x="..." y="..." z="0"/>` on every node. These come from running ForceAtlas2 in Gephi with the `LinLog mode + Prevent Overlap + Gravity 1.0` preset (or similar — check Gephi file history if the exact params matter).

**Why this matters:** Force-simulating 7,864 nodes in the browser in real-time is painful (~10-30s warm-up). If you export positions from this file and pass them to D3's force simulation as `fx` / `fy` initial values, the layout appears instantly. Then unfreeze once the user starts interacting. See PLAN.md §9 for the code pattern.

Per-node attributes in `Clusters_Att_2.gexf` include (all useful for filtering):

- `node_type` (Frame / Post / Author / Thread)
- `thread_title`, `se_site`
- `frame_type`, `subject`, `scope`
- `credibility_tier`
- `semantic_degree` (how many semantic edges this frame has — useful for sizing)
- plus the ForceAtlas2 positions

---

## 8. Vector database (Qdrant Cloud) — for semantic search

Not required for the static explorer, but useful if you add a search box that does semantic lookup (not just keyword).

- Three collections: `frames_knowledge` (main_point + source_quote), `frames_subject` (subject only), `frames_quote` (source_quote only).
- 11,637 vectors total (3,879 × 3).
- Model: see `build_embeddings.py` for the embedding call.
- Credentials / URL: see `push_to_qdrant_cloud.py` (reads from env vars — don't paste the key into source).

**For a first version, skip Qdrant** — ship with client-side fuzzy search over `main_point` and `subject` strings. Add semantic search later if users ask for it.

---

## 9. Neo4j Aura — for Cypher queries

Same graph as the gpickle, but queryable via Cypher. Credentials live in `Neo4j-e9cb6c7f-Created-2026-02-19.txt`:

```
NEO4J_URI=neo4j+s://e9cb6c7f.databases.neo4j.io
NEO4J_USERNAME=e9cb6c7f
NEO4J_DATABASE=e9cb6c7f
```

Password is in that file — do not paste it into source. Read via env var.

**For the static explorer, you probably don't need this.** The entire graph fits in a single ~3-5 MB JSON at runtime. Neo4j is for dynamic queries; the explorer is read-only visualization.

Reason to reach for it: "show me all frames with a CONTRADICTS edge between authors of different credibility tiers" — that's a Cypher one-liner and a mess in static JSON. If the explorer ever grows a power-user query mode, wire it up then.

---

## 10. Decision table — which file do I load for what?

| Goal | Load | Also |
|---|---|---|
| Render the full graph as force-directed D3 | `provenance_graph.gpickle` + `semantic_edges.json` | export to `graph_data.json` first |
| Skip the force-sim warm-up (instant layout) | `Clusters_Att_2.gexf` (for positions) | merge into the exported JSON |
| Show 39 topic supernodes (Level 1) | `topic_model_output.json` only | |
| Drill into one topic's frames (Level 2) | filter `graph_data.json` nodes by `topic_id` | |
| Ego network around one frame (Level 3) | filter `graph_data.json` edges where `frame_a == id` or `frame_b == id` | |
| Group frames by subject | `subject_clusters.json` | |
| Pre-seed the search bar with demo queries | `example_cache.json` (4 reports with questions) | |
| Inspect a specific frame's extraction | `extractions_se_all.json` (grep for the frame_id) | — read-only |
| Live data (update without redeploy) | Neo4j Aura + Cypher | only if you build a server |
| Semantic search | Qdrant Cloud collections | only if client-side search isn't enough |

---

## 11. Export script — the thing to write first

Before the explorer can render anything, you need one Python script that:

1. Loads `provenance_graph.gpickle` via `networkx`.
2. Loads `semantic_edges.json` and merges those edges into the graph.
3. (Optional) Loads `Clusters_Att_2.gexf` and copies `viz:position` onto matching nodes.
4. (Optional) Loads `topic_model_output.json` and tags each Frame with its `topic_id`.
5. Writes a single `public/graph_data.json` matching the atlas-gui JSON shape (see PLAN.md §4 for the exact schema).

Run it from inside `C:\Users\dougl\Documents\dfm_scraping\` with the existing `venv` activated (`.\venv\Scripts\Activate.ps1`). Output goes into the explorer repo's `public/` folder. Re-run manually whenever the upstream pipeline regenerates the graph.

**Don't try to rebuild the pipeline.** The graph is upstream; the explorer is a read-only consumer.

---

## 12. What NOT to touch

From `dfm_scraping/CLAUDE.md` (repeated here because it matters):

- `extractions_se_all.json`, `se_posts_normalized*.json`, `extractions*.json` — **do not hand-edit.** The pipeline regenerates these, and hand edits get blown away.
- `archive/` — old PracticalMachinist pipeline, preserved for reference.
- `src/scraping_logic/` — read-only SE scraping outputs.
- **Never delete** a file from `dfm_scraping/` — move to `./trash/` if removal is needed.

The explorer should treat `dfm_scraping/` as a strictly read-only upstream. Everything the explorer needs gets copied into its own `public/` folder during export.

---

## 13. Sanity check before building

Before the future session commits to a schema, it should run `python _diagnostics.py` inside `dfm_scraping/` (venv activated) and verify the counts in section 2 still match. If the graph has been rebuilt since 2026-03-08, the numbers shift — trust the diagnostics output, not this doc.

The schema shape won't change; the counts might.
