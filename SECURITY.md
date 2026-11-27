# Security policy

## Reporting a vulnerability

Do not open a public issue. Use **Security → Report a vulnerability** on GitHub, which reaches the maintainer privately. This includes any way to add links without the API secret, to read the feed or the MP3 files without the token, to get past the daily episode limit, or to reach the web UI without IAP.

## Supported versions

Fixes go to `main`. Older commits are not patched.

## What the service holds

LinkCast runs on a personal GCP project. The feed service already serves a private bucket behind the feed token. Once built, it will hold:

- the links and briefs sent by the digest, the extracted and translated texts, and the MP3 files, in Firestore and Cloud Storage;
- a dedicated API secret that only allows adding links, and the token in the feed URL that gives access to the feed and the MP3 files.

Anyone with the API secret can add links, and so spend money up to the daily episode limit. Anyone with the feed token can listen to the feed. Both are revocable and never committed. The paid APIs (Cloud Translation, Text-to-Speech) are limited by the daily episode limit enforced by the server; the GCP budget only sends alerts.

## The feed token

- The token is made by the maintainer in Cloud Shell and kept in Secret Manager. Cloud Run passes it to the service as an environment variable; it is never in the repository, in the logs, in an issue or in a pull request. The runbook and the docs use placeholders only.
- The service refuses to start with a token shorter than 32 characters, compares it in constant time, and answers a wrong token, a missing token and an unknown address with the same 404.
- The Cloud Run service allows unauthenticated calls (`roles/run.invoker` for `allUsers` on that service only) because a podcast app cannot log in. The token is the protection, and the bucket stays private.
- To regenerate it, add a new version of the secret, deploy a new revision of the service, and subscribe again in the podcast app. The old address stops working.

## Logs

- Cloud Run's automatic request log records the full address, so the token. The runbook adds a Logging exclusion for that log of the service **before the first deploy**. If the exclusion was missed, regenerate the token.
- Cloud Trace is kept off: trace spans carry the request URL. The runbook checks that the API is disabled before the deploy and again in the final checks.
- The service writes its own log: route name, status, size and user agent, never the path or the token. The error logs of the application and of gunicorn have the segment after `/feed/` replaced, and the container runs without an access log.
- Tests check that the token does not reach the logs.

## What protects the repository

| Control | What it covers |
|---|---|
| `.gitignore` for `.env`, `client_secret*.json`, `credentials.json`, service account keys | accidental commits of credentials |
| Dependabot with a 7-day cooldown | outdated dependencies, grouped in few pull requests |
| Actions pinned to commit SHAs | the workflows that test the code |
| Branch rules on `main` (see `docs/maintainer-agent-workflow.md`) | unreviewed or unsigned changes |
| No Google Cloud login for agent sessions (see `docs/maintainer-agent-workflow.md`) | deploys, resources and spending started by an agent |
