from common.celery_app import celery_app, TASK_EXECUTION_TIME, TASK_FAILURE_COUNTER
from celery.utils.log import get_task_logger
from functools import wraps
import time

logger = get_task_logger(__name__)

def monitor_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        task_name = func.__name__
        try:
            result = func(*args, **kwargs)
            TASK_EXECUTION_TIME.labels(task_name=task_name).observe(
                time.time() - start_time
            )
            return result
        except Exception as e:
            TASK_FAILURE_COUNTER.labels(task_name=task_name).inc()
            logger.error(f"Task {task_name} failed: {str(e)}")
            raise
    return wrapper

@celery_app.task(
    name='credit_check.verify_credit_score',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
@monitor_task
def verify_credit_score(self, loan_request_id: str, client_data: dict):
    try:
        # Simulate credit check process
        time.sleep(5)  # Simulate external API call
        
        credit_score = 700  # Simulated score
        monthly_income = float(client_data['monthly_income'])
        monthly_expenses = float(client_data['monthly_expenses'])
        dti_ratio = monthly_expenses / monthly_income
        
        return {
            'loan_request_id': loan_request_id,
            'credit_score': credit_score,
            'dti_ratio': dti_ratio,
            'is_eligible': credit_score >= 650 and dti_ratio <= 0.43
        }
        
    except Exception as exc:
        logger.error(f"Credit check failed for request {loan_request_id}: {str(exc)}")
        self.retry(exc=exc)