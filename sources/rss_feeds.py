from typing import List
from sources.base import JobSource, JobPosting
from sources.scripts import skills_finder
from dateutil import parser
import feedparser

class RSSFeeds(JobSource):

    def fetch(self, feed_url) -> List[JobPosting]:
        feed = feedparser.parse(feed_url)

        jobs = []
        for item in feed.entries:
            if item.get("tags", "N/A")[0]['term'] not in ["Writing", "Sales / Business", "Marketing", "All others", "Education"]:
                skills = skills_finder(item.get("summary", ""))
                
                if ":" in item.title:
                    company_name, job_title = item.title.split(":", 1)
                    company_name = company_name.strip()
                    job_title = job_title.strip()
                else:
                    job_title = item.title
                    company_name = item.get("author", item.get("company", "N/A"))

                jobs.append(
                    JobPosting(
                        source=feed.feed.title,
                        title=job_title,
                        company=company_name,
                        tag = item.get("tags", "N/A")[0]['term'],
                        url=item.link,
                        location=item.get("location", "N/A"),
                        published_at=parser.parse(item.get("published", "N/A")),
                        skills=skills
                    )
                )
        return jobs
