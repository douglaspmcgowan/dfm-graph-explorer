"""Export DFM graph to graph_data.json for the web explorer."""

from __future__ import annotations

import json
import pickle
import re
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx


SCRIPT_DIR = Path(__file__).resolve().parent

GRAPH_PATH = Path("C:/Users/dougl/Documents/dfm_scraping/provenance_graph.gpickle")
SEMANTIC_EDGES_PATH = Path("C:/Users/dougl/Documents/dfm_scraping/semantic_edges.json")
TOPIC_MODEL_PATH = Path("C:/Users/dougl/Documents/dfm_scraping/topic_model_output.json")
OUTPUT_PATH = Path(
    "C:/Users/dougl/My Drive (douglaspmcgowan@gmail.com)/UC Berkeley/Research/Claude Research Folder/dfm-graph-explorer/graph_data.json"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_post_year(post_date) -> int | None:
    if not post_date:
        return None
    text = str(post_date)
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4])
    return None


def clean_topic_label(raw_label) -> str | None:
    if raw_label is None:
        return None
    text = str(raw_label)
    return re.sub(r"^-?\d+_", "", text, count=1)


def normalize_tags(tags) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, list):
        return [str(x) for x in tags if x is not None and str(x).strip()]
    if isinstance(tags, tuple):
        return [str(x) for x in tags if x is not None and str(x).strip()]
    if isinstance(tags, str):
        text = tags.strip()
        if not text:
            return []
        if "|" in text:
            return [part.strip() for part in text.split("|") if part.strip()]
        if ";" in text:
            return [part.strip() for part in text.split(";") if part.strip()]
        if "," in text:
            return [part.strip() for part in text.split(",") if part.strip()]
        return [text]
    return [str(tags)]


def make_frame_label(main_point, subject) -> str:
    main_text = (main_point or "").strip()
    subject_text = (subject or "").strip()

    if main_text:
        label = main_text.split(". ", 1)[0].strip().rstrip(".").strip()
    else:
        label = ""

    if not label:
        label = subject_text

    if len(label) > 120:
        label = label[:117].rstrip() + "..."

    return label


def extract_post_anchor(post_id) -> str | None:
    if not post_id:
        return None
    match = re.search(r"(\d+)(?!.*\d)", str(post_id))
    return match.group(1) if match else None


def build_source_url(thread_url, post_id) -> str:
    thread_url_text = (thread_url or "").strip()
    if not thread_url_text:
        return ""
    anchor = extract_post_anchor(post_id)
    return f"{thread_url_text}#{anchor}" if anchor else thread_url_text


def get_predecessor_by_edge_type(graph: nx.MultiDiGraph, node_id, edge_type: str):
    if node_id is None or node_id not in graph:
        return None
    for source, _target, _key, data in graph.in_edges(node_id, keys=True, data=True):
        if data.get("edge_type") == edge_type:
            return source
    return None


def get_successor_by_edge_type(graph: nx.MultiDiGraph, node_id, edge_type: str):
    if node_id is None or node_id not in graph:
        return None
    for _source, target, _key, data in graph.out_edges(node_id, keys=True, data=True):
        if data.get("edge_type") == edge_type:
            return target
    return None


def json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except Exception:
            pass
    return str(value)


