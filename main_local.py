from sources.rss_feeds import RSSFeeds
from storage import save_to_json

def main():

    rss_urls = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://remotive.com/remote-jobs/feed",
        "https://remoteok.com/remote-python-jobs.rss"
    ]

    source = RSSFeeds()
    all_jobs = []
    for url in rss_urls:
        jobs = source.fetch(url)
        all_jobs.extend(jobs)

    save_to_json(all_jobs)
    print(f"Saved {len(all_jobs)} jobs")

if __name__ == "__main__":
    main()
