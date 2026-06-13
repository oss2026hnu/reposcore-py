from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from typer.testing import CliRunner

from cache_manager import save_cache
from calc_score import UserContributionCounts
from main import app

runner = CliRunner()


def _generated_at(hours_ago: float) -> str:
    moment = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def _write_cache(tmp_path, repo_dir, generated_at):
    metadata = {"schemaVersion": 1}
    if generated_at is not None:
        metadata["generatedAt"] = generated_at
    save_cache(
        tmp_path / repo_dir / "cache.json",
        {"metadata": metadata, "contributions": [{"user": "carol"}]},
    )


def test_no_ttl_uses_existing_cache(tmp_path):
    _write_cache(tmp_path, "oss2026hnu_reposcore-py", _generated_at(48))
    with patch("main.fetch_contributions") as mock_fetch:
        result = runner.invoke(
            app,
            ["oss2026hnu/reposcore-py", "--token", "dummy", "--output", str(tmp_path)],
        )
    assert result.exit_code == 0
    mock_fetch.assert_not_called()


def test_fresh_cache_within_ttl_hit(tmp_path):
    _write_cache(tmp_path, "oss2026hnu_reposcore-py", _generated_at(1))
    with patch("main.fetch_contributions") as mock_fetch:
        result = runner.invoke(
            app,
            [
                "oss2026hnu/reposcore-py",
                "--token",
                "dummy",
                "--output",
                str(tmp_path),
                "--cache-ttl-hours",
                "24",
            ],
        )
    assert result.exit_code == 0
    mock_fetch.assert_not_called()


def test_stale_cache_beyond_ttl_miss(tmp_path):
    _write_cache(tmp_path, "oss2026hnu_reposcore-py", _generated_at(48))
    fake = [UserContributionCounts(user="alice", feature_bug_pr_count=1)]
    with patch("main.fetch_contributions", return_value=fake) as mock_fetch:
        result = runner.invoke(
            app,
            [
                "oss2026hnu/reposcore-py",
                "--token",
                "dummy",
                "--output",
                str(tmp_path),
                "--cache-ttl-hours",
                "24",
            ],
        )
    assert result.exit_code == 0
    mock_fetch.assert_called_once()


def test_missing_generated_at_with_ttl_miss(tmp_path):
    _write_cache(tmp_path, "oss2026hnu_reposcore-py", None)
    fake = [UserContributionCounts(user="alice", feature_bug_pr_count=1)]
    with patch("main.fetch_contributions", return_value=fake) as mock_fetch:
        result = runner.invoke(
            app,
            [
                "oss2026hnu/reposcore-py",
                "--token",
                "dummy",
                "--output",
                str(tmp_path),
                "--cache-ttl-hours",
                "24",
            ],
        )
    assert result.exit_code == 0
    mock_fetch.assert_called_once()


def test_invalid_generated_at_with_ttl_miss(tmp_path):
    _write_cache(tmp_path, "oss2026hnu_reposcore-py", "invalid-date")
    fake = [UserContributionCounts(user="alice", feature_bug_pr_count=1)]
    with patch("main.fetch_contributions", return_value=fake) as mock_fetch:
        result = runner.invoke(
            app,
            [
                "oss2026hnu/reposcore-py",
                "--token",
                "dummy",
                "--output",
                str(tmp_path),
                "--cache-ttl-hours",
                "24",
            ],
        )
    assert result.exit_code == 0
    mock_fetch.assert_called_once()


def test_no_cache_overrides_ttl(tmp_path):
    _write_cache(tmp_path, "oss2026hnu_reposcore-py", _generated_at(1))  # 신선해도
    fake = [UserContributionCounts(user="alice", feature_bug_pr_count=1)]
    with patch("main.fetch_contributions", return_value=fake) as mock_fetch:
        result = runner.invoke(
            app,
            [
                "oss2026hnu/reposcore-py",
                "--token",
                "dummy",
                "--output",
                str(tmp_path),
                "--no-cache",
                "--cache-ttl-hours",
                "24",
            ],
        )
    assert result.exit_code == 0
    mock_fetch.assert_called_once()


def test_multi_repo_partial_expiry(tmp_path):
    _write_cache(tmp_path, "oss2026hnu_reposcore-py", _generated_at(1))  # 신선
    _write_cache(tmp_path, "oss2026hnu_reposcore-ts", _generated_at(48))  # 만료
    fake = [UserContributionCounts(user="bob", feature_bug_pr_count=1)]
    with (
        patch("main.fetch_contributions", return_value=fake) as mock_single,
        patch("main.fetch_multiple_contributions") as mock_multi,
    ):
        result = runner.invoke(
            app,
            [
                "oss2026hnu/reposcore-py",
                "oss2026hnu/reposcore-ts",
                "--token",
                "dummy",
                "--output",
                str(tmp_path),
                "--cache-ttl-hours",
                "24",
            ],
        )
    assert result.exit_code == 0
    mock_single.assert_called_once()
    mock_multi.assert_not_called()
    assert mock_single.call_args.args[0] == "oss2026hnu/reposcore-ts"
