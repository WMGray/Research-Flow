"""Celery task registration package."""

from worker.tasks import conference, feed, knowledge, papers, presentation, projects

__all__ = [
    "conference",
    "feed",
    "knowledge",
    "papers",
    "presentation",
    "projects",
]
