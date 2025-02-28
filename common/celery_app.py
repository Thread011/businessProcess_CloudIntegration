from celery import Celery, signals
from prometheus_client import Counter, Histogram, Gauge
import os
import time
import logging
from .config import REDIS_CONFIG, RABBITMQ_CONFIG

# Initialize Celery
celery_app = Celery('loan_processing')

# Celery Configuration
celery_app.conf.update(
    broker_url=f"amqp://{RABBITMQ_CONFIG['username']}:{RABBITMQ_CONFIG['password']}@{RABBITMQ_CONFIG['host']}:{RABBITMQ_CONFIG['port']}/",
    result_backend=f"redis://{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/0",
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    task_routes={
        'loan_request.*': {'queue': 'loan_request'},
        'credit_check.*': {'queue': 'credit_check'},
        'property_evaluation.*': {'queue': 'property_evaluation'},
        'decision.*': {'queue': 'decision'},
        'notification.*': {'queue': 'notification'}
    }
)

# Prometheus Metrics
TASK_LATENCY = Histogram(
    'celery_task_latency_seconds',
    'Task execution time in seconds',
    ['task_name']
)

TASK_COUNTER = Counter(
    'celery_task_execution_total',
    'Number of task executions',
    ['task_name', 'status']
)

TASK_FAILURE_COUNTER = Counter(
    'celery_task_failures_total',
    'Number of task failures',
    ['task_name']
)

QUEUE_SIZE = Gauge(
    'celery_queue_size',
    'Number of tasks in queue',
    ['queue_name']
)

TASK_SUCCESS_COUNTER = Counter(
    'celery_task_success_total',
    'Number of task successes',
    ['task_name']
)

logger = logging.getLogger(__name__)

# Celery Task Events
@signals.task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    try:
        queue = getattr(task.request, 'queue', None) or 'default'
        QUEUE_SIZE.labels(queue).inc()
    except (AttributeError, TypeError):
        QUEUE_SIZE.labels('default').inc()

@signals.task_postrun.connect
def task_postrun_handler(task_id, task, retval, state, **kwargs):
    """Handle task post-run events for metrics"""
    try:
        # Get task duration if available
        duration = getattr(task.request, 'runtime', None)
        if duration is None:
            # If runtime is not available, try to calculate from timestamps
            start_time = getattr(task.request, 'start_time', None)
            if start_time:
                duration = time.time() - start_time
            else:
                duration = 0  # Default if we can't calculate
                
        # Record task completion metrics
        task_name = task.name
        TASK_SUCCESS_COUNTER.labels(task_name=task_name).inc()
        
        # Log completion
        logger.info(f"Task {task_name}[{task_id}] completed with state {state}")
        
    except Exception as e:
        # Don't let metrics collection break task processing
        logger.error(f"Error in task_postrun_handler: {str(e)}")
        pass