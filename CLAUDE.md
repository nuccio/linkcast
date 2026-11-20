# linkcast

Turns links to articles, mostly in English, into a private podcast feed: the text of each article is extracted, translated into Italian and read by a synthetic voice, one episode per article. Planned stack: Python on Cloud Run, Firebase (Firestore) for the data, Cloud Storage for the MP3 files, Cloud Translation and Cloud Text-to-Speech, all on a personal GCP project. The repository has no application code yet: the backlog is in the issues, with the milestones `MVP` and `Release 1`.

## Language

- **Talk to the maintainer in Italian**: replies, questions, explanations, summaries in chat.
- **Everything written into the repository and on GitHub is in English**: documentation, issues, pull requests, comments, commit messages, log messages, code comments, docstrings, identifiers and error messages. Italian is used only in the conversation with the maintainer, and in the files listed as exceptions in `tests/test_repository_language.py`.

## Commands

```bash
python3 -m pip install pytest             # test dependencies
python3 -m pytest tests                   # repository checks, from the repository root
```

The issue that adds the application code adds its commands here (install, run, tests, lint), together with the jobs in `.github/workflows/tests.yml`.

## Layout

- `tests/`: repository checks; `test_repository_language.py` enforces the English-only rule.
- `docs/maintainer-agent-workflow.md`: the rules of the maintainer's Claude sessions.
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
- Don't push, merge or touch `main` without an explicit request. A coordinator's scope, given by the maintainer, is the explicit request for merging inside that scope, and only for that.

## Agent workflow

**Status: work in progress, not in force.** The rules of `docs/maintainer-agent-workflow.md` and of this section are not applied yet, by any session, with or without `AGENT_ROLE`. They come into force only when the maintainer declares a first satisfactory version: every configuration is complete and tested, both the repository files and the owner's manual steps (#21), and the check after setup has passed (#22). The maintainer records that declaration in a comment on #2, and a PR removes this paragraph. Until then:

- there are no coordinator or worker roles: no session is started from a role preset, and no issue is run through the workflow (no `approved` label as a start signal, no issue branches, no sub-issues created by an agent);
- work goes the normal way: one branch and one PR to `main` per change, following the "Workflow" section above, reviewed and merged by the maintainer. This holds for changes to the workflow itself too (decided by the maintainer on 2026-11-20);
- the only exception is the rehearsal of #22, which the maintainer starts on purpose to test the workflow.

These rules are in force from now, whatever the status of the workflow (decided by the maintainer on 2026-11-20):

- **English** on GitHub and in the repository, as in "Language" above.
- **Security check** on every change to code or configuration (`.claude/`, `.github/`, dependency files, infrastructure, `.gitignore`, and anything that runs): before the PR is put to the maintainer, a session or subagent that did not write the change reads the whole diff and states its outcome in the PR. Details of a vulnerability reach the maintainer privately, as `SECURITY.md` says. A change only to `README.md` or other documentation needs no security check.
- **Consistent project memory and documentation**: the same PR that changes behaviour, configuration or rules brings `CLAUDE.md`, `README.md`, `docs/` and the project memory in line with it, so that no documentation debt builds up.

Once in force, a session follows `docs/maintainer-agent-workflow.md` when its preset sets `AGENT_ROLE`. The roles, scope, merge conditions and stop conditions are there. The maintainer takes part only at the issue approval, the design approval and the final PR to `main`.

- A coordinator works alone inside its scope, one approved issue plus its sub-issues: `gh pr merge` and `gh pr review` are not under `ask`. Permission patterns cannot tell a PR's base branch apart, so "a coordinator never approves or merges a PR to `main`" is a written rule.
- Hard stops: the coordinator waits for the maintainer only for cloud costs, IAM, IAP, the API secret, the feed token and anything stored about the user, a change that drops or rewrites stored data, any change to the real GCP project, a new external service, a communication outside the repository, credentials, a departure from the approved design, a problem found by the security check, a used-up retry limit, or anything else the final PR cannot undo or that has effects outside the repository. Every other decision it takes itself and records for the final report ("Decisions taken without the maintainer"); in doubt whether a decision is a hard stop, it stops. Every hard stop sends an in-app notification and is recorded under "Interruptions".
- Retry limit: 5 pushes per PR to fix failing checks, 5 review rounds, 5 attempts to start a session on the required model.
- Small-issue path: an issue whose approved design declares no protected area and a single implementation step, and says it takes this path, is done by one worker in one PR straight to `main` (`issue/<N>/impl-1`, `Fixes #N`, documentation and project memory included), with no issue branch. Otherwise the full path applies, and `main` is merged into the issue branch once, right before the final PR, only if it is behind.
- Protected areas: a coordinator may merge into the issue branch a PR touching the protected areas listed in that file only when the approved design declares the area, the security check passed and the diff stays inside the declared areas. Changes to `SECURITY.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `docs/maintainer-agent-workflow.md`, `.claude/` and `.github/` reach `main` only through the final PR.
- Session models: the coordinator, the design worker, the security check and the reviewers run on Opus, the other workers on Sonnet. The coordinator sets the model of each worker and of the security check explicitly and checks it after the start; a missing or wrong model is retried, within the retry limit, and never replaced by another model. See "Session models" in `docs/maintainer-agent-workflow.md`.
- Permissions: the presets of both roles use Auto mode, which judges every command not under `deny` or `ask`; `.claude/settings.json` has no `allow` entries, `ask` for the write forms of `gh api`, and `deny` for the common forms of the dangerous commands, for the commands that deploy or change the GCP project, and for the Claude in Chrome tools. The presets also set `SSH_AUTH_SOCK=/dev/null` and `GIT_SSH_COMMAND=/usr/bin/false`: a session never uses SSH or the owner's credentials.
- Never: push to `main`, use `--admin`, delete a branch unless the maintainer explicitly asks for it (every role, since the role tokens can delete `issue/<N>/base`), change branch protection or rulesets or these rules, create issues outside the scope, create a repository or a fork, deploy or change the GCP project, read or print credentials.
