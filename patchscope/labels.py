"""Evaluation labels only. Never imported by retrieval or indexing."""
from pathlib import PurePosixPath
import shlex
import re


def source_path(path: str) -> bool:
    p = PurePosixPath(path)
    excluded = {'tests', 'test', 'testing', 'docs', 'doc', 'generated', 'vendor',
                'vendored', 'build', 'dist', '.git', 'examples', 'benchmarks'}
    return (not p.is_absolute() and not re.match(r'^[A-Za-z]:', path) and '..' not in p.parts and p.suffix == '.py'
            and not excluded.intersection(p.parts)
            and not p.name.startswith('test_') and not p.name.endswith('_test.py')
            and p.name not in {'setup.py', 'conftest.py', 'conf.py', 'versioneer.py'}
            and not any(part.startswith('_vendor') for part in p.parts))


def gold_paths(patch: str) -> list[str]:
    paths = set()
    old_left = new_left = 0
    for line in patch.splitlines():
        if line.startswith('diff --git '):
            old_left = new_left = 0
        hunk = re.match(r'^@@ -[0-9]+(?:,([0-9]+))? \+[0-9]+(?:,([0-9]+))? @@', line)
        if hunk:
            old_left = int(hunk.group(1) or 1)
            new_left = int(hunk.group(2) or 1)
            continue
        if old_left or new_left:
            if line.startswith(' '):
                old_left = max(0, old_left-1)
                new_left = max(0, new_left-1)
            elif line.startswith('-'):
                old_left = max(0, old_left-1)
            elif line.startswith('+'):
                new_left = max(0, new_left-1)
            continue
        if not line.startswith('+++ '):
            continue
        raw = line[4:].split('\t', 1)[0]
        if raw.startswith('"'):
            try:
                raw = shlex.split(raw)[0]
            except ValueError:
                continue
        raw = raw.replace('\\', '/')
        path = raw[2:] if raw.startswith('b/') else raw
        if source_path(path):
            paths.add(path)
    return sorted(paths)
