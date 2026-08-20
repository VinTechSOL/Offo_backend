from apscheduler.schedulers.background import BackgroundScheduler

from app.modules.orders.scheduler import auto_cancel_runner
from app.modules.orders.jobs import scheduled_order_reminder_job
from app.modules.payments.refund_processor import process_pending_refunds

scheduler = BackgroundScheduler(
    timezone="UTC"
)


def start_scheduler():
    if scheduler.running:
        return

    scheduler.add_job(
        auto_cancel_runner,
        trigger="interval",
        minutes=1,
        id="order_auto_cancel",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        scheduled_order_reminder_job,
        trigger="interval",
        minutes=1,
        id="scheduled_order_reminder",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        process_pending_refunds,
        trigger="interval",
        minutes=1,
        id="payment_refund_processor",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()

    print("✅ Order scheduler started")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("🛑 Order scheduler stopped")