# linkcast

Listen to your readings: LinkCast turns links to articles into a private podcast feed. For each link it extracts the main text, translates it into Italian and reads it with a synthetic voice, so that every article becomes an episode in the podcast app.

The project is at the start: the backlog is in the [issues](https://github.com/nuccio/linkcast/issues), with the milestones `MVP` and `Release 1`.

## What the repository holds

- **The feed service** (`src/linkcast/`): a small Flask application for Cloud Run. It answers only `/feed/<token>/feed.xml` and `/feed/<token>/episodes/<name>.mp3`, and only when the address carries the right feed token. Any other address, a wrong token and a missing token all get the same 404. The feed lists the MP3 files under a prefix of a private Cloud Storage bucket and marks the show as not to be indexed. Episodes are read from the bucket through the service, with byte ranges, so the bucket is never public.
- **The runbook** ([infra/setup.md](infra/setup.md)): the steps the maintainer runs by hand to create the resources in the GCP project, deploy the service and test the feed in Castamatic. It uses placeholders and ends with a teardown section. Sessions never run it.
- **A short test episode** (`infra/test-episode.mp3`) used by the runbook.

## Configuration

The service reads these environment variables. A template with placeholders is in `.env.example`; never commit a real `.env`.

| Variable | Meaning |
|---|---|
| `FEED_TOKEN` | The feed token, at least 32 characters. The service refuses to start without it. On Cloud Run it comes from Secret Manager. |
| `AUDIO_BUCKET` | Name of the private bucket that holds the MP3 files. Required. |
| `AUDIO_PREFIX` | Prefix of the episodes in the bucket. Default `test/`. |
| `PORT` | Port to listen on. Set by Cloud Run; default 8080. |

The service logs one line per request with the route name, the status, the size and the user agent. It never logs the path, the token or the text of an article. The error logs of the application and of gunicorn redact the segment after `/feed/`, and the container has no access log. The deployment also needs the Logging exclusion for the request log and Cloud Trace kept off; both are steps of the runbook.

## Tests

The service tests use [uv](https://docs.astral.sh/uv/) and Python 3.13:

```bash
uv sync --frozen                          # install the dependencies from uv.lock
uv run pytest tests/app                   # service tests, with a fake bucket
python3 -m pip install pytest             # test dependencies of the repository checks
python3 -m pytest tests                   # repository checks (English only, links, runbook)
```

The tests need no network and no GCP login.

## Development

- How a change gets to `main`: [CONTRIBUTING.md](CONTRIBUTING.md).
- Security policy: [SECURITY.md](SECURITY.md).
- Rules of the maintainer's Claude sessions: [docs/maintainer-agent-workflow.md](docs/maintainer-agent-workflow.md).
- The GCP project and what is still to be set up in it: [docs/gcp-project.md](docs/gcp-project.md).
- Step-by-step setup and Castamatic test: [infra/setup.md](infra/setup.md).
