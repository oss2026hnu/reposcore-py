from __future__ import annotations
import os
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from pydantic import BaseModel
from calc_score import UserContributionCounts
from typing import List, Tuple


# ── Pydantic 모델 정의 ──────────────────────────────────────────

class Author(BaseModel):
    login: str

class Label(BaseModel):
    name: str

class LabelConnection(BaseModel):
    nodes: list[Label]

class IssueNode(BaseModel):
    author: Author | None
    labels: LabelConnection

class PRNode(BaseModel):
    author: Author | None
    labels: LabelConnection

class PageInfo(BaseModel):
    hasNextPage: bool
    endCursor: str | None

class IssueConnection(BaseModel):
    pageInfo: PageInfo
    nodes: list[IssueNode]

class PRConnection(BaseModel):
    pageInfo: PageInfo
    nodes: list[PRNode]

class IssueRepository(BaseModel):
    issues: IssueConnection

class PRRepository(BaseModel):
    pullRequests: PRConnection

class IssueResponse(BaseModel):
    repository: IssueRepository

class PRResponse(BaseModel):
    repository: PRRepository


# 추가 Pydantic 모델: 이슈와 댓글 정보를 포함
class CommentAuthor(BaseModel):
    login: str | None

class CommentNode(BaseModel):
    author: CommentAuthor | None
    bodyText: str | None
    createdAt: str | None

class CommentConnection(BaseModel):
    nodes: list[CommentNode]

class IssueClaimNode(BaseModel):
    number: int
    title: str
    url: str
    author: Author | None
    labels: LabelConnection
    comments: CommentConnection

class IssueClaimConnection(BaseModel):
    pageInfo: PageInfo
    nodes: list[IssueClaimNode]

class IssueClaimRepository(BaseModel):
    issues: IssueClaimConnection

class IssueClaimResponse(BaseModel):
    repository: IssueClaimRepository


# ── 클라이언트 생성 ──────────────────────────────────────────────

def create_client(token: str) -> Client:
    transport = RequestsHTTPTransport(
        url="https://api.github.com/graphql",
        headers={"Authorization": f"Bearer {token}"},
        verify=True,
        retries=3,
    )
    return Client(transport=transport, fetch_schema_from_transport=False)


# ── 기여 데이터 수집 ──────────────────────────────────────────────

def fetch_contributions(repository: str, token: str) -> list[UserContributionCounts]:
    owner, name = repository.split("/", maxsplit=1)
    client = create_client(token)
    contributions: dict[str, UserContributionCounts] = {}

    # 이슈 수집
    issue_query = gql("""
    query($owner: String!, $name: String!, $after: String) {
        repository(owner: $owner, name: $name) {
            issues(first: 100, after: $after, states: [OPEN, CLOSED]) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    author { login }
                    labels(first: 10) {
                        nodes { name }
                    }
                }
            }
        }
    }
    """)

    cursor = None
    while True:
        with client as session:
            result = session.execute(issue_query, variable_values={
                "owner": owner,
                "name": name,
                "after": cursor,
            })

        response = IssueResponse.model_validate(result)
        issues = response.repository.issues

        for node in issues.nodes:
            if node.author is None:
                continue
            user = node.author.login
            labels = [label.name.lower() for label in node.labels.nodes]

            if user not in contributions:
                contributions[user] = UserContributionCounts(user=user)
            if "documentation" in labels:
                contributions[user].doc_issue_count += 1
            elif "bug" in labels or "enhancement" in labels:
                contributions[user].feature_bug_issue_count += 1

        if not issues.pageInfo.hasNextPage:
            break
        cursor = issues.pageInfo.endCursor

    # PR 수집
    pr_query = gql("""
    query($owner: String!, $name: String!, $after: String) {
        repository(owner: $owner, name: $name) {
            pullRequests(first: 100, after: $after, states: [MERGED]) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    author { login }
                    labels(first: 10) {
                        nodes { name }
                    }
                }
            }
        }
    }
    """)

    cursor = None
    while True:
        with client as session:
            result = session.execute(pr_query, variable_values={
                "owner": owner,
                "name": name,
                "after": cursor,
            })

        response = PRResponse.model_validate(result)
        prs = response.repository.pullRequests

        for node in prs.nodes:
            if node.author is None:
                continue
            user = node.author.login
            labels = [label.name.lower() for label in node.labels.nodes]

            if user not in contributions:
                contributions[user] = UserContributionCounts(user=user)
            if "documentation" in labels:
                contributions[user].doc_pr_count += 1
            elif "typo" in labels:
                contributions[user].typo_pr_count += 1
            elif "bug" in labels or "enhancement" in labels:
                contributions[user].feature_bug_pr_count += 1

        if not prs.pageInfo.hasNextPage:
            break
        cursor = prs.pageInfo.endCursor

    return list(contributions.values())


def fetch_open_issue_claims(repository: str, token: str, keywords: List[str] | None = None) -> Tuple[list, list]:
    """Open 이슈와 최근 댓글을 조회하여 선점 키워드 매칭 결과를 반환합니다.

    반환값: (claimed_issues, unclaimed_issues)
    claimed_issues: list of dict {number, title, url, author, labels, matched_comment_author, matched_keyword, matched_comment_body, matched_comment_created_at}
    unclaimed_issues: list of dict {number, title, url, author, labels}
    """
    owner, name = repository.split("/", maxsplit=1)
    client = create_client(token)

    issue_claim_query = gql("""
    query($owner: String!, $name: String!, $after: String) {
        repository(owner: $owner, name: $name) {
            issues(first: 100, after: $after, states: OPEN) {
                pageInfo { hasNextPage endCursor }
                nodes {
                    number
                    title
                    url
                    author { login }
                    labels(first: 10) { nodes { name } }
                    comments(first: 10) {
                        nodes { author { login } bodyText createdAt }
                    }
                }
            }
        }
    }
    """)

    cursor = None
    claimed: list = []
    unclaimed: list = []

    # 준비된 키워드 소문자 형태
    if keywords:
        lowered_keywords = [k.lower() for k in keywords]
    else:
        lowered_keywords = []

    while True:
        with client as session:
            result = session.execute(issue_claim_query, variable_values={
                "owner": owner,
                "name": name,
                "after": cursor,
            })

        response = IssueClaimResponse.model_validate(result)
        issues = response.repository.issues

        for node in issues.nodes:
            labels = [label.name for label in node.labels.nodes]

            issue_summary = {
                "number": node.number,
                "title": node.title,
                "url": node.url,
                "author": node.author.login if node.author is not None else None,
                "labels": labels,
            }

            matched = False
            # comments는 최신 순으로 가져오므로 첫 매칭을 선점으로 간주
            for c in node.comments.nodes:
                body = (c.bodyText or "").lower()
                for kw in lowered_keywords:
                    if kw and kw in body:
                        claimed.append({
                            **issue_summary,
                            "matched_comment_author": c.author.login if c.author is not None else None,
                            "matched_comment_body": c.bodyText,
                            "matched_comment_created_at": c.createdAt,
                            "matched_keyword": kw,
                        })
                        matched = True
                        break
                if matched:
                    break

            if not matched:
                unclaimed.append(issue_summary)

        if not issues.pageInfo.hasNextPage:
            break
        cursor = issues.pageInfo.endCursor

    return claimed, unclaimed