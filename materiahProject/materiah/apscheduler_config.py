from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
import logging
from .tasks import refresh_order_notifications, delete_failed_upload_statuses


def start_scheduler():
    # Configure logging for APScheduler
    logging.basicConfig()
    logging.getLogger('apscheduler').setLevel(logging.DEBUG)

    executors = {
        'default': ThreadPoolExecutor(20),
        'processpool': ProcessPoolExecutor(5)
    }

    job_defaults = {
        'coalesce': False,
        'max_instances': 1
    }

    scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults)

    # Schedule 'refresh_order_notifications' to run every day at midnight
    scheduler.add_job(refresh_order_notifications, 'cron', hour=0, minute=0)

    # Schedule 'delete_failed_upload_statuses' to run every minute
    scheduler.add_job(delete_failed_upload_statuses, 'interval', minutes=1)

    scheduler.start()
    print("Scheduler started...", flush=True)
