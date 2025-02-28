import os
from typing import Dict, Any
from pathlib import Path
import json


# RabbitMQ Configuration
RABBITMQ_CONFIG: Dict = {
    'host': os.getenv('RABBITMQ_HOST', 'localhost'),
    'port': int(os.getenv('RABBITMQ_PORT', '5672')),
    'username': os.getenv('RABBITMQ_USER', 'guest'),
    'password': os.getenv('RABBITMQ_PASSWORD', 'guest'),
    'vhost': os.getenv('RABBITMQ_VHOST', '/')
}

# Redis Configuration
REDIS_CONFIG: Dict = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', '6379')),
    'db': int(os.getenv('REDIS_DB', '0')),
    'password': os.getenv('REDIS_PASSWORD', None)
}

# Loan Processing Rules
LOAN_RULES: Dict[str, Any] = {
    'MIN_CREDIT_SCORE': 650,
    'MAX_DTI_RATIO': 0.43,
    'MIN_INCOME_MULTIPLIER': 3,
    'MAX_LOAN_DURATION_YEARS': 30,
    'MIN_LOAN_AMOUNT': 50000,
    'MAX_LOAN_AMOUNT': 2000000,
    'REQUIRED_DOCUMENTS': [
        'identity_proof',
        'income_proof',
        'tax_notice',
        'property_details'
    ]
}

# Service URLs
SERVICE_URLS: Dict[str, str] = {
    'loan_request': os.getenv('LOAN_REQUEST_URL', 'http://loan-request:8000'),
    'credit_check': os.getenv('CREDIT_CHECK_URL', 'http://credit-check:8001'),
    'property_evaluation': os.getenv('PROPERTY_EVAL_URL', 'http://property-evaluation:8002'),
    'decision': os.getenv('DECISION_URL', 'http://decision:8003'),
    'notification': os.getenv('NOTIFICATION_URL', 'http://notification:8004'),
}

# Monitoring Configuration
MONITORING_CONFIG: Dict = {
    'metrics_port': int(os.getenv('METRICS_PORT', '9090')),
    'enable_metrics': os.getenv('ENABLE_METRICS', 'True').lower() == 'true'
}

# Logging Configuration
LOGGING_CONFIG: Dict[str, Any] = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True
        },
    }
}

# API Configuration
API_CONFIG: Dict = {
    'debug': os.getenv('DEBUG', 'False').lower() == 'true',
    'host': os.getenv('API_HOST', '0.0.0.0'),
    'port': int(os.getenv('API_PORT', '8000'))
}

# Celery Configuration
CELERY_CONFIG: Dict = {
    'broker_url': f"amqp://{RABBITMQ_CONFIG['username']}:{RABBITMQ_CONFIG['password']}@{RABBITMQ_CONFIG['host']}:{RABBITMQ_CONFIG['port']}/{RABBITMQ_CONFIG['vhost']}",
    'result_backend': f"redis://{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/{REDIS_CONFIG['db']}",
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'enable_utc': True,
    'task_track_started': True,
    'task_time_limit': 30 * 60,  # 30 minutes
    'task_soft_time_limit': 25 * 60,  # 25 minutes
    'worker_prefetch_multiplier': 1
}