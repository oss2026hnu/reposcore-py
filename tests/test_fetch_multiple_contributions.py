from __future__ import annotations

import pytest

from gh_service import fetch_multiple_contributions


# ── 공통 헬퍼 ─────────────────────────────────────────────────


def make_node(login: str | None, labels: list[str]) -> dict:
    author = {"login": login} if login else None
    return {
        "author": author,
        "labels": {"nodes": [{"name": label} for label in labels]},
    }


def make_multi_issue_response(
    repo_data: dict[str, tuple[list[dict], bool, str | None]],
) -> dict:
    """repo_data: {alias: (nodes, hasNextPage, endCursor)}"""
    result = {}
    for alias, (nodes, has_next, end_cursor) in repo_data.items():
        result[alias] = {
            "issues": {
                "pageInfo": {
                    "hasNextPage": has_next,
                    "endCursor": end_cursor,
                },
                "nodes": nodes,
            }
        }
    return result


def make_multi_pr_response(
    repo_data: dict[str, tuple[list[dict], bool, str | None]],
) -> dict:
    """repo_data: {alias: (nodes, hasNextPage, endCursor)}"""
    result = {}
    for alias, (nodes, has_next, end_cursor) in repo_data.items():
        result[alias] = {
            "pullRequests": {
                "pageInfo": {
                    "hasNextPage": has_next,
                    "endCursor": end_cursor,
                },
                "nodes": nodes,
            }
        }
    return result


class DummySession:
    def __init__(self, execute_handler):
        self._execute = execute_handler
        self.calls: list[tuple] = []

    def execute(self, query, variable_values=None):
        self.calls.append((query, variable_values))
        return self._execute(query, variable_values or {})


class DummyClient:
    def __init__(self, execute_handler):
        self.session = DummySession(execute_handler)

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# ── 빈 저장소 목록 테스트 ─────────────────────────────────────


def test_empty_repositories_returns_empty_list(monkeypatch: pytest.MonkeyPatch):
    create_client_called = False

    def mock_create_client(token):
        nonlocal create_client_called
        create_client_called = True
        return DummyClient(lambda q, v: {})

    monkeypatch.setattr("gh_service.create_client", mock_create_client)

    result = fetch_multiple_contributions([], "dummy_token")

    assert result == []
    assert not create_client_called


# ── alias query 생성 흐름 테스트 ──────────────────────────────


def test_alias_query_contains_repo0_and_repo1(monkeypatch: pytest.MonkeyPatch):
    captured_queries: list[str] = []
    captured_variables: list[dict] = []

    def mock_execute(query, variable_values):
        query_str = str(query)
        captured_queries.append(query_str)
        captured_variables.append(variable_values)

        if "issues" in query_str:
            return make_multi_issue_response(
                {
                    "repo0": ([], False, None),
                    "repo1": ([], False, None),
                }
            )
        return make_multi_pr_response(
            {
                "repo0": ([], False, None),
                "repo1": ([], False, None),
            }
        )

    monkeypatch.setattr(
        "gh_service.create_client",
        lambda token: DummyClient(mock_execute),
    )

    fetch_multiple_contributions(
        ["owner/repo-a", "owner/repo-b"], "dummy_token"
    )

    issue_queries = [q for q in captured_queries if "issues" in q]
    pr_queries = [q for q in captured_queries if "pullRequests" in q]

    assert len(issue_queries) >= 1
    assert "repo0" in issue_queries[0]
    assert "repo1" in issue_queries[0]

    assert len(pr_queries) >= 1
    assert "repo0" in pr_queries[0]
    assert "repo1" in pr_queries[0]


def test_variables_contain_owner_name_after_for_each_repo(
    monkeypatch: pytest.MonkeyPatch,
):
    captured_variables: list[dict] = []

    def mock_execute(query, variable_values):
        captured_variables.append(variable_values)
        query_str = str(query)
        if "issues" in query_str:
            return make_multi_issue_response(
                {
                    "repo0": ([], False, None),
                    "repo1": ([], False, None),
                }
            )
        return make_multi_pr_response(
            {
                "repo0": ([], False, None),
                "repo1": ([], False, None),
            }
        )

    monkeypatch.setattr(
        "gh_service.create_client",
        lambda token: DummyClient(mock_execute),
    )

    fetch_multiple_contributions(
        ["ownerA/repoA", "ownerB/repoB"], "dummy_token"
    )

    issue_vars = captured_variables[0]
    assert issue_vars["owner0"] == "ownerA"
    assert issue_vars["name0"] == "repoA"
    assert "after0" in issue_vars

    assert issue_vars["owner1"] == "ownerB"
    assert issue_vars["name1"] == "repoB"
    assert "after1" in issue_vars


