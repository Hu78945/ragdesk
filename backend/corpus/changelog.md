# Changelog

## 2.4.0

- Added the `run_all` misfire policy, capped at 100 catch-up runs.
- Added `kestrel dlq replay` for re-enqueueing dead-lettered runs.
- The dashboard now shows queue depth per queue.
- Fixed a bug where jitter was applied twice to interval jobs.

## 2.3.0

- Added HashiCorp Vault support for `${secret:NAME}` references.
- Exponential backoff now adds up to 20% random jitter.
- Minimum supported PostgreSQL version raised from 12 to 14.

## 2.2.0

- Introduced scheduler high availability using PostgreSQL advisory locks.
- Added the `/readyz` endpoint.

## 2.0.0

- Breaking: job files switched from JSON to YAML. Run `kestrel convert-jobs` to migrate old JSON definitions.
- Breaking: the default API port changed from 8080 to 7420.
