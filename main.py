from fastapi import FastAPI, Query, Request
from fastapi.responses import Response

from sources.base import JobPosting
from sources.async_scripts import get_cached_jobs, redis_client, limiter

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from contextlib import asynccontextmanager
from typing import List, Optional

import logging
import os

from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests")
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency")
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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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


@limiter.limit(RATE_LIMIT)
@app.get("/jobs", response_model=List[JobPosting])
async def get_jobs(
    request: Request, # REQUIRED for SlowAPI
    q: Optional[str] = Query(None, max_length=100, pattern="^[a-zA-Z0-9 ]+$", description="Keyword search (title/description)"),
    company: Optional[str] = Query(None, max_length=100, pattern="^[a-zA-Z0-9 ]+$", description="Filter by job source"),
    page : int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of results per page"),
):

    # 🚀 Aggregate jobs from all sources
    jobs = await get_cached_jobs() or []

    logging.info(f"Total jobs before filtering: {len(jobs)}")

    # 🔍 Query-based filtering
    if q:
        q = q.lower()
        jobs = [
            job for job in jobs
            if q in job.title.lower()
            or q in " ".join(job.skills).lower()
            or (job.tag and q in job.tag.lower())
        ]
        logging.info(f"Total jobs after query filter '{q}': {len(jobs)}")

    # 🎯 Source filter (optional)
    if company:
        jobs = [
            job for job in jobs
            if company.lower() in (job.company.lower() if job.company else "None")
        ]
        logging.info(f"Total jobs after company filter '{company}': {len(jobs)}")

    # ✂️ Limit results
    start = (page - 1) * page_size
    end = start + page_size
    jobs = jobs[start:end]

    return jobs
