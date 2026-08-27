from xml.etree import ElementTree as ET

import httpx

from src.exceptions import ArxivEntryNotFoundError
from src.services.FetchService.retry import retry_on_transient_error
from src.services.FetchService.schemas import PaperMetadata

_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivMetadataFetcher:
    """Fetches paper metadata from the arXiv Atom API. Implements MetadataFetcher."""

    def __init__(self, http_client: httpx.AsyncClient, api_base: str):
        self._http_client = http_client
        self._api_base = api_base

    @retry_on_transient_error
    async def fetch(self, paper_id: str) -> PaperMetadata:
        response = await self._http_client.get(self._api_base, params={"id_list": paper_id})
        response.raise_for_status()
        return self._parse(response.text, paper_id)

    def _parse(self, atom_xml: str, arxiv_id: str) -> PaperMetadata:
        root = ET.fromstring(atom_xml)
        entry = root.find("atom:entry", _ATOM_NS)
        if entry is None:
            raise ArxivEntryNotFoundError(arxiv_id)

        title = (entry.findtext("atom:title", default="", namespaces=_ATOM_NS) or "").strip()
        abstract = (entry.findtext("atom:summary", default="", namespaces=_ATOM_NS) or "").strip()
        published_raw = entry.findtext("atom:published", default="", namespaces=_ATOM_NS)

        authors = [
            (author.findtext("atom:name", default="", namespaces=_ATOM_NS) or "").strip()
            for author in entry.findall("atom:author", _ATOM_NS)
        ]
        categories = [
            category.get("term")
            for category in entry.findall("atom:category", _ATOM_NS)
            if category.get("term")
        ]
        pdf_url = next(
            (
                link.get("href")
                for link in entry.findall("atom:link", _ATOM_NS)
                if link.get("title") == "pdf" and link.get("href")
            ),
            f"https://arxiv.org/pdf/{arxiv_id}",
        )

        return PaperMetadata(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            abstract=abstract,
            categories=categories,
            published_at=published_raw,
            pdf_url=pdf_url,
        )
