from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def fail(msg):
    print(f'FORMAT CHECK FAILED: {msg}')
    sys.exit(1)

readme = ROOT / 'README.md'
workflow = ROOT / '.github/workflows/tests.yml'
boundary = ROOT / 'docs/CAPABILITY_BOUNDARY.md'

readme_lines = readme.read_text(encoding='utf-8').splitlines()
workflow_lines = workflow.read_text(encoding='utf-8').splitlines()
boundary_lines = boundary.read_text(encoding='utf-8').splitlines()

if len(readme_lines) < 80:
    fail(f'README.md has too few lines: {len(readme_lines)}')

if '| Metric | Value |' not in readme_lines:
    fail('README.md missing standalone Key Metrics table header')

if '```mermaid' not in readme_lines:
    fail('README.md missing standalone mermaid fence')

if any('```mermaid flowchart' in line for line in readme_lines):
    fail('README.md has compressed mermaid fence and flowchart on one line')

if any(line.startswith('    flowchart LR') or line.startswith('    flowchart TD') for line in readme_lines):
    fail('README.md appears to contain indented mermaid code instead of fenced mermaid block')

if len(workflow_lines) < 40:
    fail(f'workflow has too few lines: {len(workflow_lines)}')

for required in ['name: tests', 'jobs:', '  tests:', '    runs-on: ubuntu-latest', '    steps:']:
    if required not in workflow_lines:
        fail(f'workflow missing line: {required}')

boundary_header = '| Dimension | Traditional finance systems | BI / dashboards | LLM-only tools | This PoC |'
if boundary_header not in boundary_lines:
    fail('CAPABILITY_BOUNDARY.md missing standalone comparison table header')

for path in [readme, workflow, boundary]:
    long_lines = [idx + 1 for idx, line in enumerate(path.read_text(encoding='utf-8').splitlines()) if len(line) > 500]
    if long_lines:
        fail(f'{path} has long lines > 500 chars at {long_lines[:10]}')

print('Markdown/YAML format check passed.')
