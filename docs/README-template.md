# reposcore-py

A CLI for scoring student participation in an open-source class repo, implemented in Python using GraphQL

## Quick Start

### 1. 사전 준비

GitHub GraphQL API 호출을 위해 `GITHUB_TOKEN` 환경 변수가 필요합니다.

```bash
# Codespaces 환경에서는 GitHub Codespaces Secret으로 설정 권장
# 로컬 환경에서는 아래 명령어로 설정
export GITHUB_TOKEN=ghp_xxxxx
```

### 2. 의존성 설치

```bash
python -m pip install -e .
```

### 3. 기본 실행

```bash
reposcore oss2026hnu/reposcore-py
```

### 4. 여러 저장소를 인자로 넘기는 실행

```bash
reposcore oss2026hnu/reposcore-py oss2026hnu/reposcore-cs
```

### 5. 출력 형식 지정

```bash
reposcore oss2026hnu/reposcore-py --format csv
reposcore oss2026hnu/reposcore-py --format html
```

### 6. 출력 경로 지정

```bash
reposcore oss2026hnu/reposcore-py --format html --output ./result
```

## Synopsis

```text
Usage: reposcore [OPTIONS] REPOS...

 Fetch basic repository counts from GitHub GraphQL API.

Arguments:
  repos    REPOS...  조회할 GitHub 저장소 경로입니다.
                     예: owner/repo1 owner/repo2
                     [required]

Options:
  --format  -f  TEXT  출력 파일 형식을 지정합니다. (csv | txt | html)
                      [default: txt]
  --output  -o  TEXT  결과를 저장할 출력 디렉터리 경로입니다.
                      예: ./result
  --help              Show this message and exit.
```

# 문서 목록

{{ DOCS_LIST }}