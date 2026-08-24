# Environment management

Urban Signal has one environment-variable contract owned by
[`apps/api/src/config.py`](../apps/api/src/config.py). Variable names are the
uppercase field names shown in [`.env.example`](../.env.example).

## Precedence

For the API, `pydantic-settings` reads values in this order:

1. process environment variables (including container or Kubernetes values),
2. the repository `.env` file when the process is started from the repository,
3. safe development defaults in `config.py`.

`.env.example` is a template only. Never commit `.env`, credentials, tokens, or
webhook URLs. The template intentionally contains `CHANGE_ME` placeholders and
must not be used unchanged with `APP_ENV=production`.

## Local development

The root `docker-compose.yml` is the full stack and uses these canonical names:

- PostgreSQL database: `urbansignal`
- MinIO bucket: `urban-signal-features`
- ONNX provider: `CPUExecutionProvider`

The GPU provider is an explicit opt-in:

```bash
ONNX_EXECUTION_PROVIDER=CUDAExecutionProvider docker compose up -d
```

The smaller `deploy/docker/docker-compose.dev.yml` is a standalone dependency
stack. Its development credentials are local-only and should not be reused in
production.

## Production

Set `APP_ENV=production` and provide non-placeholder values for:

- `POSTGRES_PASSWORD`
- `MINIO_SECRET_KEY`
- `MINIO_ACCESS_KEY`
- `SOCRATA_APP_TOKEN` when elevated Socrata limits are needed
- `WEBHOOK_ALERT_URLS` when alert delivery is enabled

The API refuses to start in production when PostgreSQL or MinIO still use the
development placeholder credentials. In Kubernetes, create credentials as
Secrets and reference them from workload `env` entries; do not put passwords in
manifests or shell history. For example:

```bash
kubectl create secret generic postgis-credentials \
  --from-literal=password="$POSTGRES_PASSWORD" \
  -n data-storage
```

Keep the same variable names when deploying through Compose, Kubernetes, or a
process manager so the application configuration remains portable.
