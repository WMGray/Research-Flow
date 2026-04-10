from celery import Celery

from worker.config import CeleryConfig

celery = Celery("research-flow")
celery.config_from_object(CeleryConfig)
celery.autodiscover_tasks(["worker.tasks"])
