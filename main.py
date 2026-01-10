from fastapi import FastAPI, Query
from typing import List, Optional

from sources.rss_feeds import RSSFeeds
from storage import save_to_json
import asyncio

app = FastAPI(
    title="RSS Job Aggregation API",
    description="Aggregates remote jobs from multiple RSS feeds",
    version="1.0.0",
)

RSS_URLS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://remotive.com/remote-jobs/feed",
    "https://remoteok.com/remote-python-jobs.rss",
]

rss_source = RSSFeeds()

async def fetch_rss_async(url: str) -> List[dict]:
    return await asyncio.to_thread(rss_source.fetch, url)

@app.get("/jobs")
async def get_jobs(
    q: Optional[str] = Query(None, description="Keyword search (title/description)"),
    source: Optional[str] = Query(None, description="Filter by job source"),
    limit: int = Query(50, le=200),
    save: bool = Query(False, description="Save results to JSON file"),
):

    # 🔄 Fetch all feeds concurrently
    tasks = [fetch_rss_async(url) for url in RSS_URLS]
    results = await asyncio.gather(*tasks)

    # Flatten results
    all_jobs = [job for feed in results for job in feed]

    # 🔍 Query-based filtering
    if q:
        q = q.lower()
        all_jobs = [
            job for job in all_jobs
            if q in job.title.lower()
            or q in " ".join(job.skills).lower()
            or (job.tag and q in job.tag.lower())
        ]

    # 🎯 Source filter (optional)
    if source:
        all_jobs = [
            job for job in all_jobs
            if source.lower() in (job.get("source") or "").lower()
        ]

    # ✂️ Limit results
    all_jobs = all_jobs[:limit]

    # 💾 Optional file save
    if save:
        save_to_json(all_jobs)

    return all_jobs
