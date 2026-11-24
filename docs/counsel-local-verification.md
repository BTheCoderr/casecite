# Local Counsel verification

Modified from CaseCite, Copyright 2026 Thomas Unise, Apache-2.0. See LICENSE and NOTICE.md.

This procedure is for a fresh development checkout only, using fictional data. Do not point it at any existing SmartProBono services, production database or external AI account. The local dev stack is not equivalent to the PostgreSQL/Redis production topology.

## Prerequisites
Docker Desktop/Compose, Node 24, Python 3 and available loopback ports 8000 and 3000. On an 8 GB laptop, stop other containers and heavy applications before building. Use a new checkout and a unique Compose project. Inspect inherited environment variables and do not reuse production credentials. No cloud deployment is required.

## Start
From the root, use the existing development Compose configuration:
```sh
# Remove inherited credentials for a no-model-call baseline.
# Run in a subshell so the parent shell remains unchanged.
(
  unset OPENAI_API_KEY ANTHROPIC_API_KEY VOYAGE_API_KEY SECRET_KEY
  unset GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET MICROSOFT_CLIENT_ID
  unset MICROSOFT_CLIENT_SECRET MICROSOFT_TENANT_ID
  docker compose --env-file /dev/null -p counsel-local -f docker-compose.dev.yml up -d --build
)
```
In a second terminal:
```sh
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 3000 --strictPort
```
If a port is in use, stop and resolve the conflict rather than connecting to another project. Do not expose these services through a tunnel or public interface. Verify the Compose backend is healthy before proceeding.

In a third terminal from the repository root:
```sh
python3 scripts/smoke_counsel_local.py
```
This check is read-only, fails on unavailable or unhealthy endpoints, and checks the fresh-install branding and frontend HTML title. Custom branding intentionally fails this baseline check. If startup requires an AI provider, record that as a blocker rather than supplying a real client credential. Do not mistake the check for a browser test or a production security review.

## Acceptance
- Lint, type checking, frontend/backend tests, browser tests, migrations, backup drill and production smoke all pass in fork CI.
- Dependency and container scans pass without new exclusions.
- Review both themes and mobile layout; verify sign-in and sign-out, permissions and fictional document workflows using the existing mocked-provider CI journey or a separately approved isolated provider.
- Validate a production-like PostgreSQL/Redis stack separately, including tenant isolation, audit integrity and encrypted storage; never falsely acknowledge disk encryption.
- Record commit SHA, observed pass/fail results and outstanding risks. No actual client data until all release gates are met.

## Stop
Stop the frontend with Ctrl+C. From the root:
```sh
docker compose --env-file /dev/null -p counsel-local -f docker-compose.dev.yml down
```
Volumes are retained. Do not use `down -v` unless you explicitly intend to delete this disposable project's data.
