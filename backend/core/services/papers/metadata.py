from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any


ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}
CCF_RANK_BY_VENUE = {
    "aaai": "CCF-A",
    "acl": "CCF-A",
    "association for computational linguistics": "CCF-A",
    "cvpr": "CCF-A",
    "computer vision and pattern recognition": "CCF-A",
    "eccv": "CCF-A",
    "iccv": "CCF-A",
    "icde": "CCF-A",
    "icml": "CCF-A",
    "international conference on machine learning": "CCF-A",
    "icra": "CCF-A",
    "ijcai": "CCF-A",
    "kdd": "CCF-A",
    "nips": "CCF-A",
    "neurips": "CCF-A",
    "neural information processing systems": "CCF-A",
    "sigir": "CCF-A",
    "sigmod": "CCF-A",
    "www": "CCF-A",
    "emnlp": "CCF-B",
    "naacl": "CCF-B",
    "coling": "CCF-B",
}
SCI_Q1_VENUES = {
    "cell",
    "nature",
    "pnas",
    "proceedings of the national academy of sciences",
    "science",
}


def authors_from_value(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        if not value.strip():
            return []
        return [part.strip() for part in re.split(r"\s*;\s*|\s*,\s*", value) if part.strip()]
    return []


def authors_from_resolution(resolution: object) -> list[str]:
    for field_name in ("authors", "author", "creator", "creators"):
        authors = authors_from_value(getattr(resolution, field_name, None))
        if authors:
            return authors
    return authors_from_arxiv_resolution(resolution)


def authors_from_arxiv_resolution(resolution: object) -> list[str]:
    arxiv_id = arxiv_id_from_resolution(resolution)
    if not arxiv_id:
        return []
    return fetch_arxiv_authors(arxiv_id)


def arxiv_id_from_resolution(resolution: object) -> str:
    for field_name in ("raw_input", "landing_url", "final_url", "pdf_url"):
        arxiv_id = arxiv_id_from_text(str(getattr(resolution, field_name, "") or ""))
        if arxiv_id:
            return arxiv_id
    return ""


def arxiv_id_from_text(text: str) -> str:
    match = re.search(
        r"arxiv\.org/(?:abs|pdf)/(?P<id>\d{4}\.\d{4,5}(?:v\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group("id").removesuffix(".pdf")

    match = re.search(r"\barXiv:(?P<id>\d{4}\.\d{4,5}(?:v\d+)?)", text, re.IGNORECASE)
    if match:
        return match.group("id")
    return ""


def fetch_arxiv_authors(arxiv_id: str) -> list[str]:
    query = urllib.parse.urlencode({"id_list": arxiv_id})
    request = urllib.request.Request(
        f"{ARXIV_API_URL}?{query}",
        headers={"User-Agent": "Research-Flow/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = response.read()
    except Exception:
        return []

    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return []

    entry = root.find("atom:entry", ARXIV_NS)
    if entry is None:
        return []

    authors: list[str] = []
    for author in entry.findall("atom:author", ARXIV_NS):
        name = author.findtext("atom:name", default="", namespaces=ARXIV_NS).strip()
        if name:
            authors.append(name)
    return authors


def fetch_arxiv_metadata(arxiv_id: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"id_list": arxiv_id})
    request = urllib.request.Request(
        f"{ARXIV_API_URL}?{query}",
        headers={"User-Agent": "Research-Flow/0.1"},
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        payload = response.read()

    root = ET.fromstring(payload)
    entry = root.find("atom:entry", ARXIV_NS)
    if entry is None:
        raise ValueError(f"arXiv record not found: {arxiv_id}")

    title = re.sub(
        r"\s+",
        " ",
        entry.findtext("atom:title", default="", namespaces=ARXIV_NS),
    ).strip()
    summary = re.sub(
        r"\s+",
        " ",
        entry.findtext("atom:summary", default="", namespaces=ARXIV_NS),
    ).strip()
    published = entry.findtext("atom:published", default="", namespaces=ARXIV_NS)
    year: int | None = None
    if len(published) >= 4 and published[:4].isdigit():
        year = int(published[:4])
    authors: list[str] = []
    for author in entry.findall("atom:author", ARXIV_NS):
        name = author.findtext("atom:name", default="", namespaces=ARXIV_NS).strip()
        if name:
            authors.append(name)
    return {
        "title": title,
        "abstract": summary,
        "authors": authors,
        "year": year,
        "venue": "arXiv",
        "doi": f"10.48550/arXiv.{arxiv_id}",
        "source_url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
    }


def infer_ccf_rank(*venues: str) -> str:
    for venue in venues:
        normalized = normalize_venue_key(venue)
        if normalized in CCF_RANK_BY_VENUE:
            return CCF_RANK_BY_VENUE[normalized]
        words = set(normalized.split())
        for key, rank in CCF_RANK_BY_VENUE.items():
            if key in words:
                return rank
            if " " in key and key in normalized:
                return rank
    return ""


def infer_sci_quartile(*venues: str) -> str:
    for venue in venues:
        normalized = normalize_venue_key(venue)
        if normalized in SCI_Q1_VENUES:
            return "SCI Q1"
        for key in SCI_Q1_VENUES:
            if key in normalized:
                return "SCI Q1"
    return ""


def normalize_venue_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
