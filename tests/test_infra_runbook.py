"""Checks on the runbook of the GCP project (``infra/setup.md``).

The runbook is run by hand by the maintainer. These checks keep its twelve
steps present and in order, its internal links working, and the repository
free of identifiers: no project id, bucket name, service address or token.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = REPO_ROOT / "infra" / "setup.md"
GCP_DOC = REPO_ROOT / "docs" / "gcp-project.md"
TEST_MP3 = REPO_ROOT / "infra" / "test-episode.mp3"

STEPS = [
    "Budget with alerts",
    "Enable the APIs",
    "Logging exclusion for the request log",
    "Service account",
    "Bucket",
    "Firestore",
    "Secret with the feed token",
    "Upload the test episode",
    "Artifact Registry and image",
    "Deploy the service",
    "Checks from Cloud Shell",
    "Castamatic test (PA16)",
]

PLACEHOLDERS = {
    "<PROJECT_ID>",
    "<BILLING_ACCOUNT_ID>",
    "<BUCKET_NAME>",
    "<SERVICE_URL>",
    "<FEED_TOKEN>",
}


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def headings(markdown: str) -> list[str]:
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


def github_anchor(heading: str) -> str:
    result = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return result.replace(" ", "-")


def test_every_step_is_present_and_in_order():
    found = [h for h in headings(text(RUNBOOK)) if h.startswith("Step ")]
    expected = [f"Step {n}: {title}" for n, title in enumerate(STEPS, start=1)]
    assert found == expected


def test_logging_exclusion_comes_before_the_first_deploy():
    body = text(RUNBOOK)
    assert body.index("## Step 3:") < body.index("gcloud run deploy")


def test_design_choices_are_stated():
    body = text(RUNBOOK)
    for needle in (
        "europe-west1",
        "$5",
        "50% actual, 90% actual, 100% actual and 100% forecasted",
        "roles/datastore.user",
        "--max-instances=1",
        "## Teardown",
    ):
        assert needle in body, needle


def test_checks_expect_the_right_statuses():
    body = text(RUNBOOK)
    assert "`200`, `206`, then `404` five times" in body


def test_internal_links_are_valid():
    for path in (RUNBOOK, GCP_DOC):
        body = text(path)
        anchors = {github_anchor(h) for h in headings(body)}
        for target in re.findall(r"\]\(([^)\s]+)\)", body):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            file_part, _, anchor = target.partition("#")
            if file_part:
                assert (path.parent / file_part).resolve().exists(), target
            elif anchor:
                assert anchor in anchors, target


def test_placeholders_only():
    body = text(RUNBOOK)
    used = set(re.findall(r"<[A-Z_]+>", body))
    assert used <= PLACEHOLDERS, used - PLACEHOLDERS
    assert "<PROJECT_ID>" in used and "<BUCKET_NAME>" in used


def identifier_problems(body: str) -> list[str]:
    """Return one line per value that should be a placeholder but is not."""
    problems = []
    if re.search(r"run\.app\b", body):
        problems.append("service address")
    patterns = {
        "service account": (r"@([\w.-]+)\.iam\.gserviceaccount\.com", "<PROJECT_ID>"),
        "bucket": (r"gs://([^\s/]+)", "<BUCKET_NAME>"),
        "AUDIO_BUCKET": (r"AUDIO_BUCKET=([^\s,]+)", "<BUCKET_NAME>"),
        "--project": (r"--project[= ](\S+)", "<PROJECT_ID>"),
        "config project": (r"config set project (\S+)", "<PROJECT_ID>"),
        "image path": (r"-docker\.pkg\.dev/([^/\s]+)/", "<PROJECT_ID>"),
        "project binding": (
            r"projects (?:add|remove)-iam-policy-binding (\S+)",
            "<PROJECT_ID>",
        ),
    }
    for name, (pattern, placeholder) in patterns.items():
        for match in re.findall(pattern, body):
            if match != placeholder:
                problems.append(f"{name}: {match}")
    for match in re.findall(r"/feed/([^/\s\"]*)/", body):
        if match not in {"<FEED_TOKEN>", "$FEED_TOKEN", "wrong-token", ""}:
            problems.append(f"feed token: {match}")
    stripped = re.sub(r"https?://\S+", "", body)
    if re.search(r"[A-Za-z0-9_-]{32,}", stripped):
        problems.append("token-like string")
    return problems


def test_no_identifiers_or_tokens():
    for path in (RUNBOOK, GCP_DOC):
        assert identifier_problems(text(path)) == [], path


def test_identifier_check_fails_on_real_looking_values():
    sample = (
        "gcloud config set project linkcast-123456\n"
        "docker push europe-west1-docker.pkg.dev/linkcast-123456/linkcast/x:v1\n"
        "--set-env-vars=AUDIO_BUCKET=my-real-bucket,AUDIO_PREFIX=test/\n"
        "gcloud projects add-iam-policy-binding linkcast-123456 --member=x\n"
        "curl https://linkcast-abc123-ew.a.run.app/feed/abc/feed.xml\n"
        "gcloud storage cp x gs://my-real-bucket/test/x.mp3\n"
        "linkcast-run@linkcast-123456.iam.gserviceaccount.com\n"
        "gcloud run deploy --project=linkcast-123456\n"
    )
    problems = identifier_problems(sample)
    for expected in (
        "config project: linkcast-123456",
        "image path: linkcast-123456",
        "AUDIO_BUCKET: my-real-bucket",
        "project binding: linkcast-123456",
        "service address",
        "feed token: abc",
        "bucket: my-real-bucket",
        "service account: linkcast-123456",
        "--project: linkcast-123456",
    ):
        assert expected in problems, expected


def test_token_like_check_catches_a_token():
    sample = "token K3j9dLq2Xv8mN1pR5tYw7zA4cB6eF0hG_iU-oS"
    assert "token-like string" in identifier_problems(sample)


def test_test_episode_is_a_short_small_mp3():
    data = TEST_MP3.read_bytes()
    assert len(data) < 200 * 1024
    assert data[0] == 0xFF and data[1] & 0xE0 == 0xE0  # MPEG frame sync
    assert 8 <= len(data) / (32000 / 8) <= 12  # about 10 seconds at 32 kbps
