# Operations

## Scaling workers

Kestrel separates the scheduler, which decides when runs are due, from workers, which execute them. Run the scheduler with `kestrel scheduler` and any number of workers with `kestrel worker`. Workers claim runs from PostgreSQL using `SELECT ... FOR UPDATE SKIP LOCKED`, so adding workers scales throughput horizontally without a separate message broker.

## High availability

You can run several schedulers for redundancy. They elect a leader through a PostgreSQL advisory lock, and only the leader enqueues runs. If the leader dies, a standby takes over within about 10 seconds.

## Queues

Workers can be restricted to queues with `kestrel worker --queues reports,emails`. Use separate queues to keep slow batch jobs from starving latency-sensitive ones.

## Metrics

Kestrel exposes Prometheus metrics at `/metrics` on the API port. Useful series include `kestrel_runs_total` (labelled by job and status), `kestrel_run_duration_seconds`, `kestrel_queue_depth`, and `kestrel_scheduler_is_leader`.

## Health checks

`GET /healthz` returns 200 when the process is up. `GET /readyz` returns 200 only when the database is reachable and migrations are current; use it for load-balancer readiness probes.

## Backups

All state lives in PostgreSQL, so back up the database with your usual tooling, such as `pg_dump` or continuous WAL archiving. Job definitions live in files and should be kept in version control.

## Log retention

Run logs are stored in the database and pruned after 30 days by default. Change this with `log_retention` in `kestrel.toml`. For long-term storage, ship logs to an external system by setting `log_format = "json"` and collecting stdout.
