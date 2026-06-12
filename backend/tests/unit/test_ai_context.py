from app.ai.context import commits_digest, issues_digest, merge_requests_digest, source_data_digest
from tests.fakes import sample_commits, sample_issues, sample_mrs


def test_commits_digest_includes_refs():
    digest = commits_digest(sample_commits())
    assert "commit:abc12345" in digest
    assert "feat: add payment retries" in digest


def test_empty_inputs_have_placeholders():
    assert "(no commits in range)" in commits_digest([])
    assert "(no closed issues in range)" in issues_digest([])
    assert "(no merged merge requests in range)" in merge_requests_digest([])


def test_source_data_digest_sections():
    digest = source_data_digest(sample_commits(), sample_mrs(), sample_issues())
    assert "## Commits" in digest
    assert "## Merge Requests" in digest
    assert "## Issues" in digest
    assert "mr:!42" in digest
    assert "issue:#10" in digest
