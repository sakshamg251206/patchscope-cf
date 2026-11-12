"""Independent saved-artifact sanity checks; run after evaluate and report."""
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

from patchscope.data import snapshot
from patchscope.evaluate import metrics
from patchscope.report import summarize


def main():
    root = Path(sys.argv[1] if len(sys.argv)>1 else 'results')
    config = json.loads((root/'experiment_config.json').read_text())
    assert config['completed']
    rows = list(csv.DictReader((root/'per_instance.csv').open()))
    audits = json.loads((root/'audit.json').read_text())
    expected = {a['instance_id'] for a in audits}
    assert len(expected) == config['eligible']
    assert len(rows) == config['eligible']*12
    groups = {}
    for row in rows:
        key = (row['instance_id'],row['condition'],row['method'])
        groups.setdefault(key,[]).append(row)
        gold, predicted = json.loads(row['gold_paths']), json.loads(row['predicted_paths'])
        assert len(predicted) == min(int(row['candidate_budget']),int(row['num_files']))
        assert len(predicted) == len(set(predicted))
        assert all(np.isclose(float(row[k]),v) for k,v in metrics(predicted,gold).items())
    for issue in expected:
        audit = next(a for a in audits if a['instance_id']==issue)
        files, source = snapshot(audit['repo'],audit['base_commit'],Path('data/cache'))
        assert audit['source']['source_sha256']==source['source_sha256']
        for condition in ['raw','masked']:
            baseline=groups[(issue,condition,'bm25')][0]
            pool=set(json.loads(baseline['predicted_paths']))
            for method in ['bm25','real','rewired','edge_drop']:
                cases=groups[(issue,condition,method)]
                expected_seeds=([0] if method in ['bm25','real'] else
                                config['rewiring_seeds'] if method=='rewired' else [config['seed']])
                assert sorted(int(c['seed']) for c in cases)==expected_seeds
                for row in cases:
                    assert row['base_commit']==audit['base_commit']
                    assert set(json.loads(row['predicted_paths']))==pool
                    assert pool <= set(files)
                    assert set(json.loads(row['gold_paths'])) <= set(files)
        for control in audit['rewiring']:
            assert control['successful_swaps'] <= control['requested_swaps']
    saved=list(csv.DictReader((root/'summary.csv').open()))
    actual=summarize(rows)
    assert len(saved)==len(actual)
    for left,right in zip(saved,actual):
        for key,value in right.items():
            assert left[key]==value if isinstance(value,str) else np.isclose(float(left[key]),value)
    exclusions=list(csv.DictReader((root/'exclusions.csv').open()))
    assert len(exclusions)==config['excluded']
    assert config['eligible']+config['excluded']==config['requested']
    print(f"VERIFIED: {config['eligible']} issues, {len(config['repos'])} repos, {len(rows)} rows; metrics, pairing, seeds, pools, snapshots and summaries consistent.")


if __name__=='__main__':
    main()
