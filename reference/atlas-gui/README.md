# atlas_gui (IDETC26-atlas-gui)

GUI for the Design Engineering Atlas knowledge graph. This README is what belongs on the **private GitHub** repo root (flat layout).

## data contract

Read-only access to `../atlas_pipeline/pipeline_v2/database.db`.  
Do not modify or move the database.

## status

Prototype: `preview.html` (single-file D3). Export: `export_graph.py` → `graph_data.json`.  
See `PRD.md` for requirements.

## agent workflow

1. Read this README, then `PROJECT.md`, then the newest file in `log/`.
2. One bounded task per session; confirm scope with PI if unclear.
3. End of session: update `PROJECT.md` and add **one** dated file under `log/` (append-only).

## parent workspace

The full IDETC26 paper project uses `../README.md` and `../PROJECT.md` at the workspace root — not this file.

## pushing to GitHub

The git remote for this GUI expects **atlas** files at the **IDETC26 folder root** (historical layout). Before `git push` to `IDETC26-atlas-gui`, copy from this folder to the parent directory:

```bash
cd /path/to/IDETC26
cp atlas_gui/PRD.md atlas_gui/export_graph.py atlas_gui/graph_data.json atlas_gui/preview.html .
cp atlas_gui/README.md README.md
```

Then commit and push from `IDETC26` (only those paths are tracked for the atlas remote).  
Do **not** overwrite parent `PROJECT.md` — it is the full paper `PROJECT.md`.
