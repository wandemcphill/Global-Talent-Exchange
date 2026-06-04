# GTEX Observability Stack

This stack gives the backend and workers a control tower:

- Logs: Loki via Promtail
- Metrics: Prometheus
- Dashboards: Grafana
- Tracing: OpenTelemetry Collector and Jaeger

## 1. Run the stack

```bash
docker compose -f ops/observability/docker-compose.yml up -d
```

Grafana is available at `http://localhost:3000` with `admin/admin`.

## 2. Run GTEX with telemetry enabled

For the API process:

```bash
$env:GTE_METRICS_ENABLED="true"
$env:GTE_LOG_JSON="true"
$env:GTE_OBSERVABILITY_TRACING_ENABLED="true"
$env:GTE_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="http://localhost:4318/v1/traces"
$env:GTE_OTEL_SERVICE_NAME="gtex-api"
```

For worker processes, also set a metrics port per process:

```bash
$env:GTE_METRICS_PORT="9101"
$env:GTE_OTEL_SERVICE_NAME="gtex-simulation-worker"
python -m app.backbone.simulation_worker_main
```

Use `9102` for the projection worker and `9103` for the outbox relay.

## 3. What is instrumented

- API request latency, status codes, and in-flight requests
- Match queue delay, match duration, matches per outcome, and worker job timing
- Deposit totals, withdrawal totals, GTex in circulation, and treasury balance
- Trace context propagation from API spans into outbox events, Kafka headers, and worker consumers
- Structured JSON logs with trace and span correlation fields

## 4. Alerts included

- Withdrawal failure rate above 5%
- Match queue delay above 10 seconds
- Treasury balance below the red-alert threshold
- Match viewer gateway refresh failures
- Match viewer payload bridge failures
- Match viewer stale-state detection
- Match realtime websocket reject / churn detection
- Match stream bootstrap failures

## 5. GTEX live match center dashboard

The Grafana dashboards folder now includes a dedicated GTEX live match center board:

- [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\ops\observability\grafana\dashboards\gtex-live-match-center.json](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/ops/observability/grafana/dashboards/gtex-live-match-center.json>)

This board is intended for the main `P6` operator failure modes:
- match viewer gateway access and refresh failures
- live payload bridge failures
- websocket rejects and reconnect churn
- stale-state detection
- match stream bootstrap failures

## 6. Kubernetes starter integration

The existing manifests in `ops/k8s/base` now expose `/metrics` on the API and dedicated metrics ports on the workers. To enable tracing in-cluster, set:

```bash
GTE_OBSERVABILITY_TRACING_ENABLED=true
GTE_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://otel-collector:4318/v1/traces
```

The provided starter manifests leave tracing disabled by default so the base deployment does not depend on a collector unless you deploy one.
