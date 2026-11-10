# Glossary

## Job

A named definition of work: a command, a schedule or interval, and policies such as timeout and retries. Jobs are defined in YAML files.

## Run

A single execution of a job. Each run has an ID, a status, an attempt number, timestamps, and a log.

## Attempt

One try at executing a run. A run with retries may have several attempts; the attempt counter starts at 1.

## Queue

A named channel that runs are placed on. Workers subscribe to one or more queues. Jobs without a queue use `default`.

## Scheduler

The process that evaluates schedules and enqueues runs when they are due. Only the elected leader enqueues runs.

## Worker

A process that claims queued runs and executes their commands. Workers report liveness through heartbeats.

## Dead-letter queue (DLQ)

Holding area for runs that failed every attempt. Runs can be inspected and replayed from the DLQ.

## Misfire

A scheduled run that was not started on time, typically because the scheduler was down. The misfire policy controls whether it is skipped or caught up.

## Jitter

A random delay added to a run's start time to avoid thundering-herd load spikes.
