from fastapi import FastAPI, Query, Request
from fastapi.responses import Response
from typing import List, Optional
from sources.base import JobPosting
from sources.rss_feeds import RSSFeeds
from storage import save_to_json

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from contextlib import asynccontextmanager

from redis.asyncio import Redis
import json
import asyncio
import hashlib
import logging
import os

from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests")
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))
RATE_LIMIT = os.getenv("RATE_LIMIT", "10/minute")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.ping()
    yield
    await redis_client.close()

app = FastAPI(
    lifespan=lifespan,
    title="RSS Job Aggregation API",
    description="Aggregates remote jobs from multiple RSS feeds",
    version="1.0.0",
)

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL
)
app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

RSS_URLS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://remotive.com/remote-jobs/feed",
    "https://remoteok.com/remote-python-jobs.rss",
]

rss_source = RSSFeeds()

def job_hash(job: JobPosting) -> str:
    key = f"{job.title.lower().strip()}{job.company or ''}{job.url}"
    return hashlib.sha256(key.encode()).hexdigest()

async def fetch_rss_async(url: str) -> List[JobPosting]:
    return await asyncio.wait_for(asyncio.to_thread(rss_source.fetch, url), timeout=15.0)

async def aggregate_jobs() -> list[JobPosting]:
    # 🔄 Fetch all feeds concurrently
    tasks = [fetch_rss_async(url) for url in RSS_URLS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    jobs = []
    for result in results:
        if isinstance(result, Exception):
            logging.warning("Feed fetch failed", exc_info=result)
            continue
        jobs.extend(result)

    # 🧹 Deduplication
    seen = set()
    unique_jobs = []

    for job in jobs:
        h = job_hash(job)
        if h not in seen:
            seen.add(h)
            unique_jobs.append(job)

    return unique_jobs

# 🔒 Redis client for caching (if needed in future)
redis_client = Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

async def get_cached_jobs(fetch_fn):

    cached = await redis_client.get("jobs:all")
    if cached:
        return [JobPosting.model_validate(j) for j in json.loads(cached)]
    
    lock = await redis_client.set("jobs:lock", "1", nx=True, ex=30)
    if not lock:
        await asyncio.sleep(1)
        cached = await redis_client.get("jobs:all")
        if cached:
            return [JobPosting.model_validate(j) for j in json.loads(cached)]

    jobs = await fetch_fn()

    await redis_client.setex(
        "jobs:all",
        CACHE_TTL,  # TTL seconds
        json.dumps([job.model_dump() for job in jobs])
    )

    return jobs


@limiter.limit(RATE_LIMIT)
@app.get("/jobs", response_model=List[JobPosting])
async def get_jobs(
    request: Request, # REQUIRED for SlowAPI
    q: Optional[str] = Query(None, max_length=100, pattern="^[a-zA-Z0-9 ]+$", description="Keyword search (title/description)"),
    company: Optional[str] = Query(None, max_length=100, pattern="^[a-zA-Z0-9 ]+$", description="Filter by job source"),
    page : int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of results per page"),
    save: bool = Query(False, description="Save results to JSON file"),
):

    # 🚀 Aggregate jobs from all sources
    jobs = await get_cached_jobs(aggregate_jobs)

    # 🔍 Query-based filtering
    if q:
        q = q.lower()
        jobs = [
            job for job in jobs
            if q in job.title.lower()
            or q in " ".join(job.skills).lower()
            or (job.tag and q in job.tag.lower())
        ]

    # 🎯 Source filter (optional)
    if company:
        jobs = [
            job for job in jobs
            if company.lower() in (job.company.lower() if job.company else "None")
        ]

    # ✂️ Limit results
    start = (page - 1) * page_size
    end = start + page_size
    jobs = jobs[start:end]

    # 💾 Optional file save
    if save:
        save_to_json(jobs)
    return jobs


@app.get("/health")
async def health():
    try:
        await redis_client.ping()
        return {"status": "ok"}
    except Exception:
        return {"status": "degraded"}
    
@app.middleware("http")
async def metrics_middleware(request, call_next):
    REQUEST_COUNT.inc()
    with REQUEST_LATENCY.time():
        return await call_next(request)

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
