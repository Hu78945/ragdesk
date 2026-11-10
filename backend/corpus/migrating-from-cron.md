# Migrating from cron

Many teams adopt Kestrel to replace crontab entries spread across servers. This guide maps cron concepts to Kestrel.

## Converting crontab lines

A crontab line such as `30 4 * * 1 /opt/scripts/backup.sh` becomes a job file:

```
name: weekly-backup
schedule: "30 4 * * 1"
command: ["/opt/scripts/backup.sh"]
```

Run `kestrel import-crontab /etc/crontab` to generate job files automatically. The importer writes one YAML file per line into `jobs_dir` and skips lines it cannot parse, printing a warning for each.

## Environment differences

cron runs commands with a minimal environment and `/bin/sh`. Kestrel executes the `command` array directly without a shell, so shell features such as pipes and redirection need an explicit `["sh", "-c", "..."]` wrapper. Environment variables for a job are set with the `env` map in the job file.

## Output and email

cron emails job output to the owner. Kestrel stores output in run logs instead and can notify on failure through `on_failure.webhook`. There is no built-in email notifier; point the webhook at a relay if you need email.

## Overlapping runs

cron happily starts a new run while the previous one is still going. In Kestrel, set `max_concurrency: 1` on the job to prevent overlap; the extra run is queued until the previous one finishes.

## Running both side by side

During migration, keep cron entries commented out rather than deleted, and pause the Kestrel job with `kestrel pause` until you are ready to switch over.
