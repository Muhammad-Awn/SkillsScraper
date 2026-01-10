from abc import ABC, abstractmethod
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List

class JobPosting(BaseModel):
    source: str
    title: str
    company: Optional[str]
    tag: Optional[str]
    url: HttpUrl
    location: Optional[str]
    published_at: Optional[datetime]
    skills: List[str] = []

class JobSource(ABC):
    @abstractmethod
    def fetch(self, query: str) -> List[JobPosting]:
        pass
