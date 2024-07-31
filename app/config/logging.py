import logging
from django.conf import settings
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace



def create_logging_config():
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
            "azure": {
                "level": settings.LOGGING_LEVEL,
                "class": "opentelemetry.sdk._logs.LoggingHandler",
            },
        },
        'loggers': {
            'root': {
                'handlers': ['console'],
                'level': settings.LOGGING_LEVEL,
            },
            'azure.core.pipeline.policies.http_logging_policy': {
                'handlers': ['console'],
                'level': settings.LOGGING_LEVEL,
            },
            'azure.monitor.opentelemetry.exporter.export._base': {
                'handlers': ['console'],
                'level': settings.LOGGING_LEVEL,  # Set to INFO to log what is being logged by OpenTelemetry
            },
            'opentelemetry.attributes': {
                'handlers': ['console'],
                # This will suppress WARNING messages about invalid data types
                # Such as: Invalid type Json in attribute 'params' value sequence. Expected one of ['bool', 'str', 'bytes', 'int', 'float'] or None
                # Most of these invalid types will be inside the WHERE statements of DB operations, but despite the warnings are still being logged correctly.
                'level': settings.LOGGING_LEVEL,
                'propagate': False,
            },
        },
    }


def setup_azure_monitor():
    configure_azure_monitor(
        instrumentation_options = {
            "azure_sdk": {"enabled": False},
            "django": {"enabled": True},
            "psycopg2": {"enabled": True if settings.DATABASE_NAME else False},
            "requests": {"enabled": True},
            "urllib": {"enabled": True},
            "urllib3": {"enabled": True},
        },
        resource=Resource.create({SERVICE_NAME: "ZWD-Backend"}),
        export_timeout_millis=5000
    )

    tracer_provider = TracerProvider()
    trace.set_tracer_provider(tracer_provider)

    exporter = AzureMonitorTraceExporter(
        connection_string=settings.APPLICATIONINSIGHTS_CONNECTION_STRING
    )

    span_processor = BatchSpanProcessor(exporter)
    tracer_provider.add_span_processor(span_processor)

    logger = logging.getLogger("root")
    logger.info("Azure Monitoring enabled.")
