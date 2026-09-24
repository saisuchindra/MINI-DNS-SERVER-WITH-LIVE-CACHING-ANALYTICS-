# API contract

All REST responses use `{ "success": true, "data": ... }`; validation failures use normal FastAPI 422 responses and upstream failures return 504.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Service state |
| `POST /api/dns/query` | Resolve `{domain, record_type, protocol}` using the actual cache/upstream engine |
| `GET /api/dns/query/{query_id}` | Persisted query and resolution flow |
| `GET, DELETE /api/cache` | List or clear cache |
| `GET, DELETE /api/cache/{domain}` | Inspect or remove a domain |
| `GET /api/analytics/{summary,timeseries,domains,protocols,cache}` | Live/persisted analytics |
| `GET /api/logs?limit=50&offset=0` | Paginated DNS query history |
| `POST /api/simulation/{start,stop,pause,resume}` | Automatic workload controls |
| `GET /api/simulation/status` | Simulation state/configuration |
| `POST /api/simulation/config` | Set interval, speed, weighted distribution, type, maximum |

`POST /api/dns/query` example:
```json
{"domain":"google.com","record_type":"A","protocol":"UDP"}
```
Its result contains `status` (`HIT`/`MISS`), source, observed response time, remaining TTL, answers, `query_id`, and `flow` (the educational resolution steps).

Connect to `ws://127.0.0.1:8000/ws/analytics`. Events are `dns_query`, `analytics_update`, `simulation_status`, and `error`; each is `{ "event": "...", "data": {...} }`. Send any text periodically to keep the connection open.
