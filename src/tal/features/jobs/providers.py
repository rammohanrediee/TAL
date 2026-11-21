"""Public, no-auth ATS job feeds. Board URLs are validated before any HTTP call."""

import asyncio
import json
import re
import zlib
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_RESPONSE_BYTES = 4 * 1024 * 1024
BOARD_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,159}$")


@dataclass(frozen=True)
class BoardSource:
    provider: str
    slug: str
    board_url: str


@dataclass(frozen=True)
class FoundJob:
    external_id: str
    title: str
    location: str | None
    work_mode: str | None
    employment_type: str | None
    description: str | None
    job_url: str
    apply_url: str


@dataclass(frozen=True)
class FetchedFeed:
    jobs: list[FoundJob]
    source_snapshot: bytes


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, request: Request, fp: object, code: int, msg: str, headers: object, newurl: str
    ) -> None:
        raise ValueError("Job feed redirects are not allowed")


def parse_board_url(value: str) -> BoardSource:
    parsed = urlparse(value.strip())
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Use a public HTTPS Greenhouse, Lever, or Ashby board URL")
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    if (
        host
        in {
            "boards.greenhouse.io",
            "boards.eu.greenhouse.io",
            "job-boards.greenhouse.io",
            "job-boards.eu.greenhouse.io",
        }
        and len(parts) == 1
    ):
        provider = "greenhouse"
    elif host in {"jobs.lever.co", "jobs.eu.lever.co"} and len(parts) == 1:
        provider = "lever-eu" if host == "jobs.eu.lever.co" else "lever"
    elif host == "jobs.ashbyhq.com" and len(parts) == 1:
        provider = "ashby"
    else:
        raise ValueError("That board is not supported yet")
    slug = parts[0]
    if not BOARD_SLUG.fullmatch(slug):
        raise ValueError("Invalid board identifier")
    return BoardSource(provider, slug, f"https://{host}/{slug}")


def feed_url(source: BoardSource) -> str:
    slug = quote(source.slug, safe="")
    if source.provider == "greenhouse":
        return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    if source.provider in {"lever", "lever-eu"}:
        host = "api.eu.lever.co" if source.provider == "lever-eu" else "api.lever.co"
        return f"https://{host}/v0/postings/{slug}?mode=json"
    if source.provider == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    raise ValueError("Unsupported provider")


def _fetch_json(url: str) -> object:
    opener = build_opener(NoRedirect())
    request = Request(
        url, headers={"Accept": "application/json", "User-Agent": "TAL-Job-Scanner/1.0"}
    )
    try:
        with opener.open(request, timeout=12) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
            if len(data) > MAX_RESPONSE_BYTES:
                raise ValueError("Job feed is too large")
            return json.loads(data)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ValueError("Job feed is unavailable or invalid") from error


def _public_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    return (
        value
        if parsed.scheme == "https"
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        else None
    )


def normalize_jobs(source: BoardSource, data: object) -> list[FoundJob]:
    if source.provider == "greenhouse" or source.provider == "ashby":
        rows = data.get("jobs") if isinstance(data, dict) else None
    else:
        rows = data
    if not isinstance(rows, list):
        raise ValueError("Unexpected job feed format")
    jobs: list[FoundJob] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if source.provider == "greenhouse":
            external_id, title = row.get("id"), row.get("title")
            location = (
                row.get("location", {}).get("name")
                if isinstance(row.get("location"), dict)
                else None
            )
            job_url = _public_url(row.get("absolute_url"))
            apply_url = job_url
            description = row.get("content")
            employment_type = None
            work_mode = None
        elif source.provider == "ashby":
            if row.get("isListed") is False:
                continue
            external_id, title = row.get("id"), row.get("title")
            location = row.get("location")
            job_url = _public_url(row.get("jobUrl"))
            apply_url = _public_url(row.get("applyUrl")) or job_url
            description = row.get("descriptionPlain")
            employment_type = row.get("employmentType")
            work_mode = row.get("workplaceType")
        else:
            external_id, title = row.get("id"), row.get("text")
            categories = row.get("categories") or {}
            if not isinstance(categories, dict):
                categories = {}
            location = categories.get("location")
            job_url = _public_url(row.get("hostedUrl"))
            apply_url = _public_url(row.get("applyUrl")) or job_url
            description = row.get("descriptionPlain")
            employment_type = categories.get("commitment")
            work_mode = row.get("workplaceType")
        if (
            not external_id
            or not isinstance(title, str)
            or not title.strip()
            or not job_url
            or not apply_url
        ):
            continue
        jobs.append(
            FoundJob(
                str(external_id),
                title.strip(),
                location[:300] if isinstance(location, str) else None,
                work_mode[:24] if isinstance(work_mode, str) else None,
                employment_type[:80] if isinstance(employment_type, str) else None,
                description[:50_000] if isinstance(description, str) else None,
                job_url,
                apply_url,
            )
        )
    return jobs


async def fetch_jobs(source: BoardSource) -> FetchedFeed:
    data = await asyncio.to_thread(_fetch_json, feed_url(source))
    return FetchedFeed(
        normalize_jobs(source, data),
        zlib.compress(json.dumps(data, separators=(",", ":")).encode("utf-8")),
    )
