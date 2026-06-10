from __future__ import annotations

import os
import sys
from typing import Annotated

import typer
from gql import Client, gql
from gql.transport.exceptions import TransportQueryError, TransportServerError
from gql.transport.requests import RequestsHTTPTransport

from output_writer import build_output, write_output

DEFAULT_REPOSITORY = "oss2026hnu/reposcore-py"

app = typer.Typer(help="reposcore-py CLI")


def split_repository(repository: str) -> tuple[str, str]:
    parts = repository.split("/", maxsplit=1)

    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("저장소는 owner/repo 형식이어야 합니다.")

    return parts[0], parts[1]


def fetch_repository_counts(repository: str, token: str) -> dict[str, object]:
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

    return result["repository"]


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
        str | None,
        typer.Option("--output", "-o",
            help=(
                "결과를 저장할 출력 디렉터리 경로입니다. "
                "생략하면 파일로 저장하지 않고 stdout에 출력합니다. 예: ./result"
            ),
        ),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option("--token", "-t", help="GitHub Personal Access Token. 미제공 시 GITHUB_TOKEN 환경 변수를 사용합니다."),
    ] = None,
) -> None:
    """Fetch basic repository counts from GitHub GraphQL API."""

    if len(repos) == 0:
        print("오류: 저장소를 하나 이상 입력해주세요.", file=sys.stderr)
        raise typer.Exit(1)

    results: list[dict[str, object]] = []

    resolved_token = token or os.environ.get("GITHUB_TOKEN")
    if not resolved_token:
        typer.echo("오류: GITHUB_TOKEN 환경 변수 또는 --token 옵션이 필요합니다.", err=True)
        raise typer.Exit(1)
    
    for repo in repos:
        try:
            data = fetch_repository_counts(repo, resolved_token)
            results.append(data)
        
        except RuntimeError as error:
            # 환경 변수 누락 등 설정 오류 (Exit Code: 1)
            print(f"오류: {error}", file=sys.stderr)
            raise typer.Exit(1) from error
            
        except ValueError as error:
            # 파싱 불가능한 잘못된 저장소 주소 형식 (Exit Code: 1)
            print(f"오류 ({repo}): {error}", file=sys.stderr)
            raise typer.Exit(1) from error
            
        except TransportQueryError as error:
            # 저장소를 찾을 수 없는 경우 (GraphQL 응답 내 에러 발생) (Exit Code: 3)
            print(f"오류 ({repo}): 저장소를 찾을 수 없습니다. 존재 여부와 권한을 확인하세요. (Detail: {error})", file=sys.stderr)
            raise typer.Exit(3) from error
            
        except TransportServerError as error:
            status_code = getattr(error, "code", None)
            
            if status_code in [403, 429]:
                # API 호출 한도 초과 (Exit Code: 2)
                print(f"오류 ({repo}): GitHub API 호출 한도(Rate Limit)를 초과했습니다. 잠시 후 다시 시도하세요. (Status: {status_code})", file=sys.stderr)
                raise typer.Exit(2) from error
            elif status_code == 401:
                # 잘못된 토큰 입력 등 인증 실패 (Exit Code: 4)
                print(f"오류 ({repo}): GitHub API 인증에 실패했습니다. GITHUB_TOKEN을 확인하세요. (Status: {status_code})", file=sys.stderr)
                raise typer.Exit(4) from error
            else:
                # 기타 HTTP 통신 서버 에러 (Exit Code: 1)
                print(f"오류 ({repo}): GitHub 서버 통신 중 HTTP 오류가 발생했습니다. (Status: {status_code})", file=sys.stderr)
                raise typer.Exit(1) from error
                
        except Exception as error:
            # 기타 예측하지 못한 런타임 예외 (Exit Code: 1)
            print(f"오류 ({repo}): 시스템 예외가 발생했습니다: {error}", file=sys.stderr)
            raise typer.Exit(1) from error

    try:
        content = build_output(results, format)
        write_output(content, output, format)
    except ValueError as error:
        print(f"오류: {error}", file=sys.stderr)
        raise typer.Exit(1) from error


def cli() -> None:
    app()


if __name__ == "__main__":
    cli()