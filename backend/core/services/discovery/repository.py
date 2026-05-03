from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

from core.schema import PROJECT_SCHEMA_SQL
from core.services.discovery.models import (
    ConferenceRecord,
    FeedItemRecord,
    GraphEdgeRecord,
    GraphNodeRecord,
    GraphRecord,
    RecommendationRecord,
)
from core.services.papers.models import utc_now
from core.services.papers.repository import PaperRepository
from core.storage import configured_data_root, configured_db_path


DISCOVERY_SCHEMA_SQL = (
    PROJECT_SCHEMA_SQL
    + """
CREATE TABLE IF NOT EXISTS biz_feed_item (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_asset_id INTEGER NOT NULL,
    feed_date TEXT NOT NULL,
    topic TEXT NOT NULL DEFAULT '',
    score INTEGER NOT NULL DEFAULT 0,
    reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'candidate',
    source TEXT NOT NULL DEFAULT 'paper_library',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (paper_asset_id, feed_date),
    FOREIGN KEY (paper_asset_id) REFERENCES biz_paper(asset_id)
);

CREATE INDEX IF NOT EXISTS idx_biz_feed_date ON biz_feed_item(feed_date);
CREATE INDEX IF NOT EXISTS idx_biz_feed_status ON biz_feed_item(status);

CREATE TABLE IF NOT EXISTS biz_conference (
    conference_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    acronym TEXT NOT NULL,
    year INTEGER NOT NULL,
    rank TEXT NOT NULL DEFAULT '',
    field TEXT NOT NULL DEFAULT '',
    abstract_deadline TEXT NOT NULL DEFAULT '',
    paper_deadline TEXT NOT NULL DEFAULT '',
    notification_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'tracking',
    url TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_biz_conference_acronym ON biz_conference(acronym);
CREATE INDEX IF NOT EXISTS idx_biz_conference_deadline ON biz_conference(paper_deadline);
CREATE INDEX IF NOT EXISTS idx_biz_conference_status ON biz_conference(status);
"""
)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}
DEFAULT_ARXIV_CATEGORIES = ("cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.RO")


