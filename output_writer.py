from __future__ import annotations

import csv
from html import escape
from io import StringIO
from pathlib import Path
from typing import Literal

from tabulate import tabulate

from calc_score import UserScore

OutputFormat = Literal["csv", "txt", "html"]


def normalize_output_format(output_format: str) -> OutputFormat:
    normalized = output_format.lower()

    if normalized not in ("csv", "txt", "html"):
        raise ValueError("출력 형식은 csv, txt, html 중 하나여야 합니다.")

    return normalized  # type: ignore[return-value]


def build_txt_output(scores: list[UserScore]) -> str:
    headers = [
        "user",
        "feature_bug_pr",
        "doc_pr",
        "typo_pr",
        "feature_bug_issue",
        "doc_issue",
        "total_score",
    ]

    rows = [
        [
            score.contribution.user,
            score.contribution.feature_bug_pr_count,
            score.contribution.doc_pr_count,
            score.contribution.typo_pr_count,
            score.contribution.feature_bug_issue_count,
            score.contribution.doc_issue_count,
            score.score,
        ]
        for score in scores
    ]

    return tabulate(rows, headers=headers)


def build_csv_output(scores: list[UserScore]) -> str:
    headers = [
        "user",
        "feature_bug_pr",
        "doc_pr",
        "typo_pr",
        "feature_bug_issue",
        "doc_issue",
        "total_score",
    ]

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)

    for score in scores:
        writer.writerow([
            score.contribution.user,
            score.contribution.feature_bug_pr_count,
            score.contribution.doc_pr_count,
            score.contribution.typo_pr_count,
            score.contribution.feature_bug_issue_count,
            score.contribution.doc_issue_count,
            score.score,
        ])

    return output.getvalue().strip()


def build_html_output(scores: list[UserScore]) -> str:
    html_rows = []
    for score in scores:
        c = score.contribution
        html_rows.append(
            "      <tr>"
            f"<td>{escape(c.user)}</td>"
            f"<td>{c.feature_bug_pr_count}</td>"
            f"<td>{c.doc_pr_count}</td>"
            f"<td>{c.typo_pr_count}</td>"
            f"<td>{c.feature_bug_issue_count}</td>"
            f"<td>{c.doc_issue_count}</td>"
            f"<td>{score.score}</td>"
            "</tr>"
        )

    rows = "\n".join(html_rows)

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>reposcore-py result</title>
</head>
<body>
  <table>
    <thead>
      <tr>
        <th>user</th>
        <th>feature_bug_pr</th>
        <th>doc_pr</th>
        <th>typo_pr</th>
        <th>feature_bug_issue</th>
        <th>doc_issue</th>
        <th>total_score</th>
      </tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
</body>
</html>"""


def build_output(scores: list[UserScore], output_format: str) -> str:
    normalized_format = normalize_output_format(output_format)

    if normalized_format == "csv":
        return build_csv_output(scores)

    if normalized_format == "html":
        return build_html_output(scores)

    return build_txt_output(scores)


def write_output(
    content: str,
    output_dir: str | None,
    output_format: str,
) -> Path | None:
    if output_dir is None:
        print(content)
        return None

    normalized_format = normalize_output_format(output_format)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    result_path = output_path / f"results.{normalized_format}"
    result_path.write_text(content, encoding="utf-8")

    return result_path