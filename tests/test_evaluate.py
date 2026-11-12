import csv
import json

import networkx as nx
import numpy as np
import pytest

from patchscope.evaluate import metrics, paired_bootstrap, evaluate_case, run_evaluation
from patchscope.index import build_index


def test_metrics_multiple_gold_and_truncation():
    result = metrics(['wrong', 'a', 'b'], ['a', 'b'])
    assert result == dict(hit1=0., hit5=1., hit10=1., mrr10=.5, recall5=1., recall10=1.)
    assert metrics(['x']*10+['a'], ['a'])['mrr10'] == 0
    with pytest.raises(ValueError):
        metrics(['x'], [])


def test_paired_bootstrap_known_constant_difference():
    result = paired_bootstrap(np.ones(20), np.zeros(20), seed=2026)
    assert result == dict(n=20, difference_pp=100., lower_pp=100., upper_pp=100.)
    with pytest.raises(ValueError):
        paired_bootstrap(np.ones(3), np.zeros(2))


def test_evaluate_case_same_cohort_pool_and_gold_blind_index():
    files = {'pkg/a.py': 'def apple(): pass', 'pkg/b.py': 'from .a import apple'}
    index = build_index(files)
    issue = dict(instance_id='a__b-1', repo='a/b', base_commit='a'*40,
                 problem_statement='apple in pkg/a.py fails', patch='FUTURE_SECRET',
                 test_patch='FUTURE_TEST_SECRET', hints_text='FUTURE_HINT')
    rows, audit = evaluate_case(issue, index, ['pkg/a.py'], 2026)
    assert len(rows) == 12
    assert {r['condition'] for r in rows} == {'raw', 'masked'}
    assert {r['method'] for r in rows} == {'bm25', 'real', 'rewired', 'edge_drop'}
    assert all(set(json.loads(r['predicted_paths'])) == set(files) for r in rows)
    assert len([r for r in rows if r['method'] == 'rewired']) == 6
    assert audit['mask_spans']
    changed = {**issue, 'patch': 'DIFFERENT', 'test_patch': 'DIFFERENT', 'hints_text': 'DIFFERENT'}
    again, _ = evaluate_case(changed, index, ['pkg/a.py'], 2026)
    assert [r['predicted_paths'] for r in rows] == [r['predicted_paths'] for r in again]


def test_end_to_end_fixture_exclusions_and_immutable_outputs(tmp_path):
    from patchscope.data import write_json
    rows = [dict(instance_id=f'a__b-{i}', repo='a/b', base_commit='a'*40,
                 problem_statement='apple', patch='+++ b/pkg/a.py' if i == 0 else '+++ b/new.py') for i in range(2)]
    def provider(repo, commit, cache):
        return {'pkg/a.py': 'def apple(): pass'}, {'commit': commit}
    result = run_evaluation(rows, 'revision', 2, 2026, tmp_path, tmp_path/'cache', 'test', provider)
    assert result['eligible'] == 1 and result['excluded'] == 1
    cases = list(csv.DictReader((tmp_path/'per_instance.csv').open()))
    assert len(cases) == 12
    assert len(list(csv.DictReader((tmp_path/'exclusions.csv').open()))) == 1
    with pytest.raises(FileExistsError):
        run_evaluation(rows, 'revision', 2, 2026, tmp_path, tmp_path/'cache', 'test', provider)
