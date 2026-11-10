# Troubleshooting

## Jobs stay in the queued state

If runs stay queued, check that at least one worker is running and listening on the job's queue. A worker started with `--queues reports` never picks up jobs from the `default` queue. Also check `max_concurrency`: a worker that is already running its maximum number of jobs will not claim more.

## Runs fail with KST-4102

KST-4102 means the scheduler stopped receiving heartbeats from the worker that owned the run. Common causes are the worker being killed by the out-of-memory killer, a container being rescheduled, or a network partition between the worker and PostgreSQL. Check the worker's memory limit first.

## The scheduler will not start

The error "schema version ahead of binary" means the database was migrated by a newer Kestrel release. Upgrade the binary, or restore the database from a backup taken before the migration. Downgrading the schema is not supported.

## Jobs run twice

Duplicate executions usually happen when two independent Kestrel installations point at different databases but share the same job files, or when a job is retried after KST-4102 while the original process was still alive. Make jobs idempotent, for example by writing results with an upsert keyed by the scheduled time.

## Cron schedule fires at the wrong hour

Schedules are evaluated in UTC by default. Set `timezone` on the job if you expect local time. Remember that the dashboard displays times in the browser's time zone.

## Dashboard returns 401

The dashboard needs a token with at least the `viewer` role. Tokens created with `--ttl` expire silently; create a new one with `kestrel token create`.

## High database load

Lower the polling pressure by increasing `poll_interval`, or reduce the number of idle workers. Enable `log_format = "json"` and check for jobs that produce very large logs, since run logs are stored in PostgreSQL.