def load_graph(path: Path) -> nx.MultiDiGraph:
    with open(path, "rb") as f:
        graph = pickle.load(f)
    if not isinstance(graph, nx.MultiDiGraph):
        raise TypeError(f"Expected networkx.MultiDiGraph, got {type(graph)!r}")
    return graph


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    graph = load_graph(GRAPH_PATH)
    semantic_json = load_json(SEMANTIC_EDGES_PATH)
    topic_json = load_json(TOPIC_MODEL_PATH)

    frame_ids = []
    post_ids = []
    author_ids = []
    thread_ids = []

    for node_id, attrs in graph.nodes(data=True):
        node_type = attrs.get("node_type")
        if node_type == "Frame":
            frame_ids.append(node_id)
        elif node_type == "Post":
            post_ids.append(node_id)
        elif node_type == "Author":
            author_ids.append(node_id)
        elif node_type == "Thread":
            thread_ids.append(node_id)

    frame_ids = sorted(frame_ids, key=str)
    post_ids = sorted(post_ids, key=str)
    author_ids = sorted(author_ids, key=str)
    thread_ids = sorted(thread_ids, key=str)
    frame_id_set = set(frame_ids)

    years = []
    for post_id in post_ids:
        attrs = graph.nodes[post_id]
        year = parse_post_year(attrs.get("post_date"))
        if year is not None:
            years.append(year)
    year_range = [min(years), max(years)] if years else [None, None]

    frame_assignments = topic_json.get("frame_assignments") or []
    frame_to_topic = {}
    outlier_count = 0
    for entry in frame_assignments:
        frame_id = entry.get("frame_id")
        if frame_id is None:
            continue
        topic_id = entry.get("topic_id", -1)
        raw_topic_label = entry.get("topic_label")
        cleaned_topic_label = None if topic_id == -1 else clean_topic_label(raw_topic_label)
        frame_to_topic[frame_id] = {
            "topic_id": topic_id,
            "raw_topic_label": raw_topic_label,
            "topic_label": cleaned_topic_label,
        }
        if topic_id == -1:
            outlier_count += 1

    topics_out = []
    topics_raw = topic_json.get("topics") or []
    for topic in sorted(topics_raw, key=lambda t: t.get("topic_id", 10**9)):
        topic_id = topic.get("topic_id")
        if topic_id == -1:
            continue

        raw_label = topic.get("label")
        cleaned_label = clean_topic_label(raw_label)

        top_frame_ids = []
        for item in topic.get("top_frames") or []:
            frame_id = item.get("frame_id")
            if frame_id is not None:
                top_frame_ids.append(frame_id)

        topics_out.append(
            {
                "id": f"topic_{topic_id}",
                "topic_id": topic_id,
                "label": cleaned_label or "",
                "raw_label": raw_label or "",
                "keywords": topic.get("keywords") or [],
                "n_frames": topic.get("n_frames", 0),
                "scope_distribution": topic.get("scope_distribution") or {},
                "frame_type_distribution": topic.get("frame_type_distribution") or {},
                "top_frame_ids": top_frame_ids,
            }
        )

    frames_out = []
    for frame_id in frame_ids:
        frame_attrs = graph.nodes[frame_id]

        post_id = get_predecessor_by_edge_type(graph, frame_id, "POST_CONTAINS_FRAME")
        post_attrs = graph.nodes[post_id] if post_id in graph else {}

        author_id = get_successor_by_edge_type(graph, post_id, "POST_AUTHORED_BY") if post_id else None
        author_attrs = graph.nodes[author_id] if author_id in graph else {}

        thread_id = get_predecessor_by_edge_type(graph, post_id, "THREAD_CONTAINS_POST") if post_id else None
        thread_attrs = graph.nodes[thread_id] if thread_id in graph else {}

        assignment = frame_to_topic.get(frame_id, {})
        topic_id = assignment.get("topic_id", -1)
        topic_label = assignment.get("topic_label") if topic_id != -1 else None

        main_point = frame_attrs.get("main_point") or ""
        subject = frame_attrs.get("subject") or ""

        post_date = post_attrs.get("post_date")
        post_year = parse_post_year(post_date)

        thread_url = ""
        if isinstance(thread_id, str) and thread_id.startswith("http"):
            thread_url = thread_id
        else:
            thread_url = thread_attrs.get("thread_url") or ""

        thread_title = thread_attrs.get("thread_title") or ""
        se_site = post_attrs.get("se_site") or thread_attrs.get("se_site") or ""

        frame_record = {
            "id": frame_id,
            "label": make_frame_label(main_point, subject),
            "main_point": main_point,
            "source_quote": frame_attrs.get("source_quote") or "",
            "subject": subject,
            "scope": frame_attrs.get("scope") or "",
            "frame_type": frame_attrs.get("frame_type") or "",
            "applicability": frame_attrs.get("applicability") or "",
            "epistemic_stance": frame_attrs.get("epistemic_stance") or "",
            "post_role": frame_attrs.get("post_role") or "",
            "topic_id": topic_id,
            "topic_label": topic_label,
            "post_id": post_id or "",
            "thread_url": thread_url,
            "thread_title": thread_title,
            "se_site": se_site,
            "se_tags": normalize_tags(post_attrs.get("se_tags")),
            "post_score": post_attrs.get("post_score"),
            "is_accepted_answer": bool(post_attrs.get("is_accepted_answer", False)),
            "post_date": post_date,
            "post_year": post_year,
            "author_username": author_attrs.get("author_username") or "",
            "author_reputation": author_attrs.get("reputation"),
            "credibility_tier": author_attrs.get("credibility_tier") or "",
            "source_url": build_source_url(thread_url, post_id),
        }
        frames_out.append(frame_record)

    semantic_edges_out = []
    for edge in semantic_json.get("edges") or []:
        source = edge.get("frame_a")
        target = edge.get("frame_b")
        if source not in frame_id_set or target not in frame_id_set:
            continue

        semantic_edges_out.append(
            {
                "id": len(semantic_edges_out),
                "source": source,
                "target": target,
                "label": edge.get("label") or "",
                "direction": edge.get("direction") or "",
                "confidence": edge.get("confidence"),
                "reasoning": edge.get("reasoning") or "",
            }
        )

    output = {
        "meta": {
            "generated": utc_now_iso(),
            "source": "provenance_graph.gpickle + semantic_edges.json + topic_model_output.json",
            "counts": {
                "frames": len(frame_ids),
                "posts": len(post_ids),
                "authors": len(author_ids),
                "threads": len(thread_ids),
                "topics": len(topics_out),
                "outliers": outlier_count,
                "semantic_edges": len(semantic_edges_out),
            },
            "year_range": year_range,
        },
        "topics": topics_out,
        "frames": frames_out,
        "semantic_edges": semantic_edges_out,
    }

    output = json_safe(output)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    output_size = OUTPUT_PATH.stat().st_size
    output_size_mb = output_size / (1024 * 1024)

    print(f"Script dir: {SCRIPT_DIR}")
    print(f"Graph: {GRAPH_PATH}")
    print(f"Semantic edges JSON: {SEMANTIC_EDGES_PATH}")
    print(f"Topic model JSON: {TOPIC_MODEL_PATH}")
    print(
        f"Node counts -> Frames: {len(frame_ids)}, Posts: {len(post_ids)}, "
        f"Authors: {len(author_ids)}, Threads: {len(thread_ids)}"
    )
    print(f"Graph edges total: {graph.number_of_edges()}")
    print(f"Topics exported: {len(topics_out)}")
    print(f"Outlier frame assignments: {outlier_count}")
    print(f"Frames exported: {len(frames_out)}")
    print(f"Semantic edges exported: {len(semantic_edges_out)}")
    print(f"Year range: {year_range[0]} to {year_range[1]}")
    print(f"Output written: {OUTPUT_PATH}")
    print(f"Output size: {output_size} bytes ({output_size_mb:.2f} MB)")


if __name__ == "__main__":
    main()