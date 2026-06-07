# Typer 사용 가이드

이 문서는 reposcore-py 프로젝트에서 CLI를 구성하는 데 사용하는 Typer 라이브러리의 기본 사용 방법을 정리합니다.

## 목차

- [Typer 소개](#typer-소개)
- [설치](#설치)
- [기본 구조](#기본-구조)
- [현재 프로젝트 적용 예시](#현재-프로젝트-적용-예시)
- [--help 자동 생성](#--help-자동-생성)
- [참고 링크](#참고-링크)

---

## Typer 소개

Typer는 Python 타입 힌트를 기반으로 CLI(Command Line Interface)를 쉽게 만들 수 있는 라이브러리입니다.

타입 힌트를 그대로 활용하기 때문에 별도의 인자 파싱 코드 없이도 명령줄 인자와 옵션을 정의할 수 있습니다.

---

## 설치

```bash
pip install typer
```

pyproject.toml의 dependencies에 이미 포함되어 있으므로 아래 명령으로 한 번에 설치할 수 있습니다.

```bash
pip install -e .
```

---

## 기본 구조

### typer.Typer()

앱 인스턴스를 생성합니다. `help` 매개변수로 CLI 전체 설명을 지정할 수 있습니다.

```python
import typer

app = typer.Typer(help="reposcore-py CLI")
```

### @app.command()

함수를 CLI 커맨드로 등록합니다.

```python
@app.command()
def main() -> None:
    typer.echo("Hello!")
```

### typer.Argument

위치 인자를 정의합니다. 반드시 입력해야 하는 값에 사용합니다.

```python
from typing import Annotated

def main(
    name: Annotated[str, typer.Argument(help="이름을 입력합니다.")]
) -> None:
    typer.echo(f"Hello, {name}")
```

### typer.Option

선택적 옵션을 정의합니다. `--옵션명` 형식으로 전달합니다.

```python
def main(
    format: Annotated[str, typer.Option("--format", "-f", help="출력 형식")] = "txt"
) -> None:
    typer.echo(f"format: {format}")
```

---

## 현재 프로젝트 적용 예시

`main.py`에서는 다음과 같이 Typer를 사용합니다.

```python
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
) -> None:
    ...
```

- `repos`: 하나 이상의 저장소 경로를 위치 인자로 받습니다.
- `--format` / `-f`: 출력 파일 형식을 지정합니다. 기본값은 `txt`입니다.
- `--output` / `-o`: 결과를 저장할 디렉터리 경로를 지정합니다.

---

## --help 자동 생성

Typer는 타입 힌트와 `help` 매개변수를 바탕으로 `--help` 옵션을 자동으로 생성합니다.

```bash
python main.py --help
```

또는

```bash
reposcore --help
```

---

## 참고 링크

- [Typer 공식 문서](https://typer.tiangolo.com)
