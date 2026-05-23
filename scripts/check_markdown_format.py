from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only without project deps.
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
MAX_LINE_LENGTH = 500
FORBIDDEN_CHARS = {"\ufffc": "object replacement character"}


def fail(message: str) -> None:
    raise SystemExit(f"FORMAT CHECK FAILED: {message}")


def read_lines(relative_path: str) -> list[str]:
    path = ROOT / relative_path
    if not path.exists():
        fail(f"{relative_path} does not exist")
    return path.read_text(encoding="utf-8").splitlines()


def read_text(relative_path: str) -> str:
    path = ROOT / relative_path
    if not path.exists():
        fail(f"{relative_path} does not exist")
    return path.read_text(encoding="utf-8")


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


def check_no_forbidden_chars(relative_path: str) -> None:
    text = read_text(relative_path)
    for char, label in FORBIDDEN_CHARS.items():
        if char in text:
            fail(f"{relative_path} contains {label}")


def check_fenced_blocks(relative_path: str) -> None:
    fence_count = sum(1 for line in read_lines(relative_path) if line.startswith("```"))
    if fence_count % 2:
        fail(f"{relative_path} has unbalanced fenced code blocks")


def check_required_headings(relative_path: str, headings: list[str]) -> None:
    lines = set(read_lines(relative_path))
    missing = [heading for heading in headings if heading not in lines]
    if missing:
        fail(f"{relative_path} missing required headings: {missing}")


def check_readme() -> None:
    lines = read_lines("README.md")
    if len(lines) < 80:
        fail("README.md must have at least 80 lines")
    if lines[0] != "# Securities Month-End Reconciliation Agent":
        fail("README.md first line must be the project title")
    if "```mermaid" not in lines:
        fail("README.md must contain an independent ```mermaid fence line")
    if "| Metric | Value |" not in lines:
        fail("README.md must contain a multi-line Key Metrics table")
    check_required_headings(
        "README.md",
        [
            "## Demo",
            "## Key Metrics",
            "## Quick Demo Path",
            "## Architecture",
            "## Run Locally",
            "## Engineering Quality",
            "## Agent Workbench",
            "## Data Quality",
        ],
    )
    check_no_long_lines("README.md")
    check_no_forbidden_chars("README.md")
    check_fenced_blocks("README.md")


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
    if yaml is not None:
        data = yaml.safe_load(read_text(".github/workflows/tests.yml"))
        if not isinstance(data, dict):
            fail(".github/workflows/tests.yml is not a YAML mapping")
        if "jobs" not in data or "tests" not in data["jobs"]:
            fail(".github/workflows/tests.yml must contain jobs.tests")
        steps = data["jobs"]["tests"].get("steps", [])
        if not isinstance(steps, list) or len(steps) < 6:
            fail(".github/workflows/tests.yml must contain a multi-step tests job")
    check_no_long_lines(".github/workflows/tests.yml")
    check_no_forbidden_chars(".github/workflows/tests.yml")


def main() -> None:
    check_readme()
    check_workflow()
    check_min_lines("docs/DESIGN_DECISIONS.md", 30)
    check_min_lines("docs/TESTING_AND_QUALITY.md", 30)
    check_no_long_lines("docs/DESIGN_DECISIONS.md")
    check_no_long_lines("docs/TESTING_AND_QUALITY.md")
    check_no_forbidden_chars("docs/DESIGN_DECISIONS.md")
    check_no_forbidden_chars("docs/TESTING_AND_QUALITY.md")
    check_fenced_blocks("docs/TESTING_AND_QUALITY.md")
    print("markdown and workflow format ok")


if __name__ == "__main__":
    main()
