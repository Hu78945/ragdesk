"""Golden Q&A set over backend/corpus. A retrieved chunk is relevant when it comes from
`doc` and its text contains `contains` (case-insensitive) — robust to chunker changes.
Questions with no `relevant` entries are out of scope and should be refused."""

R = dict  # one relevant (doc, evidence) pair

# fmt: off

GOLDEN: list[dict] = [
    {
        "q": "Which PostgreSQL version does Kestrel require?",
        "relevant": [
            R(doc="getting-started.md", contains="PostgreSQL 14 or newer"),
            R(doc="changelog.md", contains="raised from 12 to 14"),
        ],
    },
    {
        "q": "Can I run Kestrel on Windows?",
        "relevant": [R(doc="getting-started.md", contains="only through WSL2")],
    },
    {
        "q": "How much memory does a worker process need?",
        "relevant": [R(doc="getting-started.md", contains="roughly 64 MB")],
    },
    {
        "q": "What command initializes the database schema before the first start?",
        "relevant": [R(doc="getting-started.md", contains="kestrel migrate up")],
    },
    {
        "q": "How do I run the scheduler and a worker in a single process?",
        "relevant": [R(doc="getting-started.md", contains="--all-in-one")],
    },
    {
        "q": "How can I manually kick off a job outside its schedule?",
        "relevant": [
            R(doc="getting-started.md", contains="kestrel trigger"),
            R(doc="api.html", contains="/trigger"),
        ],
    },
    {
        "q": "What is the default value of max_concurrency?",
        "relevant": [R(doc="configuration.md", contains="Default 8")],
    },
    {
        "q": "How do I set configuration options through environment variables?",
        "relevant": [R(doc="configuration.md", contains="KESTREL_` prefix")],
    },
    {
        "q": "If a setting is in both the config file and a command-line flag, which one wins?",
        "relevant": [R(doc="configuration.md", contains="Later sources win")],
    },
    {
        "q": "Can I change the listen address without restarting?",
        "relevant": [R(doc="configuration.md", contains="not hot-reloadable")],
    },
    {
        "q": "What exit code does kestrel config check return for an invalid job file?",
        "relevant": [R(doc="configuration.md", contains="exits with status 3")],
    },
    {
        "q": "Which queue does a job go to if none is specified?",
        "relevant": [
            R(doc="configuration.md", contains="go to the `default` queue"),
            R(doc="glossary.md", contains="Jobs without a queue use"),
        ],
    },
    {
        "q": "How do I make a cron schedule run in Berlin local time?",
        "relevant": [R(doc="scheduling.md", contains="Europe/Berlin")],
    },
    {
        "q": "What happens to runs that were missed while the scheduler was offline?",
        "relevant": [R(doc="scheduling.md", contains="misfire_policy")],
    },
    {
        "q": "What is the maximum number of catch-up runs with the run_all policy?",
        "relevant": [
            R(doc="scheduling.md", contains="up to a limit of 100"),
            R(doc="changelog.md", contains="capped at 100"),
        ],
    },
    {
        "q": "How do I avoid a load spike when lots of jobs start at midnight?",
        "relevant": [
            R(doc="scheduling.md", contains="Jitter spreads load"),
            R(doc="glossary.md", contains="thundering-herd"),
        ],
    },
    {
        "q": "Does Kestrel support second-level precision in cron expressions?",
        "relevant": [R(doc="scheduling.md", contains="cron_seconds = true")],
    },
    {
        "q": "What happens to a run scheduled during the hour skipped by daylight saving time?",
        "relevant": [R(doc="scheduling.md", contains="skipped hour")],
    },
    {
        "q": "Can interval-based jobs overlap with themselves?",
        "relevant": [R(doc="scheduling.md", contains="Interval jobs never overlap")],
    },
    {
        "q": "How many attempts does a job get by default?",
        "relevant": [R(doc="retries.md", contains="The default is 3 attempts")],
    },
    {
        "q": "How does exponential backoff behave between retries?",
        "relevant": [
            R(doc="retries.md", contains="doubles the delay"),
            R(doc="changelog.md", contains="Exponential backoff now adds"),
        ],
    },
    {
        "q": "How can I stop retrying for specific exit codes?",
        "relevant": [R(doc="retries.md", contains="abort_on")],
    },
    {
        "q": "How long are dead-lettered runs kept?",
        "relevant": [R(doc="retries.md", contains="14 days by default")],
    },
    {
        "q": "How do I re-run something from the dead-letter queue?",
        "relevant": [
            R(doc="retries.md", contains="kestrel dlq replay"),
            R(doc="changelog.md", contains="kestrel dlq replay"),
        ],
    },
    {
        "q": "How often do workers send heartbeats?",
        "relevant": [R(doc="retries.md", contains="heartbeat every 5 seconds")],
    },
    {
        "q": "What does error KST-4102 mean?",
        "relevant": [
            R(doc="retries.md", contains="KST-4102"),
            R(doc="troubleshooting.md", contains="KST-4102 means"),
            R(doc="api.html", contains="KST-4102 means"),
        ],
    },
    {
        "q": "How do I get notified when a job ultimately fails?",
        "relevant": [
            R(doc="retries.md", contains="on_failure.webhook"),
            R(doc="migrating-from-cron.md", contains="notify on failure"),
        ],
    },
    {
        "q": "What roles are built into Kestrel?",
        "relevant": [R(doc="security.md", contains="three built-in roles")],
    },
    {
        "q": "Which role do I need to pause or replay runs?",
        "relevant": [R(doc="security.md", contains="plus triggering, pausing, and replaying")],
    },
    {
        "q": "Can I define my own custom roles?",
        "relevant": [R(doc="security.md", contains="Custom roles are not supported")],
    },
    {
        "q": "What is the oldest TLS version the API accepts?",
        "relevant": [R(doc="security.md", contains="older than 1.2")],
    },
    {
        "q": "How should a job get a database password without writing it in the YAML file?",
        "relevant": [R(doc="security.md", contains="${secret:NAME}")],
    },
    {
        "q": "How long are audit events retained?",
        "relevant": [R(doc="security.md", contains="retained for 90 days")],
    },
    {
        "q": "Where do I report a security vulnerability?",
        "relevant": [R(doc="security.md", contains="security@kestrel.example")],
    },
    {
        "q": "How do workers avoid claiming the same run twice?",
        "relevant": [R(doc="operations.md", contains="SKIP LOCKED")],
    },
    {
        "q": "How is a leader chosen when several schedulers run?",
        "relevant": [
            R(doc="operations.md", contains="advisory lock"),
            R(doc="changelog.md", contains="advisory locks"),
        ],
    },
    {
        "q": "Which endpoint should a load balancer use for readiness probes?",
        "relevant": [R(doc="operations.md", contains="GET /readyz")],
    },
    {
        "q": "Which Prometheus metric shows the queue backlog?",
        "relevant": [R(doc="operations.md", contains="kestrel_queue_depth")],
    },
    {
        "q": "How long are run logs kept before being pruned?",
        "relevant": [R(doc="operations.md", contains="pruned after 30 days")],
    },
    {
        "q": "What is the API rate limit per token?",
        "relevant": [R(doc="api.html", contains="600 requests per minute")],
    },
    {
        "q": "What is the maximum page size for list endpoints?",
        "relevant": [R(doc="api.html", contains="maximum is 500")],
    },
    {
        "q": "What signal does a running command receive when its run is cancelled?",
        "relevant": [R(doc="api.html", contains="SIGTERM")],
    },
    {
        "q": "What does error code KST-2003 indicate?",
        "relevant": [R(doc="api.html", contains="KST-2003 means")],
    },
    {
        "q": "What was the default API port before version 2.0?",
        "relevant": [R(doc="changelog.md", contains="from 8080 to 7420")],
    },
    {
        "q": "How do I convert old JSON job definitions?",
        "relevant": [R(doc="changelog.md", contains="kestrel convert-jobs")],
    },
    {
        "q": "Why does the scheduler say 'schema version ahead of binary'?",
        "relevant": [
            R(doc="troubleshooting.md", contains="schema version ahead of binary"),
            R(doc="getting-started.md", contains="refuses to start if the schema version"),
        ],
    },
    {
        "q": "Can I import my existing crontab?",
        "relevant": [R(doc="migrating-from-cron.md", contains="kestrel import-crontab")],
    },
    {
        "q": "How do I use a shell pipe in a job command?",
        "relevant": [R(doc="migrating-from-cron.md", contains='["sh", "-c"')],
    },
    {
        "q": "Does Kestrel send an email when a job fails?",
        "relevant": [R(doc="migrating-from-cron.md", contains="no built-in email notifier")],
    },
    {
        "q": "Why are my runs stuck in the queued state?",
        "relevant": [R(doc="troubleshooting.md", contains="at least one worker is running")],
    },
    # Out of scope: the corpus does not answer these.
    {"q": "How much does the Kestrel enterprise edition cost?", "relevant": []},
    {"q": "How do I configure Kafka as the message broker?", "relevant": []},
    {"q": "What is the capital of Australia?", "relevant": []},
    {"q": "Is there an official Python SDK for Kestrel?", "relevant": []},
    {"q": "How do I set up single sign-on with Okta?", "relevant": []},
    {"q": "Which GPU do I need for model training?", "relevant": []},
    {"q": "Who founded Kestrel and in what year?", "relevant": []},
    {"q": "Give me a recipe for banana bread.", "relevant": []},
    {"q": "Which release added GraphQL support?", "relevant": []},
    {"q": "How do I import Kubernetes CronJob manifests?", "relevant": []},
]
# fmt: on
