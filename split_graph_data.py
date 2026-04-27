"""Split the monolithic graph_data.json into smaller files for lazy loading.

Output layout (written to ./data/):
    data/
      topics.json              - meta + all topic summaries + cross-topic edges
                                 + a light search index (id, label, frame_type,
                                 se_site, credibility_tier, author_username,
                                 year, topic_id) for every frame.
                                 Preloaded on page open.
      frames/topic_<id>.json   - full frames + in-topic semantic edges for one
                                 topic. Lazy-loaded when user drills in.

Run:
    python split_graph_data.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "graph_data.json"
OUT_DIR = HERE / "data"
FRAMES_DIR = OUT_DIR / "frames"

SEARCH_INDEX_FIELDS = (
    "id",
    "topic_id",
    "label",
    "frame_type",
    "se_site",
    "credibility_tier",
    "author_username",
    "post_year",
)


def pick(d: dict, keys) -> dict:
    return {k: d.get(k) for k in keys if k in d}


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    frames = data.get("frames") or []
    edges = data.get("semantic_edges") or []
    topics = data.get("topics") or []
    meta = data.get("meta") or {}

    # Bucket frames by topic.
    frames_by_topic: dict = defaultdict(list)
    for frame in frames:
        tid = frame.get("topic_id")
        frames_by_topic[tid].append(frame)

    # Bucket semantic edges: in-topic vs cross-topic.
    frame_topic: dict = {f.get("id"): f.get("topic_id") for f in frames}
    in_topic_edges: dict = defaultdict(list)
    cross_topic_edges: list = []
    for edge in edges:
        src_topic = frame_topic.get(edge.get("source"))
        tgt_topic = frame_topic.get(edge.get("target"))
        if src_topic is None or tgt_topic is None:
            continue
        if src_topic == tgt_topic:
            in_topic_edges[src_topic].append(edge)
        else:
            cross_topic_edges.append(edge)

    # Light search index — minimum needed to:
    #   * render search results (label + topic_id + frame_type),
    #   * compute global filter counts without loading all bundles,
    #   * show a minimal card for a cross-topic neighbor in Level 3.
    search_index = [pick(f, SEARCH_INDEX_FIELDS) for f in frames]

    # Write topics.json.
    OUT_DIR.mkdir(exist_ok=True)
    FRAMES_DIR.mkdir(exist_ok=True)

    topics_payload = {
        "meta": meta,
        "topics": topics,
        "cross_topic_edges": cross_topic_edges,
        "search_index": search_index,
    }
    (OUT_DIR / "topics.json").write_text(
        json.dumps(topics_payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    # Clear old frame bundles before rewriting.
    for old in FRAMES_DIR.glob("topic_*.json"):
        old.unlink()

    # Write per-topic frame bundles.
    for tid, tframes in frames_by_topic.items():
        bundle = {
            "topic_id": tid,
            "frames": tframes,
            "semantic_edges": in_topic_edges.get(tid, []),
        }
        filename = f"topic_{tid}.json"
        (FRAMES_DIR / filename).write_text(
            json.dumps(bundle, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    # Size report.
    total_bytes = 0
    print(f"Wrote {OUT_DIR}:")
    topics_bytes = (OUT_DIR / "topics.json").stat().st_size
    print(f"  topics.json                {topics_bytes:>9,} bytes")
    total_bytes += topics_bytes
    bundles = sorted(FRAMES_DIR.glob("topic_*.json"))
    bundle_sizes = [(b.name, b.stat().st_size) for b in bundles]
    for name, size in bundle_sizes[:3]:
        print(f"  frames/{name:<22} {size:>9,} bytes")
    if len(bundles) > 3:
        remaining = sum(s for _, s in bundle_sizes[3:])
        print(f"  frames/... ({len(bundles)-3} more)   {remaining:>9,} bytes")
    total_bytes += sum(s for _, s in bundle_sizes)
    source_bytes = SOURCE.stat().st_size
    print(f"Total split: {total_bytes:,} bytes across {1 + len(bundles)} files")
    print(f"Source     : {source_bytes:,} bytes (single file)")
    print(f"Frame count per bundle (min/max): "
          f"{min(len(v) for v in frames_by_topic.values())} / "
          f"{max(len(v) for v in frames_by_topic.values())}")


if __name__ == "__main__":
    main()
