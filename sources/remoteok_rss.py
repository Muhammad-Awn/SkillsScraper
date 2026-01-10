from typing import List
from sources.base import JobSource, JobPosting
from sources.scripts import skills_finder
from dateutil import parser
import feedparser

class RemoteOKSource(JobSource):
    feed_url = "https://remoteok.com/remote-python-jobs.rss"

    def fetch(self) -> List[JobPosting]:
        feed = feedparser.parse(self.feed_url)

        jobs = []
        for item in feed.entries:
            if item.get("tags", "N/A")[0]['term'] not in ["Writing", "Sales / Business", "Marketing", "All others", "Education"]:
                skills = skills_finder(item.get("summary", ""))


                jobs.append(
                    JobPosting(
                        source=feed.feed.title,
                        title=item.title,
                        company=item.get("company", "N/A"),
                        tag = item.get("tags", "N/A")[0]['term'],
                        url=item.link,
                        location=item.get("location", "N/A"),
                        published_at=parser.parse(item.get("published", "N/A")),
                        skills=skills
                    )
                )
        return jobs
