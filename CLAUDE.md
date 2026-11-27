# linkcast

Turns links to articles, mostly in English, into a private podcast feed: the text of each article is extracted, translated into Italian and read by a synthetic voice, one episode per article. Planned stack: Python on Cloud Run, Firebase (Firestore) for the data, Cloud Storage for the MP3 files, Cloud Translation and Cloud Text-to-Speech, all on a personal GCP project. The repository holds the first piece of application code, the feed service (see `README.md`); the backlog is in the issues, with the milestones `MVP` and `Release 1`.

## Language

- **Talk to the maintainer in Italian**: replies, questions, explanations, summaries in chat.
- **Everything written into the repository and on GitHub is in English**: documentation, issues, pull requests, comments, commit messages, log messages, code comments, docstrings, identifiers and error messages. Italian is used only in the conversation with the maintainer, and in the files listed as exceptions in `tests/test_repository_language.py`.

## Commands

```bash
python3 -m pip install pytest             # test dependencies of the repository checks
python3 -m pytest tests                   # repository checks, from the repository root
uv sync --frozen                          # service dependencies from uv.lock (Python 3.13)
uv run pytest tests/app                   # service tests, from the repository root
```

The service runs in the container built from `Dockerfile` (gunicorn, `linkcast.app:create_app()`); it needs `FEED_TOKEN` and `AUDIO_BUCKET`, see `.env.example`. Sessions never run it against the real GCP project. The jobs in `.github/workflows/tests.yml` are `Repository checks` (`python -m pytest tests`) and `Service tests` (`uv sync --frozen`, `uv run pytest tests/app`). No linter yet.

## Layout

- `src/linkcast/`: the feed service: `app.py` (routes, configuration, request log), `token.py` (feed token check), `storage.py` (reads the bucket), `feed.py` (RSS).
- `tests/app/`: tests of the service, run with `uv run pytest tests/app`.
- `tests/`: repository checks, `test_infra_runbook.py` checks that the twelve steps of `infra/setup.md` are present and in order, that the internal links of it and of `docs/gcp-project.md` resolve, and that neither holds a project id, bucket name, service address or token; `test_repository_language.py` enforces the English-only rule, `test_workflow_doc.py` checks the internal links of the workflow document and that the no-design rule and the complete-input rule are in it and in this file.
- `docs/maintainer-agent-workflow.md`: the rules of the maintainer's Claude sessions.
- `infra/`: the runbook `setup.md` (run by the maintainer by hand, never by a session) and the test MP3.
- `docs/gcp-project.md`: the GCP project and what the runbook creates; `docs/diagrams/`: diagrams of the designs.
- `Dockerfile`, `.dockerignore`, `pyproject.toml`, `uv.lock`, `.env.example`: container and dependencies of the service.
- `.github/`: CI (`workflows/tests.yml`), Dependabot, `CODEOWNERS`.

## Rules that matter

- **Never commit or print secrets**: `.env`, `client_secret*.json`, `credentials.json`, service account keys, the API secret used by the digest and the feed token. Only `.env.example` files with placeholders are tracked. Don't read real credential files.
- Never log the API secret, the feed token, or the text of the articles.
- **Cloud costs and the GCP project.** Sessions never deploy and never create or change resources in the real GCP project. A new GCP resource or API, a change of quota, budget or the daily episode limit, and any change to IAM, IAP, the API secret or the feed token need an issue agreed with the maintainer. See `SECURITY.md`.
- `tests/test_repository_language.py` fails when a tracked file contains Italian, outside its exceptions. Fix the text; an exception is one line with a reason in that test.
- Add tests with every change.
- Update `README.md` when behaviour or configuration changes.

## Workflow

- One branch per issue from `main`; PR against `main` with `Fixes #N`; squash and merge. Commits must be signed. Details in `CONTRIBUTING.md`. Sessions whose preset sets `AGENT_ROLE` use the branch model of `docs/maintainer-agent-workflow.md` instead.
- In the maintainer's sessions, check the identity before pushing: `gh api user --jq .login` (or `get_me` of the GitHub MCP tools where `gh` is not installed) must print `$AGENT_GH_LOGIN`. Without that variable, or on a mismatch, the session has no role and does not push, approve or merge.
- Issues and PR descriptions that list steps or acceptance criteria write them as task-list checkboxes (`- [ ]`), so the maintainer can tick off where they are. Only the maintainer ticks the boxes of an issue body: a session never edits the body of an issue to tick a box (an edit after the `approved` label voids the approval), and reports progress in a comment instead. A session ticks boxes only in the description of a PR it opened. A ticked box is never an approval or a start signal.
- Don't push, merge or touch `main` without an explicit request. A coordinator's scope, given by the maintainer, is the explicit request for merging inside that scope, and only for that.

## Agent workflow

**Status: in force since 2026-11-22**, declared by the maintainer on #2.

These rules apply to every session, with or without a role:

