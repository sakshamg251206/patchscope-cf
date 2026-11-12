"""Label-informed diagnostic only, never deployment query preprocessing."""
from collections import Counter
from pathlib import PurePosixPath
import re
from .index import module_name


def mask_query(text: str, gold: list[str], indexed_paths: list[str]):
    counts = Counter(PurePosixPath(path).stem for path in indexed_paths)
    patterns = set()
    for path in gold:
        patterns.add(path)
        patterns.add(path.replace('/', '\\'))
        patterns.add(path[:-3].replace('/', '.'))
        module = module_name(path).removesuffix('.__init__')
        if '.' in module or len(module) >= 4:
            patterns.add(module)
        basename = PurePosixPath(path).name
        stem = PurePosixPath(path).stem
        if counts[stem] == 1 and len(stem) >= 4 and stem not in {'__init__', 'main', 'base', 'utils', 'core', 'test'}:
            patterns.update([basename, stem])
    if not patterns:
        return text, []
    expression = r'(?<![\w])(?:' + '|'.join(re.escape(p) for p in sorted(patterns, key=lambda p: (-len(p), p))) + r')(?![\w])'
    matches = list(re.finditer(expression, text, flags=re.IGNORECASE))
    spans = [dict(start=m.start(), end=m.end(), text=m.group()) for m in matches]
    masked = re.sub(expression, ' ', text, flags=re.IGNORECASE)
    assert not re.search(expression, masked, flags=re.IGNORECASE)
    return masked, spans
