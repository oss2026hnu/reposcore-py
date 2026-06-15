from __future__ import annotations

import pytest

from calc_score import UserContributionCounts, UserScore
from output_writer import (
    build_csv_output,
    build_html_output,
    build_output,
    build_txt_output,
    normalize_output_format,
    write_output,
)


def make_score(
    user: str,
    feature_bug_pr: int = 0,
    doc_pr: int = 0,
    typo_pr: int = 0,
    feature_bug_issue: int = 0,
    doc_issue: int = 0,
    score: int = 0,
) -> UserScore:
    return UserScore(
        contribution=UserContributionCounts(
            user=user,
            feature_bug_pr_count=feature_bug_pr,
            doc_pr_count=doc_pr,
            typo_pr_count=typo_pr,
            feature_bug_issue_count=feature_bug_issue,
            doc_issue_count=doc_issue,
        ),
        score=score,
    )


SAMPLE = [make_score("alice", feature_bug_pr=1, doc_issue=2, score=5)]


# ── normalize_output_format ────────────────────────────────
@pytest.mark.parametrize("value", ["csv", "txt", "html"])
def test_normalize_allows_supported_formats(value):
    assert normalize_output_format(value) == value


def test_normalize_is_case_insensitive():
    assert normalize_output_format("CSV") == "csv"


def test_normalize_rejects_unsupported_format():
    with pytest.raises(ValueError):
        normalize_output_format("json")


# ── build_csv_output ───────────────────────────────────────
def test_csv_has_header_and_row():
    out = build_csv_output(SAMPLE)
    expected_header = (
        "user,feature_bug_pr,doc_pr,typo_pr,feature_bug_issue,doc_issue,total_score"
    )
    assert expected_header in out
    assert "alice" in out
    assert ",5" in out


def test_csv_detail_counts_preserved():
    scores = [make_score("bob", feature_bug_pr=2, doc_pr=1, typo_pr=3, score=11)]
    out = build_csv_output(scores)
    assert ",2," in out
    assert ",1," in out
    assert ",3," in out


# ── build_txt_output ───────────────────────────────────────
def test_txt_has_headers_and_values():
    out = build_txt_output(SAMPLE)
    for header in (
        "user",
        "feature_bug_pr",
        "doc_pr",
        "typo_pr",
        "feature_bug_issue",
        "doc_issue",
        "total_score",
    ):
        assert header in out
    assert "alice" in out
    assert "5" in out


def test_txt_no_repo_header():
    out = build_txt_output(SAMPLE)
    assert "repo" not in out


# ── build_html_output ──────────────────────────────────────
def test_html_has_table_and_user():
    out = build_html_output(SAMPLE)
    assert "<table>" in out
    assert "alice" in out


def test_html_has_user_header_not_repo():
    out = build_html_output(SAMPLE)
    assert "<th>user</th>" in out
    assert "<th>repo</th>" not in out


def test_html_has_all_detail_headers():
    out = build_html_output(SAMPLE)
    for header in (
        "feature_bug_pr",
        "doc_pr",
        "typo_pr",
        "feature_bug_issue",
        "doc_issue",
        "total_score",
    ):
        assert f"<th>{header}</th>" in out


def test_html_escapes_special_characters():
    out = build_html_output([make_score("a<b>&x", score=1)])
    assert "&lt;" in out
    assert "&gt;" in out
    assert "&amp;" in out
    assert "<b>" not in out


def test_html_score_always_present():
    out = build_html_output([make_score("carol", feature_bug_pr=1, score=3)])
    assert "<th>total_score</th>" in out
    assert "<td>3</td>" in out


# ── build_output 분기 ──────────────────────────────────────
def test_build_output_csv_branch():
    assert build_output(SAMPLE, "csv") == build_csv_output(SAMPLE)


def test_build_output_txt_branch():
    assert build_output(SAMPLE, "txt") == build_txt_output(SAMPLE)


def test_build_output_html_branch():
    assert build_output(SAMPLE, "html") == build_html_output(SAMPLE)


def test_build_output_rejects_unsupported_format():
    with pytest.raises(ValueError):
        build_output(SAMPLE, "json")


# ── write_output: stdout ───────────────────────────────────
def test_write_output_to_stdout(capsys):
    result = write_output("hello-content", None, "csv")
    captured = capsys.readouterr()
    assert result is None
    assert "hello-content" in captured.out


# ── write_output: 파일 저장 ────────────────────────────────
@pytest.mark.parametrize("fmt", ["csv", "txt", "html"])
def test_write_output_creates_result_file(tmp_path, fmt):
    content = f"sample-{fmt}"
    result_path = write_output(content, str(tmp_path), fmt)
    expected = tmp_path / f"results.{fmt}"
    assert result_path == expected
    assert expected.exists()
    assert expected.read_text(encoding="utf-8") == content
