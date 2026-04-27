# DFM Graph Explorer — prep package

Goal: fork the `atlas-gui` prototype from Caseysimone Ballestas, swap in Douglas's DFM knowledge graph (7,864 nodes, pulled from Stack Exchange + PracticalMachinist forum posts), and deploy a living explorer at `dfm-graph-explorer.vercel.app` (or similar).

This folder is the **starting kit for a future Claude Code session.** The session should be able to open this README, follow the plan, and start building without needing to re-research anything.

---

## Read these, in order

| # | File | Why |
|---|---|---|
| 1 | `PLAN.md` | Master roadmap — what to build, phases, decisions, file tree. **Start here.** |
| 2 | `reference/USER_KG_POINTERS.md` | Where Douglas's graph data lives, field-by-field schema, which file to export from |
| 3 | `reference/PLAYBOOK_EXTRACTS.md` | Distilled guidance from `build-playbook.md`, `explainer_site_playbook.md`, and the Streamlit-to-Vercel `BUILD_PLAN_V2.md` |
| 4 | `reference/atlas-gui/PRD.md` | The original atlas-gui PRD — the spec we're cloning and adapting |
| 5 | `reference/atlas-gui/preview.html` | The working single-file D3 prototype we're forking |
| 6 | `reference/atlas-gui/graph_data.json` | Atlas-gui's exported data — the JSON shape we need to match |

---

## The shortest version

- **Source site:** `https://caseysimoneb.github.io/IDETC26-atlas-gui/preview.html` (1,481 lines, single-file D3, dark theme, three-level nav). Full source in `reference/atlas-gui/`.
- **Our graph:** `C:\Users\dougl\Documents\dfm_scraping\` — 3,879 extracted frames, 1,936 posts, 1,138 authors, 911 threads, 4,272 semantic edges. Live on Neo4j Aura. Also exported as `provenance_graph.gpickle` and `Clusters_Att_2.gexf`.
- **The problem atlas-gui doesn't solve:** their graph is 228 nodes. Ours is 7,864. Need clustering / hierarchical reveal / canvas rendering. See `PLAN.md §5`.
- **Deploy target:** Vercel, static, `vercel --prod --yes`.

---

## Current working directory for the future session

```
C:\Users\dougl\My Drive (douglaspmcgowan@gmail.com)\UC Berkeley\Research\Claude Research Folder\dfm-graph-explorer\
```

The session should `cd` here and work. Everything it needs is in this folder or linked from `reference/USER_KG_POINTERS.md`.

---

## One-paragraph context for the future session

Douglas is a UC Berkeley PhD student who built a knowledge-graph pipeline (`dfm_scraping`) that scrapes engineering forum posts and uses an LLM-as-judge setup to extract 8 frame types (risk, heuristic, principle, case, workaround, observation, comparison, other). The graph is already live on a Streamlit app (`dfm-kg-agent.streamlit.app`) but he wants a cleaner, graph-first public explorer — modeled on a peer's IDETC26 atlas GUI. This folder has the atlas-gui source cloned, the user's data sources catalogued, and playbook-distilled aesthetic decisions. Read `PLAN.md` then build.
