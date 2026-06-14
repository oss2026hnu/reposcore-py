# reposcore-py

A CLI for scoring student participation in an open-source class repo, implemented in Python using GraphQL.

## Quick Start

처음 도구를 사용하는 분들을 위한 구체적인 실행 예시입니다. 아래 명령어들을 복사하여 터미널에서 바로 테스트해 볼 수 있습니다.

### 실행 전 준비

`reposcore-py`는 GitHub GraphQL API를 사용하므로 GitHub Personal Access Token이 필요합니다.

토큰은 `GITHUB_TOKEN` 환경 변수로 설정할 수 있습니다.

```bash
export GITHUB_TOKEN=YOUR_GITHUB_TOKEN
```

또는 실행할 때 `--token` 옵션으로 직접 전달할 수도 있습니다.

```bash
reposcore oss2026hnu/reposcore-py --token YOUR_GITHUB_TOKEN
```

### 1. 단일 저장소 조회
가장 기본적인 형태로, 하나의 저장소에 대한 기여자 점수를 조회합니다.
```bash
reposcore oss2026hnu/reposcore-py
```

### 2. 여러 저장소 조회
공백으로 구분하여 여러 저장소 경로를 입력하면, 각 저장소의 결과를 한 번에 조회할 수 있습니다.
```bash
reposcore oss2026hnu/reposcore-py oss2026hnu/reposcore-cs oss2026hnu/reposcore-ts
```

### 3. `--format` 옵션을 사용한 출력 형식 지정
`-f` 또는 `--format` 옵션을 사용하여 출력 포맷을 지정합니다. (기본값: txt)
```bash
# CSV 형식으로 출력
reposcore oss2026hnu/reposcore-py --format csv

# HTML 형식으로 출력
reposcore oss2026hnu/reposcore-py --format html
```

### 4. `--output` 옵션을 사용한 파일 저장 위치 지정
`-o` 또는 `--output` 옵션을 사용해 결과를 터미널에 출력하는 대신 지정한 디렉터리 경로에 파일로 저장합니다.
```bash
reposcore oss2026hnu/reposcore-py --format html --output ./result
```

## Synopsis

```text
{{ SYNOPSIS }}
```