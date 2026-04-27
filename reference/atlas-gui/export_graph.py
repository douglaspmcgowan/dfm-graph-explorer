#!/usr/bin/env python3
"""One-time export of atlas graph data from SQLite to JSON.

Usage:
    python export_graph.py
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = (SCRIPT_DIR / "../atlas_pipeline/pipeline_v2/database.db").resolve()
OUTPUT_PATH = SCRIPT_DIR / "graph_data.json"


@dataclass(frozen=True)
class PaperInfo:
    paper_id: int
    filename: str
    year: int | None
    title: str
    authors: str


def connect_read_only(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def parse_filename_metadata(filename: str) -> Tuple[str, str]:
    """Best-effort fallback conversion from filename to title/authors."""
    stem = filename.rsplit(".", 1)[0]
    parts = stem.split("_")
    if len(parts) >= 3 and parts[0].isdigit() and len(parts[0]) == 4:
        lastname = parts[1].replace("-", " ").strip()
        remainder = " ".join(parts[2:]).replace("-", " ").strip()
        authors = f"{lastname} et al." if lastname else "Unknown"
        title = remainder.title() if remainder else filename
        return title, authors
    return filename, "Unknown"


def derive_title_and_authors(filename: str, raw_text: str | None, prompt_text: str | None) -> Tuple[str, str]:
    """Extract a cleaner title from available text with conservative author fallback."""
    fallback_title, fallback_authors = parse_filename_metadata(filename)
    text = (prompt_text or raw_text or "").replace("\r", "\n")
    if not text.strip():
        return fallback_title, fallback_authors

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    lines = [re.sub(r"\s+", " ", ln) for ln in lines[:80]]
    if not lines:
        return fallback_title, fallback_authors

    def looks_like_title(line: str) -> bool:
        if len(line) < 15 or len(line) > 220:
            return False
        low = line.lower()
        bad_starts = ("abstract", "keywords", "introduction", "references")
        if low.startswith(bad_starts):
            return False
        if re.search(r"\bdoi\b|http[s]?://", low):
            return False
        alpha = sum(ch.isalpha() for ch in line)
        if alpha < 12:
            return False
        digit_ratio = sum(ch.isdigit() for ch in line) / max(len(line), 1)
        if digit_ratio > 0.2:
            return False
        return True

    title_idx = next((i for i, line in enumerate(lines) if looks_like_title(line)), None)
    if title_idx is None:
        return fallback_title, fallback_authors

    title = re.sub(r"^\[p\.\d+\]\s*", "", lines[title_idx], flags=re.IGNORECASE).strip()
    title = re.sub(r"\s+", " ", title)
    low_title = title.lower()
    invalid_title_starts = (
        "copyright",
        "proceedings",
        "de-vol",
        "de vol",
        "volume ",
        "vol. ",
        "vol ",
    )
    if low_title.startswith(invalid_title_starts):
        title = fallback_title
    if not title:
        title = fallback_title

    # No authoritative authors column exists in DB; keep stable fallback.
    return title, fallback_authors


def load_nodes(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    query = """
        SELECT id, entity_type, label, description, paper_count
        FROM nodes
        ORDER BY id
    """
    return conn.execute(query).fetchall()


def load_node_papers(conn: sqlite3.Connection) -> Dict[int, Dict[int, PaperInfo]]:
    query = """
        SELECT nm.node_id, p.id AS paper_id, p.filename, p.year, p.raw_text, p.prompt_text
        FROM node_members nm
        JOIN subjects s
          ON nm.entity_type = 'subject' AND nm.entity_id = s.id
        JOIN papers p
          ON p.id = s.paper_id
        WHERE p.is_empirical = 1

        UNION ALL

        SELECT nm.node_id, p.id AS paper_id, p.filename, p.year, p.raw_text, p.prompt_text
        FROM node_members nm
        JOIN tasks t
          ON nm.entity_type = 'task' AND nm.entity_id = t.id
        JOIN papers p
          ON p.id = t.paper_id
        WHERE p.is_empirical = 1

        UNION ALL

        SELECT nm.node_id, p.id AS paper_id, p.filename, p.year, p.raw_text, p.prompt_text
        FROM node_members nm
        JOIN problems pr
          ON nm.entity_type = 'problem' AND nm.entity_id = pr.id
        JOIN papers p
          ON p.id = pr.paper_id
        WHERE p.is_empirical = 1

        UNION ALL

        SELECT nm.node_id, p.id AS paper_id, p.filename, p.year, p.raw_text, p.prompt_text
        FROM node_members nm
        JOIN constructs c
          ON nm.entity_type = 'construct' AND nm.entity_id = c.id
        JOIN papers p
          ON p.id = c.paper_id
        WHERE p.is_empirical = 1
    """
    rows = conn.execute(query).fetchall()
    node_to_papers: Dict[int, Dict[int, PaperInfo]] = defaultdict(dict)
    for row in rows:
        node_id = int(row["node_id"])
        paper_id = int(row["paper_id"])
        if paper_id in node_to_papers[node_id]:
            continue
        filename = row["filename"]
        title, authors = derive_title_and_authors(
            filename=filename,
            raw_text=row["raw_text"],
            prompt_text=row["prompt_text"],
        )
        node_to_papers[node_id][paper_id] = PaperInfo(
            paper_id=paper_id,
            filename=filename,
            year=row["year"],
            title=title,
            authors=authors,
        )
    return node_to_papers


def load_clean_edges(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    # Exact clean-edge filter from pipeline_v2/INVESTIGATION.md (stg4_export.py):
    query = """
        SELECT ge.source_node_id, ge.target_node_id, ge.edge_type, ge.weight
        FROM graph_edges ge
        JOIN nodes n1 ON ge.source_node_id = n1.id
        JOIN nodes n2 ON ge.target_node_id = n2.id
        WHERE n1.label != 'multi-phase design process'
          AND n2.label != 'multi-phase design process'
          AND n1.label != 'no design object'
          AND n2.label != 'no design object'
          AND n1.paper_count > 1
          AND n2.paper_count > 1
        ORDER BY ge.source_node_id, ge.target_node_id
    """
    return conn.execute(query).fetchall()


def load_paper_stats(conn: sqlite3.Connection) -> Tuple[int, int, int]:
    row = conn.execute(
        """
        SELECT COUNT(*) AS paper_count, MIN(year) AS min_year, MAX(year) AS max_year
        FROM papers
        WHERE is_empirical = 1
        """
    ).fetchone()
    return int(row["paper_count"]), int(row["min_year"]), int(row["max_year"])


def build_export_payload(conn: sqlite3.Connection) -> dict:
    nodes = load_nodes(conn)
    node_papers = load_node_papers(conn)
    clean_edges = load_clean_edges(conn)
    paper_count, min_year, max_year = load_paper_stats(conn)

    node_paper_ids: Dict[int, Set[int]] = {
        node_id: set(papers.keys()) for node_id, papers in node_papers.items()
    }
    paper_year_lookup: Dict[int, int | None] = {}
    paper_info_lookup: Dict[int, PaperInfo] = {}
    for papers in node_papers.values():
        for paper in papers.values():
            paper_year_lookup[paper.paper_id] = paper.year
            paper_info_lookup[paper.paper_id] = paper

    exported_nodes = []
    for node in nodes:
        node_id = int(node["id"])
        papers = list(node_papers.get(node_id, {}).values())
        papers.sort(
            key=lambda p: (p.year is None, -(p.year or -1), p.title.lower())
        )
        years = [p.year for p in papers if p.year is not None]
        first_year = min(years) if years else None
        exported_nodes.append(
            {
                "id": str(node_id),
                "label": node["label"],
                "type": node["entity_type"],
                "description": (node["description"] or "").strip(),
                "paper_count": int(node["paper_count"] or 0),
                "first_year": first_year,
                "papers": [
                    {
                        "paper_id": p.paper_id,
                        "title": p.title,
                        "year": p.year,
                        "authors": p.authors,
                    }
                    for p in papers
                ],
            }
        )

    exported_edges = []
    for edge in clean_edges:
        source = int(edge["source_node_id"])
        target = int(edge["target_node_id"])
        shared_papers = node_paper_ids.get(source, set()) & node_paper_ids.get(target, set())
        years = sorted(
            {
                year
                for pid in shared_papers
                for year in [paper_year_lookup.get(pid)]
                if year is not None
            }
        )
        exported_edges.append(
            {
                "source": str(source),
                "target": str(target),
                "type": edge["edge_type"].replace("-", "_"),
                "weight": int(edge["weight"] or 0),
                "years": years,
                "papers": [
                    {
                        "paper_id": pid,
                        "title": paper_info_lookup[pid].title if pid in paper_info_lookup else "",
                        "authors": paper_info_lookup[pid].authors if pid in paper_info_lookup else "Unknown",
                        "year": paper_info_lookup[pid].year if pid in paper_info_lookup else None,
                        "doi": None,
                    }
                    for pid in sorted(
                        shared_papers,
                        key=lambda pid: (
                            paper_info_lookup[pid].year is None if pid in paper_info_lookup else True,
                            -(paper_info_lookup[pid].year or -1) if pid in paper_info_lookup else 1,
                            paper_info_lookup[pid].title.lower() if pid in paper_info_lookup else "",
                        ),
                    )
                ],
            }
        )

    payload = {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "node_count": len(exported_nodes),
            "edge_count": len(exported_edges),
            "paper_count": paper_count,
            "year_range": [min_year, max_year],
        },
        "nodes": exported_nodes,
        "edges": exported_edges,
    }
    return payload


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")

    with connect_read_only(DB_PATH) as conn:
        payload = build_export_payload(conn)

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(
        "Export complete:"
        f" nodes={payload['meta']['node_count']},"
        f" edges={payload['meta']['edge_count']},"
        f" papers={payload['meta']['paper_count']},"
        f" file={OUTPUT_PATH.name} ({size_mb:.2f} MB)"
    )


if __name__ == "__main__":
    main()
