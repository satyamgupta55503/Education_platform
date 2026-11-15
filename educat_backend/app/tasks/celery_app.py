"""
EduCat AI — Celery App + All Background Tasks
Tasks: embedding generation, monthly token reset,
       session summary, PDF reports, data purge, BKT update.
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# ── Celery App ────────────────────────────────────────────────────
celery_app = Celery(
    "educat_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.celery_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,           # Ack after task completes (safe for crashes)
    worker_prefetch_multiplier=1,  # One task at a time per worker (prevents RAM spike)
    task_soft_time_limit=120,      # Warn after 2 min
    task_time_limit=300,           # Kill after 5 min
    beat_schedule={
        # Monthly token reset: 1st of every month at 00:01 IST
        "monthly-token-reset": {
            "task": "tasks.monthly_token_reset",
            "schedule": crontab(hour=18, minute=31, day_of_month=1),  # 00:01 IST = 18:31 UTC
        },
        # Daily streak update: midnight IST
        "daily-streak-update": {
            "task": "tasks.daily_streak_update",
            "schedule": crontab(hour=18, minute=35),  # 00:05 IST
        },
        # Weekly parent report: Saturday 8am IST
        "weekly-parent-report": {
            "task": "tasks.weekly_parent_report",
            "schedule": crontab(hour=2, minute=30, day_of_week=6),  # Sat 8:00 IST
        },
        # Data purge: daily 3am IST
        "daily-data-purge": {
            "task": "tasks.data_purge",
            "schedule": crontab(hour=21, minute=30),  # 03:00 IST
        },
        # Workspace quota reset: 1st of month at 01:00 IST
        "workspace-quota-reset": {
            "task": "tasks.workspace_quota_reset",
            "schedule": crontab(hour=19, minute=31, day_of_month=1),
        },
        # BM25 index rebuild: daily 4am IST
        "bm25-index-rebuild": {
            "task": "tasks.rebuild_bm25_indexes",
            "schedule": crontab(hour=22, minute=30),
        },
    },
)
