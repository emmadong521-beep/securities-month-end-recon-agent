from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAX_LINE_LENGTH = 500


def fail(message: str) -> None:
    raise SystemExit(f"FORMAT CHECK FAILED: {message}")


def read_lines(relative_path: str) -> list[str]:
    path = ROOT / relative_path
    if not path.exists():
        fail(f"{relative_path} does not exist")
    return path.read_text(encoding="utf-8").splitlines()


def check_min_lines(relative_path: str, minimum: int) -> None:
    lines = read_lines(relative_path)
    if len(lines) < minimum:
        fail(f"{relative_path} has {len(lines)} lines; expected at least {minimum}")


def check_no_long_lines(relative_path: str) -> None:
    for line_no, line in enumerate(read_lines(relative_path), start=1):
        if len(line) > MAX_LINE_LENGTH:
            fail(
                f"{relative_path}:{line_no} has {len(line)} characters; "
                f"expected at most {MAX_LINE_LENGTH}"
            )


def check_readme() -> None:
    lines = read_lines("README.md")
    if len(lines) < 80:
        fail("README.md must have at least 80 lines")
    if "```mermaid" not in lines:
        fail("README.md must contain an independent ```mermaid fence line")
    check_no_long_lines("README.md")


def check_workflow() -> None:
    lines = read_lines(".github/workflows/tests.yml")
    if len(lines) < 40:
        fail(".github/workflows/tests.yml must have at least 40 lines")
    if lines[0] != "name: tests":
        fail(".github/workflows/tests.yml must start with 'name: tests'")
    if not any(line.startswith("  tests:") for line in lines):
        fail(".github/workflows/tests.yml must define a tests job")
    if not any("uses: actions/checkout@v4" in line for line in lines):
        fail(".github/workflows/tests.yml must use actions/checkout@v4")
    check_no_long_lines(".github/workflows/tests.yml")


def main() -> None:
    check_readme()
    check_workflow()
    check_min_lines("docs/DESIGN_DECISIONS.md", 30)
    check_min_lines("docs/TESTING_AND_QUALITY.md", 30)
    check_no_long_lines("docs/DESIGN_DECISIONS.md")
    check_no_long_lines("docs/TESTING_AND_QUALITY.md")
    print("markdown and workflow format ok")


if __name__ == "__main__":
    main()
