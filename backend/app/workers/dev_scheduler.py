from apscheduler.schedulers.blocking import BlockingScheduler
from app.workers.scheduled_orders import run_executor


def start_scheduler():
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        run_executor,
        trigger="interval",
        minutes=1,
        id="scheduled_orders_executor",
        replace_existing=True,
    )

    print("🟢 Scheduled Orders Executor running every 1 minute...")
    scheduler.start()


if __name__ == "__main__":
    start_scheduler()
