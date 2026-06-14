from typer.testing import CliRunner

import main

runner = CliRunner()


def test_format_option_is_case_insensitive(monkeypatch):
    def fake_load_or_fetch_contributions(
        repos,
        token,
        output,
        cache=True,  # no_cache=False 에서 신규 표준 매개변수인 cache=True로 리팩토링
        since=None,
        until=None,
        page_size=100,
    ):
        return [[] for _ in repos]

    monkeypatch.setattr(
        main,
        "_load_or_fetch_contributions",
        fake_load_or_fetch_contributions,
    )

    result = runner.invoke(
        main.app,
        ["oss2026hnu/reposcore-py", "--format", "CSV", "--token", "dummy-token"],
    )

    assert result.exit_code == 0


def test_page_size_option_is_passed_to_loader(monkeypatch):
    captured = {}

    def fake_load_or_fetch_contributions(
        repos,
        token,
        output,
        cache=True,  # 신규 표준 매개변수인 cache=True로 반영
        since=None,
        until=None,
        page_size=100,
    ):
        captured["page_size"] = page_size
        return [[] for _ in repos]

    monkeypatch.setattr(
        main,
        "_load_or_fetch_contributions",
        fake_load_or_fetch_contributions,
    )

    result = runner.invoke(
        main.app,
        ["oss2026hnu/reposcore-py", "--token", "dummy-token", "--page-size", "25"],
    )

    assert result.exit_code == 0
    assert captured["page_size"] == 25


def test_page_size_envvar_is_passed_to_loader(monkeypatch):
    captured = {}

    def fake_load_or_fetch_contributions(
        repos,
        token,
        output,
        cache=True,  # 신규 표준 매개변수인 cache=True로 반영
        since=None,
        until=None,
        page_size=100,
    ):
        captured["page_size"] = page_size
        return [[] for _ in repos]

    monkeypatch.setattr(
        main,
        "_load_or_fetch_contributions",
        fake_load_or_fetch_contributions,
    )

    result = runner.invoke(
        main.app,
        ["oss2026hnu/reposcore-py", "--token", "dummy-token"],
        env={"REPOSCORE_PAGE_SIZE": "30"},
    )

    assert result.exit_code == 0
    assert captured["page_size"] == 30


# [신규 단위 테스트 검증 스펙 완벽 추가] --cache / --no-cache 한 쌍이 제어 로직에 정상 바인딩되는지 검증합니다.
def test_cache_and_no_cache_toggle_options(monkeypatch):
    captured = {}

    def fake_load_or_fetch_contributions(
        repos,
        token,
        output,
        cache=True,
        since=None,
        until=None,
        page_size=100,
    ):
        captured["cache"] = cache
        return [[] for _ in repos]

    monkeypatch.setattr(
        main,
        "_load_or_fetch_contributions",
        fake_load_or_fetch_contributions,
    )

    # Case 1: 명시적으로 --cache 옵션을 주었을 때 True 가 찍히는지 확인
    result_cache = runner.invoke(
        main.app,
        ["oss2026hnu/reposcore-py", "--token", "dummy-token", "--cache"],
    )
    assert result_cache.exit_code == 0
    assert captured["cache"] is True

    # Case 2: 명시적으로 대칭 옵션인 --no-cache 를 주었을 때 False 가 찍히는지 확인
    result_no_cache = runner.invoke(
        main.app,
        ["oss2026hnu/reposcore-py", "--token", "dummy-token", "--no-cache"],
    )
    assert result_no_cache.exit_code == 0
    assert captured["cache"] is False