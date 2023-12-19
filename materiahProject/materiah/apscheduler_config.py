from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
import logging
from .tasks import refresh_order_notifications, delete_failed_upload_statuses


def start_scheduler():
    """
       start_scheduler handles the setup and starting of the job scheduler. Utilizes
       the Advanced Python Scheduler (APScheduler) to run jobs in the background.
       The function sets up logging and then creates a BackgroundScheduler instance
       with ThreadPoolExecutor and ProcessPoolExecutor executors.
       It then defines two jobs that are to be run at specified intervals by the scheduler.
       """

    # Configure logging for the APScheduler. This will help in tracking
    # the operations being performed by the scheduler.
    logging.basicConfig()
    logging.getLogger('apscheduler').setLevel(logging.DEBUG)

    # Define executor instances that APScheduler will use to run jobs.
    # The ThreadPoolExecutor is used to run jobs in a pool of threads, and
    # the ProcessPoolExecutor is used to run jobs in a pool of processes.
    executors = {
        'default': ThreadPoolExecutor(20),
        'processpool': ProcessPoolExecutor(5)
    }

    # Define the defaults for jobs that will be added to the scheduler.
    job_defaults = {
        'coalesce': False,  # prevents jobs from bunching up
        'max_instances': 1  # only run one instance of each job at a time
    }

    # Create an instance of the BackgroundScheduler using the executors and job defaults
    scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults)

    # Add a job to the scheduler. The function 'refresh_order_notifications' will
    # be run daily at midnight according to the cron-like schedule specified by hour=0, minute=0.
    scheduler.add_job(refresh_order_notifications, 'cron', hour=0, minute=0)

    # Add another job to the scheduler. The function 'delete_failed_upload_statuses' will be
    # run every 20 minutes.
    scheduler.add_job(delete_failed_upload_statuses, 'interval', minutes=20)

    # Officially start the scheduler. No jobs will run until this method is called.
    scheduler.start()
    print("Scheduler started...", flush=True)
