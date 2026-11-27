# GCP project

- A GCP project named **LinkCast** exists on the maintainer's personal account.
- It was created on 2026-11-22, by hand, from the Google Cloud console.
- Only the maintainer administers it, from the console or Cloud Shell.
- The project id is kept by the maintainer and is not written in this repository, which is public.

## What issue #1 creates

The maintainer creates these resources by hand, following [`infra/setup.md`](../infra/setup.md). No session creates or changes anything in the project. The region is `europe-west1`.

| Resource | Purpose |
|---|---|
| Budget, $5 per month | Alerts at 50%, 90%, 100% of actual and 100% of forecast spending; it only warns |
| APIs: Cloud Run, Firestore, Secret Manager, Artifact Registry | Needed by the resources below |
| Logging exclusion for the request log of the service `linkcast` | Keeps the feed token out of the logs |
| Service account `linkcast-run` | The only identity of the service |
| Private Cloud Storage bucket | Holds the test MP3 under `test/` |
| Firestore `(default)` database, Native mode | Empty; ready for later issues |
| Secret `feed-token` in Secret Manager | The feed token, read by the service at start |
| Artifact Registry repository `linkcast`, keeping the last 2 images | Holds the container image |
| Cloud Run service `linkcast` | Serves the feed and the MP3 files, only with the right token |

IAM roles: `roles/storage.objectViewer` on the bucket, `roles/secretmanager.secretAccessor` on the secret and `roles/datastore.user` on the project, all for `linkcast-run`; `roles/run.invoker` for `allUsers` on the service only. No service account key is created.

Cloud Translation and Text-to-Speech are not enabled by #1. The runbook ends with the Castamatic test and a teardown section that removes everything.

## Status

The resources exist only once the maintainer has run the runbook; this page does not record whether that has happened. Identifiers (project id, bucket name, service address, token) are never written here.
