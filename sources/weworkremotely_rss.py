from typing import List
from sources.base import JobSource, JobPosting
from sources.scripts import skills_finder
from dateutil import parser
import feedparser

class WeWorkRemotelyRSSSource(JobSource):
    feed_url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"

    def fetch(self) -> List[JobPosting]:
        feed = feedparser.parse(self.feed_url)

        jobs = []
        for item in feed.entries:
            if item.get("tags", "N/A")[0]['term'] not in ["Writing", "Sales / Business", "Marketing", "All others", "Education"]:
                skills = skills_finder(item.get("summary", ""))
                company_name, job_title = item.title.split(":", 1)

                jobs.append(
                    JobPosting(
                        source=feed.feed.title,
                        title=job_title.strip(),
                        company=company_name.strip(),
                        tag = item.get("tags", "N/A")[0]['term'],
                        url=item.link,
                        location=item.get("location", "N/A"),
                        published_at=parser.parse(item.get("published", "N/A")),
                        skills=skills
                    )
                )
        return jobs