# ── issue 결과 저장소별 분리 테스트 ──────────────────────────


def test_issue_results_are_separated_by_repository(monkeypatch: pytest.MonkeyPatch):
    def mock_execute(query, variable_values):
        query_str = str(query)
        if "issues" in query_str:
            return make_multi_issue_response(
                {
                    "repo0": (
                        [make_node("user_a", ["bug"])],
                        False,
                        None,
                    ),
                    "repo1": (
                        [make_node("user_b", ["documentation"])],
                        False,
                        None,
                    ),
                }
            )
        return make_multi_pr_response(
            {
                "repo0": ([], False, None),
                "repo1": ([], False, None),
            }
        )

    monkeypatch.setattr(
        "gh_service.create_client",
        lambda token: DummyClient(mock_execute),
    )

    result = fetch_multiple_contributions(
        ["owner/repo-a", "owner/repo-b"], "dummy_token"
    )

    assert len(result) == 2

    repo0_users = {c.user for c in result[0]}
    repo1_users = {c.user for c in result[1]}

    assert "user_a" in repo0_users
    assert "user_b" not in repo0_users

    assert "user_b" in repo1_users
    assert "user_a" not in repo1_users


def test_issue_results_order_matches_input_order(monkeypatch: pytest.MonkeyPatch):
    def mock_execute(query, variable_values):
        query_str = str(query)
        if "issues" in query_str:
            return make_multi_issue_response(
                {
                    "repo0": (
                        [make_node("first_repo_user", ["bug"])],
                        False,
                        None,
                    ),
                    "repo1": (
                        [make_node("second_repo_user", ["bug"])],
                        False,
                        None,
                    ),
                }
            )
        return make_multi_pr_response(
            {
                "repo0": ([], False, None),
                "repo1": ([], False, None),
            }
        )

    monkeypatch.setattr(
        "gh_service.create_client",
        lambda token: DummyClient(mock_execute),
    )

    result = fetch_multiple_contributions(
        ["owner/first-repo", "owner/second-repo"], "dummy_token"
    )

    assert len(result) == 2
    assert result[0][0].user == "first_repo_user"
    assert result[1][0].user == "second_repo_user"


# ── PR 결과 저장소별 분리 테스트 ─────────────────────────────


def test_pr_results_are_separated_by_repository(monkeypatch: pytest.MonkeyPatch):
    def mock_execute(query, variable_values):
        query_str = str(query)
        if "issues" in query_str:
            return make_multi_issue_response(
                {
                    "repo0": ([], False, None),
                    "repo1": ([], False, None),
                }
            )
        return make_multi_pr_response(
            {
                "repo0": (
                    [make_node("user_a", ["enhancement"])],
                    False,
                    None,
                ),
                "repo1": (
                    [make_node("user_b", ["typo"])],
                    False,
                    None,
                ),
            }
        )

    monkeypatch.setattr(
        "gh_service.create_client",
        lambda token: DummyClient(mock_execute),
    )

    result = fetch_multiple_contributions(
        ["owner/repo-a", "owner/repo-b"], "dummy_token"
    )

    assert len(result) == 2

    repo0_by_user = {c.user: c for c in result[0]}
    repo1_by_user = {c.user: c for c in result[1]}

    assert "user_a" in repo0_by_user
    assert repo0_by_user["user_a"].feature_bug_pr_count == 1
    assert "user_b" not in repo0_by_user

    assert "user_b" in repo1_by_user
    assert repo1_by_user["user_b"].typo_pr_count == 1
    assert "user_a" not in repo1_by_user


# ── issue pagination cursor 저장소별 관리 테스트 ──────────────


