"""
This module imports all Celery tasks from the various services
to ensure they are registered with the Celery worker.
"""

# Import Celery app
from .celery_app import celery_app

# Import tasks from services
# Notification Service
try:
    from services.notification.tasks import send_notification
except ImportError:
    print("Warning: Could not import notification tasks")

# Loan Request Service
try:
    from services.loan_request.tasks import *
except ImportError:
    print("Warning: Could not import loan_request tasks")

# Credit Check Service
try:
    from services.credit_check.tasks import *
except ImportError:
    print("Warning: Could not import credit_check tasks")

# Property Evaluation Service
try:
    from services.property_evaluation.tasks import *
except ImportError:
    print("Warning: Could not import property_evaluation tasks")

# Decision Service
try:
    from services.decision.tasks import *
except ImportError:
    print("Warning: Could not import decision tasks")

# List of all available tasks for reference
available_tasks = celery_app.tasks.keys()
print(f"Available Celery tasks: {available_tasks}")
