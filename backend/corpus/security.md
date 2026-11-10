# Security

## Authentication

The HTTP API and the dashboard require a bearer token. Create tokens with `kestrel token create --role <role> --name <name>`; the token value is shown once and only its SHA-256 hash is stored. Tokens can be given an expiry with `--ttl 720h`. Revoke a token with `kestrel token revoke <name>`.

## Roles

Kestrel has three built-in roles:

- `viewer` — read-only access to jobs, runs, and logs.
- `operator` — everything a viewer can do, plus triggering, pausing, and replaying runs.
- `admin` — full access, including token management and deleting jobs.

Custom roles are not supported in the open-source edition.

## TLS

Set `tls_cert_file` and `tls_key_file` to serve the API over HTTPS. When TLS is enabled, Kestrel refuses connections using TLS versions older than 1.2. Kestrel does not obtain certificates automatically; use a reverse proxy or a tool such as certbot for that.

## Secrets in jobs

Never put credentials directly in job YAML. Reference them with `${secret:NAME}`; Kestrel resolves secrets from environment variables prefixed with `KESTREL_SECRET_`, or from HashiCorp Vault when `vault_addr` is configured. Resolved secret values are masked as `****` in run logs.

## Audit log

Every API call that changes state is written to the `audit_events` table with the token name, action, target, and timestamp. Audit events are retained for 90 days.

## Reporting vulnerabilities

Report security issues privately to security@kestrel.example. The maintainers aim to acknowledge reports within two business days.