def test_issue_pagination_cursor_managed_per_repository(
    monkeypatch: pytest.MonkeyPatch,
):
    call_count = 0
    captured_variables: list[dict] = []

    def mock_execute(query, variable_values):
        nonlocal call_count
        query_str = str(query)

        if "issues" in query_str:
            call_count += 1
            captured_variables.append(dict(variable_values))

            if call_count == 1:
                # 첫 번째 issue 조회: repo0은 다음 페이지 있음, repo1은 없음
                return make_multi_issue_response(
                    {
                        "repo0": (
                            [make_node("user_a", ["bug"])],
                            True,
                            "cursor0",
                        ),
                        "repo1": (
                            [make_node("user_b", ["documentation"])],
                            False,
                            None,
                        ),
                    }
                )
            else:
                # 두 번째 issue 조회: repo0만 active
                return make_multi_issue_response(
                    {
                        "repo0": (
                            [make_node("user_a", ["enhancement"])],
                            False,
                            None,
                        ),
                    }
                )

        return make_multi_pr_response(
            {
                "repo0": ([], False, None),
                "repo1": ([], False, None),
            }
        )

    monkeypatch.setattr(
        "gh_service.create_client",
        lambda token: DummyClient(mock_execute),
    )

    result = fetch_multiple_contributions(
        ["owner/repo-a", "owner/repo-b"], "dummy_token"
    )

    # issue query가 2번 실행되었는지 확인
    assert call_count == 2

    # 두 번째 issue query에는 repo0만 포함 (after0="cursor0")
    second_vars = captured_variables[1]
    assert second_vars["after0"] == "cursor0"
    assert "owner1" not in second_vars

    # repo0은 두 페이지 결과가 누적됨
    repo0_by_user = {c.user: c for c in result[0]}
    assert repo0_by_user["user_a"].feature_bug_issue_count == 2

    # repo1은 첫 페이지 결과만 포함
    repo1_by_user = {c.user: c for c in result[1]}
    assert repo1_by_user["user_b"].doc_issue_count == 1


# ── PR pagination cursor 저장소별 관리 테스트 ────────────────


def test_pr_pagination_cursor_managed_per_repository(monkeypatch: pytest.MonkeyPatch):
    pr_call_count = 0
    captured_pr_variables: list[dict] = []

    def mock_execute(query, variable_values):
        nonlocal pr_call_count
        query_str = str(query)

        if "issues" in query_str:
            return make_multi_issue_response(
                {
                    "repo0": ([], False, None),
                    "repo1": ([], False, None),
                }
            )

        # PR 조회
        pr_call_count += 1
        captured_pr_variables.append(dict(variable_values))

        if pr_call_count == 1:
            return make_multi_pr_response(
                {
                    "repo0": (
                        [make_node("user_a", ["bug"])],
                        True,
                        "pr_cursor0",
                    ),
                    "repo1": (
                        [make_node("user_b", ["typo"])],
                        False,
                        None,
                    ),
                }
            )
        else:
            return make_multi_pr_response(
                {
                    "repo0": (
                        [make_node("user_a", ["enhancement"])],
                        False,
                        None,
                    ),
                }
            )

    monkeypatch.setattr(
        "gh_service.create_client",
        lambda token: DummyClient(mock_execute),
    )

    result = fetch_multiple_contributions(
        ["owner/repo-a", "owner/repo-b"], "dummy_token"
    )

    assert pr_call_count == 2

    second_pr_vars = captured_pr_variables[1]
    assert second_pr_vars["after0"] == "pr_cursor0"
    assert "owner1" not in second_pr_vars

    repo0_by_user = {c.user: c for c in result[0]}
    assert repo0_by_user["user_a"].feature_bug_pr_count == 2

    repo1_by_user = {c.user: c for c in result[1]}
    assert repo1_by_user["user_b"].typo_pr_count == 1


# ── 단일 저장소 입력 테스트 ───────────────────────────────────


def test_single_repository_returns_single_element_list(
    monkeypatch: pytest.MonkeyPatch,
):
    def mock_execute(query, variable_values):
        query_str = str(query)
        if "issues" in query_str:
            return make_multi_issue_response(
                {"repo0": ([make_node("solo_user", ["bug"])], False, None)}
            )
        return make_multi_pr_response(
            {"repo0": ([], False, None)}
        )

    monkeypatch.setattr(
        "gh_service.create_client",
        lambda token: DummyClient(mock_execute),
    )

    result = fetch_multiple_contributions(["owner/solo-repo"], "dummy_token")

    assert len(result) == 1
    assert result[0][0].user == "solo_user"
    assert result[0][0].feature_bug_issue_count == 1
