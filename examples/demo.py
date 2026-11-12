"""Credential-free local demo; not a benchmark result or a real issue."""
from pathlib import Path

from patchscope.index import build_index, tokenize
from patchscope.retrieve import BM25, rank


def main():
    root = Path(__file__).resolve().parents[1]
    files = {str(path.relative_to(root)): path.read_text()
             for path in sorted((root/'patchscope').glob('*.py'))}
    index = build_index(files)
    query = 'paired bootstrap confidence interval evaluation metrics'
    scores = BM25(index.tokens).scores(tokenize(query))
    predicted = rank(index.paths, scores, index.graph, budget=5)
    assert predicted and all(path in files for path in predicted)
    print('Local demonstration query:', query)
    for i, path in enumerate(predicted, 1):
        print(f'{i:2}. {path}')
    print('Demonstration only: no measured localization accuracy is implied.')


if __name__ == '__main__':
    main()
