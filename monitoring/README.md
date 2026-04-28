# Monitoring — Grafana Alloy (Docker)

`config.alloy` runs inside a Docker container alongside Django and
ships Prometheus metrics from `/metrics` to Grafana Cloud.

## Run locally

```powershell
# 1. Make sure GRAFANA_CLOUD_TOKEN is in DjangoProject/.env:
#    GRAFANA_CLOUD_TOKEN=glc_eyJ...

# 2. Start Django on the host (in one terminal):
python manage.py runserver

# 3. Start Alloy in Docker (in another terminal, from DjangoProject/):
docker compose up
#   → first time: pulls the grafana/alloy image (~120 MB)
#   → after that: starts in ~2 seconds

# Useful:
docker compose logs -f alloy   # tail Alloy's logs
docker compose down            # stop + remove
```

## Verify

- Alloy debug UI: <http://localhost:12345> (shows scrape status, last error, etc.)
- Grafana Cloud → Explore → query `up{job="django"}` should be `1`.

## Production notes

- Replace `host.docker.internal:8000` with the Django container's
  service name once Django itself is dockerised (e.g. `web:8000`).
- The `extra_hosts: host-gateway` line stays harmless either way.
- `GRAFANA_CLOUD_TOKEN` belongs in your hosting platform's secrets
  store, not committed `.env`.
