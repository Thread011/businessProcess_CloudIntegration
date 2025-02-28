from prometheus_client import Counter, Histogram, Gauge, start_http_server
from functools import wraps
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Service-level metrics
REQUEST_COUNTER = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['service', 'endpoint', 'method', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['service', 'endpoint', 'method']
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_active',
    'Number of active HTTP requests',
    ['service']
)

# Business metrics
LOAN_REQUESTS = Counter(
    'loan_requests_total',
    'Total number of loan requests',
    ['status']
)

LOAN_AMOUNT = Histogram(
    'loan_amount_euros',
    'Distribution of loan amounts',
    buckets=[50000, 100000, 250000, 500000, 1000000, 2000000]
)

def monitor_endpoint(service_name: str):
    """Decorator to monitor FastAPI endpoints"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            endpoint = func.__name__
            method = kwargs.get('method', 'unknown')
            
            ACTIVE_REQUESTS.labels(service=service_name).inc()
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                status = '2xx'
                return result
            except Exception as e:
                status = '5xx'
                raise
            finally:
                duration = time.time() - start_time
                ACTIVE_REQUESTS.labels(service=service_name).dec()
                REQUEST_COUNTER.labels(
                    service=service_name,
                    endpoint=endpoint,
                    method=method,
                    status=status
                ).inc()
                REQUEST_LATENCY.labels(
                    service=service_name,
                    endpoint=endpoint,
                    method=method
                ).observe(duration)
        
        return wrapper
    return decorator

class MetricsService:
    def __init__(self, service_name: str, port: int = 8000):
        self.service_name = service_name
        self.port = port
    
    def start(self):
        """Starts the Prometheus metrics HTTP server"""
        try:
            start_http_server(self.port)
            logger.info(f"Metrics server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {str(e)}")
            raise
    
    def record_loan_request(self, status: str):
        """Records a loan request with its status"""
        LOAN_REQUESTS.labels(status=status).inc()
    
    def record_loan_amount(self, amount: float):
        """Records a loan amount"""
        LOAN_AMOUNT.observe(amount)
    
    def custom_metric(
        self,
        metric_type: str,
        name: str,
        description: str,
        value: Any,
        labels: Optional[Dict[str, str]] = None
    ):
        """Records a custom metric"""
        try:
            if metric_type.lower() == 'counter':
                metric = Counter(name, description, labelnames=labels.keys() if labels else [])
                metric.labels(**labels).inc(value) if labels else metric.inc(value)
            elif metric_type.lower() == 'gauge':
                metric = Gauge(name, description, labelnames=labels.keys() if labels else [])
                metric.labels(**labels).set(value) if labels else metric.set(value)
            elif metric_type.lower() == 'histogram':
                metric = Histogram(name, description, buckets=buckets)
                metric.labels(**labels).observe(value) if labels else metric.observe(value)
            else:
                raise ValueError(f"Invalid metric type: {metric_type}")
        except Exception as e:
            logger.error(f"Error recording custom metric: {str(e)}")
            raise
