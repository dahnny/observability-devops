import json
import logging
import os
import random
import time
from datetime import datetime

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


SERVICE_NAME = os.getenv("SERVICE_NAME", "sample-app")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://otel-collector:4317"
)


resource = Resource.create({
    "service.name": SERVICE_NAME
})


# -----------------------------
# 1. OpenTelemetry logging setup
# -----------------------------

logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(
        OTLPLogExporter(
            endpoint=OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,
        )
    )
)
set_logger_provider(logger_provider)

logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(logging.INFO)
logger.propagate = False

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)

otel_log_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logger.addHandler(otel_log_handler)


def get_trace_id() -> str:
    """
    Get the current OpenTelemetry trace ID.

    This is important because we want logs and traces to share the same ID.
    Later in Grafana, this lets us jump from a Loki log line to the Tempo trace.
    """
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context()

    if not span_context.is_valid:
        return "no-trace"

    return format(span_context.trace_id, "032x")


def log_json(level: str, message: str, **extra):
    """
    Write logs as JSON.

    Loki works better when logs are structured.
    Structured logs are easier to search than random plain text.
    """
    log_record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "service": SERVICE_NAME,
        "message": message,
        "trace_id": get_trace_id(),
        **extra,
    }

    logger.info(json.dumps(log_record))


# -----------------------------
# 2. OpenTelemetry tracing setup
# -----------------------------

trace_provider = TracerProvider(resource=resource)

otlp_exporter = OTLPSpanExporter(
    endpoint=OTEL_EXPORTER_OTLP_ENDPOINT,
    insecure=True,
)

trace_provider.add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

trace.set_tracer_provider(trace_provider)

tracer = trace.get_tracer(__name__)


# -----------------------------
# 3. FastAPI app
# -----------------------------

app = FastAPI(title="Stage 6 Sample App")

FastAPIInstrumentor.instrument_app(app)


# -----------------------------
# 4. Prometheus metrics
# -----------------------------

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path", "status_code"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2, 5],
)


@app.middleware("http")
async def metrics_and_logging_middleware(request: Request, call_next):
    """
    This middleware runs for every request.

    It measures:
    - request count
    - request duration
    - status code

    It also writes a structured log for each request.
    """
    start_time = time.time()

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        status_code = 500
        duration = time.time() - start_time

        REQUEST_COUNT.labels(
            method=request.method,
            path=request.url.path,
            status_code=str(status_code),
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            path=request.url.path,
            status_code=str(status_code),
        ).observe(duration)

        log_json(
            "error",
            "request failed",
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_seconds=duration,
            error=str(exc),
        )

        raise

    duration = time.time() - start_time

    REQUEST_COUNT.labels(
        method=request.method,
        path=request.url.path,
        status_code=str(status_code),
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        path=request.url.path,
        status_code=str(status_code),
    ).observe(duration)

    log_json(
        "info",
        "request completed",
        method=request.method,
        path=request.url.path,
        status_code=status_code,
        duration_seconds=duration,
    )

    return response


@app.get("/")
def root():
    return {
        "service": SERVICE_NAME,
        "message": "Stage 6 sample app is running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
    }


@app.get("/checkout")
def checkout():
    """
    A realistic business endpoint.

    In a real app, this could be payment/order processing.
    """
    with tracer.start_as_current_span("checkout-operation"):
        processing_time = random.uniform(0.1, 0.8)
        time.sleep(processing_time)

        log_json(
            "info",
            "checkout completed",
            endpoint="/checkout",
            processing_time_seconds=processing_time,
        )

        return {
            "status": "success",
            "message": "checkout completed",
            "processing_time_seconds": processing_time,
        }


@app.get("/slow")
def slow():
    """
    Used for latency testing.

    This helps us prove latency metrics, traces, and alerts later.
    """
    with tracer.start_as_current_span("slow-operation"):
        delay = random.uniform(2.0, 4.0)
        time.sleep(delay)

        log_json(
            "warning",
            "slow endpoint completed",
            endpoint="/slow",
            delay_seconds=delay,
        )

        return {
            "status": "slow",
            "delay_seconds": delay,
        }


@app.get("/error")
def error():
    """
    Used for error testing.

    This helps us prove error-rate metrics and alerts later.
    """
    log_json(
        "error",
        "intentional error triggered",
        endpoint="/error",
    )

    raise Exception("Intentional test error")


@app.get("/metrics")
def metrics():
    """
    Prometheus scrapes this endpoint.

    This is how Prometheus collects app metrics.
    """
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
