# Retries and Failure Handling

A run fails when its command exits with a non-zero status, exceeds its `timeout`, or its worker stops sending heartbeats.

## Retry policy

Each job can declare a retry policy:

```
retry:
  max_attempts: 5
  backoff: exponential
  initial_delay: 10s
  max_delay: 10m
```

`max_attempts` counts the first attempt, so a value of 5 means one run plus four retries. The default is 3 attempts. Supported backoff strategies are `fixed`, `linear`, and `exponential`. Exponential backoff doubles the delay after every failure and adds up to 20% random jitter, capped at `max_delay`.

## Non-retryable exit codes

List exit codes in `retry.abort_on` to stop retrying immediately. For example, `abort_on: [2, 64]` treats usage errors as permanent failures.

## Worker heartbeats

Workers send a heartbeat every 5 seconds. If no heartbeat arrives for 30 seconds, the scheduler marks the worker as lost and its in-flight runs as failed with error code KST-4102 ("worker lost"). Those runs are then retried according to their policy, so jobs must be idempotent.

## Dead-letter queue

When a run exhausts all attempts it moves to the dead-letter queue. Dead-lettered runs are kept for 14 days by default (`dead_letter_retention` in `kestrel.toml`). Inspect them with `kestrel dlq list` and re-enqueue one with `kestrel dlq replay <run-id>`.

## Alerts on failure

Set `on_failure.webhook` to a URL and Kestrel will POST a JSON payload describing the failed run after the final attempt. Webhook deliveries time out after 5 seconds and are retried three times.
