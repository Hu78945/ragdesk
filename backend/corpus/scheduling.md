# Scheduling

Kestrel supports cron expressions, fixed intervals, and one-off runs.

## Cron syntax

The `schedule` field accepts standard five-field cron expressions (minute, hour, day of month, month, day of week). A sixth leading field for seconds is accepted when `cron_seconds = true` is set in `kestrel.toml`. The shortcuts `@hourly`, `@daily`, `@weekly`, and `@monthly` are also supported.

## Fixed intervals

Use `every: 15m` instead of `schedule` to run a job at a fixed interval measured from the end of the previous run. Interval jobs never overlap with themselves.

## Time zones

Schedules are evaluated in UTC unless the job sets `timezone`, for example `timezone: Europe/Berlin`. Kestrel uses the IANA time zone database embedded in the binary. During daylight-saving transitions, a run scheduled inside a skipped hour is executed once at the first valid minute after the gap, and a run inside a repeated hour fires only once.

## Jitter

Setting `jitter: 30s` delays each run by a random amount between zero and the given duration. Jitter spreads load when many jobs share the same cron expression, such as everything scheduled at midnight.

## Misfire policy

If the scheduler was down when a run was due, the `misfire_policy` field decides what happens on recovery:

- `skip` (default) — missed runs are dropped and the next regular run proceeds.
- `run_once` — a single catch-up run is executed no matter how many runs were missed.
- `run_all` — every missed run is executed in order, up to a limit of 100.

## Pausing schedules

`kestrel pause <job>` stops new runs from being scheduled while letting in-flight runs finish. `kestrel resume <job>` re-enables the schedule. Paused state is stored in the database and survives restarts.
