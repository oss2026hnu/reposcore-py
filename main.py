from __future__ import annotations

import os
import sys
from typing import Annotated, Any, Optional

import typer
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from output_writer import build_output, write_output
from repo_cache import get_cached_repository_counts, set_cached_repository_counts


DEFAULT_REPOSITORY = "oss2026hnu/reposcore-py"

app = typer.Typer(help="reposcore-py CLI")


def split_repository(repository: str) -> tuple[str, str]:
    parts = repository.split("/", maxsplit=1)

    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("저장소는 owner/repo 형식이어야 합니다.")

    return parts[0], parts[1]


def fetch_repository_counts(
    repository: str,
    use_cache: bool = True,
) -> dict[str, Any]:
    if use_cache:
        cached_data = get_cached_repository_counts(repository)
        if cached_data is not None:
            return cached_data

    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        raise RuntimeError("GitHub GraphQL API 호출을 위해 GITHUB_TOKEN 환경 변수가 필요합니다.")

    owner, name = split_repository(repository)

    transport = RequestsHTTPTransport(
        url="https://api.github.com/graphql",
        headers={"Authorization": f"Bearer {token}"},
        verify=True,
        retries=3,
    )

    query = gql(
        """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            nameWithOwner
            issues(first: 1) {
              totalCount
            }
            pullRequests(first: 1) {
              totalCount
            }
          }
        }
        """
    )

    with Client(transport=transport, fetch_schema_from_transport=False) as session:
        result = session.execute(
            query,
            variable_values={
                "owner": owner,
                "name": name,
            },
        )

    repository_data = result["repository"]

    if use_cache:
        set_cached_repository_counts(repository, repository_data)

    return repository_data


@app.command()
def main(
    repos: Annotated[
        list[str],
        typer.Argument(help="조회할 GitHub 저장소 경로입니다. 예: owner/repo1 owner/repo2"),
    ],
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="출력 파일 형식을 지정합니다. (csv | txt | html)"),
    ] = "txt",
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="결과를 저장할 출력 디렉터리 경로입니다. 예: ./result"),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="캐시를 사용하지 않고 GitHub API에서 새로 조회합니다."),
    ] = False,
) -> None:
    """Fetch basic repository counts from GitHub GraphQL API."""

    if len(repos) == 0:
        typer.echo("오류: 저장소를 하나 이상 입력해주세요.", err=True)
        raise typer.Exit(1)

    results: list[dict[str, Any]] = []

    for repo in repos:
        try:
            data = fetch_repository_counts(repo, use_cache=not no_cache)
        except Exception as error:
            print(f"오류 ({repo}): {error}", file=sys.stderr)
            raise typer.Exit(1) from error

        results.append(data)

    try:
        content = build_output(results, format)
        write_output(content, output, format)
    except ValueError as error:
        typer.echo(f"오류: {error}", err=True)
        raise typer.Exit(1) from error


def cli() -> None:
    app()


if __name__ == "__main__":
    cli()
