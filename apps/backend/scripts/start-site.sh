#!/bin/sh
# Container start for the deployed site: load file-mounted secrets, migrate,
# then serve. A failed migration exits before the server starts.
set -eu

for name in VERASIG_JWT_SECRET VERASIG_SECRET_KEYS VERASIG_DB_PASSWORD \
  VERASIG_STRIPE_SECRET_KEY VERASIG_STRIPE_WEBHOOK_SECRET VERASIG_SMTP_PASSWORD; do
  file_var="${name}_FILE"
  eval "file_path=\${${file_var}:-}"
  if [ -n "${file_path}" ]; then
    value="$(cat "${file_path}")"
    export "${name}=${value}"
  fi
done

uv run --no-sync alembic upgrade head
exec uv run --no-sync uvicorn verasig.entrypoints.site:create_site_from_env \
  --factory --host 0.0.0.0 --port 8000
