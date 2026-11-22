"""Checks on the maintainer's agent workflow document.

The rules of the agent sessions live in ``docs/maintainer-agent-workflow.md``
and are summarised in ``CLAUDE.md``. These checks keep the internal links of
the document working, the rules on issues that declare no design and on
issues as the complete input present in both files, and the rules that keep
routine GitHub steps free of permission prompts in the document.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DOC = REPO_ROOT / "docs" / "maintainer-agent-workflow.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

NO_DESIGN_HEADING = "Issues that declare no design"


def github_anchor(heading: str) -> str:
    """Return the anchor GitHub generates for a Markdown heading."""
    text = heading.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def headings(markdown: str) -> list[str]:
    """Return the text of every heading outside fenced code blocks."""
    found = []
    in_fence = False
    for line in markdown.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        match = re.match(r"#{1,6} (.+)", line)
        if match and not in_fence:
            found.append(match.group(1))
    return found


def test_github_anchor_matches_github_rules():
    assert github_anchor("Waiting for CI") == "waiting-for-ci"
    assert github_anchor("Issues that declare no design") == (
        "issues-that-declare-no-design"
    )
    assert github_anchor("Decision: full autonomy inside the scope") == (
        "decision-full-autonomy-inside-the-scope"
    )


def test_internal_links_of_the_workflow_doc_resolve():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    anchors = {github_anchor(heading) for heading in headings(text)}
    links = set(re.findall(r"\]\(#([^)]+)\)", text))
    assert links, "the workflow document is expected to link its own sections"
    missing = sorted(link for link in links if link not in anchors)
    assert not missing, f"links to sections that do not exist: {missing}"


def test_workflow_doc_defines_issues_that_declare_no_design():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    assert NO_DESIGN_HEADING in headings(text)
    section = text.split(f"### {NO_DESIGN_HEADING}", 1)[1].split("\n## ", 1)[0]
    for required in (
        "no protected area",
        "single implementation step",
        "small-issue path",
        "`approved` label",
        "hard stop",
        "voids it",
    ):
        assert required in section, f"the section does not mention {required!r}"


def test_claude_md_points_to_the_no_design_rule():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "declare that no design is needed" in text
    assert f'"{NO_DESIGN_HEADING}"' in text


def section(text: str, heading: str) -> str:
    """Return the body of a ``###`` section, up to the next heading of level 2 or 3."""
    body = text.split(f"### {heading}\n", 1)[1]
    return re.split(r"\n#{2,3} ", body, maxsplit=1)[0]


def test_routine_github_steps_use_gh_subcommands():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    assert "GitHub commands" in headings(text)
    commands = section(text, "GitHub commands")
    for required in (
        "gh issue create --parent",
        "gh issue comment",
        "gh issue edit <N> --add-label",
        "gh issue edit <N> --remove-label",
        "gh pr create",
        "gh pr edit",
        "gh pr comment",
        "gh pr review",
        "gh pr merge",
        "never a write form of `gh api`",
        "No `allow` entry",
        "read:org",
    ):
        assert required in commands, f"the section does not mention {required!r}"


def test_approval_check_names_its_one_expected_prompt():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    check = section(text, "Checking an approval")
    assert "gh issue view <N> --json updatedAt" in check
    assert "lastEditedAt" in check
    assert "one expected permission prompt" in check


def test_both_role_tokens_have_read_org():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    token_step = next(
        line for line in text.splitlines()
        if line.startswith("2. Create a classic personal access token")
    )
    assert "`read:org` on both" in token_step
    assert "ok token has read:org" in text


def test_final_report_lists_every_permission_prompt():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    assert "Each permission prompt is listed on its own" in text
    assert "known gap" in text
    assert "Starting a worker" in headings(text)


def test_settings_keep_ask_on_gh_api_writes_and_have_no_allow():
    settings = json.loads(
        (REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    permissions = settings["permissions"]
    assert "allow" not in permissions or not permissions["allow"]
    for entry in ("Bash(gh api -X*)", "Bash(gh api graphql*)"):
        assert entry in permissions["ask"]


COMPLETE_INPUT_HEADING = "Issues are the complete input"


def test_workflow_doc_defines_issues_as_the_complete_input():
    text = WORKFLOW_DOC.read_text(encoding="utf-8")
    assert COMPLETE_INPUT_HEADING in headings(text)
    rule = section(text, COMPLETE_INPUT_HEADING)
    for required in (
        "never open the maintainer's concept document",
        "do not ask about it and do not look it up",
        "Referenced decisions to confirm",
        "what the design assumed",
        "does not list there",
        "hard stop",
    ):
        assert required in rule, f"the section does not mention {required!r}"


def test_claude_md_points_to_the_complete_input_rule():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "Referenced decisions to confirm" in text
    assert f'"{COMPLETE_INPUT_HEADING}"' in text


def test_workflow_is_in_force_in_both_files():
    for path in (WORKFLOW_DOC, CLAUDE_MD):
        text = path.read_text(encoding="utf-8")
        assert "**Status: in force since 2026-11-22**" in text, path.name
        assert "not in force" not in text, path.name
