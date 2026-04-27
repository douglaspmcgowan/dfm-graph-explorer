"""Delegate: rewrite export_graph.py to accept CLI args for all paths.

Keeps existing behavior and output schema unchanged. Only changes:
  1. Add argparse with --graph, --semantic-edges, --topic-model, --output, -v/--verbose.
  2. Defaults preserve today's hardcoded Windows paths so `python export_graph.py`
     still works without args on Douglas's machine.
  3. Add a short module docstring and one-line usage examples.

Everything else — functions, field logic, JSON shape — must stay byte-identical
where possible. Do NOT rewrite the field-mapping logic.

Writes: export_graph.cli.draft.py (for review before replacing the original)
"""
from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "export_graph.cli.draft.py"

MODEL_CANDIDATES = [os.environ.get("OPENAI_MODEL") or "", "gpt-5.4", "gpt-5", "gpt-5-mini", "gpt-4.1"]
MODEL_CANDIDATES = [m for m in MODEL_CANDIDATES if m]


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY not set")

    current = (HERE / "export_graph.py").read_text(encoding="utf-8")

    prompt = f"""Rewrite the following `export_graph.py` to accept CLI arguments,
WITHOUT changing its output JSON schema or the frame/edge/topic mapping logic.

Required changes:
1. Add `argparse` with these flags:
     --graph PATH          path to the gpickle (default: current hardcoded path)
     --semantic-edges PATH path to semantic_edges.json (default: current hardcoded path)
     --topic-model PATH    path to topic_model_output.json (default: current hardcoded path)
     --output PATH         output graph_data.json path (default: current hardcoded path)
     -v, --verbose         enable per-step progress prints
2. Replace the module-level constants `GRAPH_PATH`, `SEMANTIC_EDGES_PATH`,
   `TOPIC_MODEL_PATH`, `OUTPUT_PATH` with CLI-argument resolution in a
   `parse_args()` function.
3. Keep the same defaults (the existing Windows paths) so that running
   `python export_graph.py` with NO arguments still produces the same output.
4. Print a one-line summary at the end with absolute output path and counts
   (frame / edge / topic).
5. Add a module docstring at the top with two usage examples.

Do NOT touch:
  - Any function body except where paths are read.
  - The JSON shape produced.
  - Any helper like `parse_post_year`, `normalize_tags`, etc.
  - Frame/edge/topic assembly logic.

Output ONLY the full revised Python file contents — no markdown fences, no prose.

--- current file ---
{current}
"""

    client = OpenAI()
    last_err = ""
    for model in MODEL_CANDIDATES:
        try:
            resp = client.responses.create(model=model, input=prompt, reasoning={"effort": "medium"})
            text = getattr(resp, "output_text", None) or ""
            if not text:
                parts = []
                for item in getattr(resp, "output", []) or []:
                    for block in getattr(item, "content", []) or []:
                        t = getattr(block, "text", None)
                        if t:
                            parts.append(t)
                text = "\n".join(parts)
            if text:
                OUTPUT.write_text(text, encoding="utf-8")
                print(f"Wrote {OUTPUT} ({len(text)} chars, model={model})")
                return
            last_err = f"{model}: empty output"
        except Exception as exc:  # noqa: BLE001
            last_err = f"{model}: {exc}"
    raise RuntimeError(last_err)


if __name__ == "__main__":
    main()
