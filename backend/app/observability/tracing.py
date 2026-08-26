from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
import logging
from typing import Any

from fastapi import FastAPI

try:
    from opentelemetry import propagate, trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
    from opentelemetry.trace import SpanKind

    _TRACING_BACKEND_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    propagate = None
    trace = None
    OTLPSpanExporter = None
    FastAPIInstrumentor = None
    SQLAlchemyInstrumentor = None
    Resource = None
    TracerProvider = None
    BatchSpanProcessor = None
    TraceIdRatioBased = None
    SpanKind = None
    _TRACING_BACKEND_AVAILABLE = False

logger = logging.getLogger(__name__)

_TRACING_INITIALIZED = False
_INSTRUMENTED_APP_IDS: set[int] = set()
_INSTRUMENTED_ENGINE_IDS: set[int] = set()


class _NoopSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        return None


class _NoopSpanContext:
    def __enter__(self) -> _NoopSpan:
        return _NoopSpan()

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _NoopTracer:
    def start_as_current_span(self, name: str, **_: Any) -> _NoopSpanContext:
        return _NoopSpanContext()


def configure_tracing(
    *,
    enabled: bool,
    service_name: str,
    environment: str,
    service_version: str,
    exporter_endpoint: str | None,
    sample_ratio: float,
    app: FastAPI | None = None,
    engine: Any | None = None,
) -> None:
    global _TRACING_INITIALIZED
    if not _TRACING_BACKEND_AVAILABLE or not enabled or not exporter_endpoint:
        return
    if not _TRACING_INITIALIZED:
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": service_version,
                "deployment.environment": environment,
            }
        )
        provider = TracerProvider(
            resource=resource,
            sampler=TraceIdRatioBased(max(0.0, min(1.0, sample_ratio))),
        )
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=exporter_endpoint)))
        trace.set_tracer_provider(provider)
        _TRACING_INITIALIZED = True
        logger.info(
            "observability.tracing.enabled service=%s endpoint=%s",
            service_name,
            exporter_endpoint,
        )
    provider = trace.get_tracer_provider()
    if app is not None and id(app) not in _INSTRUMENTED_APP_IDS:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        _INSTRUMENTED_APP_IDS.add(id(app))
    if engine is not None and id(engine) not in _INSTRUMENTED_ENGINE_IDS:
        SQLAlchemyInstrumentor().instrument(engine=engine, tracer_provider=provider)
        _INSTRUMENTED_ENGINE_IDS.add(id(engine))


def enrich_trace_headers(headers: Mapping[str, Any] | None = None) -> dict[str, str]:
    carrier = {str(key): str(value) for key, value in dict(headers or {}).items() if value is not None}
    if not _TRACING_BACKEND_AVAILABLE:
        return carrier
    propagate.inject(carrier)
    return carrier


def extract_context_from_carrier(carrier: Mapping[str, Any] | None) -> Any:
    normalized = {str(key): str(value) for key, value in dict(carrier or {}).items() if value is not None}
    if not _TRACING_BACKEND_AVAILABLE:
        return None
    return propagate.extract(normalized)


def _get_tracer(name: str = "gtex.observability") -> Any:
    if not _TRACING_BACKEND_AVAILABLE or SpanKind is None:
        return _NoopTracer()
    return trace.get_tracer(name)


@contextmanager
def start_consumer_span(
    name: str,
    *,
    carrier: Mapping[str, Any] | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> Any:
    context = extract_context_from_carrier(carrier)
    tracer = _get_tracer()
    kwargs = {"context": context} if context is not None else {}
    if SpanKind is not None:
        kwargs["kind"] = SpanKind.CONSUMER
    with tracer.start_as_current_span(name, **kwargs) as span:
        for key, value in dict(attributes or {}).items():
            if value is not None:
                span.set_attribute(key, value)
        yield span


@contextmanager
def start_internal_span(
    name: str,
    *,
    attributes: Mapping[str, Any] | None = None,
) -> Any:
    tracer = _get_tracer()
    kwargs = {}
    if SpanKind is not None:
        kwargs["kind"] = SpanKind.INTERNAL
    with tracer.start_as_current_span(name, **kwargs) as span:
        for key, value in dict(attributes or {}).items():
            if value is not None:
                span.set_attribute(key, value)
        yield span


@contextmanager
def start_producer_span(
    name: str,
    *,
    carrier: Mapping[str, Any] | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> Any:
    context = extract_context_from_carrier(carrier)
    tracer = _get_tracer()
    kwargs = {"context": context} if context is not None else {}
    if SpanKind is not None:
        kwargs["kind"] = SpanKind.PRODUCER
    with tracer.start_as_current_span(name, **kwargs) as span:
        for key, value in dict(attributes or {}).items():
            if value is not None:
                span.set_attribute(key, value)
        yield span
