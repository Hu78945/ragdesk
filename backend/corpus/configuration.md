# Configuration

Kestrel reads configuration from `kestrel.toml` in the working directory, then applies environment variables, then command-line flags. Later sources win, so a flag always overrides the file.

## Configuration file

The most important keys are:

- `database_url` — PostgreSQL connection string. Required.
- `listen_addr` — address for the HTTP API and dashboard. Default `0.0.0.0:7420`.
- `jobs_dir` — directory scanned for job definitions. Default `./jobs`.
- `max_concurrency` — maximum number of jobs a single worker runs at the same time. Default 8.
- `poll_interval` — how often idle workers poll for new runs. Default `2s`.
- `log_format` — either `text` or `json`. Default `text`.

## Environment variables

Every key can be set through an environment variable by upper-casing it and adding the `KESTREL_` prefix. For example, `KESTREL_MAX_CONCURRENCY=16` sets `max_concurrency`. The database URL may also be provided as plain `DATABASE_URL` for compatibility with hosting platforms.

## Reloading configuration

Sending `SIGHUP` to the scheduler reloads job definitions from `jobs_dir` without dropping running jobs. Changes to `database_url` or `listen_addr` are not hot-reloadable and require a restart.

## Validating configuration

Run `kestrel config check` to validate the merged configuration and every job file. The command exits with status 3 when a job definition is invalid and prints the offending file and line.

## Per-job overrides

A job definition can override `timeout`, `max_concurrency` (to limit how many runs of that job may overlap), `retry` policy, and `queue`. Jobs without an explicit queue go to the `default` queue.
