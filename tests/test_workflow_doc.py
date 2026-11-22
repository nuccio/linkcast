"""Checks on the maintainer's agent workflow document.

The rules of the agent sessions live in ``docs/maintainer-agent-workflow.md``
and are summarised in ``CLAUDE.md``. These checks keep the internal links of
the document working and the rule on issues that declare no design present in
both files.
"""

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
