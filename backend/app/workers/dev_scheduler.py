# app/core/scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore

from app.modules.orders.jobs import (
    scheduled_order_visibility_job,
    scheduled_order_reminder_job,
    scheduled_order_expiry_job,
)

# -----------------------------
# APScheduler configuration
# -----------------------------
jobstores = {
    "default": MemoryJobStore()
}

executors = {
    "default": ThreadPoolExecutor(max_workers=5)
}

job_defaults = {
    "coalesce": True,
    "max_instances": 1,
    "misfire_grace_time": 30,
}

scheduler = BackgroundScheduler(
    timezone="UTC",
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
)


# -----------------------------
# Lifecycle helpers
# -----------------------------
def start_scheduler():
    if scheduler.running:
        return

    scheduler.add_job(
        scheduled_order_visibility_job,
        trigger="interval",
        seconds=30,
        id="scheduled_order_visibility",
        replace_existing=True,
    )

    scheduler.add_job(
        scheduled_order_reminder_job,
        trigger="interval",
        seconds=60,
        id="scheduled_order_reminder",
        replace_existing=True,
    )

    scheduler.add_job(
        scheduled_order_expiry_job,
        trigger="interval",
        seconds=60,
        id="scheduled_order_expiry",
        replace_existing=True,
    )

    scheduler.start()
    print("🕒 APScheduler started")


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("🛑 APScheduler stopped")
