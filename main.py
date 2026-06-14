from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated

import typer
from gql.transport.exceptions import TransportQueryError, TransportServerError

from cache_manager import load_cache, save_cache
from calc_score import (
    UserContributionCounts,
    UserScore,
    calculate_repository_scores,
    calculate_total_scores,
)
from gh_service import fetch_contributions, fetch_multiple_contributions
from output_writer import build_output, write_output

app = typer.Typer(help="reposcore-py CLI")


def version_callback(value: bool) -> None:
    if value:
        try:
            ver = version("reposcore-py")
        except PackageNotFoundError:
            ver = "unknown"
        typer.echo(ver)
        raise typer.Exit()


def split_repository(repository: str) -> tuple[str, str]:
    parts = repository.split("/")

    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("저장소는 owner/repo 형식이어야 합니다.")

    return parts[0], parts[1]


def _dump_contributions(
    contributions: list[UserContributionCounts],
) -> list[dict]:
    return [
        contribution.model_dump()
        if hasattr(contribution, "model_dump")
        else vars(contribution)
        for contribution in contributions
    ]


def _score_to_result(score: UserScore) -> dict:
    """UserScore를 output_writer가 기대하는 dict 형태로 변환합니다."""
    contribution = score.contribution
    return {
        "nameWithOwner": contribution.user,
        "issues": {
            "totalCount": contribution.feature_bug_issue_count
            + contribution.doc_issue_count,
        },
        "pullRequests": {
            "totalCount": contribution.feature_bug_pr_count
            + contribution.doc_pr_count
            + contribution.typo_pr_count,
        },
        "totalScore": score.score,
    }


def _load_or_fetch_contributions(
    repos: list[str],
    token: str,
    output: str | None,
    no_cache: bool = False,
    since: date | None = None,
    until: date | None = None,
) -> list[list[UserContributionCounts]]:
    all_contributions: list[list[UserContributionCounts]] = [[] for _ in repos]
    cache_paths: list[Path | None] = []
    missing_indexes: list[int] = []
    missing_repos: list[str] = []

    for index, repo in enumerate(repos):
        owner, repo_name = split_repository(repo)
        cache_path = None

        if not no_cache and output:
            cache_path = Path(output) / f"{owner}_{repo_name}" / "cache.json"

        cache_paths.append(cache_path)
        cached_data = load_cache(cache_path) if cache_path else {}

        if "contributions" in cached_data:
            all_contributions[index] = [
                UserContributionCounts(**contribution)
                for contribution in cached_data["contributions"]
            ]
        else:
            missing_indexes.append(index)
            missing_repos.append(repo)

    if missing_repos:
        if len(missing_repos) == 1:
            fetched_contributions = [
                fetch_contributions(missing_repos[0], token, since, until)
            ]
        else:
            fetched_contributions = fetch_multiple_contributions(
                missing_repos,
                token,
                since,
                until,
            )

        for index, repo, contributions in zip(
            missing_indexes,
            missing_repos,
            fetched_contributions,
            strict=True,
        ):
            all_contributions[index] = contributions
            cache_path = cache_paths[index]

            if cache_path:
                owner, repo_name = split_repository(repo)
                save_cache(
                    cache_path,
                    {
                        "metadata": {
                            "repository": repo,
                            "owner": owner,
                            "name": repo_name,
                            "schemaVersion": 1,
                            "generatedAt": datetime.now(timezone.utc)
                            .isoformat(timespec="seconds")
                            .replace("+00:00", "Z"),
                        },
                        "contributions": _dump_contributions(contributions),
                    },
                )

    return all_contributions


