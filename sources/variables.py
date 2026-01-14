import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_URL="rediss://default:AVPRAAIncDEwMDNhY2E0YTM4NmM0Y2QyOWJiM2EyYWE5Mjk1ZWQyZXAxMjE0NTc@stirring-condor-21457.upstash.io:6379"
CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))

RSS_URLS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://remotive.com/remote-jobs/feed",
    "https://remoteok.com/remote-python-jobs.rss",
]

RATE_LIMIT = os.getenv("RATE_LIMIT", "10/minute")
UPLOAD_LIMIT = os.getenv("UPLOAD_LIMIT", "2/minute")
MAX_FEEDS = int(os.getenv("MAX_FEEDS", "10"))