class DiscoveryRepository:
    def __init__(
        self,
        db_path: Path | None = None,
        data_root: Path | None = None,
    ) -> None:
        self.db_path = db_path or configured_db_path()
        self.data_root = data_root or configured_data_root()
        self.initialize()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.data_root.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(DISCOVERY_SCHEMA_SQL)
            self._seed_conferences(conn)
            conn.commit()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def refresh_feed_from_papers(
        self,
        *,
        feed_date: str,
        topic: str = "",
        limit: int = 20,
    ) -> list[FeedItemRecord]:
        now = utc_now()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT bp.asset_id, bp.title, bp.abstract, bp.paper_stage,
                    bp.refine_status, bp.review_status, bp.ccf_rank,
                    bp.sci_quartile, ar.updated_at
                FROM biz_paper bp
                JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                WHERE ar.is_deleted = 0
                ORDER BY ar.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            for row in rows:
                score, reason = self._score_paper(row)
                conn.execute(
                    """
                    INSERT INTO biz_feed_item (
                        paper_asset_id, feed_date, topic, score, reason,
                        status, source, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'candidate', 'paper_library', ?, ?)
                    ON CONFLICT(paper_asset_id, feed_date) DO UPDATE SET
                        topic = excluded.topic,
                        score = excluded.score,
                        reason = excluded.reason,
                        updated_at = excluded.updated_at
                    """,
                    (row["asset_id"], feed_date, topic, score, reason, now, now),
                )
            conn.commit()
        return self.list_feed_items({"feed_date": feed_date, "page_size": limit})[0]

    def refresh_feed_from_arxiv(
        self,
        *,
        feed_date: str,
        categories: list[str] | None = None,
        limit: int = 20,
        query: str = "",
    ) -> list[FeedItemRecord]:
        categories = categories or list(DEFAULT_ARXIV_CATEGORIES)
        entries = self._fetch_arxiv_entries(categories=categories, limit=limit, query=query)
        paper_repository = PaperRepository(db_path=self.db_path, data_root=self.data_root)
        now = utc_now()
        for entry in entries:
            with self.connect() as conn:
                paper_id = self._find_paper_by_source_url(conn, entry["source_url"])
            if paper_id is None:
                paper = paper_repository.create_paper(
                    {
                        "title": entry["title"],
                        "abstract": entry["abstract"],
                        "authors": entry["authors"],
                        "year": entry["year"],
                        "venue": "arXiv",
                        "venue_short": "arXiv",
                        "source_url": entry["source_url"],
                        "pdf_url": entry["pdf_url"],
                        "source_kind": "feed",
                        "tags": entry["categories"],
                    }
                )
                paper_id = paper.paper_id
            topic = entry["primary_category"] or ",".join(entry["categories"])
            with self.connect() as conn:
                score = self._score_arxiv_entry(entry)
                conn.execute(
                    """
                    INSERT INTO biz_feed_item (
                        paper_asset_id, feed_date, topic, score, reason,
                        status, source, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'candidate', 'arxiv', ?, ?)
                    ON CONFLICT(paper_asset_id, feed_date) DO UPDATE SET
                        topic = excluded.topic,
                        score = excluded.score,
                        reason = excluded.reason,
                        source = 'arxiv',
                        updated_at = excluded.updated_at
                    """,
                    (
                        paper_id,
                        feed_date,
                        topic,
                        score,
                        entry["reason"],
                        now,
                        now,
                    ),
                )
                conn.commit()
        return self.list_feed_items({"feed_date": feed_date, "page_size": limit})[0]

    def list_feed_items(self, query: dict[str, Any]) -> tuple[list[FeedItemRecord], int]:
        where = ["ar.is_deleted = 0"]
        params: list[Any] = []
        if query.get("feed_date"):
            where.append("fi.feed_date = ?")
            params.append(query["feed_date"])
        if query.get("status"):
            where.append("fi.status = ?")
            params.append(query["status"])
        if query.get("q"):
            where.append("(bp.title LIKE ? OR bp.abstract LIKE ? OR fi.topic LIKE ?)")
            pattern = f"%{query['q']}%"
            params.extend([pattern, pattern, pattern])
        where_sql = " AND ".join(where)
        page, page_size, offset = self._page(query)
        with self.connect() as conn:
            total = int(
                conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM biz_feed_item fi
                    JOIN biz_paper bp ON bp.asset_id = fi.paper_asset_id
                    JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                    WHERE {where_sql}
                    """,
                    params,
                ).fetchone()[0]
            )
            rows = conn.execute(
                f"""
                SELECT fi.*, bp.title, bp.abstract, bp.authors, bp.pub_year,
                    bp.venue, bp.source_url, bp.pdf_url
                FROM biz_feed_item fi
                JOIN biz_paper bp ON bp.asset_id = fi.paper_asset_id
                JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                WHERE {where_sql}
                ORDER BY fi.score DESC, fi.updated_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return [self._feed_from_row(row) for row in rows], total

    def update_feed_item(self, item_id: int, values: dict[str, Any]) -> FeedItemRecord:
        allowed = {"status", "topic", "reason", "score"}
        mapped = {key: value for key, value in values.items() if key in allowed}
        now = utc_now()
        with self.connect() as conn:
            row = conn.execute(
                "SELECT item_id FROM biz_feed_item WHERE item_id = ?",
                (item_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Feed item not found: {item_id}")
            if mapped:
                columns = [f"{key} = ?" for key in mapped]
                conn.execute(
                    f"""
                    UPDATE biz_feed_item
                    SET {', '.join(columns)}, updated_at = ?
                    WHERE item_id = ?
                    """,
                    [*mapped.values(), now, item_id],
                )
            conn.commit()
        return self.get_feed_item(item_id)

    def get_feed_item(self, item_id: int) -> FeedItemRecord:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT fi.*, bp.title, bp.abstract, bp.authors, bp.pub_year,
                    bp.venue, bp.source_url, bp.pdf_url
                FROM biz_feed_item fi
                JOIN biz_paper bp ON bp.asset_id = fi.paper_asset_id
                WHERE fi.item_id = ?
                """,
                (item_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Feed item not found: {item_id}")
        return self._feed_from_row(row)

    def create_conference(self, values: dict[str, Any]) -> ConferenceRecord:
        now = utc_now()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO biz_conference (
                    name, acronym, year, rank, field, abstract_deadline,
                    paper_deadline, notification_date, status, url, notes,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    values["name"],
                    values["acronym"],
                    values["year"],
                    values.get("rank", ""),
                    values.get("field", ""),
                    values.get("abstract_deadline", ""),
                    values.get("paper_deadline", ""),
                    values.get("notification_date", ""),
                    values.get("status", "tracking"),
                    values.get("url", ""),
                    values.get("notes", ""),
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_conference(int(cursor.lastrowid))

    def list_conferences(self, query: dict[str, Any]) -> tuple[list[ConferenceRecord], int]:
        where = ["1 = 1"]
        params: list[Any] = []
        if query.get("q"):
            where.append("(name LIKE ? OR acronym LIKE ? OR field LIKE ?)")
            pattern = f"%{query['q']}%"
            params.extend([pattern, pattern, pattern])
        if query.get("status"):
            where.append("status = ?")
            params.append(query["status"])
        where_sql = " AND ".join(where)
        page, page_size, offset = self._page(query)
        with self.connect() as conn:
            total = int(
                conn.execute(
                    f"SELECT COUNT(*) FROM biz_conference WHERE {where_sql}",
                    params,
                ).fetchone()[0]
            )
            rows = conn.execute(
                f"""
                SELECT *
                FROM biz_conference
                WHERE {where_sql}
                ORDER BY paper_deadline ASC, acronym ASC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return [self._conference_from_row(row) for row in rows], total

    def get_conference(self, conference_id: int) -> ConferenceRecord:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM biz_conference WHERE conference_id = ?",
                (conference_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Conference not found: {conference_id}")
        return self._conference_from_row(row)

    def update_conference(
        self,
        conference_id: int,
        values: dict[str, Any],
    ) -> ConferenceRecord:
        allowed = {
            "name",
            "acronym",
            "year",
            "rank",
            "field",
            "abstract_deadline",
            "paper_deadline",
            "notification_date",
            "status",
            "url",
            "notes",
        }
        mapped = {key: value for key, value in values.items() if key in allowed}
        now = utc_now()
        with self.connect() as conn:
            row = conn.execute(
                "SELECT conference_id FROM biz_conference WHERE conference_id = ?",
                (conference_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Conference not found: {conference_id}")
            if mapped:
                columns = [f"{key} = ?" for key in mapped]
                conn.execute(
                    f"""
                    UPDATE biz_conference
                    SET {', '.join(columns)}, updated_at = ?
                    WHERE conference_id = ?
                    """,
                    [*mapped.values(), now, conference_id],
                )
            conn.commit()
        return self.get_conference(conference_id)

    def list_recommendations(self, limit: int = 10) -> list[RecommendationRecord]:
        recommendations: list[RecommendationRecord] = []
        with self.connect() as conn:
            paper_rows = conn.execute(
                """
                SELECT bp.asset_id, bp.title, bp.paper_stage, bp.review_status,
                    bp.refine_status, bp.ccf_rank, bp.sci_quartile
                FROM biz_paper bp
                JOIN asset_registry ar ON ar.asset_id = bp.asset_id
                WHERE ar.is_deleted = 0
                ORDER BY ar.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            knowledge_rows = conn.execute(
                """
                SELECT bk.asset_id, bk.title, bk.review_status, bk.confidence_score
                FROM biz_knowledge bk
                JOIN asset_registry ar ON ar.asset_id = bk.asset_id
                WHERE ar.is_deleted = 0
                ORDER BY bk.confidence_score DESC, ar.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        for row in paper_rows:
            score, reason = self._score_paper(row)
            action = "confirm-review" if row["review_status"] == "waiting_review" else "open-paper"
            recommendations.append(
                RecommendationRecord(
                    recommendation_id=f"paper-{row['asset_id']}",
                    target_type="paper",
                    target_id=int(row["asset_id"]),
                    title=row["title"],
                    reason=reason,
                    score=score,
                    action=action,
                    metadata={"paper_stage": row["paper_stage"]},
                )
            )
        for row in knowledge_rows:
            score = int(float(row["confidence_score"] or 0.0) * 100)
            recommendations.append(
                RecommendationRecord(
                    recommendation_id=f"knowledge-{row['asset_id']}",
                    target_type="knowledge",
                    target_id=int(row["asset_id"]),
                    title=row["title"],
                    reason="High-confidence knowledge item ready for human review.",
                    score=score,
                    action="review-knowledge",
                    metadata={"review_status": row["review_status"]},
                )
            )
        return sorted(recommendations, key=lambda item: item.score, reverse=True)[:limit]

    def get_graph(self, limit: int = 200) -> GraphRecord:
        with self.connect() as conn:
            asset_rows = conn.execute(
                """
                SELECT asset_id, display_name, asset_type, file_size, updated_at
                FROM asset_registry
                WHERE is_deleted = 0
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            link_rows = conn.execute(
                """
                SELECT id, source_id, target_id, relation_type
                FROM asset_link
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        asset_ids = {int(row["asset_id"]) for row in asset_rows}
        nodes = [
            GraphNodeRecord(
                id=f"asset-{row['asset_id']}",
                label=row["display_name"],
                type=row["asset_type"],
                metadata={
                    "asset_id": int(row["asset_id"]),
                    "file_size": int(row["file_size"] or 0),
                    "updated_at": row["updated_at"],
                },
            )
            for row in asset_rows
        ]
        edges = [
            GraphEdgeRecord(
                id=f"edge-{row['id']}",
                source=f"asset-{row['source_id']}",
                target=f"asset-{row['target_id']}",
                relation=row["relation_type"],
                metadata={"link_id": int(row["id"])},
            )
            for row in link_rows
            if int(row["source_id"]) in asset_ids and int(row["target_id"]) in asset_ids
        ]
        return GraphRecord(nodes=nodes, edges=edges)

    def _fetch_arxiv_entries(
        self,
        *,
        categories: list[str],
        limit: int,
        query: str,
    ) -> list[dict[str, Any]]:
        category_query = " OR ".join(f"cat:{category}" for category in categories)
        search_query = category_query
        if query:
            search_query = f"({category_query}) AND all:{query}"
        params = urllib.parse.urlencode(
            {
                "search_query": search_query,
                "start": 0,
                "max_results": limit,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        request = urllib.request.Request(
            f"{ARXIV_API_URL}?{params}",
            headers={"User-Agent": "Research-Flow/0.1 (arxiv daily feed)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                xml_bytes = response.read()
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Failed to fetch arXiv daily feed: {exc}") from exc
        return self._parse_arxiv_entries(xml_bytes)

    def _parse_arxiv_entries(self, xml_bytes: bytes) -> list[dict[str, Any]]:
        root = ET.fromstring(xml_bytes)
        entries: list[dict[str, Any]] = []
        for entry in root.findall("atom:entry", ARXIV_NS):
            title = self._entry_text(entry, "atom:title")
            abstract = self._entry_text(entry, "atom:summary")
            source_url = self._entry_text(entry, "atom:id")
            published = self._entry_text(entry, "atom:published")
            authors = [
                self._entry_text(author, "atom:name")
                for author in entry.findall("atom:author", ARXIV_NS)
            ]
            categories = [
                category.attrib.get("term", "")
                for category in entry.findall("atom:category", ARXIV_NS)
                if category.attrib.get("term")
            ]
            primary_category_node = entry.find("arxiv:primary_category", ARXIV_NS)
            primary_category = (
                primary_category_node.attrib.get("term", "")
                if primary_category_node is not None
                else (categories[0] if categories else "")
            )
            pdf_url = ""
            for link in entry.findall("atom:link", ARXIV_NS):
                if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                    pdf_url = link.attrib.get("href", "")
                    break
            entries.append(
                {
                    "title": " ".join(title.split()),
                    "abstract": " ".join(abstract.split()),
                    "authors": authors,
                    "year": self._published_year(published),
                    "source_url": source_url,
                    "pdf_url": pdf_url,
                    "categories": categories,
                    "primary_category": primary_category,
                    "reason": f"Latest arXiv submission in {primary_category or 'selected categories'}.",
                }
            )
        return entries

    def _entry_text(self, node: ET.Element, path: str) -> str:
        child = node.find(path, ARXIV_NS)
        return child.text.strip() if child is not None and child.text else ""

    def _published_year(self, value: str) -> int | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).year
        except ValueError:
            return None

    def _find_paper_by_source_url(
        self,
        conn: sqlite3.Connection,
        source_url: str,
    ) -> int | None:
        row = conn.execute(
            """
            SELECT bp.asset_id
            FROM biz_paper bp
            JOIN asset_registry ar ON ar.asset_id = bp.asset_id
            WHERE bp.source_url = ? AND ar.is_deleted = 0
            LIMIT 1
            """,
            (source_url,),
        ).fetchone()
        return int(row["asset_id"]) if row else None

    def _score_arxiv_entry(self, entry: dict[str, Any]) -> int:
        score = 70
        if entry["primary_category"] in {"cs.AI", "cs.CL", "cs.CV", "cs.LG"}:
            score += 10
        if entry["pdf_url"]:
            score += 10
        if len(entry["authors"]) >= 3:
            score += 5
        return min(score, 100)

    def _seed_conferences(self, conn: sqlite3.Connection) -> None:
        count = int(conn.execute("SELECT COUNT(*) FROM biz_conference").fetchone()[0])
        if count:
            return
        now = utc_now()
        seeds = [
            ("NeurIPS", "NeurIPS", 2026, "CCF-A", "Machine Learning", "", "", "", "tracking"),
            ("ICML", "ICML", 2026, "CCF-A", "Machine Learning", "", "", "", "tracking"),
            ("ICLR", "ICLR", 2027, "CCF-A", "Machine Learning", "", "", "", "tracking"),
            ("KDD", "KDD", 2026, "CCF-A", "Data Mining", "", "", "", "tracking"),
            ("ACL", "ACL", 2026, "CCF-A", "NLP", "", "", "", "tracking"),
            ("AAAI", "AAAI", 2027, "CCF-A", "AI", "", "", "", "tracking"),
        ]
        conn.executemany(
            """
            INSERT INTO biz_conference (
                name, acronym, year, rank, field, abstract_deadline,
                paper_deadline, notification_date, status, url, notes,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', ?, ?)
            """,
            [(*seed, now, now) for seed in seeds],
        )

    def _score_paper(self, row: sqlite3.Row) -> tuple[int, str]:
        score = 50
        reasons: list[str] = []
        if row["paper_stage"] in {"refined", "review_confirmed", "sectioned", "noted"}:
            score += 20
            reasons.append("refined artifact is available")
        if row["refine_status"] == "succeeded":
            score += 10
            reasons.append("parse refinement succeeded")
        if row["review_status"] == "waiting_review":
            score += 10
            reasons.append("waiting for human review")
        if row["ccf_rank"] or row["sci_quartile"]:
            score += 10
            reasons.append("venue ranking metadata is present")
        return min(score, 100), "; ".join(reasons) or "recently updated paper"

    def _page(self, query: dict[str, Any]) -> tuple[int, int, int]:
        page = max(int(query.get("page", 1)), 1)
        page_size = min(max(int(query.get("page_size", 20)), 1), 100)
        return page, page_size, (page - 1) * page_size

    def _feed_from_row(self, row: sqlite3.Row) -> FeedItemRecord:
        return FeedItemRecord(
            item_id=int(row["item_id"]),
            paper_id=int(row["paper_asset_id"]),
            title=row["title"],
            abstract=row["abstract"] or "",
            authors=json.loads(row["authors"] or "[]"),
            year=int(row["pub_year"]) if row["pub_year"] is not None else None,
            venue=row["venue"] or "",
            source_url=row["source_url"] or "",
            pdf_url=row["pdf_url"] or "",
            score=int(row["score"]),
            reason=row["reason"],
            topic=row["topic"],
            status=row["status"],
            source=row["source"],
            feed_date=row["feed_date"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _conference_from_row(self, row: sqlite3.Row) -> ConferenceRecord:
        return ConferenceRecord(
            conference_id=int(row["conference_id"]),
            name=row["name"],
            acronym=row["acronym"],
            year=int(row["year"]),
            rank=row["rank"],
            field=row["field"],
            abstract_deadline=row["abstract_deadline"],
            paper_deadline=row["paper_deadline"],
            notification_date=row["notification_date"],
            status=row["status"],
            url=row["url"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