@app.command()
def main(
    repos: Annotated[
        list[str],
        typer.Argument(
            help="조회할 GitHub 저장소 경로입니다. 예: owner/repo1 owner/repo2"
        ),
    ],
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="현재 버전을 출력하고 종료합니다.",
            is_eager=True,
            callback=version_callback,
        ),
    ] = False,
    # [수정] 제한적인 Enum 형식을 과감히 철폐하고 문자열(str) 유연 인터페이스로 전환
    format: Annotated[
        str | None,
        typer.Option(
            "--format",
            "-f",
            help=(
                "출력 파일 형식을 지정합니다. 쉼표(,)로 구분하여 여러 형식을 동시에 줄 수 있습니다. "
                "사용 가능한 형식: csv, txt, html. 형식을 아예 주지 않거나 유효한 형식이 없으면 전체 형식을 모두 출력합니다."
            ),
        ),
    ] = None,
    output: Annotated[
        str | None,
        typer.Option(
            "--output",
            "-o",
            help=(
                "결과를 저장할 출력 디렉터리 경로입니다. "
                "생략하면 파일로 저장하지 않고 stdout에 출력합니다. 예: ./result"
            ),
        ),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option(
            "--token",
            "-t",
            help=(
                "GitHub Personal Access Token. "
                "미제공 시 GITHUB_TOKEN 환경 변수를 사용합니다."
            ),
        ),
    ] = None,
    aggregate: Annotated[
        bool,
        typer.Option(
            "--aggregate",
            help="여러 저장소의 결과를 하나로 합산하여 전체 기여 점수를 출력합니다.",
        ),
    ] = False,
    no_cache: Annotated[
        bool,
        typer.Option(
            "--no-cache",
            help="캐시를 사용하지 않고 GitHub API에서 최신 데이터를 다시 조회합니다.",
        ),
    ] = False,
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            help=(
                "이 날짜 이후의 기여만 점수 계산에 포함합니다. "
                "예: 2026-06-01 (YYYY-MM-DD)"
            ),
        ),
    ] = None,
    until: Annotated[
        str | None,
        typer.Option(
            "--until",
            help=(
                "이 날짜까지의 기여만 점수 계산에 포함합니다. "
                "예: 2026-06-10 (YYYY-MM-DD)"
            ),
        ),
    ] = None,
) -> None:
    """Fetch basic repository counts from GitHub GraphQL API."""

    if len(repos) == 0:
        print("오류: 저장소를 하나 이상 입력해주세요.", file=sys.stderr)
        raise typer.Exit(1)

    resolved_token = token or os.environ.get("GITHUB_TOKEN")
    if not resolved_token:
        typer.echo(
            "오류: GITHUB_TOKEN 환경 변수 또는 --token 옵션이 필요합니다.", err=True
        )
        raise typer.Exit(1)

    parsed_since: date | None = None
    parsed_until: date | None = None

    if since is not None:
        try:
            parsed_since = date.fromisoformat(since)
        except ValueError:
            print(
                f"오류: --since 날짜 형식이 잘못되었습니다. "
                f"YYYY-MM-DD 형식으로 입력하세요. (입력값: {since})",
                file=sys.stderr,
            )
            raise typer.Exit(1)

    if until is not None:
        try:
            parsed_until = date.fromisoformat(until)
        except ValueError:
            print(
                f"오류: --until 날짜 형식이 잘못되었습니다. "
                f"YYYY-MM-DD 형식으로 입력하세요. (입력값: {until})",
                file=sys.stderr,
            )
            raise typer.Exit(1)

    if (
        parsed_since is not None
        and parsed_until is not None
        and parsed_since > parsed_until
    ):
        print("오류: --since 날짜가 --until 날짜보다 늦습니다.", file=sys.stderr)
        raise typer.Exit(1)

    try:
        all_contributions = _load_or_fetch_contributions(
            repos,
            resolved_token,
            output,
            no_cache,
            parsed_since,
            parsed_until,
        )

    except ValueError as error:
        print(f"오류: {error}", file=sys.stderr)
        raise typer.Exit(1) from error

    except TransportQueryError as error:
        print(
            "오류: 저장소를 찾을 수 없습니다. 존재 여부와 권한을 확인하세요. "
            f"(Detail: {error})",
            file=sys.stderr,
        )
        raise typer.Exit(3) from error

    except TransportServerError as error:
        status_code = getattr(error, "code", None)

        if status_code in [403, 429]:
            print(
                "오류: GitHub API 호출 한도(Rate Limit)를 초과했습니다. "
                f"잠시 후 다시 시도하세요. (Status: {status_code})",
                file=sys.stderr,
            )
            raise typer.Exit(2) from error
        if status_code == 401:
            print(
                "오류: GitHub API 인증에 실패했습니다. "
                f"GITHUB_TOKEN을 확인하세요. (Status: {status_code})",
                file=sys.stderr,
            )
            raise typer.Exit(4) from error

        print(
            "오류: GitHub 서버 통신 중 HTTP 오류가 발생했습니다. "
            f"(Status: {status_code})",
            file=sys.stderr,
        )
        raise typer.Exit(1) from error

    except Exception as error:
        print(f"오류: {error}", file=sys.stderr)
        raise typer.Exit(1) from error

    # ── [이슈 구현] 쉼표 매핑 기반 5단계 정규화 파이프라인 수립 ──
    allowed_formats = ["csv", "txt", "html"]
    selected_formats = []

    if not format or not format.strip():
        # 인자가 주어지지 않았거나 공백만 왔을 때 stderr 가이드라인 출력 후 전체 가동
        print("안내: 형식을 지정하지 않았거나 유효한 형식이 없어 전체 형식(csv, txt, html)을 출력합니다.", file=sys.stderr)
        selected_formats = list(allowed_formats)
    else:
        # 1~4단계 정규화 처리: 쉼표 분할 ➔ 공백 제거 ➔ 소문자 정렬 ➔ 빈 문자열 탈락
        tokens = [t.strip().lower() for t in format.split(",") if t.strip()]
        
        # 5단계 정규화 처리: 원본 순서를 유지하며 중복만 깔끔하게 제거 (dict.fromkeys 치트키 활용)
        unique_tokens = list(dict.fromkeys(tokens))
        
        for token in unique_tokens:
            if token in allowed_formats:
                selected_formats.append(token)
            else:
                # 유효하지 않은 형식 포함 시 안내 스킵 및 필터링
                print(f"안내: '{token}'은(는) 지원하지 않는 형식입니다. 제외하고 남은 유효 형식을 사용합니다. (가능한 형식: csv, txt, html)", file=sys.stderr)
        
        # 선별 결과 남은 형식이 단 하나도 없으면 복구 조치 수행
        if not selected_formats:
            print("안내: 유효한 형식을 찾을 수 없어 전체 형식(csv, txt, html)을 모두 출력합니다.", file=sys.stderr)
            selected_formats = list(allowed_formats)

    try:
        if aggregate:
            scores = calculate_total_scores(all_contributions)
        else:
            scores = [
                score
                for repo_contributions in all_contributions
                for score in calculate_repository_scores(repo_contributions)
            ]

        results = [_score_to_result(score) for score in scores]
        
        # [핵심] 정규화 필터를 통과해 선별된 다중 포맷 배열을 순회하며 일괄 파일 생성
        for fmt in selected_formats:
            content = build_output(results, fmt)
            write_output(content, output, fmt)
            
    except Exception as error:
        print(f"출력 오류: {error}", file=sys.stderr)
        raise typer.Exit(1) from error


def cli() -> None:
    app()


if __name__ == "__main__":
    cli()