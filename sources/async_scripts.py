from sources.base import JobPosting
from sources.rss_feeds import RSSFeeds
from sources.variables import REDIS_URL, CACHE_TTL, RSS_URLS

from slowapi import Limiter
from slowapi.util import get_remote_address

from urllib.parse import urlparse
import ipaddress
import socket

from redis.asyncio import Redis
import json
import asyncio
import hashlib
import logging

rss_source = RSSFeeds()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL
)

# 🔒 Redis client for caching (if needed in future)
redis_client = Redis.from_url(
    REDIS_URL,
    decode_responses=True
)

# 🔍 Validate feed URLs to avoid SSRF
def validate_feed_url(url: str) -> bool:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return False

    try:
        ip = socket.gethostbyname(parsed.hostname)
        if ipaddress.ip_address(ip).is_private:
            return False
    except Exception:
        return False

    return True

async def get_feed_urls():
    feeds = await redis_client.smembers("rss:feeds")
    return list(feeds) or RSS_URLS

#################################################################
RSS_SEMAPHORE = asyncio.Semaphore(5)

async def fetch_rss_async(url: str):
    async with RSS_SEMAPHORE:
        return await asyncio.wait_for(asyncio.to_thread(rss_source.fetch, url), timeout=15.0)

def job_hash(job: JobPosting) -> str:
    key = f"{job.title.lower().strip()}{job.company or ''}{job.url}"
    return hashlib.sha256(key.encode()).hexdigest()

async def aggregate_jobs() -> list[JobPosting]:
    # 🔄 Fetch all feeds concurrently
    feed_urls = await get_feed_urls()
    tasks = [fetch_rss_async(url) for url in feed_urls]
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

async def get_cached_jobs():

    try:
        cached = await redis_client.get("jobs:all")
        if cached:
            return [JobPosting.model_validate(j) for j in json.loads(cached)]
    except Exception:
        logging.warning("Redis read failed", exc_info=True)
    
    lock = await redis_client.set("jobs:lock", "1", nx=True, ex=30)

    if lock:
        # We are the cache builder
        jobs = await aggregate_jobs()

        try:
            await redis_client.setex(
                "jobs:all",
                CACHE_TTL,
                json.dumps([job.model_dump(mode="json") for job in jobs])
            )
        except Exception:
            logging.warning("Redis write failed", exc_info=True)

        return jobs

    # Another worker is building the cache
    for _ in range(3):
        await asyncio.sleep(1)
        try:
            cached = await redis_client.get("jobs:all")
            if cached:
                return [
                    JobPosting.model_validate(j)
                    for j in json.loads(cached)
                ]
        except Exception:
            break

    # Absolute fallback (never return None)
    logging.warning("Cache unavailable, falling back to direct fetch")
    return await aggregate_jobs()

