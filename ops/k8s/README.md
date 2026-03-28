# GTEX Kubernetes Starter

This folder is the first Kubernetes step for the existing backend topology. It does not try to split GTEX into many repos or many images. It runs the current modular monolith and worker entrypoints as separate workloads with shared configuration.

## What is included

- `base/api.yaml`: FastAPI deployment and ClusterIP service
- `base/outbox-relay.yaml`: singleton outbox relay deployment
- `base/simulation-worker.yaml`: broker-driven simulation worker deployment
- `base/projection-worker.yaml`: broker-driven projection worker deployment
- `base/hpa-api.yaml`: API and worker HPAs
- `base/ingress.yaml`: starter ingress for the API
- `base/configmap.yaml`: shared non-secret environment
- `base/secret.example.yaml`: example secret manifest, intentionally not wired into kustomize
- `base/migration-job.yaml`: one-off Alembic migration job, also not wired into kustomize

## Build the backend image

```bash
docker build -t ghcr.io/your-org/gtex-backend:latest -f Dockerfile .
```

Push the image to your registry, then replace the placeholder image name in the manifests or use a kustomize image override.

## Apply order

1. Create a real secret manifest from `base/secret.example.yaml` without committing secrets.
2. Apply the namespace, config, API, workers, ingress, and HPAs:

```bash
kubectl apply -k ops/k8s/base
```

3. Run the Alembic job when you need a schema migration:

```bash
kubectl apply -f ops/k8s/base/migration-job.yaml
kubectl logs -n gtex job/gtex-db-migrate
```

## Notes

- The starter HPAs use CPU utilization because that is available on most clusters. For production workers, move to queue-lag-driven autoscaling when you have KEDA or custom metrics in place.
- The starter manifests now expose Prometheus scrape targets for the API and worker metrics endpoints. Tracing stays opt-in until you provide an OpenTelemetry collector endpoint.
- Postgres, Redis, and Kafka or Redpanda are treated as external dependencies in this starter. Use managed services or dedicated platform charts instead of baking them into the application manifests.
- The API pod disables the outbox relay and worker consumers so those responsibilities stay isolated to their own deployments.
