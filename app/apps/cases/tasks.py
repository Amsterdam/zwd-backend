


import celery

DEFAULT_RETRY_DELAY = 2
MAX_RETRIES = 6

LOCK_EXPIRE = 5

class BaseTaskWithRetry(celery.Task):
    autoretry_for = (Exception,)
    max_retries = MAX_RETRIES
    default_retry_delay = DEFAULT_RETRY_DELAY


@celery.shared_task(bind=True, base=BaseTaskWithRetry)
def task_create_case(self, case_id):
    return f"task_create_casesuccess: '{case_id}'"