- **English** on GitHub and in the repository, as in "Language" above.
- **Security check** on every change to code or configuration (`.claude/`, `.github/`, dependency files, infrastructure, `.gitignore`, and anything that runs): before the PR is put to the maintainer, a session or subagent that did not write the change reads the whole diff and states its outcome in the PR. Details of a vulnerability reach the maintainer privately, as `SECURITY.md` says. A change only to `README.md`, or to documentation that defines no rules, needs no security check; `SECURITY.md`, `CLAUDE.md`, `CONTRIBUTING.md` and `docs/maintainer-agent-workflow.md` define rules, so a change to them gets one.
- **Consistent project memory and documentation**: the same PR that changes behaviour, configuration or rules brings `CLAUDE.md`, `README.md`, `docs/` and the project memory in line with it, so that no documentation debt builds up.

A session follows `docs/maintainer-agent-workflow.md` when its preset sets `AGENT_ROLE`. The roles, scope, merge conditions and stop conditions are there. The maintainer takes part only at the issue approval, the design approval and the final PR to `main`. An issue may declare that no design is needed: it then also declares that it touches no protected area and none of the topics of a design's decision section, has a single implementation step, takes the small-issue path, and names its files and tests. The owner's `approved` label on the issue covers these declarations, which count as the approved design, with no design sub-issue. The coordinator checks them before starting; if one is missing or does not hold, then or later, it is a departure from the approved issue and a hard stop. See "Issues that declare no design" in `docs/maintainer-agent-workflow.md`. An issue is the complete input: agents never open the maintainer's concept document, and a code an issue cites without its text is not looked up or asked about; the design lists it under "Referenced decisions to confirm" for the maintainer, and in an issue that declares no design it is a hard stop. See "Issues are the complete input" in `docs/maintainer-agent-workflow.md`.

- A coordinator works alone inside its scope, one approved issue plus its sub-issues: `gh pr merge` and `gh pr review` are not under `ask`. Permission patterns cannot tell a PR's base branch apart, so "a coordinator never approves or merges a PR to `main`" is a written rule.
- Hard stops: the coordinator waits for the maintainer only for cloud costs, IAM, IAP, the API secret, the feed token and anything stored about the user, a change that drops or rewrites stored data, any change to the real GCP project, a new external service, a communication outside the repository, credentials, a departure from the approved design (or from the declarations of an approved issue that declares no design), a problem found by the security check, a used-up retry limit, or anything else the final PR cannot undo or that has effects outside the repository. Every other decision it takes itself and records for the final report ("Decisions taken without the maintainer"); in doubt whether a decision is a hard stop, it stops. Every hard stop sends an in-app notification and is recorded under "Interruptions".
- Retry limit: 5 pushes per PR to fix failing checks, 5 review rounds, 5 attempts to start a session on the required model.
- Small-issue path: an issue whose approved design (or, for an issue that declares no design, the approved issue) declares no protected area and a single implementation step, and says it takes this path, is done by one worker in one PR straight to `main` (`issue/<N>/impl-1`, `Fixes #N`, documentation and project memory included), with no issue branch. Otherwise the full path applies, and `main` is merged into the issue branch once, right before the final PR, only if it is behind.
- Protected areas: a coordinator may merge into the issue branch a PR touching the protected areas listed in that file only when the approved design declares the area, the security check passed and the diff stays inside the declared areas. Changes to `SECURITY.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `docs/maintainer-agent-workflow.md`, `.claude/` and `.github/` reach `main` only through the final PR.
- Session models: the coordinator, the design worker, the security check and the reviewers run on Opus, the other workers on Sonnet. The coordinator sets the model of each worker and of the security check explicitly and checks it after the start; a missing or wrong model is retried, within the retry limit, and never replaced by another model. See "Session models" in `docs/maintainer-agent-workflow.md`.
- Permissions: the presets of both roles use Auto mode, which judges every command not under `deny` or `ask`; `.claude/settings.json` has no `allow` entries, `ask` for the write forms of `gh api`, and `deny` for the common forms of the dangerous commands, of the commands that deploy or change the GCP project, and for the Claude in Chrome tools. The presets also set `SSH_AUTH_SOCK=/dev/null` and `GIT_SSH_COMMAND=/usr/bin/false`: a session never uses SSH or the owner's credentials. Routine GitHub steps use `gh` subcommands, never a write form of `gh api` (both role tokens carry `read:org`, which `gh pr edit` needs); the GraphQL step of the approval check is the one expected permission prompt, and the final report lists every prompt. See "GitHub commands" and "Checking an approval" in `docs/maintainer-agent-workflow.md`.
- Never: push to `main`, use `--admin`, delete a branch unless the maintainer explicitly asks for it (every role, since the role tokens can delete `issue/<N>/base`), change branch protection or rulesets or these rules, create issues outside the scope, create a repository or a fork, deploy or change the GCP project, read or print credentials.
