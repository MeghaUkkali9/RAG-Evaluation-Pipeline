from xml.etree import ElementTree as ET

import httpx

from src.exceptions import ArxivEntryNotFoundError
from src.services.FetchService.retry import RateLimiter, retry_request
from src.services.FetchService.schemas import PaperMetadata

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivMetadataFetcher:
    def __init__(self, http_client: httpx.AsyncClient, api_base: str, rate_limiter: RateLimiter):
        self._http_client = http_client
        self._api_base = api_base
        self._rate_limiter = rate_limiter

    async def fetch(self, paper_id: str) -> PaperMetadata:
        
        async def send_request() -> httpx.Response:
            
            await self._rate_limiter.wait()
            
            response = await self._http_client.get(self._api_base, params={"id_list": paper_id})
            response.raise_for_status()
            
            return response

        response = await retry_request(send_request)
        return self._parse(response.text, paper_id)

    def _parse(self, atom_xml: str, arxiv_id: str) -> PaperMetadata:
        root = ET.fromstring(atom_xml)
        entry = root.find("atom:entry", ATOM_NS)
        
        if entry is None:
            raise ArxivEntryNotFoundError(arxiv_id)

        title = (entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip()
        abstract = (entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or "").strip()
        published_raw = entry.findtext("atom:published", default="", namespaces=ATOM_NS)

        authors = [
            (author.findtext("atom:name", default="", namespaces=ATOM_NS) or "").strip()
            for author in entry.findall("atom:author", ATOM_NS)
        ]
        categories = [
            category.get("term")
            for category in entry.findall("atom:category", ATOM_NS)
            if category.get("term")
        ]
        pdf_url = next(
            (
                link.get("href")
                for link in entry.findall("atom:link", ATOM_NS)
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
            published_date=published_raw,
            pdf_url=pdf_url,
        )
