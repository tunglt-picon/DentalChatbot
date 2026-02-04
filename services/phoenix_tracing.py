"""Phoenix Observability Tracing Service."""
import logging
import json
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager
import config

logger = logging.getLogger(__name__)

_tracer = None
_phoenix_enabled = False


def initialize_phoenix():
    global _tracer, _phoenix_enabled
    
    if not config.settings.phoenix_enabled:
        logger.info("[PHOENIX] Phoenix tracing is disabled")
        return
    
    try:
        from phoenix.otel import register
        from opentelemetry import trace
        
        endpoint = config.settings.phoenix_endpoint
        logger.info(f"[PHOENIX] Initializing Phoenix tracing with endpoint: {endpoint}")
        
        base_endpoint = endpoint.replace('/v1/traces', '').rstrip('/')
        
        register(
            project_name=config.settings.phoenix_project_name,
            endpoint=base_endpoint,
        )
        
        _tracer = trace.get_tracer(__name__)
        _phoenix_enabled = True
        
        logger.info(f"[PHOENIX] Phoenix tracing initialized successfully with endpoint: {base_endpoint}")
    except ImportError as e:
        logger.warning(f"[PHOENIX] Phoenix dependencies not installed: {e}")
        logger.warning("[PHOENIX] Install with: pip install arize-phoenix openinference-semantic-conventions opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc")
    except Exception as e:
        logger.error(f"[PHOENIX] Failed to initialize Phoenix: {e}", exc_info=True)


def get_tracer():
    global _tracer, _phoenix_enabled
    
    if not _phoenix_enabled:
        return None
    
    return _tracer


def is_enabled() -> bool:
    return _phoenix_enabled


@contextmanager
def phoenix_span(span_name: str, attributes: Optional[Dict[str, Any]] = None):
    if not _phoenix_enabled:
        yield None
        return
    
    tracer = get_tracer()
    if not tracer:
        yield None
        return
    
    start_time = time.time()
    with tracer.start_as_current_span(span_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        
        try:
            yield span
        finally:
            end_time = time.time()
            duration = end_time - start_time
            span.set_attribute("custom.duration_seconds", duration)
            span.set_attribute("custom.duration_ms", duration * 1000)
