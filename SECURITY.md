# Security policy

## Reporting a vulnerability

Do not open a public issue. Use **Security → Report a vulnerability** on GitHub, which reaches the maintainer privately. This includes any way to add links without the API secret, to read the feed or the MP3 files without the token, to get past the daily episode limit, or to reach the web UI without IAP.

## Supported versions

Fixes go to `main`. Older commits are not patched.

## What the service holds

LinkCast runs on a personal GCP project. Once built, it will hold:

- the links and briefs sent by the digest, the extracted and translated texts, and the MP3 files, in Firestore and Cloud Storage;
- a dedicated API secret that only allows adding links, and the token in the feed URL that gives access to the feed and the MP3 files.

Anyone with the API secret can add links, and so spend money up to the daily episode limit. Anyone with the feed token can listen to the feed. Both are revocable and never committed. The paid APIs (Cloud Translation, Text-to-Speech) are limited by the daily episode limit enforced by the server; the GCP budget only sends alerts.

## What protects the repository

| Control | What it covers |
|---|---|
| `.gitignore` for `.env`, `client_secret*.json`, `credentials.json`, service account keys | accidental commits of credentials |
| Dependabot with a 7-day cooldown | outdated dependencies, grouped in few pull requests |
| Actions pinned to commit SHAs | the workflows that test the code |
| Branch rules on `main` (see `docs/maintainer-agent-workflow.md`) | unreviewed or unsigned changes |
| No Google Cloud login for agent sessions (see `docs/maintainer-agent-workflow.md`) | deploys, resources and spending started by an agent |
