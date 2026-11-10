# Getting Started with Kestrel

Kestrel is an open-source, self-hosted job scheduler for running recurring and one-off background jobs. It is written in Go, stores its state in PostgreSQL, and ships as a single static binary called `kestrel`. This corpus is fictional sample documentation bundled with ragdesk for demos and evaluation.

## Requirements

Kestrel needs PostgreSQL 14 or newer. A single scheduler node needs about 256 MB of RAM; each worker process needs roughly 64 MB plus whatever the jobs themselves consume. Kestrel runs on Linux and macOS; Windows is supported only through WSL2.

## Installation

Install the binary with the official script:

```
curl -fsSL https://get.kestrel.example/install.sh | sh
```

Alternatively, pull the container image `ghcr.io/kestrel-sched/kestrel:2.4`. Verify the install with `kestrel version`, which prints the build version and the supported schema version.

## Initializing the database

Before the first start, run `kestrel migrate up` against an empty database. Migrations are forward-only; Kestrel refuses to start if the schema version in the database is newer than the binary supports.

## Your first job

Jobs are defined in YAML files placed in the jobs directory (default `./jobs`). A minimal job looks like this:

```
name: nightly-report
schedule: "0 2 * * *"
command: ["python", "report.py"]
timeout: 10m
```

Start the scheduler and one worker in a single process with `kestrel run --all-in-one`. The web dashboard is then available on port 7420. Trigger a job manually with `kestrel trigger nightly-report`.

## Next steps

Read the configuration guide to tune ports and concurrency, the scheduling guide for cron syntax and time zones, and the retries guide to decide what happens when a job fails.
