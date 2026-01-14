from typing import List
from sources.base import JobPosting
import json

def save_to_json(jobs: List[JobPosting], filename="jobs.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump([job.dict() for job in jobs], f, indent=2, default=str)
